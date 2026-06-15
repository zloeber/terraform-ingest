"""Tests for prepush-gate planning and helpers."""

import importlib.util
import json
import sys
from pathlib import Path


def _prepush_gate_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "prepush-gate.py"
    spec = importlib.util.spec_from_file_location("prepush_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load prepush-gate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["prepush_gate"] = module
    spec.loader.exec_module(module)
    return module


def test_security_scan_plan_full_when_unknown() -> None:
    gate = _prepush_gate_module()
    assert gate.security_scan_plan(None) == (True, True, True)
    assert gate.security_scan_plan(set()) == (True, True, True)


def test_security_scan_plan_deps_triggers_sync() -> None:
    gate = _prepush_gate_module()
    assert gate.security_scan_plan({"pyproject.toml"}) == (True, True, True)
    assert gate.security_scan_plan({"uv.lock"}) == (True, True, True)


def test_security_scan_plan_src_without_sync() -> None:
    gate = _prepush_gate_module()
    assert gate.security_scan_plan({"src/terraform_ingest/cli.py"}) == (
        False,
        True,
        True,
    )


def test_security_scan_plan_skips_docs_only() -> None:
    gate = _prepush_gate_module()
    assert gate.security_scan_plan({"docs/dev.md", "README.md"}) == (
        False,
        False,
        False,
    )


def test_should_validate_server_json_when_relevant() -> None:
    gate = _prepush_gate_module()
    assert gate.should_validate_server_json({"docs/dev.md"}) is False
    assert gate.should_validate_server_json({"server.json"}) is True
    assert gate.should_validate_server_json({"src/terraform_ingest/cli.py"}) is True


def test_is_docs_only_true_for_markdown_and_docs_tree() -> None:
    gate = _prepush_gate_module()
    assert gate.is_docs_only({"docs/dev.md", "mkdocs.yml", ".mex/ROUTER.md"})
    assert gate.is_docs_only({"README.md"})


def test_is_docs_only_false_when_src_changes() -> None:
    gate = _prepush_gate_module()
    assert not gate.is_docs_only({"docs/dev.md", "src/terraform_ingest/cli.py"})


def test_pytest_targets_maps_src_module_to_test_file() -> None:
    gate = _prepush_gate_module()
    targets = gate.pytest_targets({"src/terraform_ingest/models.py"})
    assert targets == ["tests/test_models.py"]


def test_pytest_targets_includes_direct_test_changes() -> None:
    gate = _prepush_gate_module()
    targets = gate.pytest_targets({"tests/test_api.py"})
    assert targets == ["tests/test_api.py"]


def test_pytest_targets_falls_back_for_unmapped_src() -> None:
    gate = _prepush_gate_module()
    assert gate.pytest_targets({"src/terraform_ingest/cli.py"}) == []


def test_should_build_docker_when_packaging_changes() -> None:
    gate = _prepush_gate_module()
    assert gate.should_build_docker({"Dockerfile"}, docs_only=False)
    assert gate.should_build_docker(
        {"skills/terraform-ingest/SKILL.md"}, docs_only=False
    )
    assert gate.should_build_docker({"src/terraform_ingest/cli.py"}, docs_only=False)
    assert not gate.should_build_docker({"docs/dev.md"}, docs_only=False)
    assert not gate.should_build_docker({"tests/test_api.py"}, docs_only=False)
    assert not gate.should_build_docker({"docs/dev.md"}, docs_only=True)


def test_docker_build_cmd_uses_pep440_dev_version() -> None:
    gate = _prepush_gate_module()
    cmd = gate.docker_build_cmd()
    assert cmd[:3] == ["docker", "build", "--target"]
    assert "builder-slim" in cmd
    version_arg = next(arg for arg in cmd if arg.startswith("DEPLOY_VERSION="))
    assert version_arg.startswith("DEPLOY_VERSION=0.0.0.dev0+g")


def test_gate_summary_writes_json(tmp_path: Path) -> None:
    gate = _prepush_gate_module()
    summary = gate.GateSummary(
        mode="quick",
        passed=True,
        failed_stage=None,
        docs_only=False,
        round=1,
        stages={"lint": "pass"},
    )
    out = tmp_path / "summary.json"
    summary.write(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["mode"] == "quick"
    assert data["passed"] is True
    assert data["stages"]["lint"] == "pass"
