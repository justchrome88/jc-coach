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

RECOMMENDATION_DEFINITIONS = [
    {
        "category": "survival",
        "title": DEFAULT_TITLE,
        "description": (
            "Не отдавать первый контакт без размена: снизить entry deaths и early deaths, сохранив KAST и ADR."
        ),
        "priority": "high",
    },
    {
        "category": "aim",
        "title": "Поднять стабильный ADR",
        "description": (
            "Увеличить урон и не превращать снижение смертей в пассивность: ADR вверх, KAST не ниже baseline."
        ),
        "priority": "high",
    },
    {
        "category": "grenades",
        "title": "Добавить value гранат",
        "description": "Поднять utility damage и flash assists за счет повторяемых opening/retake гранат.",
        "priority": "medium",
    },
    {
        "category": "map",
        "title": "Стабилизировать слабые карты",
        "description": "Играть карты с понятным планом: меньше ранних смертей, выше ADR, лучше конверсия раундов.",
        "priority": "medium",
    },
]


def ensure_default_recommendation(db: Session) -> CoachRecommendation | None:
    recommendations = ensure_default_recommendations(db)
    survival = next((item for item in recommendations if item.category == "survival"), None)
    return survival or (recommendations[0] if recommendations else None)


def ensure_default_recommendations(db: Session) -> list[CoachRecommendation]:
    matches = _ordered_matches(db)
    if not matches:
        return []

    existing_system = list(
        db.scalars(
            select(CoachRecommendation)
            .where(CoachRecommendation.created_by == "system")
            .order_by(CoachRecommendation.category.asc(), CoachRecommendation.id.asc())
        ).all()
    )
    existing_categories = {item.category for item in existing_system}

    created = []
    for definition in RECOMMENDATION_DEFINITIONS:
        if definition["category"] in existing_categories:
            continue
        recommendation = _new_system_recommendation(definition, matches)
        db.add(recommendation)
        created.append(recommendation)

    if created:
        db.commit()
        for recommendation in created:
            db.refresh(recommendation)

    recommendations = list(
        db.scalars(
            select(CoachRecommendation)
            .where(CoachRecommendation.status == "active")
            .order_by(CoachRecommendation.category.asc(), CoachRecommendation.id.asc())
        ).all()
    )
    for recommendation in recommendations:
        _repair_existing_recommendation_anchor(db, recommendation)
    return recommendations


def evaluate_new_matches(db: Session) -> list[MatchRecommendationEvaluation]:
    recommendations = ensure_default_recommendations(db)
    if not recommendations:
        return []
    matches = _ordered_matches(db)
    evaluations = []
    for recommendation in recommendations:
        baseline_ids = set(json.loads(recommendation.baseline_match_ids_json or "[]"))
        evaluated_ids = set(
            db.scalars(
                select(MatchRecommendationEvaluation.match_id).where(
                    MatchRecommendationEvaluation.recommendation_id == recommendation.id
                )
            ).all()
        )
        for match in matches:
            if match.id in baseline_ids or match.id in evaluated_ids:
                continue
            if recommendation.start_after_match_id is not None and match.id <= recommendation.start_after_match_id:
                continue
            evaluations.append(evaluate_match(db, recommendation, match))

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
    positive, negative, missing = _signals(evidence, baseline, recommendation.category)
    status, score, comment = _status_score_comment(recommendation.category, positive, negative, missing)
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
    return _progress_for_recommendation(db, recommendation)


def get_all_recommendation_progress(db: Session) -> list[dict[str, Any]]:
    recommendations = ensure_default_recommendations(db)
    if not recommendations:
        return []
    evaluate_new_matches(db)
    return [_progress_for_recommendation(db, recommendation) for recommendation in recommendations]


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


def get_all_evaluations_by_match_id(db: Session) -> dict[int, list[MatchRecommendationEvaluation]]:
    ensure_default_recommendations(db)
    evaluate_new_matches(db)
    evaluations = db.scalars(select(MatchRecommendationEvaluation)).all()
    grouped: dict[int, list[MatchRecommendationEvaluation]] = {}
    for evaluation in evaluations:
        grouped.setdefault(evaluation.match_id, []).append(evaluation)
    return grouped


def update_recommendation_status(db: Session, recommendation_id: int, status: str) -> CoachRecommendation:
    allowed = {"active", "paused", "completed", "failed", "archived"}
    if status not in allowed:
        raise ValueError(f"Unsupported recommendation status: {status}")
    recommendation = db.get(CoachRecommendation, recommendation_id)
    if recommendation is None:
        raise ValueError("Recommendation not found.")
    recommendation.status = status
    if status in {"completed", "failed", "archived"}:
        recommendation.ended_at = datetime.now(UTC).replace(tzinfo=None)
    elif status == "active":
        recommendation.ended_at = None
    db.commit()
    db.refresh(recommendation)
    return recommendation


