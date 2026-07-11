from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.db.models import (
    AIDomainAnalysis,
    CoachDomainSlot,
    CoachEvidenceBaseline,
    CoachMissionProposal,
    DemoParseArtifact,
    Match,
    MetricSnapshot,
    SteamAccount,
)
from app.services.ai_coach import configured_model_route_identity, invoke_configured_structured_model
from app.services.coach_domain_model import CANONICAL_COACH_DOMAINS, require_canonical_domain
from app.services.metrics.snapshots import upsert_metric_snapshot
from app.services.mission_domain import list_active_coach_missions, mission_domain_key, serialize_coach_mission
from app.services.shared.runtime_contracts import metric_registry_contract

BASELINE_VERSION = "coach-domain-baseline-v1"
TEMPORAL_SEMANTIC_VERSION = "3.1.0"
TEMPORAL_IMPLEMENTATION_VERSION = "temporal-survival-v1.0.0"
EVIDENCE_SCHEMA_VERSION = "coach-domain-evidence-v1"
OUTPUT_SCHEMA_VERSION = "ai-domain-hypothesis-v1"
PROMPT_VERSION = "two-domain-hypothesis-v1"
MODEL_MAX_ATTEMPTS = 2
DOMAIN_SLOT_STATUSES = {
    "insufficient_baseline",
    "analyzing",
    "proposal_ready",
    "no_material_problem",
    "analysis_failed",
    "proposal_superseded",
    "active",
    "paused",
    "completed",
}
ANALYSIS_STATUSES = {"supported_hypothesis", "no_material_problem", "insufficient_evidence"}
ALLOWED_VERSIONS = {"3.0.0", TEMPORAL_SEMANTIC_VERSION}
WINDOW_MIN, WINDOW_MAX = 3, 5
PROMPT_PATHS = {
    "impact_leak": BASE_DIR / "app/contracts/coach/prompts/impact_leak_hypothesis_prompt.md",
    "bad_fight_selection": BASE_DIR / "app/contracts/coach/prompts/bad_fight_selection_hypothesis_prompt.md",
}
SCHEMA_PATH = BASE_DIR / "app/contracts/coach/schemas/ai-domain-hypothesis.schema.json"
FORBIDDEN_CLAIMS = re.compile(
    r"\b(exact (angle|position|rotation|spacing)|crosshair placement|economy mistake|clutch decision)\b",
    re.IGNORECASE,
)
METRIC_DIRECTIONS = {
    "average_survival_time_seconds": "higher_is_better",
    "median_survival_time_seconds": "higher_is_better",
    "p25_survival_time_seconds": "higher_is_better",
    "early_death_rate_before_45_seconds": "lower_is_better",
    "average_death_time_seconds": "higher_is_better",
    "average_death_time_t_side_seconds": "higher_is_better",
    "average_death_time_ct_side_seconds": "higher_is_better",
    "opening_death_rate": "lower_is_better",
    "opening_deaths": "lower_is_better",
    "opening_duel_losses": "lower_is_better",
    "opening_duel_win_rate": "higher_is_better",
    "untraded_death_rate": "lower_is_better",
    "untraded_deaths": "lower_is_better",
    "traded_death_rate": "higher_is_better",
    "trade_success_rate": "higher_is_better",
    "survival_rate": "higher_is_better",
    "kast": "higher_is_better",
    "adr": "stay_above_guardrail",
    "kills_per_round": "stay_above_guardrail",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def temporal_survival_metrics(evidence: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    identity = dict(evidence.get("identity") or {})
    owner = str(identity.get("owner_steamid") or "")
    rounds = [dict(row) for row in (evidence.get("phase") or {}).get("rounds", [])]
    participation = dict(evidence.get("participation") or {})
    roster = {str(value) for value in participation.get("roster_steamids", [])}
    spawns = [dict(row) for row in participation.get("owner_spawns", [])]
    disconnects = [dict(row) for row in participation.get("owner_disconnects", [])]
    connects = [dict(row) for row in participation.get("owner_connects", [])]
    team_events = [dict(row) for row in participation.get("owner_team_events", [])]
    deaths = [dict(row) for row in (evidence.get("events") or {}).get("deaths", [])]
    owner_deaths = {int(row["round_number"]): row for row in deaths if row.get("victim_steamid") == owner}
    ledger: list[dict[str, Any]] = []
    for row in rounds:
        number, start, end = int(row["round_number"]), int(row["start_tick"]), int(row["end_tick"])
        disconnected = [r for r in disconnects if start <= int(r.get("tick") or -1) <= end]
        reconnected = [r for r in connects if start <= int(r.get("tick") or -1) <= end]
        side_rows = [
            r for r in [*spawns, *team_events] if r.get("round_number") == number and int(r.get("team") or 0) in {2, 3}
        ]
        side = "T" if side_rows and int(side_rows[0]["team"]) == 2 else "CT" if side_rows else None
        present = owner in roster or any(r.get("round_number") == number for r in spawns)
        complete = present and side is not None and not disconnected
        death = owner_deaths.get(number)
        death_tick = int(death["tick"]) if death and death.get("tick") is not None else None
        accepted_death = death_tick is not None and start <= death_tick <= end
        boundary = min(death_tick, end) if accepted_death else end
        outcome = (
            "not_participating"
            if not present
            else "incomplete_round"
            if not complete
            else "died"
            if accepted_death
            else "survived"
        )
        ledger.append(
            {
                "round_number": number,
                "phase": row.get("phase") or ("overtime" if number >= 24 else "regulation"),
                "side": side,
                "outcome": outcome,
                "participated": complete,
                "start_tick": start,
                "boundary_tick": boundary,
                "survival_time_seconds": round((boundary - start) / 64.0, 3) if complete else None,
                "disconnect": bool(disconnected),
                "reconnect": bool(reconnected),
                "post_round_death_excluded": bool(death_tick is not None and death_tick > end),
            }
        )
    accepted = [r for r in ledger if r["participated"]]
    times = [float(r["survival_time_seconds"]) for r in accepted]
    died = [r for r in accepted if r["outcome"] == "died"]
    death_times = [float(r["survival_time_seconds"]) for r in died]
    side_deaths = {side: [float(r["survival_time_seconds"]) for r in died if r["side"] == side] for side in ("T", "CT")}
    if not times:
        raise ValueError("temporal_survival_no_complete_participated_rounds")
    metrics = {
        "survival_time_seconds_per_participated_round": times,
        "average_survival_time_seconds": round(statistics.fmean(times), 3),
        "median_survival_time_seconds": round(statistics.median(times), 3),
        "p25_survival_time_seconds": round(_percentile(times, 0.25), 3),
        "early_death_rate_before_45_seconds": round(sum(value < 45 for value in death_times) / len(times), 3),
        "average_death_time_seconds": round(statistics.fmean(death_times), 3) if death_times else None,
        "average_death_time_t_side_seconds": round(statistics.fmean(side_deaths["T"]), 3) if side_deaths["T"] else None,
        "average_death_time_ct_side_seconds": round(statistics.fmean(side_deaths["CT"]), 3)
        if side_deaths["CT"]
        else None,
    }
    return metrics, ledger


def store_temporal_snapshot(
    db: Session, *, owner_user_id: int, base_snapshot: MetricSnapshot, artifact_path: Path
) -> MetricSnapshot:
    evidence = json.loads(artifact_path.read_text(encoding="utf-8"))
    metrics, ledger = temporal_survival_metrics(evidence)
    confidence = {
        "confidence": "high",
        "metrics": {
            key: {
                "level": "high" if value is not None else "unavailable",
                "usable_for_insights": value is not None,
                "usable_for_missions": value is not None,
                "hard_recommendation_eligible": value is not None,
                "reason_codes": ["accepted_round_presence_death_boundary_v1"] if value is not None else ["zero_deaths"],
            }
            for key, value in metrics.items()
            if key != "survival_time_seconds_per_participated_round"
        },
    }
    metadata = {
        "schema_version": "temporal-survival-evidence-v1",
        "contract_version": TEMPORAL_SEMANTIC_VERSION,
        "source_event_set_id": base_snapshot.source_event_set_id,
        "source_parser_artifact_id": base_snapshot.source_parser_artifact_id,
        "round_ledger": ledger,
        "artifact_path": str(artifact_path),
        "metric_validation": {
            key: {"status": "validated" if value is not None else "quarantined"} for key, value in metrics.items()
        },
    }
    return upsert_metric_snapshot(
        db,
        owner_user_id=owner_user_id,
        match_id=base_snapshot.match_id,
        player_key=base_snapshot.player_key,
        player_name=base_snapshot.player_name,
        player_steamid=base_snapshot.player_steamid,
        source="coach_metric_temporal_survival",
        metric_domain="coach_performance",
        semantic_version=TEMPORAL_SEMANTIC_VERSION,
        scope="player_match",
        validation_status="validated",
        implementation_version=TEMPORAL_IMPLEMENTATION_VERSION,
        source_parser_artifact_id=base_snapshot.source_parser_artifact_id,
        source_event_set_id=base_snapshot.source_event_set_id,
        input_event_hash=digest(metrics),
        metrics=metrics,
        confidence_baseline=confidence,
        caveats=["Times use accepted round-start/death-or-round-end boundaries at the parser's 64 tick contract."],
        metadata=metadata,
    )


def select_or_create_baseline(db: Session, *, owner_user_id: int, analysis_cutoff: datetime) -> CoachEvidenceBaseline:
    account = db.scalar(select(SteamAccount).where(SteamAccount.user_id == owner_user_id))
    if account is None:
        raise ValueError("owner_steam_identity_missing")
    cutoff = analysis_cutoff.astimezone(UTC).replace(tzinfo=None) if analysis_cutoff.tzinfo else analysis_cutoff
    matches = list(
        db.scalars(
            select(Match)
            .where(Match.user_id == owner_user_id)
            .where(Match.played_at < cutoff)
            .order_by(Match.played_at.asc(), Match.id.asc())
        ).all()
    )
    eligible, exclusions, seen_sources = [], [], set()
    for match in matches:
        reasons: list[str] = []
        if match.result not in {"win", "loss", "draw"}:
            reasons.append("not_completed_accepted")
        if match.steam_account_id != account.id:
            reasons.append("owner_steam_account_mismatch")
        snapshots = list(
            db.scalars(
                select(MetricSnapshot)
                .where(MetricSnapshot.owner_user_id == owner_user_id)
                .where(MetricSnapshot.match_id == match.id)
                .where(MetricSnapshot.semantic_version == "3.0.0")
                .where(MetricSnapshot.validation_status == "validated")
            ).all()
        )
        by_domain = {row.metric_domain: row for row in snapshots}
        if not {"coach_performance", "coach_utility", "coach_aim"}.issubset(by_domain):
            reasons.append("missing_validated_v3_groups")
        temporal_rows = list(
            db.scalars(
                select(MetricSnapshot)
                .where(MetricSnapshot.owner_user_id == owner_user_id)
                .where(MetricSnapshot.match_id == match.id)
                .where(MetricSnapshot.semantic_version == TEMPORAL_SEMANTIC_VERSION)
                .where(MetricSnapshot.source == "coach_metric_temporal_survival")
                .where(MetricSnapshot.validation_status == "validated")
            ).all()
        )
        if len(temporal_rows) != 1:
            reasons.append("missing_validated_temporal_survival")
        event_sets = {row.source_event_set_id for row in by_domain.values() if row.source_event_set_id}
        artifact_ids = {row.source_parser_artifact_id for row in by_domain.values() if row.source_parser_artifact_id}
        if len(event_sets) != 1:
            reasons.append("event_set_provenance_mismatch")
        if len(artifact_ids) != 1:
            reasons.append("parser_artifact_provenance_mismatch")
        artifact = db.get(DemoParseArtifact, next(iter(artifact_ids))) if len(artifact_ids) == 1 else None
        if artifact is None or artifact.status != "parsed":
            reasons.append("parser_artifact_not_accepted")
        source_identity = (
            artifact.demo_sha1 if artifact else None
        ) or f"{match.source}:{match.external_match_id or match.id}"
        if source_identity in seen_sources:
            reasons.append("duplicate_source_identity")
        if reasons:
            exclusions.append({"match_id": match.id, "reasons": sorted(set(reasons))})
            continue
        seen_sources.add(source_identity)
        eligible.append(
            {
                "match_id": match.id,
                "played_at": match.played_at.isoformat(),
                "snapshot_ids_by_metric_group": {
                    "performance": [by_domain["coach_performance"].id, temporal_rows[0].id],
                    "utility": [by_domain["coach_utility"].id],
                    "aim": [by_domain["coach_aim"].id],
                },
                "event_set_id": next(iter(event_sets)),
                "parser_artifact_id": next(iter(artifact_ids)),
                "metric_semantic_versions": ["3.0.0", TEMPORAL_SEMANTIC_VERSION],
                "source_identity_hash": hashlib.sha256(source_identity.encode()).hexdigest(),
            }
        )
    selected = eligible[-30:]
    identity = {
        "version": BASELINE_VERSION,
        "owner_user_id": owner_user_id,
        "owner_steam_id": account.steam_id,
        "matches": selected,
    }
    baseline_hash = digest(identity)
    existing = db.scalar(select(CoachEvidenceBaseline).where(CoachEvidenceBaseline.baseline_hash == baseline_hash))
    if existing:
        return existing
    row = CoachEvidenceBaseline(
        owner_user_id=owner_user_id,
        owner_steam_id=account.steam_id,
        analysis_cutoff=cutoff,
        status="eligible" if len(selected) == 30 else "insufficient_baseline",
        baseline_hash=baseline_hash,
        evidence_version=BASELINE_VERSION,
        match_ids_json=canonical_json([r["match_id"] for r in selected]),
        lineage_json=canonical_json(selected),
        exclusions_json=canonical_json(exclusions),
    )
    db.add(row)
    db.flush()
    return row


def build_domain_evidence(db: Session, *, baseline: CoachEvidenceBaseline, domain_key: str) -> dict[str, Any]:
    domain = require_canonical_domain(domain_key)
    lineage = json.loads(baseline.lineage_json)
    observations, refs, metric_versions, snapshot_lineage = [], {}, {}, []
    for item in lineage:
        snapshots = list(
            db.scalars(
                select(MetricSnapshot).where(
                    MetricSnapshot.id.in_(sum(item["snapshot_ids_by_metric_group"].values(), []))
                )
            ).all()
        )
        values: dict[str, Any] = {}
        for snapshot in snapshots:
            values.update(json.loads(snapshot.metrics_json))
            metric_versions.update({key: snapshot.semantic_version for key in json.loads(snapshot.metrics_json)})
            snapshot_lineage.append(
                {
                    "snapshot_id": snapshot.id,
                    "match_id": snapshot.match_id,
                    "event_set_id": snapshot.source_event_set_id,
                    "parser_artifact_id": snapshot.source_parser_artifact_id,
                    "semantic_version": snapshot.semantic_version,
                }
            )
        perf = next(
            row for row in snapshots if row.metric_domain == "coach_performance" and row.semantic_version == "3.0.0"
        )
        metadata = json.loads(perf.metadata_json)
        artifact_path = BASE_DIR / str(metadata["artifact_path"])
        temporal, _ = temporal_survival_metrics(json.loads(artifact_path.read_text(encoding="utf-8")))
        values.update(
            {key: value for key, value in temporal.items() if key != "survival_time_seconds_per_participated_round"}
        )
        metric_versions.update({key: TEMPORAL_SEMANTIC_VERSION for key in temporal})
        match = db.get(Match, item["match_id"])
        observation = {
            "match_id": match.id,
            "played_at": match.played_at.isoformat(),
            "map": match.map_name,
            "result": match.result,
            "round_differential": (match.rounds_for or 0) - (match.rounds_against or 0),
            "metrics": values,
        }
        observations.append(observation)
        refs[f"match:{match.id}"] = {"match_id": match.id, "fact": "validated per-match observation"}
    keys = _domain_metric_keys(domain)
    aggregates = {key: _mean([o["metrics"].get(key) for o in observations]) for key in keys}
    aggregates.update(
        {
            "win_rate": round(sum(o["result"] == "win" for o in observations) / len(observations), 3),
            "average_round_differential": _mean([o["round_differential"] for o in observations]),
        }
    )
    for key, value in aggregates.items():
        refs[f"aggregate:{key}"] = {"metric_key": key, "value": value, "sample_matches": len(observations)}
    trends = {
        key: {
            "first_10": _mean([o["metrics"].get(key) for o in observations[:10]]),
            "last_10": _mean([o["metrics"].get(key) for o in observations[-10:]]),
        }
        for key in keys
    }
    ranked = sorted(observations, key=lambda o: _observation_score(domain, o), reverse=True)
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "domain_key": domain,
        "owner": {
            "user_id": baseline.owner_user_id,
            "steam_id_hash": hashlib.sha256(baseline.owner_steam_id.encode()).hexdigest()[:16],
        },
        "baseline": {
            "id": baseline.id,
            "hash": baseline.baseline_hash,
            "analysis_cutoff": baseline.analysis_cutoff.isoformat(),
            "match_ids": json.loads(baseline.match_ids_json),
            "sample_matches": len(observations),
        },
        "metric_versions": {key: metric_versions.get(key, "derived_v1") for key in aggregates},
        "aggregates": aggregates,
        "chronological_trends": trends,
        "per_match_observations": observations,
        "strong_positive_examples": [o["match_id"] for o in ranked[:3]],
        "counterexamples": [o["match_id"] for o in ranked[-3:]],
        "confidence": "high",
        "availability": {key: aggregates[key] is not None for key in aggregates},
        "caveats": [
            "Only supplied aggregate and event-derived metrics may support claims.",
            "Map/side/weapon context is descriptive and does not prove exact tactical cause.",
        ],
        "allowed_claim_boundaries": _claim_boundaries(domain),
        "target_policy": {key: METRIC_DIRECTIONS[key] for key in keys if key in METRIC_DIRECTIONS},
        "evidence_refs": refs,
        "source_snapshot_event_set_lineage": snapshot_lineage,
    }


def validate_domain_output(output: Any, bundle: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(output, Mapping):
        return ("malformed_structured_output",)
    required = {
        "schema_version",
        "domain_key",
        "analysis_status",
        "headline",
        "hypothesis",
        "reasoning_summary",
        "primary_pattern",
        "evidence_refs",
        "counterevidence_refs",
        "metric_refs",
        "match_refs",
        "confidence",
        "confidence_rationale",
        "caveats",
        "recommended_focus",
        "mission_proposal",
    }
    if missing := required - set(output):
        errors.append("missing_fields:" + ",".join(sorted(missing)))
    if output.get("schema_version") != OUTPUT_SCHEMA_VERSION:
        errors.append("invalid_schema_version")
    if output.get("domain_key") != bundle.get("domain_key") or output.get("domain_key") not in CANONICAL_COACH_DOMAINS:
        errors.append("invalid_domain")
    if output.get("analysis_status") not in ANALYSIS_STATUSES:
        errors.append("invalid_analysis_status")
    valid_refs = set((bundle.get("evidence_refs") or {}).keys())
    for field in ("evidence_refs", "counterevidence_refs"):
        if not isinstance(output.get(field), list) or any(ref not in valid_refs for ref in output.get(field, [])):
            errors.append(f"unresolved_{field}")
    match_ids = set((bundle.get("baseline") or {}).get("match_ids", []))
    if any(not isinstance(mid, int) or mid not in match_ids for mid in output.get("match_refs", [])):
        errors.append("unsupported_match_reference")
    registered = _registered_metric_keys()
    bundle_versions = bundle.get("metric_versions") or {}
    aggregates = bundle.get("aggregates") or {}
    for ref in output.get("metric_refs", []):
        if not isinstance(ref, Mapping):
            errors.append("malformed_metric_reference")
            continue
        key = ref.get("metric_key")
        if key not in registered and key not in {"win_rate", "average_round_differential"}:
            errors.append(f"unsupported_metric:{key}")
            continue
        if bundle_versions.get(key) not in ALLOWED_VERSIONS | {"derived_v1"}:
            errors.append(f"unaccepted_metric_version:{key}")
        if not _same_number(ref.get("value"), aggregates.get(key)):
            errors.append(f"metric_value_mismatch:{key}")
        if ref.get("evidence_ref") != f"aggregate:{key}":
            errors.append(f"metric_evidence_mismatch:{key}")
    text = " ".join(
        str(output.get(field) or "")
        for field in ("headline", "hypothesis", "reasoning_summary", "primary_pattern", "recommended_focus")
    )
    if FORBIDDEN_CLAIMS.search(text):
        errors.append("unsupported_tactical_claim")
    if re.search(r"(api[_ -]?key|password|bearer\s|sk-[A-Za-z0-9])", canonical_json(output), re.I):
        errors.append("secret_or_raw_payload_leakage")
    proposal = output.get("mission_proposal")
    if output.get("analysis_status") == "supported_hypothesis":
        if not isinstance(proposal, Mapping):
            errors.append("supported_hypothesis_missing_proposal")
        else:
            errors.extend(_validate_target(proposal, aggregates, registered))
    elif proposal is not None:
        errors.append("non_supported_status_has_proposal")
    return tuple(dict.fromkeys(errors))


def run_domain_analysis(
    db: Session,
    *,
    owner_user_id: int,
    domain_key: str,
    analysis_cutoff: datetime,
    model_call: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = invoke_configured_structured_model,
    model_identity: str | None = None,
) -> dict[str, Any]:
    domain = require_canonical_domain(domain_key)
    baseline = select_or_create_baseline(db, owner_user_id=owner_user_id, analysis_cutoff=analysis_cutoff)
    slot = _slot(db, owner_user_id, baseline.owner_steam_id, domain)
    slot.baseline_id = baseline.id
    if baseline.status != "eligible":
        _set_slot(
            slot,
            "insufficient_baseline",
            {"eligible_matches": len(json.loads(baseline.match_ids_json)), "required": 30},
        )
        db.flush()
        return {"slot": slot, "analysis": None, "reused": False}
    bundle = build_domain_evidence(db, baseline=baseline, domain_key=domain)
    prompt_template = PROMPT_PATHS[domain].read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt_template.encode()).hexdigest()
    evidence_hash = digest(bundle)
    configured_identity = model_identity or configured_model_route_identity()
    identity = digest(
        {
            "owner": owner_user_id,
            "domain": domain,
            "baseline": baseline.baseline_hash,
            "prompt": PROMPT_VERSION,
            "evidence": EVIDENCE_SCHEMA_VERSION,
            "model_route": configured_identity,
        }
    )
    accepted = db.scalar(
        select(AIDomainAnalysis)
        .where(AIDomainAnalysis.idempotency_key == identity)
        .where(AIDomainAnalysis.validation_status == "accepted")
        .order_by(AIDomainAnalysis.id.desc())
    )
    if accepted:
        _apply_accepted(db, slot, accepted, json.loads(accepted.structured_output_json or "{}"), baseline)
        return {"slot": slot, "analysis": accepted, "reused": True}
    _set_slot(slot, "analyzing", {})
    db.flush()
    previous = db.scalar(
        select(AIDomainAnalysis)
        .where(AIDomainAnalysis.idempotency_key == identity)
        .order_by(AIDomainAnalysis.attempt_number.desc())
    )
    first_attempt = (previous.attempt_number + 1) if previous else 1
    for attempt in range(first_attempt, first_attempt + MODEL_MAX_ATTEMPTS):
        repair = (
            ""
            if not previous
            else "\nREPAIR: The prior output failed: "
            + ", ".join(previous.validation_errors_json and json.loads(previous.validation_errors_json) or [])
        )
        prompt = prompt_template + "\n\nVALIDATED_EVIDENCE_BUNDLE:\n" + canonical_json(bundle) + repair
        try:
            output, telemetry = model_call(prompt=prompt, schema_path=SCHEMA_PATH)
            errors = validate_domain_output(output, bundle)
            failure = None
        except TimeoutError:
            output, telemetry, errors, failure = (
                None,
                {"provider": "configured", "model": "configured_default", "route": "configured_provider"},
                ("provider_timeout",),
                "provider_timeout",
            )
        except (RuntimeError, json.JSONDecodeError) as exc:
            output, telemetry, errors, failure = (
                None,
                {"provider": "configured", "model": "configured_default", "route": "configured_provider"},
                (str(exc),),
                "provider_error",
            )
        analysis = AIDomainAnalysis(
            owner_user_id=owner_user_id,
            owner_steam_id=baseline.owner_steam_id,
            domain_key=domain,
            baseline_id=baseline.id,
            baseline_hash=baseline.baseline_hash,
            idempotency_key=identity,
            attempt_number=attempt,
            prompt_version=PROMPT_VERSION,
            prompt_hash=prompt_hash,
            evidence_schema_version=EVIDENCE_SCHEMA_VERSION,
            evidence_hash=evidence_hash,
            provider=telemetry.get("provider", "configured"),
            model=telemetry.get("model", "configured_default"),
            routing_json=canonical_json({"route": telemetry.get("route")}),
            settings_json=canonical_json({"temperature": 0.2, "max_attempts": 2}),
            request_id=telemetry.get("request_id"),
            input_tokens=telemetry.get("input_tokens"),
            output_tokens=telemetry.get("output_tokens"),
            latency_ms=telemetry.get("latency_ms"),
            raw_response_hash=telemetry.get("raw_response_hash") or (digest(output) if output else None),
            structured_output_json=canonical_json(output) if output else None,
            validation_status="accepted" if not errors else "rejected",
            validation_errors_json=canonical_json(list(errors)),
            failure_reason_code=failure or ("validation_failed" if errors else None),
            supersedes_analysis_id=previous.id if previous else None,
        )
        db.add(analysis)
        db.flush()
        previous = analysis
        if not errors:
            _apply_accepted(db, slot, analysis, output, baseline)
            db.flush()
            return {"slot": slot, "analysis": analysis, "reused": False}
        if failure == "provider_timeout":
            break
    _set_slot(
        slot,
        "analysis_failed",
        {"reason_codes": json.loads(previous.validation_errors_json) if previous else ["unknown"]},
    )
    slot.current_analysis_id = previous.id if previous else None
    db.flush()
    return {"slot": slot, "analysis": previous, "reused": False}


def coach_domain_slots_payload(db: Session, *, owner_user_id: int, include_provenance: bool = False) -> dict[str, Any]:
    account = db.scalar(select(SteamAccount).where(SteamAccount.user_id == owner_user_id))
    if account is None:
        raise PermissionError("owner_steam_identity_missing")
    result = {}
    for domain in CANONICAL_COACH_DOMAINS:
        slot = db.scalar(
            select(CoachDomainSlot)
            .where(CoachDomainSlot.owner_user_id == owner_user_id)
            .where(CoachDomainSlot.domain_key == domain)
        )
        active = next(
            (
                m
                for m in list_active_coach_missions(db, user_id=owner_user_id, owner_steam_id=account.steam_id)
                if mission_domain_key(m) == domain
            ),
            None,
        )
        analysis = db.get(AIDomainAnalysis, slot.current_analysis_id) if slot and slot.current_analysis_id else None
        output = json.loads(analysis.structured_output_json) if analysis and analysis.structured_output_json else None
        baseline = db.get(CoachEvidenceBaseline, slot.baseline_id) if slot and slot.baseline_id else None
        proposal = db.get(CoachMissionProposal, slot.current_proposal_id) if slot and slot.current_proposal_id else None
        item = {
            "domain": {
                "key": domain,
                "title": "Impact Leak / Useful vs Useless Deaths"
                if domain == "impact_leak"
                else "Bad Fight Selection / Duel Discipline",
            },
            "slot_status": slot.status if slot else "insufficient_baseline",
            "baseline_summary": {
                "id": baseline.id,
                "hash": baseline.baseline_hash,
                "matches_count": len(json.loads(baseline.match_ids_json)),
                "analysis_cutoff": baseline.analysis_cutoff.isoformat(),
            }
            if baseline
            else None,
            "ai_analysis_status": output.get("analysis_status") if output else None,
            "hypothesis_summary": {
                key: output.get(key) for key in ("headline", "hypothesis", "primary_pattern", "recommended_focus")
            }
            if output
            else None,
            "proposal_summary": json.loads(proposal.payload_json) if proposal else None,
            "confidence": output.get("confidence") if output else None,
            "caveats": output.get("caveats", []) if output else [],
            "activation_eligibility": bool(proposal and not active),
            "current_mission": serialize_coach_mission(active) if active else None,
        }
        if include_provenance and analysis:
            item["technical_provenance"] = {
                "analysis_id": analysis.id,
                "baseline_hash": analysis.baseline_hash,
                "prompt_version": analysis.prompt_version,
                "prompt_hash": analysis.prompt_hash,
                "evidence_schema_version": analysis.evidence_schema_version,
                "evidence_hash": analysis.evidence_hash,
                "provider": analysis.provider,
                "model": analysis.model,
                "route": json.loads(analysis.routing_json),
                "validation_status": analysis.validation_status,
            }
        result[domain] = item
    return {"schema_version": "coach-domain-slots-v1", "owner_user_id": owner_user_id, "coach_domain_slots": result}


def _apply_accepted(
    db: Session,
    slot: CoachDomainSlot,
    analysis: AIDomainAnalysis,
    output: Mapping[str, Any],
    baseline: CoachEvidenceBaseline,
) -> None:
    slot.current_analysis_id = analysis.id
    status = output["analysis_status"]
    if status == "supported_hypothesis":
        old = db.scalar(
            select(CoachMissionProposal)
            .where(CoachMissionProposal.owner_user_id == slot.owner_user_id)
            .where(CoachMissionProposal.domain_key == slot.domain_key)
            .where(CoachMissionProposal.is_current.is_(True))
        )
        payload = dict(output["mission_proposal"])
        proposal_hash = digest({"analysis": analysis.id, "payload": payload})
        proposal = db.scalar(select(CoachMissionProposal).where(CoachMissionProposal.proposal_hash == proposal_hash))
        if proposal is None:
            if old:
                old.is_current = False
            proposal = CoachMissionProposal(
                owner_user_id=slot.owner_user_id,
                owner_steam_id=slot.owner_steam_id,
                domain_key=slot.domain_key,
                analysis_id=analysis.id,
                baseline_id=baseline.id,
                proposal_hash=proposal_hash,
                payload_json=canonical_json(payload),
                provenance_json=canonical_json({"metric_versions": ALLOWED_VERSIONS}),
                is_current=True,
            )
            db.add(proposal)
            db.flush()
            if old:
                old.superseded_by_id = proposal.id
        slot.current_proposal_id = proposal.id
        _set_slot(slot, "proposal_ready", {"analysis_status": status})
    else:
        slot.current_proposal_id = None
        _set_slot(
            slot,
            "no_material_problem" if status == "no_material_problem" else "analysis_failed",
            {"analysis_status": status},
        )


def _slot(db: Session, user_id: int, steam_id: str, domain: str) -> CoachDomainSlot:
    slot = db.scalar(
        select(CoachDomainSlot)
        .where(CoachDomainSlot.owner_user_id == user_id)
        .where(CoachDomainSlot.domain_key == domain)
    )
    if slot:
        return slot
    slot = CoachDomainSlot(
        owner_user_id=user_id,
        owner_steam_id=steam_id,
        domain_key=domain,
        status="insufficient_baseline",
        state_json="{}",
    )
    db.add(slot)
    db.flush()
    return slot


def _set_slot(slot: CoachDomainSlot, status: str, state: Mapping[str, Any]) -> None:
    if status not in DOMAIN_SLOT_STATUSES:
        raise ValueError("invalid_domain_slot_status")
    slot.status, slot.state_json = status, canonical_json(dict(state))


def _validate_target(proposal: Mapping[str, Any], aggregates: Mapping[str, Any], registered: set[str]) -> list[str]:
    errors = []
    key = proposal.get("primary_metric")
    baseline = proposal.get("baseline_value")
    if key not in registered:
        errors.append(f"unsupported_primary_metric:{key}")
    if key not in METRIC_DIRECTIONS:
        errors.append(f"metric_direction_not_contract_compatible:{key}")
    if proposal.get("target_direction") != METRIC_DIRECTIONS.get(key):
        errors.append("target_direction_mismatch")
    if not _same_number(baseline, aggregates.get(key)):
        errors.append("proposal_baseline_mismatch")
    minimum, maximum = proposal.get("minimum_future_matches"), proposal.get("maximum_future_matches")
    if (
        not isinstance(minimum, int)
        or not isinstance(maximum, int)
        or not (WINDOW_MIN <= minimum <= maximum <= WINDOW_MAX)
    ):
        errors.append("future_window_out_of_policy")
    target, delta = proposal.get("target_value"), proposal.get("target_delta")
    if (target is None) == (delta is None):
        errors.append("target_requires_exactly_one_value_or_delta")
    if isinstance(baseline, (int, float)):
        effective = (
            target
            if isinstance(target, (int, float))
            else baseline + delta
            if isinstance(delta, (int, float))
            else None
        )
        if effective is None or abs(effective - baseline) > max(abs(baseline) * 0.35, 0.1):
            errors.append("target_not_plausible_relative_to_baseline")
        direction = METRIC_DIRECTIONS.get(key)
        if direction == "higher_is_better" and effective is not None and effective <= baseline:
            errors.append("target_wrong_direction")
        if direction == "lower_is_better" and effective is not None and effective >= baseline:
            errors.append("target_wrong_direction")
    for field in ("secondary_metrics", "guardrail_metrics"):
        if any(key not in registered for key in proposal.get(field, [])):
            errors.append(f"unsupported_{field}")
    return errors


def _domain_metric_keys(domain: str) -> list[str]:
    common = [
        "adr",
        "kills_per_round",
        "kast",
        "deaths",
        "survival_rate",
        "average_survival_time_seconds",
        "median_survival_time_seconds",
        "p25_survival_time_seconds",
        "early_death_rate_before_45_seconds",
        "average_death_time_seconds",
        "average_death_time_t_side_seconds",
        "average_death_time_ct_side_seconds",
        "opening_deaths",
        "opening_death_rate",
        "traded_deaths",
        "untraded_deaths",
        "traded_death_rate",
        "untraded_death_rate",
        "multi_kill_rounds",
    ]
    if domain == "bad_fight_selection":
        common += [
            "opening_duel_attempts",
            "opening_duel_wins",
            "opening_duel_losses",
            "opening_duel_win_rate",
            "trade_opportunities",
            "trade_kills",
            "trade_success_rate",
        ]
    return common


def _claim_boundaries(domain: str) -> dict[str, Any]:
    forbidden = (
        ["exact positioning", "rotations", "economy mistakes", "clutch decisions"]
        if domain == "impact_leak"
        else ["exact angle", "spacing", "crosshair placement", "rotation"]
    )
    return {
        "allowed": ["conversion", "death cost", "survival timing"]
        if domain == "impact_leak"
        else ["isolated fights", "opening discipline", "tradeability", "passivity guardrail"],
        "forbidden": forbidden,
    }


def _observation_score(domain: str, observation: Mapping[str, Any]) -> float:
    m = observation["metrics"]
    if domain == "impact_leak":
        return (
            float(m.get("untraded_death_rate") or 0)
            + float(m.get("early_death_rate_before_45_seconds") or 0)
            - float(m.get("kast") or 0) / 100
        )
    return (
        float(m.get("opening_death_rate") or 0)
        + float(m.get("untraded_death_rate") or 0)
        - float(m.get("opening_duel_win_rate") or 0)
    )


def _registered_metric_keys() -> set[str]:
    registry = metric_registry_contract()
    return {row["metric_key"] for row in registry["metrics"]} | {
        "average_survival_time_seconds",
        "median_survival_time_seconds",
        "p25_survival_time_seconds",
        "early_death_rate_before_45_seconds",
        "average_death_time_seconds",
        "average_death_time_t_side_seconds",
        "average_death_time_ct_side_seconds",
        "survival_time_seconds_per_participated_round",
    }


def _mean(values: Sequence[Any]) -> float | None:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    return round(statistics.fmean(numbers), 3) if numbers else None


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _same_number(left: Any, right: Any) -> bool:
    return (
        isinstance(left, (int, float)) and isinstance(right, (int, float)) and abs(float(left) - float(right)) < 0.0005
    )
