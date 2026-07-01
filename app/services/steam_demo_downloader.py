from __future__ import annotations

import bz2
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR, get_settings
from app.db.models import Match
from app.services.demo_parser import DemoParseError, import_demo_file
from app.services.steam_integration import decode_match_share_code


class SteamDemoDownloadError(RuntimeError):
    pass


def steam_demo_downloader_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.steam_bot_refresh_token
        or (settings.steam_bot_username and settings.steam_bot_password)
    )


def download_pending_steam_demos(
    db: Session,
    limit: int = 10,
    player_identifier: str | None = None,
) -> dict[str, Any]:
    matches = _pending_steam_history_matches(db, limit=limit)
    if not matches:
        return {
            "configured": steam_demo_downloader_configured(),
            "processed": 0,
            "imported": 0,
            "failed": 0,
            "results": [],
        }
    if not steam_demo_downloader_configured():
        return {
            "configured": False,
            "processed": 0,
            "imported": 0,
            "failed": 0,
            "pending": len(matches),
            "results": [],
            "message": "Steam service bot is not configured.",
        }

    share_codes = [_share_code_for_match(match) for match in matches]
    metadata = _fetch_demo_urls(share_codes)
    by_share_code = {item.get("share_code"): item for item in metadata.get("results", []) if item.get("share_code")}

    results = []
    imported = failed = 0
    for match in matches:
        share_code = _share_code_for_match(match)
        item = by_share_code.get(share_code) or {"ok": False, "error": "Steam bot did not return this share code."}
        try:
            if not item.get("ok"):
                message = item.get("error") or item.get("code") or "Could not resolve demo URL."
                raise SteamDemoDownloadError(str(message))
            result = _download_and_import_match(
                db,
                match,
                share_code=share_code,
                demo_url=str(item["demo_url"]),
                player_identifier=player_identifier,
            )
            imported += 1 if result.get("imported") else 0
            results.append(result)
        except Exception as exc:
            failed += 1
            _mark_match_download_error(db, match, str(exc))
            results.append({"match_id": match.id, "share_code": share_code, "status": "failed", "error": str(exc)})

    return {
        "configured": True,
        "processed": len(matches),
        "imported": imported,
        "failed": failed,
        "results": results,
    }


def _pending_steam_history_matches(db: Session, limit: int) -> list[Match]:
    target_limit = max(1, min(limit, 50))
    rows = db.scalars(
        select(Match)
        .where(Match.source == "steam_history")
        .where(Match.demo_file.is_(None))
        .order_by(Match.id.asc())
        .limit(max(target_limit * 5, 25))
    ).all()
    matches = [
        match
        for match in rows
        if _share_code_for_match(match) and _match_raw(match).get("status") != "demo_download_error"
    ]
    return matches[:target_limit]


def _download_and_import_match(
    db: Session,
    match: Match,
    share_code: str,
    demo_url: str,
    player_identifier: str | None,
) -> dict[str, Any]:
    decoded = decode_match_share_code(share_code)
    demo_path = _download_demo_file(demo_url, share_code)
    try:
        import_result = import_demo_file(
            db,
            demo_path,
            original_filename=f"{share_code}.dem",
            player_identifier=player_identifier,
        )
    except DemoParseError as exc:
        raise SteamDemoDownloadError(f"Downloaded demo but parser failed: {exc}") from exc
    finally:
        shutil.rmtree(demo_path.parent, ignore_errors=True)

    db.refresh(match)
    raw = _match_raw(match)
    raw.update(
        {
            "status": "demo_imported",
            "download_method": "steam_service_bot",
            "decoded": decoded,
            "demo_url_host": urlparse(demo_url).netloc,
            "imported_demo_match_id": import_result.get("match_id"),
            "imported_at": datetime.now(UTC).isoformat(),
            "next_step": None,
        }
    )
    match.demo_file = import_result.get("stored_path")
    match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
    db.commit()
    return {
        "match_id": match.id,
        "share_code": share_code,
        "status": "imported",
        "demo_match_id": import_result.get("match_id"),
        "imported": import_result.get("imported", 0),
        "duplicate": import_result.get("skipped_duplicates", 0),
    }


