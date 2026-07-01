from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import CoachRecommendation, Match, MatchRecommendationEvaluation

DEFAULT_TITLE = "Снизить первые смерти"
TARGET_PERIOD_MATCHES = 10
BASELINE_PERIOD_MATCHES = 15


def ensure_default_recommendation(db: Session) -> CoachRecommendation | None:
    active = db.scalar(
        select(CoachRecommendation)
        .where(CoachRecommendation.status == "active")
        .order_by(CoachRecommendation.created_at.desc(), CoachRecommendation.id.desc())
        .limit(1)
    )
    if active:
        _repair_existing_recommendation_anchor(db, active)
        return active

    matches = _ordered_matches(db)
    if not matches:
        return None

    baseline_matches = matches[-BASELINE_PERIOD_MATCHES:]
    baseline_metrics = _aggregate_baseline(baseline_matches)
    target_metrics = _target_metrics(baseline_metrics)
    recommendation = CoachRecommendation(
        title=DEFAULT_TITLE,
        description=(
            "Не отдавать первый контакт без размена: снизить entry deaths и early deaths, "
            "сохранив KAST и ADR."
        ),
        category="survival",
        status="active",
        priority="high",
        started_at=datetime.now(UTC).replace(tzinfo=None),
        target_period_matches=TARGET_PERIOD_MATCHES,
        baseline_period_matches=len(baseline_matches),
        start_after_match_id=max((match.id for match in matches if match.id is not None), default=None),
        baseline_metrics_json=json.dumps(baseline_metrics, ensure_ascii=False),
        target_metrics_json=json.dumps(target_metrics, ensure_ascii=False),
        success_rules_json=json.dumps(
            [
                "entry_deaths ниже baseline",
                "early_deaths ниже baseline",
                "KAST не ниже baseline",
                "ADR не упал больше чем на 10%",
            ],
            ensure_ascii=False,
        ),
        failure_rules_json=json.dumps(
            [
                "entry_deaths выше baseline",
                "early_deaths выше baseline",
                "KAST ниже baseline",
                "ADR упал больше чем на 15%",
            ],
            ensure_ascii=False,
        ),
        baseline_match_ids_json=json.dumps([match.id for match in baseline_matches]),
        coach_comment=(
            "Следующие 10 матчей цель считается успешной, если первых смертей меньше baseline "
            "и при этом не проседает impact."
        ),
        created_by="system",
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def evaluate_new_matches(db: Session) -> list[MatchRecommendationEvaluation]:
    recommendation = ensure_default_recommendation(db)
    if not recommendation:
        return []

    baseline_ids = set(json.loads(recommendation.baseline_match_ids_json or "[]"))
    evaluated_ids = set(
        db.scalars(
            select(MatchRecommendationEvaluation.match_id).where(
                MatchRecommendationEvaluation.recommendation_id == recommendation.id
            )
        ).all()
    )
    matches = _ordered_matches(db)
    evaluations = []
    for match in matches:
        if match.id in baseline_ids or match.id in evaluated_ids:
            continue
        if recommendation.start_after_match_id is not None and match.id <= recommendation.start_after_match_id:
            continue
        evaluation = evaluate_match(db, recommendation, match)
        evaluations.append(evaluation)

    if evaluations:
        db.commit()
        for evaluation in evaluations:
            db.refresh(evaluation)
    return evaluations


def evaluate_match(
    db: Session,
    recommendation: CoachRecommendation,
    match: Match,
) -> MatchRecommendationEvaluation:
    baseline = json.loads(recommendation.baseline_metrics_json)
    evidence = _match_evidence(match)
    positive, negative, missing = _signals(evidence, baseline)
    status, score, comment = _status_score_comment(positive, negative, missing, evidence, baseline)
    evaluation = MatchRecommendationEvaluation(
        recommendation_id=recommendation.id,
        match_id=match.id,
        score=score,
        status=status,
        evidence_json=json.dumps(evidence, ensure_ascii=False),
        positive_signals_json=json.dumps(positive, ensure_ascii=False),
        negative_signals_json=json.dumps(negative, ensure_ascii=False),
        coach_comment=comment,
    )
    db.add(evaluation)
    return evaluation


def get_active_recommendation_progress(db: Session) -> dict[str, Any] | None:
    recommendation = ensure_default_recommendation(db)
    if not recommendation:
        return None
    evaluate_new_matches(db)
    evaluations = db.scalars(
        select(MatchRecommendationEvaluation)
        .where(MatchRecommendationEvaluation.recommendation_id == recommendation.id)
        .order_by(MatchRecommendationEvaluation.evaluated_at.asc(), MatchRecommendationEvaluation.id.asc())
    ).all()
    target_evaluations = evaluations[: recommendation.target_period_matches]
    counts = Counter(evaluation.status for evaluation in target_evaluations)
    baseline = json.loads(recommendation.baseline_metrics_json)
    current = _aggregate_current_evaluations(target_evaluations)
    progress_score = _progress_score(target_evaluations, recommendation.target_period_matches)
    last = target_evaluations[-1] if target_evaluations else None
    return {
        "recommendation": recommendation,
        "baseline": baseline,
        "target": json.loads(recommendation.target_metrics_json),
        "current": current,
        "evaluations": target_evaluations,
        "counts": {"green": counts["green"], "yellow": counts["yellow"], "red": counts["red"], "gray": counts["gray"]},
        "progress_score": progress_score,
        "completed_matches": len(target_evaluations),
        "target_matches": recommendation.target_period_matches,
        "last_status": last.status if last else None,
        "last_comment": last.coach_comment if last else "Новые матчи после постановки цели ещё не оценивались.",
        "summary": _progress_summary(progress_score, len(target_evaluations)),
    }


def get_evaluations_by_match_id(db: Session) -> dict[int, MatchRecommendationEvaluation]:
    recommendation = ensure_default_recommendation(db)
    if not recommendation:
        return {}
    evaluate_new_matches(db)
    evaluations = db.scalars(
        select(MatchRecommendationEvaluation).where(
            MatchRecommendationEvaluation.recommendation_id == recommendation.id
        )
    ).all()
    return {evaluation.match_id: evaluation for evaluation in evaluations}


def _aggregate_baseline(matches: list[Match]) -> dict[str, float | int | None]:
    return {
        "matches_count": len(matches),
        "entry_deaths_per_match": _avg(matches, "entry_deaths"),
        "early_deaths_per_match": _avg(matches, "early_deaths"),
        "kast": _avg(matches, "kast"),
        "adr": _avg(matches, "adr"),
    }


def _repair_existing_recommendation_anchor(db: Session, recommendation: CoachRecommendation) -> None:
    if recommendation.start_after_match_id is not None:
        return
    baseline_ids = json.loads(recommendation.baseline_match_ids_json or "[]")
    if not baseline_ids:
        return
    recommendation.start_after_match_id = max(baseline_ids)
    db.execute(
        delete(MatchRecommendationEvaluation).where(
            MatchRecommendationEvaluation.recommendation_id == recommendation.id,
            MatchRecommendationEvaluation.match_id <= recommendation.start_after_match_id,
        )
    )
    db.commit()


def _target_metrics(baseline: dict[str, float | int | None]) -> dict[str, str]:
    entry = baseline.get("entry_deaths_per_match")
    early = baseline.get("early_deaths_per_match")
    kast = baseline.get("kast")
    adr = baseline.get("adr")
    return {
        "entry_deaths_per_match": f"<={round(entry * 0.85, 2)}" if entry is not None else "need data",
        "early_deaths_per_match": f"<={round(early * 0.9, 2)}" if early is not None else "need data",
        "kast": f">={kast}" if kast is not None else "need data",
        "adr": f">={round(adr * 0.9, 2)}" if adr is not None else "need data",
    }


def _match_evidence(match: Match) -> dict[str, float | int | None]:
    return {
        "entry_deaths": match.entry_deaths,
        "early_deaths": match.early_deaths if match.early_deaths is not None else match.entry_deaths,
        "kast": match.kast,
        "adr": match.adr,
    }


def _signals(
    evidence: dict[str, float | int | None],
    baseline: dict[str, float | int | None],
) -> tuple[list[str], list[str], list[str]]:
    positive = []
    negative = []
    missing = []
    _compare_lower(
        evidence,
        baseline,
        "entry_deaths",
        "entry_deaths_per_match",
        "entry deaths ниже baseline",
        "entry deaths выше baseline",
        positive,
        negative,
        missing,
    )
    _compare_lower(
        evidence,
        baseline,
        "early_deaths",
        "early_deaths_per_match",
        "early deaths ниже baseline",
        "early deaths выше baseline",
        positive,
        negative,
        missing,
    )
    _compare_higher(
        evidence,
        baseline,
        "kast",
        "kast",
        "KAST не ниже baseline",
        "KAST ниже baseline",
        positive,
        negative,
        missing,
    )
    _compare_adr(evidence, baseline, positive, negative, missing)
    return positive, negative, missing


def _status_score_comment(
    positive: list[str],
    negative: list[str],
    missing: list[str],
    evidence: dict[str, float | int | None],
    baseline: dict[str, float | int | None],
) -> tuple[str, int, str]:
    if missing:
        return "gray", 0, "Недостаточно данных для оценки цели по этому матчу."

    adr = evidence.get("adr")
    baseline_adr = baseline.get("adr")
    passive_drop = adr is not None and baseline_adr is not None and adr < baseline_adr * 0.85
    first_deaths_better = "entry deaths ниже baseline" in positive and "early deaths ниже baseline" in positive
    if first_deaths_better and passive_drop:
        return (
            "yellow",
            55,
            "Первых смертей меньше, но ADR сильно просел. Это похоже на пассивность, а не полноценный прогресс.",
        )

    score = max(0, min(100, 25 * len(positive) - 20 * len(negative) + 20))
    if len(positive) >= 3 and len(negative) == 0:
        return "green", max(score, 82), "Хороший матч по цели: первых смертей меньше, impact не потерян."
    if len(negative) >= 3 or ("entry deaths выше baseline" in negative and "KAST ниже baseline" in negative):
        return "red", min(score, 35), "Матч провалил цель: первые смерти и участие в раундах хуже baseline."
    return "yellow", max(45, min(score, 70)), "Смешанный матч по цели: есть прогресс, но часть метрик просела."


def _compare_lower(
    evidence: dict[str, float | int | None],
    baseline: dict[str, float | int | None],
    evidence_key: str,
    baseline_key: str,
    positive_text: str,
    negative_text: str,
    positive: list[str],
    negative: list[str],
    missing: list[str],
) -> None:
    value = evidence.get(evidence_key)
    baseline_value = baseline.get(baseline_key)
    if value is None or baseline_value is None:
        missing.append(evidence_key)
        return
    if value < baseline_value:
        positive.append(positive_text)
    elif value > baseline_value:
        negative.append(negative_text)


def _compare_higher(
    evidence: dict[str, float | int | None],
    baseline: dict[str, float | int | None],
    evidence_key: str,
    baseline_key: str,
    positive_text: str,
    negative_text: str,
    positive: list[str],
    negative: list[str],
    missing: list[str],
) -> None:
    value = evidence.get(evidence_key)
    baseline_value = baseline.get(baseline_key)
    if value is None or baseline_value is None:
        missing.append(evidence_key)
        return
    if value >= baseline_value:
        positive.append(positive_text)
    else:
        negative.append(negative_text)


def _compare_adr(
    evidence: dict[str, float | int | None],
    baseline: dict[str, float | int | None],
    positive: list[str],
    negative: list[str],
    missing: list[str],
) -> None:
    adr = evidence.get("adr")
    baseline_adr = baseline.get("adr")
    if adr is None or baseline_adr is None:
        missing.append("adr")
        return
    if adr >= baseline_adr * 0.9:
        positive.append("ADR не просел критично")
    elif adr < baseline_adr * 0.85:
        negative.append("ADR сильно ниже baseline")


def _aggregate_current_evaluations(evaluations: list[MatchRecommendationEvaluation]) -> dict[str, float | None]:
    evidence_items = [json.loads(evaluation.evidence_json) for evaluation in evaluations]
    return {
        "entry_deaths_per_match": _avg_dict(evidence_items, "entry_deaths"),
        "early_deaths_per_match": _avg_dict(evidence_items, "early_deaths"),
        "kast": _avg_dict(evidence_items, "kast"),
        "adr": _avg_dict(evidence_items, "adr"),
    }


def _progress_score(evaluations: list[MatchRecommendationEvaluation], target_matches: int) -> int:
    if not evaluations:
        return 0
    status_weight = {"green": 100, "yellow": 55, "red": 0, "gray": 20}
    average = sum(status_weight.get(evaluation.status, 0) for evaluation in evaluations) / len(evaluations)
    completion_factor = min(1, len(evaluations) / target_matches)
    return round(average * completion_factor)


def _progress_summary(progress_score: int, matches_count: int) -> str:
    if matches_count == 0:
        return "Ждём новые матчи после постановки цели."
    if progress_score >= 70:
        return "Движешься верно: цель выполняется на большинстве матчей."
    if progress_score >= 40:
        return "Прогресс смешанный: цель частично выполняется, но стабильности пока нет."
    return "Цель пока проваливается: первые смерти или impact требуют внимания."


def _ordered_matches(db: Session) -> list[Match]:
    return list(db.scalars(select(Match).order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all())


def _avg(matches: list[Match], attr: str) -> float | None:
    values = []
    for match in matches:
        value = getattr(match, attr)
        if attr == "early_deaths" and value is None:
            value = match.entry_deaths
        if value is not None:
            values.append(value)
    return round(sum(values) / len(values), 2) if values else None


def _avg_dict(items: list[dict[str, Any]], key: str) -> float | None:
    values = [item[key] for item in items if item.get(key) is not None]
    return round(sum(values) / len(values), 2) if values else None
