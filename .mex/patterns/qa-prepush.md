# QA Pre-Push Gate

Use when finishing agent or human work that modified tracked files.

## Two-tier workflow

| Phase | Command | Purpose |
|-------|---------|---------|
| Iteration | `task qa:quick` | Lint + targeted tests |
| Hand-off / push | `task qa:prepush` | Full gate |

## Token-efficient agent rule

**Read `.terraform-ingest/summary.json` only.** Do not paste `*.log` files unless running with `--verbose`.

## Optional hook

```bash
task qa:hooks:install   # .git/hooks/pre-push → task qa:prepush
```

## Docs-only waiver

Diffs limited to `docs/**`, `*.md`, `mkdocs.yml`, `.mex/**` skip test/build/security.

## Related

- `scripts/prepush-gate.py` — stage runner + summary writer
- `skills/terraform-ingest-release-audit/SKILL.md` — agent hand-off contract
- `docs/qa_prepush.md` — operator reference