def _fetch_demo_urls(share_codes: list[str]) -> dict[str, Any]:
    helper = BASE_DIR / "tools" / "steam-gc" / "fetch-demo-urls.js"
    if not helper.exists():
        raise SteamDemoDownloadError("Steam service bot helper is not installed.")

    settings = get_settings()
    credential_dir = BASE_DIR / "data" / "steam_bot_credentials"
    credential_dir.mkdir(parents=True, exist_ok=True)
    credential_dir.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "STEAM_BOT_CREDENTIAL_DIR": str(credential_dir),
            "STEAM_BOT_TIMEOUT_MS": str(max(5, settings.steam_bot_timeout_seconds) * 1000),
        }
    )
    optional_env = {
        "STEAM_BOT_USERNAME": settings.steam_bot_username,
        "STEAM_BOT_PASSWORD": settings.steam_bot_password,
        "STEAM_BOT_SHARED_SECRET": settings.steam_bot_shared_secret,
        "STEAM_BOT_TWO_FACTOR_CODE": settings.steam_bot_two_factor_code,
        "STEAM_BOT_REFRESH_TOKEN": settings.steam_bot_refresh_token,
    }
    for key, value in optional_env.items():
        if value:
            env[key] = value

    result = subprocess.run(
        ["node", str(helper)],
        cwd=str(helper.parent),
        env=env,
        input=json.dumps({"share_codes": share_codes}, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=max(10, settings.steam_bot_timeout_seconds + 10),
        check=False,
    )
    output = (result.stdout or "").strip().splitlines()[-1:] or [""]
    try:
        payload = json.loads(output[0])
    except json.JSONDecodeError as exc:
        message = (result.stderr or result.stdout or "Steam service bot helper did not return JSON.").strip()
        raise SteamDemoDownloadError(message) from exc
    if result.returncode != 0 or not payload.get("ok"):
        raise SteamDemoDownloadError(str(payload.get("error") or payload.get("code") or "Steam service bot failed."))
    return payload


def _download_demo_file(url: str, share_code: str) -> Path:
    if not url.startswith(("http://", "https://")):
        raise SteamDemoDownloadError("Steam service bot returned an invalid demo URL.")
    suffix = ".dem.bz2" if url.endswith(".bz2") else ".dem"
    safe_share = share_code.replace("/", "_")
    temp_dir = Path(tempfile.mkdtemp(prefix="jc-steam-demo-"))
    archive_path = temp_dir / f"{safe_share}{suffix}"
    demo_path = temp_dir / f"{safe_share}.dem"
    request = Request(url, headers={"User-Agent": "jc-coach/0.1"})
    try:
        with urlopen(request, timeout=120) as response:
            archive_path.write_bytes(response.read())
    except HTTPError as exc:
        if exc.code in {404, 410, 502}:
            raise SteamDemoDownloadError(
                f"Valve replay CDN returned HTTP {exc.code}; the demo is likely expired or temporarily unavailable."
            ) from exc
        raise
    if archive_path.suffix == ".bz2":
        demo_path.write_bytes(bz2.decompress(archive_path.read_bytes()))
        archive_path.unlink(missing_ok=True)
        return demo_path
    return archive_path


def _mark_match_download_error(db: Session, match: Match, message: str) -> None:
    raw = _match_raw(match)
    raw.update({"status": "demo_download_error", "error": message, "failed_at": datetime.now(UTC).isoformat()})
    match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
    db.commit()


def _share_code_for_match(match: Match) -> str:
    raw = _match_raw(match)
    return str(raw.get("share_code") or match.external_match_id or "").strip()


def _match_raw(match: Match) -> dict[str, Any]:
    try:
        raw = json.loads(match.raw_json or "{}")
    except json.JSONDecodeError:
        raw = {}
    return raw if isinstance(raw, dict) else {}