def extend_recommendation_target(
    db: Session,
    recommendation_id: int,
    additional_matches: int = 5,
) -> CoachRecommendation:
    recommendation = db.get(CoachRecommendation, recommendation_id)
    if recommendation is None:
        raise ValueError("Recommendation not found.")
    if recommendation.status not in {"active", "paused"}:
        raise ValueError("Only active or paused recommendations can be extended.")
    increment = max(1, min(additional_matches, 25))
    recommendation.target_period_matches = min(recommendation.target_period_matches + increment, 100)
    recommendation.coach_comment = f"{recommendation.coach_comment or ''} Extended by {increment} matches.".strip()
    db.commit()
    db.refresh(recommendation)
    return recommendation


def restart_recommendation_category(db: Session, category: str) -> CoachRecommendation:
    definition = _definition_for_category(category)
    matches = _ordered_matches(db)
    if not matches:
        raise ValueError("Cannot restart recommendation without matches.")
    active_items = list(
        db.scalars(
            select(CoachRecommendation)
            .where(CoachRecommendation.category == category)
            .where(CoachRecommendation.status.in_(("active", "paused")))
            .order_by(CoachRecommendation.id.asc())
        ).all()
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    for recommendation in active_items:
        recommendation.status = "archived"
        recommendation.ended_at = now
    new_recommendation = _new_system_recommendation(definition, matches)
    db.add(new_recommendation)
    db.commit()
    db.refresh(new_recommendation)
    return new_recommendation


def list_recommendation_history(db: Session, limit: int = 100) -> list[CoachRecommendation]:
    ensure_default_recommendations(db)
    return list(
        db.scalars(
            select(CoachRecommendation)
            .order_by(
                CoachRecommendation.category.asc(),
                CoachRecommendation.created_at.desc(),
                CoachRecommendation.id.desc(),
            )
            .limit(max(1, min(limit, 250)))
        ).all()
    )


def recommendation_category_summary(db: Session) -> list[dict[str, Any]]:
    progress_by_category = {
        item["recommendation"].category: item for item in get_all_recommendation_progress(db)
    }
    history = list_recommendation_history(db)
    summary = []
    for definition in RECOMMENDATION_DEFINITIONS:
        category = definition["category"]
        category_history = [item for item in history if item.category == category]
        active = next((item for item in category_history if item.status == "active"), None)
        progress = progress_by_category.get(category)
        summary.append(
            {
                "category": category,
                "title": definition["title"],
                "active_recommendation_id": active.id if active else None,
                "active_status": active.status if active else None,
                "history_count": len(category_history),
                "latest_started_at": category_history[0].started_at if category_history else None,
                "progress_score": progress["progress_score"] if progress else None,
                "completed_matches": progress["completed_matches"] if progress else 0,
                "target_matches": progress["target_matches"] if progress else TARGET_PERIOD_MATCHES,
            }
        )
    return summary


def _progress_for_recommendation(db: Session, recommendation: CoachRecommendation) -> dict[str, Any]:
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


def _new_system_recommendation(definition: dict[str, str], matches: list[Match]) -> CoachRecommendation:
    baseline_matches = matches[-BASELINE_PERIOD_MATCHES:]
    baseline_metrics = _aggregate_baseline(baseline_matches)
    baseline_ids = [match.id for match in baseline_matches]
    start_after_match_id = max((match.id for match in matches if match.id is not None), default=None)
    category = definition["category"]
    return CoachRecommendation(
        title=definition["title"],
        description=definition["description"],
        category=category,
        status="active",
        priority=definition["priority"],
        started_at=datetime.now(UTC).replace(tzinfo=None),
        target_period_matches=TARGET_PERIOD_MATCHES,
        baseline_period_matches=len(baseline_matches),
        start_after_match_id=start_after_match_id,
        baseline_metrics_json=json.dumps(baseline_metrics, ensure_ascii=False),
        target_metrics_json=json.dumps(_target_metrics(baseline_metrics, category), ensure_ascii=False),
        success_rules_json=json.dumps(_success_rules(category), ensure_ascii=False),
        failure_rules_json=json.dumps(_failure_rules(category), ensure_ascii=False),
        baseline_match_ids_json=json.dumps(baseline_ids),
        coach_comment=_coach_comment(category),
        created_by="system",
    )


def _definition_for_category(category: str) -> dict[str, str]:
    definition = next((item for item in RECOMMENDATION_DEFINITIONS if item["category"] == category), None)
    if definition is None:
        raise ValueError(f"Unsupported recommendation category: {category}")
    return definition


def _aggregate_baseline(matches: list[Match]) -> dict[str, float | int | None]:
    return {
        "matches_count": len(matches),
        "kd": _avg(matches, "kd"),
        "entry_deaths_per_match": _avg(matches, "entry_deaths"),
        "early_deaths_per_match": _avg(matches, "early_deaths"),
        "kast": _avg(matches, "kast"),
        "adr": _avg(matches, "adr"),
        "utility_damage": _avg(matches, "utility_damage"),
        "flash_assists": _avg(matches, "flash_assists"),
        "winrate": _winrate(matches),
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


def _target_metrics(baseline: dict[str, float | int | None], category: str) -> dict[str, str]:
    entry = baseline.get("entry_deaths_per_match")
    early = baseline.get("early_deaths_per_match")
    kast = baseline.get("kast")
    adr = baseline.get("adr")
    utility = baseline.get("utility_damage")
    flashes = baseline.get("flash_assists")
    winrate = baseline.get("winrate")
    targets = {
        "kast": f">={kast}" if kast is not None else "need data",
        "adr": f">={round(adr * 0.9, 2)}" if adr is not None else "need data",
    }
    if category == "survival":
        targets.update(
            {
                "entry_deaths_per_match": f"<={round(entry * 0.85, 2)}" if entry is not None else "need data",
                "early_deaths_per_match": f"<={round(early * 0.9, 2)}" if early is not None else "need data",
            }
        )
    elif category == "aim":
        targets["adr"] = f">={round(adr * 1.05, 2)}" if adr is not None else "need data"
    elif category == "grenades":
        targets["utility_damage"] = f">={round(utility * 1.2, 2)}" if utility is not None else "need data"
        targets["flash_assists"] = f">={round(flashes * 1.2, 2)}" if flashes is not None else "need data"
    elif category == "map":
        targets["winrate"] = f">={round(min(100, winrate + 5), 2)}" if winrate is not None else "need data"
        targets["entry_deaths_per_match"] = f"<={round(entry * 0.9, 2)}" if entry is not None else "need data"
    return targets


def _success_rules(category: str) -> list[str]:
    rules = {
        "survival": ["entry deaths ниже baseline", "early deaths ниже baseline", "KAST не ниже baseline"],
        "aim": ["ADR не ниже baseline", "KAST не ниже baseline"],
        "grenades": ["utility damage не ниже baseline", "flash assists не ниже baseline"],
        "map": ["матч выигран или entry deaths ниже baseline", "ADR не просел критично"],
    }
    return rules.get(category, ["метрики не хуже baseline"])


def _failure_rules(category: str) -> list[str]:
    rules = {
        "survival": ["entry deaths выше baseline", "early deaths выше baseline", "KAST ниже baseline"],
        "aim": ["ADR сильно ниже baseline", "KAST ниже baseline"],
        "grenades": ["utility damage ниже baseline", "flash assists ниже baseline"],
        "map": ["матч проигран и entry deaths выше baseline", "ADR сильно ниже baseline"],
    }
    return rules.get(category, ["метрики хуже baseline"])


def _coach_comment(category: str) -> str:
    comments = {
        "survival": "Следующие 10 матчей цель успешна, если первых смертей меньше baseline и impact не проседает.",
        "aim": "Следующие 10 матчей цель успешна, если ADR растёт без провала KAST.",
        "grenades": "Следующие 10 матчей цель успешна, если utility damage/flash assists дают больше value.",
        "map": "Следующие 10 матчей цель успешна, если слабые карты играются стабильнее и без раннего развала.",
    }
    return comments.get(category, "Следующие матчи оцениваются против baseline.")


def _match_evidence(match: Match) -> dict[str, float | int | str | None]:
    return {
        "result": match.result,
        "entry_deaths": match.entry_deaths,
        "early_deaths": match.early_deaths if match.early_deaths is not None else match.entry_deaths,
        "kast": match.kast,
        "adr": match.adr,
        "kd": match.kd,
        "utility_damage": match.utility_damage,
        "flash_assists": match.flash_assists,
    }


def _signals(
    evidence: dict[str, float | int | str | None],
    baseline: dict[str, float | int | None],
    category: str,
) -> tuple[list[str], list[str], list[str]]:
    positive: list[str] = []
    negative: list[str] = []
    missing: list[str] = []
    if category == "aim":
        _compare_adr(evidence, baseline, positive, negative, missing, 1.0, 0.9)
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
    elif category == "grenades":
        _compare_higher(
            evidence,
            baseline,
            "utility_damage",
            "utility_damage",
            "utility damage не ниже baseline",
            "utility damage ниже baseline",
            positive,
            negative,
            missing,
        )
        _compare_higher(
            evidence,
            baseline,
            "flash_assists",
            "flash_assists",
            "flash assists не ниже baseline",
            "flash assists ниже baseline",
            positive,
            negative,
            missing,
        )
    elif category == "map":
        if evidence.get("result") == "win":
            positive.append("матч выигран")
        elif evidence.get("result") == "loss":
            negative.append("матч проигран")
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
        _compare_adr(evidence, baseline, positive, negative, missing)
    else:
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
    category: str,
    positive: list[str],
    negative: list[str],
    missing: list[str],
) -> tuple[str, int, str]:
    if missing and len(missing) >= len(positive) + len(negative) + 1:
        return "gray", 0, f"Недостаточно данных для оценки цели `{category}` по этому матчу."
    score = max(0, min(100, 30 * len(positive) - 25 * len(negative) + 30))
    if len(positive) >= 2 and not negative:
        return "green", max(score, 82), _category_comment(category, "green")
    if len(negative) >= 2 and len(negative) > len(positive):
        return "red", min(score, 35), _category_comment(category, "red")
    return "yellow", max(45, min(score, 72)), _category_comment(category, "yellow")


def _category_comment(category: str, status: str) -> str:
    comments = {
        ("survival", "green"): "Хороший матч по survival: первых смертей меньше, impact не потерян.",
        ("survival", "yellow"): "Смешанный survival матч: часть дисциплины лучше, но стабильности нет.",
        ("survival", "red"): "Survival цель провалена: первые смерти или участие хуже baseline.",
        ("aim", "green"): "Aim цель выполняется: урон держится, KAST не просел.",
        ("aim", "yellow"): "Aim прогресс смешанный: impact есть, но недостаточно стабильно.",
        ("aim", "red"): "Aim цель провалена: ADR/KAST ниже baseline.",
        ("grenades", "green"): "Гранаты дали value лучше baseline.",
        ("grenades", "yellow"): "Utility value частичный: нужно больше повторяемых гранат.",
        ("grenades", "red"): "Utility цель провалена: гранаты почти не повлияли на матч.",
        ("map", "green"): "Карта сыграна по плану: результат или entry discipline лучше baseline.",
        ("map", "yellow"): "Карта смешанная: есть рабочие элементы, но без стабильности.",
        ("map", "red"): "Карта провалена: результат/entry/ADR требуют отдельного плана.",
    }
    return comments.get((category, status), "Матч оценен относительно baseline.")


def _compare_lower(
    evidence: dict[str, Any],
    baseline: dict[str, Any],
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
    evidence: dict[str, Any],
    baseline: dict[str, Any],
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
    evidence: dict[str, Any],
    baseline: dict[str, Any],
    positive: list[str],
    negative: list[str],
    missing: list[str],
    target_multiplier: float = 0.9,
    failure_multiplier: float = 0.85,
) -> None:
    adr = evidence.get("adr")
    baseline_adr = baseline.get("adr")
    if adr is None or baseline_adr is None:
        missing.append("adr")
        return
    if adr >= baseline_adr * target_multiplier:
        positive.append("ADR не ниже baseline")
    elif adr < baseline_adr * failure_multiplier:
        negative.append("ADR сильно ниже baseline")


def _aggregate_current_evaluations(evaluations: list[MatchRecommendationEvaluation]) -> dict[str, float | None]:
    evidence_items = [json.loads(evaluation.evidence_json) for evaluation in evaluations]
    return {
        "entry_deaths_per_match": _avg_dict(evidence_items, "entry_deaths"),
        "early_deaths_per_match": _avg_dict(evidence_items, "early_deaths"),
        "kast": _avg_dict(evidence_items, "kast"),
        "adr": _avg_dict(evidence_items, "adr"),
        "utility_damage": _avg_dict(evidence_items, "utility_damage"),
        "flash_assists": _avg_dict(evidence_items, "flash_assists"),
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
    return "Цель пока проваливается: нужны изменения в следующих матчах."


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


def _winrate(matches: list[Match]) -> float | None:
    if not matches:
        return None
    wins = sum(1 for match in matches if match.result == "win")
    return round(wins / len(matches) * 100, 2)
