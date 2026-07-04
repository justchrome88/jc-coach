from collections import namedtuple

import pytest

from app.services.steam_storage_guard import (
    STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
    STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED,
    SteamImportStorageBudget,
    SteamStorageBudgetExceeded,
)

DiskUsage = namedtuple("usage", ["total", "used", "free"])


def test_storage_preflight_passes_with_enough_free(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("STEAM_IMPORT_MIN_FREE_BYTES", "100")
    monkeypatch.setenv("STEAM_IMPORT_PRESERVE_FREE_BYTES", "50")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.steam_storage_guard.shutil.disk_usage",
        lambda _path: DiskUsage(total=1000, used=100, free=900),
    )
    try:
        budget = SteamImportStorageBudget()
        result = budget.preflight()
    finally:
        get_settings.cache_clear()

    assert result["filesystems"]["upload"]["free_bytes"] == 900


def test_storage_preflight_fails_below_min_free(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("STEAM_IMPORT_MIN_FREE_BYTES", "1000")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.steam_storage_guard.shutil.disk_usage",
        lambda _path: DiskUsage(total=1000, used=900, free=100),
    )
    try:
        budget = SteamImportStorageBudget()
        with pytest.raises(SteamStorageBudgetExceeded) as exc:
            budget.preflight()
    finally:
        get_settings.cache_clear()

    assert exc.value.status == STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED


def test_preserve_free_floor_blocks_operation(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("STEAM_IMPORT_MIN_FREE_BYTES", "0")
    monkeypatch.setenv("STEAM_IMPORT_PRESERVE_FREE_BYTES", "500")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.steam_storage_guard.shutil.disk_usage",
        lambda _path: DiskUsage(total=1000, used=600, free=400),
    )
    try:
        budget = SteamImportStorageBudget()
        with pytest.raises(SteamStorageBudgetExceeded) as exc:
            budget.ensure_temp_write(1, phase="download")
    finally:
        get_settings.cache_clear()

    assert exc.value.status == STEAM_IMPORT_DISK_BUDGET_EXCEEDED


def test_unknown_size_reserves_configured_bytes(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES", "700")
    monkeypatch.setenv("STEAM_IMPORT_MAX_BYTES_PER_JOB", "600")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.steam_storage_guard.shutil.disk_usage",
        lambda _path: DiskUsage(total=10_000, used=100, free=9_900),
    )
    try:
        budget = SteamImportStorageBudget()
        with pytest.raises(SteamStorageBudgetExceeded) as exc:
            budget.reserve_next_demo(expected_bytes=None)
    finally:
        get_settings.cache_clear()

    assert exc.value.status == STEAM_IMPORT_DISK_BUDGET_EXCEEDED
