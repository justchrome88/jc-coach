from pathlib import Path

from scripts.architecture_guardrails import (
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
    assert set(TARGET_PACKAGE_BY_LEGACY_MODULE) == {
        path.stem for path in root.glob("*.py") if path.name != "__init__.py"
    }


def test_registered_route_contract_matches_pre_refactor_baseline():
    assert len(route_inventory()) == 87
    assert route_fingerprint() == EXPECTED_ROUTE_FINGERPRINT
