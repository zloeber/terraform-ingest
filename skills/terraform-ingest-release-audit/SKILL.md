---
name: terraform-ingest-release-audit
description: Mandatory before calling work complete when the session changed repo files. Use qa:quick during iteration and qa:prepush before hand-off. Read .terraform-ingest/summary.json only — not log files.
---

# Auditing Release Readiness

Use this skill **whenever** your session added or edited tracked files and you are about to hand off or say the task is done. Read-only Q&A with no writes can skip it.

## Workflow

1. During iteration: `task qa:quick`
2. Before hand-off or push: `task qa:prepush`
3. Read `.terraform-ingest/summary.json` for pass/fail by stage
4. Fix failures; re-run until `passed: true`
5. Return a short readiness summary from the JSON (not log tails)

## Commands

- `task qa:quick` — lint + targeted tests (agent iteration)
- `task qa:prepush` — full gate before push/PR
- `task qa:prepush:loop -- 3` — bounded retry after auto-fix
- `task qa:hooks:install` — optional git pre-push hook

## Output contract

Return from `summary.json`:

- `mode`, `passed`, `failed_stage`
- `stages` map (pass / fail / skip)
- unresolved blockers if any
- push readiness recommendation

Do **not** paste `.terraform-ingest/*.log` into chat unless debugging with `--verbose`.

## Docs-only changes

When the diff is docs-only, `qa:quick` passes immediately and `qa:prepush` skips test/build/security.

## Safety

- Do not claim readiness unless `summary.json` shows `"passed": true`
