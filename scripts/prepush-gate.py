#!/usr/bin/env python3
"""Cross-agent pre-push quality gate runner."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

LOGS_DIR = Path(".terraform-ingest")
SUMMARY_PATH = LOGS_DIR / "summary.json"

SECURITY_DEP_FILES = frozenset({"pyproject.toml", "uv.lock"})
SECURITY_SRC_PREFIX = "src/"

DOCKER_RELEVANT_FILES = frozenset(
    {"Dockerfile", ".dockerignore", "pyproject.toml", "uv.lock", "README.md"}
)
DOCKER_RELEVANT_PREFIXES = ("src/", "skills/")

NON_DOCS_PREFIXES = (
    "src/",
    "tests/",
    "scripts/",
    "skills/",
    ".github/workflows/",
)
NON_DOCS_FILES = frozenset(
    {
        "pyproject.toml",
        "uv.lock",
        "Taskfile.yml",
        "server.json",
        "pytest.ini",
    }
)

StageStatus = Literal["pass", "fail", "skip"]


@dataclass
class GateSummary:
    mode: Literal["quick", "full"]
    passed: bool
    failed_stage: str | None
    docs_only: bool
    round: int
    stages: dict[str, StageStatus] = field(default_factory=dict)
    stage_logs: dict[str, str] = field(default_factory=dict)
    changed_paths: list[str] = field(default_factory=list)
    pytest_targets: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def write(self, path: Path = SUMMARY_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")


def run_step(
    name: str,
    cmd: list[str],
    logs_dir: Path,
    *,
    verbose: bool,
    shell: bool = False,
) -> bool:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{name}.log"
    print(f"==> {name}")
    with log_path.open("w", encoding="utf-8") as log_file:
        completed = subprocess.run(
            cmd if not shell else " ".join(cmd),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            shell=shell,
            text=True,
            check=False,
        )
    if completed.returncode == 0:
        print(f"PASS: {name}")
        return True
    print(f"FAIL: {name}")
    if verbose:
        print(f"--- last output ({log_path}) ---")
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-40:]:
            print(line)
        print("--- end output ---")
    return False


def skip_step(name: str, reason: str) -> bool:
    print(f"SKIP: {name} ({reason})")
    return True


def resolve_script_cmd(script_name: str) -> list[str]:
    if shutil.which("uv"):
        return ["uv", "run", "python", f"scripts/{script_name}"]
    return [sys.executable, f"scripts/{script_name}"]


def _git_lines(args: list[str]) -> list[str] | None:
    if not shutil.which("git") or not Path(".git").exists():
        return None
    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def changed_paths() -> set[str] | None:
    """Collect changed paths; None means run the full pipeline."""
    chunks: list[str] = []
    for spec in (
        ["diff", "--name-only", "HEAD"],
        ["diff", "--cached", "--name-only"],
    ):
        lines = _git_lines(spec)
        if lines is None:
            return None
        chunks.extend(lines)
    upstream = _git_lines(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if upstream:
        branch_diff = _git_lines(["diff", "--name-only", f"{upstream[0]}...HEAD"])
        if branch_diff is None:
            return None
        chunks.extend(branch_diff)
    return set(chunks)


def is_docs_only(changed: set[str]) -> bool:
    """True when every changed path is documentation or scaffold prose."""
    if not changed:
        return False
    for path in changed:
        if any(path.startswith(prefix) for prefix in NON_DOCS_PREFIXES):
            return False
        if path in NON_DOCS_FILES:
            return False
        if path.startswith("docs/"):
            continue
        if path.endswith(".md"):
            continue
        if path == "mkdocs.yml":
            continue
        if path.startswith(".mex/"):
            continue
        return False
    return True


def should_validate_skills(changed: set[str] | None, docs_only: bool) -> bool:
    if not Path("skills").is_dir():
        return False
    if changed is None or not changed:
        return True
    if docs_only:
        return any(path.startswith("skills/") for path in changed)
    return True


def security_scan_plan(changed: set[str] | None) -> tuple[bool, bool, bool]:
    """Return (sync_deps, pip_audit, bandit) for context-aware security."""
    if changed is None or not changed:
        return (True, True, True)
    deps = any(path in SECURITY_DEP_FILES for path in changed)
    src = any(path.startswith(SECURITY_SRC_PREFIX) for path in changed)
    if deps:
        return (True, True, True)
    if src:
        return (False, True, True)
    return (False, False, False)


def should_validate_server_json(changed: set[str] | None) -> bool:
    if not Path("server.json").exists():
        return False
    if changed is None or not changed:
        return True
    return any(
        path == "server.json" or path.startswith(SECURITY_SRC_PREFIX)
        for path in changed
    )


def should_build_docker(changed: set[str] | None, docs_only: bool) -> bool:
    """Run builder-slim when packaging inputs changed; skip docs-only and unrelated diffs."""
    if docs_only or not Path("Dockerfile").is_file():
        return False
    if changed is None or not changed:
        return True
    normalized = {Path(path).as_posix() for path in changed}
    return any(
        path in DOCKER_RELEVANT_FILES
        or any(path.startswith(prefix) for prefix in DOCKER_RELEVANT_PREFIXES)
        for path in normalized
    )


def docker_build_cmd() -> list[str]:
    """Validate the slim builder stage with the same PEP 440 dev version CI uses."""
    sha = "local"
    if shutil.which("git") and Path(".git").exists():
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            sha = completed.stdout.strip()
    version = f"0.0.0.dev0+g{sha}"
    return [
        "docker",
        "build",
        "--target",
        "builder-slim",
        "--build-arg",
        f"DEPLOY_VERSION={version}",
        "-f",
        "Dockerfile",
        ".",
    ]


def docker_build_skip_reason(changed: set[str] | None, docs_only: bool) -> str | None:
    if not Path("Dockerfile").is_file():
        return "no Dockerfile"
    if docs_only:
        return "docs-only diff"
    if should_build_docker(changed, docs_only=False):
        return None
    return "no Docker packaging changes"


def pytest_targets(changed: set[str] | None) -> list[str]:
    """Map changed files to pytest paths; empty list means run the full suite."""
    if changed is None:
        return []
    targets: set[str] = set()
    unmapped_src = False
    for raw_path in changed:
        path = Path(raw_path).as_posix()
        if path.startswith("tests/") and path.endswith(".py"):
            targets.add(path)
            continue
        if not path.startswith("src/terraform_ingest/") or not path.endswith(".py"):
            continue
        module = Path(path).name.removesuffix(".py")
        candidate = Path("tests") / f"test_{module}.py"
        if candidate.is_file():
            targets.add(candidate.as_posix())
        else:
            unmapped_src = True
    if unmapped_src:
        return []
    return sorted(targets)


def targeted_test_cmd(changed: set[str] | None) -> list[str]:
    targets = pytest_targets(changed)
    if not targets:
        return ["task", "test"]
    return [
        "uv",
        "run",
        "pytest",
        "--maxfail=1",
        "--disable-warnings",
        "-v",
        *targets,
    ]


def record_stage(
    summary: GateSummary,
    name: str,
    status: StageStatus,
    *,
    log_name: str | None = None,
) -> None:
    summary.stages[name] = status
    if log_name:
        summary.stage_logs[name] = log_name


def run_stage(
    summary: GateSummary,
    name: str,
    cmd: list[str] | None,
    logs_dir: Path,
    *,
    verbose: bool,
    skip_reason: str | None = None,
) -> bool:
    if skip_reason:
        skip_step(name, skip_reason)
        record_stage(summary, name, "skip")
        return True
    if cmd is None:
        record_stage(summary, name, "skip")
        return True
    ok = run_step(name, cmd, logs_dir, verbose=verbose)
    record_stage(summary, name, "pass" if ok else "fail", log_name=f"{name}.log")
    return ok


def run_security_scan(
    summary: GateSummary,
    logs_dir: Path,
    *,
    verbose: bool,
    changed: set[str] | None,
    docs_only: bool,
) -> bool:
    if docs_only:
        for stage in ("security_sync", "security_audit", "security_bandit"):
            skip_step(stage, "docs-only diff")
            record_stage(summary, stage, "skip")
        return True

    sync_deps, pip_audit, bandit = security_scan_plan(changed)
    if not (sync_deps or pip_audit or bandit):
        for stage in ("security_sync", "security_audit", "security_bandit"):
            skip_step(stage, "no changes under src/, pyproject.toml, or uv.lock")
            record_stage(summary, stage, "skip")
        return True

    failed = False
    if sync_deps:
        failed |= not run_stage(
            summary,
            "security_sync",
            ["uv", "sync", "--frozen", "--extra", "test", "--group", "dev"],
            logs_dir,
            verbose=verbose,
        )
    else:
        run_stage(
            summary,
            "security_sync",
            None,
            logs_dir,
            verbose=verbose,
            skip_reason="lockfile unchanged",
        )

    if pip_audit:
        failed |= not run_stage(
            summary,
            "security_audit",
            ["uv", "run", "pip-audit"],
            logs_dir,
            verbose=verbose,
        )
    else:
        run_stage(
            summary,
            "security_audit",
            None,
            logs_dir,
            verbose=verbose,
            skip_reason="not required for this diff",
        )

    if bandit:
        failed |= not run_stage(
            summary,
            "security_bandit",
            ["uv", "run", "bandit", "-r", "src", "-ll"],
            logs_dir,
            verbose=verbose,
        )
    else:
        run_stage(
            summary,
            "security_bandit",
            None,
            logs_dir,
            verbose=verbose,
            skip_reason="not required for this diff",
        )
    return not failed


def run_quick_gate(
    summary: GateSummary,
    logs_dir: Path,
    *,
    verbose: bool,
    fail_fast: bool,
    changed: set[str] | None,
    docs_only: bool,
) -> bool:
    summary.pytest_targets = pytest_targets(changed)
    failed = False

    if docs_only:
        run_stage(
            summary,
            "lint",
            None,
            logs_dir,
            verbose=verbose,
            skip_reason="docs-only diff",
        )
        run_stage(
            summary,
            "unit_tests",
            None,
            logs_dir,
            verbose=verbose,
            skip_reason="docs-only diff",
        )
        run_stage(
            summary,
            "skills_validate",
            None,
            logs_dir,
            verbose=verbose,
            skip_reason="docs-only diff",
        )
        return False

    if not run_stage(summary, "lint", ["task", "lint"], logs_dir, verbose=verbose):
        failed = True
        if fail_fast:
            return True

    if not failed or not fail_fast:
        if not run_stage(
            summary,
            "unit_tests",
            targeted_test_cmd(changed),
            logs_dir,
            verbose=verbose,
        ):
            failed = True
            if fail_fast:
                return True

    if (not failed or not fail_fast) and should_validate_skills(changed, docs_only):
        if not run_stage(
            summary,
            "skills_validate",
            resolve_script_cmd("validate_skills.py"),
            logs_dir,
            verbose=verbose,
        ):
            failed = True
    elif not docs_only:
        run_stage(
            summary,
            "skills_validate",
            None,
            logs_dir,
            verbose=verbose,
            skip_reason="skills unchanged",
        )

    return failed


def run_full_gate(
    summary: GateSummary,
    logs_dir: Path,
    *,
    verbose: bool,
    fail_fast: bool,
    strict: bool,
    changed: set[str] | None,
    docs_only: bool,
) -> bool:
    failed = False
    stages: list[tuple[str, list[str] | None, str | None]] = [
        ("format", ["task", "format"], None if not docs_only else "docs-only diff"),
        ("lint_fix", ["task", "lint:fix"], None if not docs_only else "docs-only diff"),
        ("lint", ["task", "lint"], None if not docs_only else "docs-only diff"),
    ]

    for name, cmd, skip_reason in stages:
        if not run_stage(
            summary, name, cmd, logs_dir, verbose=verbose, skip_reason=skip_reason
        ):
            failed = True
            if fail_fast:
                return True

    if should_validate_skills(changed, docs_only):
        if not run_stage(
            summary,
            "skills_validate",
            resolve_script_cmd("validate_skills.py"),
            logs_dir,
            verbose=verbose,
        ):
            failed = True
            if fail_fast:
                return True
    else:
        run_stage(
            summary,
            "skills_validate",
            None,
            logs_dir,
            verbose=verbose,
            skip_reason="skills unchanged",
        )

    server_skip = None
    if docs_only:
        server_skip = "docs-only diff"
    elif not should_validate_server_json(changed):
        server_skip = "server.json unchanged"

    if not run_stage(
        summary,
        "server_json",
        ["uv", "run", "python", "src/terraform_ingest/validate_server.py"],
        logs_dir,
        verbose=verbose,
        skip_reason=server_skip,
    ):
        failed = True
        if fail_fast:
            return True

    test_skip = "docs-only diff" if docs_only else None
    if not run_stage(
        summary,
        "unit_tests",
        ["task", "test"],
        logs_dir,
        verbose=verbose,
        skip_reason=test_skip,
    ):
        failed = True
        if fail_fast:
            return True

    build_skip = "docs-only diff" if docs_only else None
    if not run_stage(
        summary,
        "build",
        ["task", "build"],
        logs_dir,
        verbose=verbose,
        skip_reason=build_skip,
    ):
        failed = True
        if fail_fast:
            return True

    if shutil.which("docker"):
        docker_skip = docker_build_skip_reason(changed, docs_only)
        if not run_stage(
            summary,
            "docker_build",
            docker_build_cmd(),
            logs_dir,
            verbose=verbose,
            skip_reason=docker_skip,
        ):
            failed = True
            if fail_fast:
                return True
    else:
        skip_step("docker_build", "docker not installed")
        record_stage(summary, "docker_build", "skip")

    if not run_security_scan(
        summary, logs_dir, verbose=verbose, changed=changed, docs_only=docs_only
    ):
        failed = True
        if fail_fast:
            return True

    if shutil.which("gitleaks"):
        gitleaks_ok = run_stage(
            summary,
            "security_gitleaks",
            ["task", "secret:search"],
            logs_dir,
            verbose=verbose,
            skip_reason="docs-only diff" if docs_only else None,
        )
        if docs_only:
            pass
        elif strict and not gitleaks_ok:
            failed = True
    else:
        skip_step("security_gitleaks", "gitleaks not installed")
        record_stage(summary, "security_gitleaks", "skip")

    return failed


def finalize_summary(summary: GateSummary) -> int:
    summary.passed = summary.failed_stage is None and all(
        status != "fail" for status in summary.stages.values()
    )
    summary.write()
    print(f"\nSummary: {SUMMARY_PATH}")
    if summary.passed:
        print(f"Gate ({summary.mode}): PASS")
        return 0
    print(f"Gate ({summary.mode}): FAIL at {summary.failed_stage}")
    print("Read summary.json for stage status; re-run with --verbose for log tails.")
    return 1


def run_gate_round(
    *,
    mode: Literal["quick", "full"],
    round_idx: int,
    verbose: bool,
    fail_fast: bool,
    strict: bool,
) -> tuple[int, GateSummary]:
    logs_dir = LOGS_DIR
    changed = changed_paths()
    docs_only = bool(changed) and is_docs_only(changed)

    summary = GateSummary(
        mode=mode,
        passed=False,
        failed_stage=None,
        docs_only=docs_only,
        round=round_idx,
        changed_paths=sorted(changed) if changed is not None else [],
    )

    if mode == "quick":
        failed = run_quick_gate(
            summary,
            logs_dir,
            verbose=verbose,
            fail_fast=fail_fast,
            changed=changed,
            docs_only=docs_only,
        )
    else:
        failed = run_full_gate(
            summary,
            logs_dir,
            verbose=verbose,
            fail_fast=fail_fast,
            strict=strict,
            changed=changed,
            docs_only=docs_only,
        )

    if failed:
        summary.failed_stage = next(
            (name for name, status in summary.stages.items() if status == "fail"),
            None,
        )

    return finalize_summary(summary), summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quick", action="store_true", help="Fast gate for agent iteration"
    )
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first failing stage",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print log tails on failure (or set QA_VERBOSE=1)",
    )
    args = parser.parse_args()

    verbose = args.verbose or os.getenv("QA_VERBOSE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    mode: Literal["quick", "full"] = "quick" if args.quick else "full"

    if args.rounds < 1:
        print("ERROR: --rounds must be >= 1")
        return 2

    if not Path("Taskfile.yml").exists():
        print("ERROR: run this script from repo root")
        return 2

    if not shutil.which("task"):
        print("ERROR: task is required but not found in PATH")
        return 2

    round_idx = 1
    while True:
        print(f"\n### QA ROUND {round_idx} ({mode}) ###")
        exit_code, _summary = run_gate_round(
            mode=mode,
            round_idx=round_idx,
            verbose=verbose,
            fail_fast=args.fail_fast,
            strict=args.strict,
        )
        if exit_code == 0:
            if not args.loop or round_idx >= args.rounds:
                return 0
        elif not args.loop or round_idx >= args.rounds:
            return exit_code
        round_idx += 1
        print("\nRetrying QA pipeline...")


if __name__ == "__main__":
    raise SystemExit(main())
