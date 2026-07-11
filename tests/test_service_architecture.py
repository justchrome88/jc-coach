import importlib
from pathlib import Path

import pytest

from scripts.architecture_guardrails import (
    CANONICAL_MODULE_BY_LEGACY_MODULE,
    COMPATIBILITY_FACADES,
    SERVICE_PACKAGES,
    TARGET_PACKAGE_BY_LEGACY_MODULE,
    ImportGraph,
    api_domain_calculation_violations,
    architecture_violations,
    build_import_graph,
    canonical_domain_violations,
    contract_location_violations,
    facade_file_contains_logic,
    import_boundary_violations,
    mission_suppression_violations,
    private_cross_package_import_violations,
    root_service_module_violations,
    route_fingerprint,
    route_inventory,
    runtime_narrative_import_violations,
    strongly_connected_components,
)

EXPECTED_ROUTE_FINGERPRINT = "1daa112946fff309fbfb11f2593b4980dae977d15582143dd2f2be9364b90653"
R03_ALLOWLISTED_ROUTE_ADDITION = {
    "source": "web",
    "path": "/coach/domains/{domain}/activate",
    "methods": ["POST"],
    "name": "activate_coach_domain_page",
}


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
        canonical_public = set(
            getattr(
                canonical_module,
                "__all__",
                {name for name in vars(canonical_module) if not name.startswith("_") and name != "annotations"},
            )
        )
        assert canonical_public <= set(vars(legacy_module))


def test_registered_route_contract_matches_pre_refactor_baseline():
    assert len(route_inventory()) == 88
    assert R03_ALLOWLISTED_ROUTE_ADDITION in route_inventory()
    assert route_fingerprint() == EXPECTED_ROUTE_FINGERPRINT


def test_current_repository_passes_strict_architecture_guardrails():
    assert architecture_violations() == []


def test_cycle_detector_rejects_service_cycle(tmp_path):
    first = _write(tmp_path, "app/services/alpha.py", "import app.services.beta\n")
    second = _write(tmp_path, "app/services/beta.py", "import app.services.alpha\n")
    graph = build_import_graph([first, second], root=tmp_path)
    assert strongly_connected_components(graph, prefix="app.services") == [
        ["app.services.alpha", "app.services.beta"]
    ]


@pytest.mark.parametrize(
    ("source", "target", "reason"),
    [
        ("app.services.metrics.value", "app.services.coach.ai", "forbidden_dependency"),
        ("app.services.ingestion.steam", "app.services.missions.lifecycle", "forbidden_dependency"),
        ("app.services.parsing.demo", "app.services.coach.ai", "forbidden_dependency"),
        ("app.services.missions.lifecycle", "app.services.coach.provider", "missions_import_provider"),
    ],
)
def test_dependency_direction_rejects_forbidden_edges(source, target, reason):
    graph = ImportGraph(modules={source: Path("source.py"), target: Path("target.py")}, edges={source: {target}})
    assert any(item.startswith(reason) for item in import_boundary_violations(graph))


def test_root_service_allowlist_rejects_dumping_ground(tmp_path):
    service_root = tmp_path / "app/services"
    _write(tmp_path, "app/services/utils.py", "VALUE = 1\n")
    assert root_service_module_violations(service_root) == ["non_allowlisted_root_service_module:utils.py"]


def test_runtime_narrative_import_is_rejected(tmp_path):
    path = _write(tmp_path, "app/runtime.py", "import project_docs.architecture\n")
    assert runtime_narrative_import_violations([path], root=tmp_path)


def test_private_cross_package_import_is_rejected(tmp_path):
    path = _write(
        tmp_path,
        "app/services/metrics/value.py",
        "from app.services.coach.ai import _private_helper\n",
    )
    assert private_cross_package_import_violations([path], root=tmp_path)


def test_api_domain_calculation_is_rejected(tmp_path):
    path = _write(
        tmp_path,
        "app/api/routes/bad.py",
        "@router.get('/bad')\ndef bad(kills: int, deaths: int):\n    return kills / deaths\n",
    )
    assert api_domain_calculation_violations([path], root=tmp_path)


def test_compatibility_facade_with_business_logic_is_rejected(tmp_path):
    path = _write(
        tmp_path,
        "app/services/legacy.py",
        "from app.services.coach.ai import *\n\ndef calculate():\n    return 1\n",
    )
    assert facade_file_contains_logic(path) is True


def test_canonical_domain_guard_rejects_extra_domain():
    assert canonical_domain_violations(("impact_leak", "bad_fight_selection", "aim"))


def test_cross_domain_suppression_guard_requires_domain_keying():
    assert mission_suppression_violations("def suppress(active_missions): return bool(active_missions)")


def test_runtime_contract_outside_contract_root_is_rejected(tmp_path):
    _write(tmp_path, "app/services/runtime.json", "{}\n")
    assert contract_location_violations(tmp_path) == [
        "runtime_contract_outside_app_contracts:app/services/runtime.json"
    ]


def _write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
