from __future__ import annotations

import shutil
from pathlib import Path

from scripts import r02a2_repository_guardrails as guardrails


def _write(root: Path, relative: str, content: str = "fixture\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _domain_source(
    *,
    domains: tuple[str, ...] = guardrails.CANONICAL_COACH_DOMAINS,
    model: str = guardrails.ACTIVE_MISSION_MODEL,
    include_invariant: bool = True,
) -> str:
    invariants = (guardrails.DOMAIN_SUPPRESSION_INVARIANT,) if include_invariant else ()
    return (
        f"CANONICAL_COACH_DOMAINS = {domains!r}\n"
        f"ACTIVE_MISSION_MODEL = {model!r}\n"
        f"COACH_DOMAIN_INVARIANTS = {invariants!r}\n"
    )


def test_current_repository_passes_all_r02a2_guardrails():
    assert guardrails.collect_errors() == []


def test_docs_shell_rejects_extra_narrative_and_runtime_contracts(tmp_path):
    _write(tmp_path, "docs/README.md", "# Current narrative\n")
    _write(tmp_path, "docs/current.schema.json", "{}\n")
    errors = guardrails.layout_errors(
        tmp_path,
        {"docs/README.md", "docs/current.schema.json"},
    )
    codes = {error.code for error in errors}
    assert "current_narrative_under_docs" in codes
    assert "docs_file_not_allowlisted" in codes
    assert "runtime_contract_under_docs" in codes


def test_docs_shell_rejects_more_than_six_files(tmp_path):
    paths = {f"docs/extra-{index}.md" for index in range(7)}
    for path in paths:
        _write(tmp_path, path, "DO NOT WRITE\n")
    errors = guardrails.layout_errors(tmp_path, paths)
    assert "docs_file_count_exceeded" in {error.code for error in errors}


def test_project_docs_rejects_runtime_prompts_and_schemas(tmp_path):
    paths = {
        "project_docs/product/current_prompt.md",
        "project_docs/architecture/runtime.schema.json",
    }
    for path in paths:
        _write(tmp_path, path)
    errors = guardrails.layout_errors(tmp_path, paths)
    assert {error.code for error in errors} == {"runtime_material_under_project_docs"}


def test_new_root_service_module_requires_architecture_policy(tmp_path):
    _write(tmp_path, "app/services/unplanned_boundary.py")
    errors = guardrails.layout_errors(tmp_path, {"app/services/unplanned_boundary.py"})
    assert [error.code for error in errors] == ["root_service_module_not_allowlisted"]


def test_ast_guard_rejects_runtime_docs_and_archive_reads(tmp_path):
    _write(
        tmp_path,
        "app/services/runtime_reader.py",
        "from pathlib import Path\n"
        "Path('docs/CURRENT_STATUS.md').read_text()\n"
        "Path('_legacy_archive/evidence.json').read_bytes()\n",
    )
    errors = guardrails.python_io_errors(tmp_path, {"app/services/runtime_reader.py"})
    assert {error.code for error in errors} == {"runtime_docs_read", "runtime_archive_read"}


def test_ast_guard_rejects_active_control_archive_reads_and_docs_writers(tmp_path):
    _write(
        tmp_path,
        "scripts/active_control.py",
        "from pathlib import Path\n"
        "Path('_legacy_archive/state.json').read_text()\n"
        "Path('docs/HANDOFF.md').write_text('current')\n",
    )
    errors = guardrails.python_io_errors(tmp_path, {"scripts/active_control.py"})
    assert {error.code for error in errors} == {"active_control_archive_read", "docs_stub_writer"}


def test_archived_text_is_not_scanned_for_active_path_false_positives(tmp_path):
    _write(
        tmp_path,
        "_legacy_archive/report.md",
        "Path('docs/CURRENT_STATUS.md').read_text()\n",
    )
    assert guardrails.python_io_errors(tmp_path, {"_legacy_archive/report.md"}) == []


