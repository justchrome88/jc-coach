import importlib
from pathlib import Path

from scripts.architecture_guardrails import (
    CANONICAL_MODULE_BY_LEGACY_MODULE,
    COMPATIBILITY_FACADES,
    SERVICE_PACKAGES,
    TARGET_PACKAGE_BY_LEGACY_MODULE,
    route_fingerprint,
    route_inventory,
)

EXPECTED_ROUTE_FINGERPRINT = "92cfbaef7254c8b2ed5284876ebd5ceeff3285dbb6e03946649c32c958403168"


def test_target_service_packages_are_shallow_and_explicit():
    root = Path("app/services")
    assert set(SERVICE_PACKAGES) == {"ingestion", "parsing", "metrics", "coach", "missions", "owner", "shared"}
    for package in SERVICE_PACKAGES:
        assert (root / package / "__init__.py").is_file()
    assert set(TARGET_PACKAGE_BY_LEGACY_MODULE) == set(CANONICAL_MODULE_BY_LEGACY_MODULE)
    for module in CANONICAL_MODULE_BY_LEGACY_MODULE.values():
        assert Path(*module.split(".")).with_suffix(".py").is_file()


def test_temporary_compatibility_facades_import_canonical_public_symbols():
    for legacy, canonical in COMPATIBILITY_FACADES.items():
        legacy_module = importlib.import_module(legacy)
        canonical_module = importlib.import_module(canonical)
        canonical_public = {
            name for name in vars(canonical_module) if not name.startswith("_") and name not in {"annotations"}
        }
        assert canonical_public <= set(vars(legacy_module))


def test_registered_route_contract_matches_pre_refactor_baseline():
    assert len(route_inventory()) == 87
    assert route_fingerprint() == EXPECTED_ROUTE_FINGERPRINT
