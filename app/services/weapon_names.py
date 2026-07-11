from __future__ import annotations

_ALIASES = {
    "ak47": "ak47",
    "weapon_ak47": "ak47",
    "m4a1": "m4a1",
    "weapon_m4a1": "m4a1",
    "m4a1_silencer": "m4a1_silencer",
    "weapon_m4a1_silencer": "m4a1_silencer",
}


def canonical_weapon_name(raw_name: object) -> str | None:
    if raw_name is None:
        return None
    normalized = str(raw_name).strip().lower()
    if not normalized:
        return None
    return _ALIASES.get(normalized, normalized.removeprefix("weapon_"))
