"""Steam share-code parsing and decoding primitives."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

SHARE_CODE_DICTIONARY = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789"
SHARE_CODE_PATTERN = re.compile(rf"^(CSGO)?(-?[{SHARE_CODE_DICTIONARY}]{{5}}){{5}}$")
_BITMASK64 = 2**64 - 1


def parse_share_code_input(value: str) -> dict[str, Any]:
    text = value.strip()
    if not text:
        raise ValueError("Share code is required.")
    parsed = urlparse(text)
    if parsed.query:
        query = parse_qs(parsed.query)
        known_values = query.get("code") or query.get("sharecode") or query.get("match")
        if known_values:
            text = known_values[0]
    return {"share_code": text}


def decode_match_share_code(code: str) -> dict[str, int]:
    if not SHARE_CODE_PATTERN.match(code):
        raise ValueError("Invalid Steam match share code.")
    payload = re.sub(r"CSGO\-|\-", "", code)[::-1]
    number = 0
    for char in payload:
        number = number * len(SHARE_CODE_DICTIONARY) + SHARE_CODE_DICTIONARY.index(char)
    number = _swap_share_code_endianness(number)
    return {
        "matchid": number & _BITMASK64,
        "outcomeid": (number >> 64) & _BITMASK64,
        "token": (number >> 128) & 0xFFFF,
    }


def _swap_share_code_endianness(number: int) -> int:
    result = 0
    for offset in range(0, 144, 8):
        result = (result << 8) + ((number >> offset) & 0xFF)
    return result
