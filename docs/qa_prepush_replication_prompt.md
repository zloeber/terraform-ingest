# QA Pre-Push Gate — Replication Prompt

Portable prompt for adding a **token-efficient**, two-tier pre-push quality gate to any repository. No local path references required.

Copy everything inside the **Prompt** block into an agent session in the target repository.

---

## Prompt (copy from here)

```
Implement a token-efficient two-tier pre-push quality gate in THIS repository.

Do not assume access to any other checkout on disk. Use the pattern specification below.

## Design goals (priority order)

1. **Reliability** — evidence before hand-off (`summary.json` shows pass/fail)
2. **Token efficiency** — agents read JSON summary, not log tails
3. **Speed during iteration** — quick gate for mid-session checks
4. **Full gate before push** — comprehensive check at PR/push time
5. **Context-aware skips** — docs-only diffs skip test/build/security

## Two-tier commands

| Command | When | Typical stages |
|---------|------|----------------|
| `task qa:quick` | Agent iteration | lint + targeted tests |
| `task qa:prepush` | Before push/PR | format, lint:fix, lint, validators, test, build, security |
| `task pre-push` | Git hook alias | same as qa:prepush |
| `task qa:hooks:install` | Optional | install `.git/hooks/pre-push` |

## Step 0 — Inspect THIS repo first

Read: task runner config, lint/test/build commands, CI workflows, agent contracts (AGENTS.md, CLAUDE.md, .mex/), and whether the repo has `skills/`, `server.json`, CHANGELOG.md, or manifest fixtures.

Produce a short gap analysis.

## Step 1 — Stage runner (`scripts/prepush-gate.py`)

Core behaviors:

```python
LOGS_DIR = Path(".<project>")           # gitignored
SUMMARY_PATH = LOGS_DIR / "summary.json"

@dataclass
class GateSummary:
    mode: Literal["quick", "full"]
    passed: bool
    failed_stage: str | None
    docs_only: bool
    round: int
    stages: dict[str, Literal["pass", "fail", "skip"]]
    stage_logs: dict[str, str]          # stage → "<name>.log"
    changed_paths: list[str]
    pytest_targets: list[str]           # quick mode only
    timestamp: str

def run_step(name, cmd, logs_dir, *, verbose: bool) -> bool:
    # Write stdout/stderr to logs_dir/<name>.log
    # On failure: print FAIL + log path; print log tail ONLY if verbose

def changed_paths() -> set[str] | None:
    # git diff HEAD, --cached, upstream...HEAD

def is_docs_only(changed) -> bool:
    # True when ALL paths are docs/**, *.md, mkdocs.yml, .mex/**, etc.
    # False if src/, tests/, scripts/, skills/, lockfiles, workflows changed

def security_scan_plan(changed) -> tuple[bool, bool, bool]:
    # (sync_deps, audit, bandit) — skip all three for docs-only

def pytest_targets(changed) -> list[str]:
    # Map src/foo.py → tests/test_foo.py; empty list = full suite fallback

def main():
    parser.add_argument("--quick")
    parser.add_argument("--loop"); parser.add_argument("--rounds", default=1)
    parser.add_argument("--fail-fast")   # stop at first failure
    parser.add_argument("--verbose")     # print log tails (or QA_VERBOSE=1)
    # Always write summary.json; exit code from summary.passed
```

**Default output on failure (token-efficient):**
```
FAIL: lint
Summary: .<project>/summary.json
Read summary.json for stage status; re-run with --verbose for log tails.
```

### Quick gate (`--quick`)

| Stage | Runs when |
|-------|-----------|
| `lint` | Always (verify only, no auto-fix) |
| `unit_tests` | Targeted pytest from changed paths, else full suite |
| `skills_validate` | When `skills/` changed |

**Docs-only quick gate:** skip all stages → immediate pass.

### Full gate (default)

| Stage | Runs when |
|-------|-----------|
| `format`, `lint_fix`, `lint` | Skip on docs-only |
| `skills_validate` | Skip on docs-only unless `skills/` changed |
| `server_json` / validators | Context-aware |
| `unit_tests`, `build` | Skip on docs-only |
| `security_*` | Context-aware; skip on docs-only |
| `security_gitleaks` | Optional; `--strict` only |

## Step 2 — Shell wrapper + git hook

`scripts/prepush-gate.zsh` — exec uv/python on prepush-gate.py

`scripts/install-git-hooks.zsh` — write `.git/hooks/pre-push`:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec task qa:prepush
```

