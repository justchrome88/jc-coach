"""Shared persistence queries for playable matches."""

from __future__ import annotations

from sqlalchemy import Select, select

from app.db.models import Match

NON_PLAYABLE_MATCH_SOURCES = {"steam_history"}


def playable_match_select() -> Select[tuple[Match]]:
    return select(Match).where(Match.source.not_in(NON_PLAYABLE_MATCH_SOURCES))


def is_playable_match(match: Match) -> bool:
    return match.source not in NON_PLAYABLE_MATCH_SOURCES
