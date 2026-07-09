from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import get_settings

STEAM_IMPORT_DISK_BUDGET_EXCEEDED = "disk_budget_exceeded"
STEAM_IMPORT_BATCH_CAP_REACHED = "batch_cap_reached"
STEAM_IMPORT_DEMO_TOO_LARGE = "demo_too_large"
STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED = "storage_preflight_failed"
STEAM_IMPORT_UPLOAD_DIR_ON_SMALL_ROOT_WARNING = "upload_dir_on_small_root_warning"


class SteamStorageBudgetExceeded(RuntimeError):
    def __init__(self, message: str, *, status: str, budget: dict[str, Any]):
        super().__init__(message)
        self.status = status
        self.budget = budget


@dataclass(frozen=True)
class SteamStorageGuardSettings:
    max_demos_per_run: int
    max_bytes_per_job: int
    max_single_demo_bytes: int
    min_free_bytes: int
    preserve_free_bytes: int
    unknown_demo_reserve_bytes: int
    upload_dir: Path
    temp_dir: Path

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_demos_per_run": self.max_demos_per_run,
            "max_bytes_per_job": self.max_bytes_per_job,
            "max_single_demo_bytes": self.max_single_demo_bytes,
            "min_free_bytes": self.min_free_bytes,
            "preserve_free_bytes": self.preserve_free_bytes,
            "unknown_demo_reserve_bytes": self.unknown_demo_reserve_bytes,
            "upload_dir": str(self.upload_dir),
            "temp_dir": str(self.temp_dir),
        }


@dataclass
class SteamImportStorageBudget:
    settings: SteamStorageGuardSettings = field(default_factory=lambda: steam_storage_guard_settings())
    downloaded_bytes: int = 0
    decompressed_bytes: int = 0
    stored_bytes: int = 0

    @property
    def consumed_bytes(self) -> int:
        return self.downloaded_bytes + self.decompressed_bytes + self.stored_bytes

    def snapshot(self) -> dict[str, Any]:
        upload = storage_snapshot(self.settings.upload_dir)
        temp = storage_snapshot(self.settings.temp_dir)
        return {
            "settings": self.settings.as_dict(),
            "usage": {
                "downloaded_bytes": self.downloaded_bytes,
                "decompressed_bytes": self.decompressed_bytes,
                "stored_bytes": self.stored_bytes,
                "consumed_bytes": self.consumed_bytes,
                "remaining_job_bytes": max(0, self.settings.max_bytes_per_job - self.consumed_bytes),
            },
            "filesystems": {
                "upload": upload,
                "temp": temp,
                "same_filesystem": upload["device"] == temp["device"],
            },
            "warnings": storage_layout_warnings(upload, self.settings),
        }

    def preflight(self) -> dict[str, Any]:
        for path, label in ((self.settings.upload_dir, "upload_dir"), (self.settings.temp_dir, "temp_dir")):
            snapshot = storage_snapshot(path)
            _ensure_min_free(snapshot, self.settings.min_free_bytes, label, self.snapshot())
            _ensure_preserve_free(snapshot, 0, self.settings.preserve_free_bytes, label, self.snapshot())
        return self.snapshot()

    def reserve_next_demo(self, expected_bytes: int | None = None) -> dict[str, Any]:
        reserve = expected_bytes if expected_bytes is not None else self.settings.unknown_demo_reserve_bytes
        self.ensure_single_demo_size(expected_bytes)
        self.ensure_job_budget(reserve, phase="before_demo")
        for path, label in ((self.settings.upload_dir, "upload_dir"), (self.settings.temp_dir, "temp_dir")):
            _ensure_preserve_free(
                storage_snapshot(path),
                reserve,
                self.settings.preserve_free_bytes,
                label,
                self.snapshot(),
            )
        return self.snapshot()

    def ensure_single_demo_size(self, size_bytes: int | None) -> None:
        if size_bytes is None:
            return
        if size_bytes > self.settings.max_single_demo_bytes:
            raise SteamStorageBudgetExceeded(
                f"Demo is too large for configured import limit: {size_bytes} bytes.",
                status=STEAM_IMPORT_DEMO_TOO_LARGE,
                budget=self.snapshot(),
            )

    def ensure_job_budget(self, additional_bytes: int, *, phase: str) -> None:
        if self.consumed_bytes + additional_bytes > self.settings.max_bytes_per_job:
            raise SteamStorageBudgetExceeded(
                f"Steam import job byte budget exceeded during {phase}.",
                status=STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
                budget=self.snapshot(),
            )

    def ensure_temp_write(self, additional_bytes: int, *, phase: str) -> None:
        self.ensure_job_budget(additional_bytes, phase=phase)
        _ensure_preserve_free(
            storage_snapshot(self.settings.temp_dir),
            additional_bytes,
            self.settings.preserve_free_bytes,
            "temp_dir",
            self.snapshot(),
        )

    def ensure_upload_write(self, additional_bytes: int, *, phase: str) -> None:
        self.ensure_job_budget(additional_bytes, phase=phase)
        _ensure_preserve_free(
            storage_snapshot(self.settings.upload_dir),
            additional_bytes,
            self.settings.preserve_free_bytes,
            "upload_dir",
            self.snapshot(),
        )

    def record_downloaded(self, size_bytes: int) -> None:
        self.downloaded_bytes += max(0, size_bytes)

    def record_decompressed(self, size_bytes: int) -> None:
        self.decompressed_bytes += max(0, size_bytes)

    def record_stored(self, size_bytes: int) -> None:
        self.stored_bytes += max(0, size_bytes)