def test_domain_guard_rejects_third_domain_and_global_suppression(tmp_path):
    _write(
        tmp_path,
        "app/services/coach_domain_model.py",
        _domain_source(
            domains=("impact_leak", "bad_fight_selection", "aim"),
            model="one_active_mission_per_owner",
            include_invariant=False,
        ),
    )
    errors = guardrails.domain_policy_errors(tmp_path)
    assert {error.code for error in errors} == {
        "noncanonical_coach_domains",
        "global_cross_domain_mission_suppression",
    }


def test_domain_guard_accepts_two_domains_and_per_domain_suppression(tmp_path):
    _write(tmp_path, "app/services/coach_domain_model.py", _domain_source())
    assert guardrails.domain_policy_errors(tmp_path) == []


def test_agent_principle_guard_rejects_incomplete_matrix_and_stale_commit_policy(tmp_path):
    _write(
        tmp_path,
        "project_control/manifests/AGENT_PRINCIPLE_PARITY.md",
        "| Principle | Old source | New canonical source | Disposition |\n"
        "|---|---|---|---|\n"
        "| no push | old | new | same |\n\n"
        "Parity result: `PASS`.\n",
    )
    _write(
        tmp_path,
        "project_control/agents/PROJECT_OPERATING_PROTOCOL.md",
        "User performs\n`git add`, commit and push.\n",
    )
    errors = guardrails.agent_principle_parity_errors(tmp_path)
    assert {error.code for error in errors} == {
        "agent_principle_matrix_incomplete",
        "conflicting_active_agent_principle",
    }


def test_durable_docs_reject_current_routing_but_allow_explicit_history(tmp_path):
    path = "project_docs/product/example.md"
    _write(
        tmp_path,
        path,
        "# Example\n\n## Historical Decisions\n\nCURRENT_TASK: OLD_TASK\n",
    )
    assert guardrails.durable_doc_route_errors(tmp_path) == []

    _write(
        tmp_path,
        path,
        "# Example\n\nNEXT_TASK: ACTIVE_ROUTE\n\n"
        "## Superseded Route\n\nThe required next lane was OLD_LANE.\n",
    )
    errors = guardrails.durable_doc_route_errors(tmp_path)
    assert [error.code for error in errors] == ["dynamic_route_in_durable_docs"]


def test_current_document_contract_rejects_semantic_regressions(tmp_path):
    shutil.copytree(guardrails.ROOT / "project_docs", tmp_path / "project_docs")

    ai = tmp_path / "project_docs/product/AI_COACH.md"
    ai.write_text(
        ai.read_text(encoding="utf-8")
        .replace("versioned domain prompts", "domain prompts without versions")
        .replace("bounded aggregate", "aggregate")
        + "\nPrompt versioning remains future work.\n",
        encoding="utf-8",
    )
    steam = tmp_path / "project_docs/operations/STEAM_IMPORT.md"
    steam.write_text(
        steam.read_text(encoding="utf-8").replace(
            "Steam import is accepted with warnings for controlled personal use.",
            "Steam import acceptance is blocked.",
        ),
        encoding="utf-8",
    )
    testing = tmp_path / "project_docs/operations/TESTING.md"
    testing.write_text(
        testing.read_text(encoding="utf-8").replace(
            "accepted general local CI-equivalent",
            "accepted local CI-equivalent gate during the restricted foundation-hardening lane; legacy",
        ),
        encoding="utf-8",
    )
    domain = tmp_path / "project_docs/product/CANONICAL_COACH_DOMAIN_MODEL.md"
    domain.write_text(
        domain.read_text(encoding="utf-8").replace("exactly two MVP coach domains", "three MVP coach domains"),
        encoding="utf-8",
    )

    codes = {error.code for error in guardrails.current_document_contract_errors(tmp_path)}
    assert {
        "current_domain_document_parity",
        "trade_document_missing_bounded_capability",
        "ai_contract_documentation_parity",
        "implemented_ai_contract_described_as_future",
        "steam_import_documentation_parity",
        "testing_documentation_parity",
    } <= codes