## Step 3 — Task runner entries

```yaml
qa:quick:
  cmds: [zsh ./scripts/prepush-gate.zsh --quick]

qa:prepush:
  cmds: [zsh ./scripts/prepush-gate.zsh]

qa:prepush:loop:
  cmds: [zsh ./scripts/prepush-gate.zsh --loop --rounds={{default "3" .CLI_ARGS}}]

pre-push:
  cmds: [task: qa:prepush]

qa:hooks:install:
  cmds: [zsh ./scripts/install-git-hooks.zsh]
```

## Step 4 — Agent behavioural contract

Add to AGENTS.md, CLAUDE.md, or `.mex/ROUTER.md`:

> **QA GATE** — During iteration run `task qa:quick`. Before hand-off or push run `task qa:prepush`. Read **only** `.<project>/summary.json` for results — do not paste log files into chat. Use `--verbose` only when debugging.

Optional: `skills/<project>-release-audit/SKILL.md` with the same contract.

## Step 5 — Project-specific validators (opt-in)

Wire only what exists: skills, server.json, CHANGELOG, manifest fixtures.

## Step 6 — Tests

`tests/scripts/test_prepush_gate_security.py`:
- security_scan_plan cases
- is_docs_only cases
- pytest_targets mapping
- GateSummary JSON write

## Step 7 — Documentation

- `docs/qa_prepush.md` — two-tier workflow, summary.json schema, flags
- Update dev/PR docs
- Gitignore `.<project>/`

## Step 8 — CI parity

Ubuntu CI: fast validators only (skills, lint, test). Full gate stays local.

## Constraints

- Match THIS repo's existing commands
- Minimize scope — adapt pattern, don't build a framework
- Agents must cite summary.json, not logs
- Run qa:quick + qa:prepush and show summary.json before claiming complete
- Only commit if I explicitly ask

## Output I expect

1. Gap analysis
2. Files created/updated
3. Contents of `summary.json` from qa:quick and qa:prepush runs
4. Portability notes for the next repo
```

---

## Quick-start (minimal)

```
Implement a token-efficient two-tier QA gate in this repository:

- `task qa:quick` — lint + targeted tests (agent iteration)
- `task qa:prepush` — full gate before push
- `scripts/prepush-gate.py` writes `.<project>/summary.json`; agents read JSON only, not logs
- Docs-only waiver skips test/build/security
- Optional `task qa:hooks:install` for git pre-push hook
- Agent contract in AGENTS.md / CLAUDE.md

Inspect this repo's task/lint/test commands first. Run both gates and show summary.json.
```

---

## Token-efficiency principles

| Do | Don't |
|----|-------|
| Read `summary.json` (~50–100 tokens) | Paste 40-line log tails into chat |
| `qa:quick` during iteration | Full gate on every tiny edit |
| Skip test/build on docs-only | Run full pytest for markdown typos |
| `--fail-fast` when debugging | Run all stages when first already failed |
| Git hook for push enforcement | Agent-only enforcement |

## summary.json schema

```json
{
  "mode": "quick",
  "passed": true,
  "failed_stage": null,
  "docs_only": false,
  "round": 1,
  "stages": { "lint": "pass", "unit_tests": "pass" },
  "stage_logs": { "lint": "lint.log" },
  "changed_paths": ["src/app.py"],
  "pytest_targets": ["tests/test_app.py"],
  "timestamp": "2026-06-11T12:00:00+00:00"
}
```

## Adaptation cheat sheet

| Stack | qa:quick | qa:prepush |
|-------|----------|------------|
| Python + uv + task | lint + targeted pytest | + format, build, pip-audit, bandit |
| npm | lint + affected tests | + build, npm audit |
| Go | go vet + targeted tests | + fmt, full test, govulncheck |
| No task runner | prepush-gate calls make/npm directly | same |

| Repo feature | Action |
|--------------|--------|
| No skills/ | Omit skills_validate |
| No server.json | Omit server_json stage |
| Docs-only diff | Skip test/build/security in both tiers |
| Heavy optional extras | Security sync without `--all-extras` |

## Context-aware logic (embedded reference)

```
docs-only diff     → quick: all skip (pass); full: skip test/build/security
lockfile changed   → security: sync + audit + bandit
src/ changed       → security: audit + bandit (no sync)
docs/markdown only → security: skip all
no git metadata    → run everything
```