def steam_storage_guard_settings() -> SteamStorageGuardSettings:
    settings = get_settings()
    max_demos = max(1, int(settings.steam_import_max_demos_per_run))
    return SteamStorageGuardSettings(
        max_demos_per_run=max_demos,
        max_bytes_per_job=max(1, int(settings.steam_import_max_bytes_per_job)),
        max_single_demo_bytes=max(1, int(settings.steam_import_max_single_demo_bytes)),
        min_free_bytes=max(0, int(settings.steam_import_min_free_bytes)),
        preserve_free_bytes=max(0, int(settings.steam_import_preserve_free_bytes)),
        unknown_demo_reserve_bytes=max(1, int(settings.steam_import_unknown_demo_reserve_bytes)),
        upload_dir=Path(settings.upload_dir).resolve(),
        temp_dir=Path(settings.temp_dir).resolve(),
    )


def storage_snapshot(path: Path) -> dict[str, Any]:
    path.mkdir(parents=True, exist_ok=True)
    resolved = path.resolve()
    usage = shutil.disk_usage(resolved)
    return {
        "path": str(resolved),
        "device": os.stat(resolved).st_dev,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def storage_layout_warnings(upload_snapshot: dict[str, Any], settings: SteamStorageGuardSettings) -> list[str]:
    warnings: list[str] = []
    upload_path = Path(str(upload_snapshot["path"]))
    if upload_path.is_relative_to(Path("/")) and upload_snapshot["total_bytes"] < 50 * 1024**3:
        warnings.append(STEAM_IMPORT_UPLOAD_DIR_ON_SMALL_ROOT_WARNING)
    if upload_snapshot["free_bytes"] < settings.min_free_bytes:
        warnings.append(STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED)
    return warnings


def _ensure_min_free(snapshot: dict[str, Any], min_free_bytes: int, label: str, budget: dict[str, Any]) -> None:
    if snapshot["free_bytes"] < min_free_bytes:
        raise SteamStorageBudgetExceeded(
            f"Steam import storage preflight failed for {label}: free space is below minimum.",
            status=STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED,
            budget=budget,
        )


def _ensure_preserve_free(
    snapshot: dict[str, Any],
    additional_bytes: int,
    preserve_free_bytes: int,
    label: str,
    budget: dict[str, Any],
) -> None:
    if snapshot["free_bytes"] - additional_bytes < preserve_free_bytes:
        raise SteamStorageBudgetExceeded(
            f"Steam import disk budget exceeded for {label}: preserve-free floor would be crossed.",
            status=STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
            budget=budget,
        )
