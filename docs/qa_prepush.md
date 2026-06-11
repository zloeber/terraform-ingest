# QA Pre-Push Gate

Two-tier quality gate with machine-readable output for token-efficient agent hand-off.

## Commands

| Command | When to use |
|---------|-------------|
| `task qa:quick` | **Agent iteration** — lint + targeted tests (~30s) |
| `task qa:prepush` | **Before push/PR** — full gate |
| `task qa:prepush:loop -- 3` | Full gate with bounded retry after auto-fix |
| `task pre-push` | Alias for `qa:prepush` |
| `task qa:hooks:install` | Install git pre-push hook |
| `task security:scan` | Manual full security audit |

## Agent workflow (token-efficient)

1. During iteration: `task qa:quick`
2. Before hand-off or push: `task qa:prepush`
3. **Read only** `.terraform-ingest/summary.json` — do not paste log files into chat
4. Re-run with `--verbose` or `QA_VERBOSE=1` only when debugging a failed stage

Example summary:

```json
{
  "mode": "quick",
  "passed": false,
  "failed_stage": "lint",
  "docs_only": false,
  "stages": { "lint": "fail", "unit_tests": "skip" },
  "stage_logs": { "lint": "lint.log" }
}
```

## Full gate stages

| Stage | What it runs |
|-------|----------------|
| `format` | `task format` |
| `lint_fix` | `task lint:fix` |
| `lint` | `task lint` |
| `skills_validate` | `scripts/validate_skills.py` |
| `server_json` | MCP registry check (when relevant) |
| `unit_tests` | `task test` |
| `build` | `task build` |
| `security_*` | Context-aware sync, pip-audit, bandit |
| `security_gitleaks` | Optional; fails only with `--strict` |

## Quick gate stages

| Stage | What it runs |
|-------|----------------|
| `lint` | `task lint` (verify only, no auto-fix) |
| `unit_tests` | Targeted pytest for changed modules, else full suite |
| `skills_validate` | Only when `skills/` changed |

## Docs-only waiver

When the git diff is **only** documentation (`docs/**`, `*.md`, `mkdocs.yml`, `.mex/**`):

- **Quick gate:** all stages skipped → immediate pass
- **Full gate:** skips format, lint, test, build, security, server.json

## Flags

```bash
zsh ./scripts/prepush-gate.zsh --quick          # fast gate
zsh ./scripts/prepush-gate.zsh --fail-fast      # stop at first failure
zsh ./scripts/prepush-gate.zsh --verbose        # print log tails on failure
QA_VERBOSE=1 task qa:prepush                    # same as --verbose
```

## CI parity

Ubuntu CI runs unit tests, lint, build, and bundled skill validation. Run `task qa:prepush` locally before push.

To replicate this gate in another repository, see [QA Gate Replication Prompt](qa_prepush_replication_prompt.md).
