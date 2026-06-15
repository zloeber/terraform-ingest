# Agent Skills

Agent Skills teach AI agents how to guide users through terraform-ingest workflows. Skills live in `./skills/<skill-name>/SKILL.md` using the [Claude Code skill format](https://docs.anthropic.com/en/docs/claude-code/skills) and deploy to any supported agent via the CLI.

## Overview

Skills complement the [MCP service](mcp.md) by covering setup and orchestration **before** an agent connects to MCP, and by providing CLI fallbacks when MCP is unavailable.

| Skill | Purpose |
|-------|---------|
| [terraform-ingest](../skills/terraform-ingest/SKILL.md) | Hub — routes to the right workflow |
| [terraform-ingest-setup](../skills/terraform-ingest-setup/SKILL.md) | Install, init config, git credentials |
| [terraform-ingest-configure](../skills/terraform-ingest-configure/SKILL.md) | Build and validate `config.yaml` |
| [terraform-ingest-ingest](../skills/terraform-ingest-ingest/SKILL.md) | Run ingestion and verify output |
| [terraform-ingest-release-audit](../skills/terraform-ingest-release-audit/SKILL.md) | Pre-push QA gate before hand-off |

Phase 2 (planned): `terraform-ingest-mcp-connect`, `terraform-ingest-query`  
Phase 3 (planned): `terraform-ingest-import`, `terraform-ingest-troubleshoot`

## CLI management

List, validate, and deploy skills from the application:

```bash
terraform-ingest skills list
terraform-ingest skills show terraform-ingest
terraform-ingest skills validate
terraform-ingest skills validate-config config.yaml
terraform-ingest skills install --scope project --target cursor
terraform-ingest skills install --scope user --target claude_code --dry-run
```

Supported deploy targets: `cursor`, `claude_code`, `codex`, `opencode`, `github_copilot`, `windsurf`, `hermes`, `openclaw`.

When `--target` is omitted, `install` auto-detects agents from existing config directories.

## First-time user flow

An agent should run these skills in order:

1. **Setup** — `uv sync`, `terraform-ingest init config.yaml`
2. **Configure** — add repositories via `terraform-ingest config add-repo`
3. **Validate** — `terraform-ingest skills validate-config config.yaml`
4. **Ingest** — `terraform-ingest ingest config.yaml`
5. **MCP** (optional) — connect agent per [MCP guide](mcp.md)

## Config validation

```bash
terraform-ingest skills validate-config config.yaml
```

Checks:

- YAML parses and matches `IngestConfig` schema
- `output_dir` and `clone_dir` are writable
- Warns if `repositories` is empty

## Interface selection

Agents should prefer MCP tools when connected, otherwise use CLI:

| Task | MCP | CLI |
|------|-----|-----|
| Start ingest | `run_ingestion` | `terraform-ingest ingest config.yaml` |
| Poll progress | `get_ingestion_status` | `terraform-ingest ingestion status` |
| Add repo | — | `terraform-ingest config add-repo` |
| Deploy skills | — | `terraform-ingest skills install` |

## Release readiness

During iteration:

```bash
task qa:quick
```

Before hand-off or push:

```bash
task qa:prepush
```

Read `.terraform-ingest/summary.json` for pass/fail — do not paste log files into agent chat. See [QA Pre-Push Gate](qa_prepush.md).

Full design document: [docs/superpowers/specs/2026-06-10-terraform-ingest-agent-skills-design.md](superpowers/specs/2026-06-10-terraform-ingest-agent-skills-design.md)

## Using with Cursor / Claude Code / Codex

Deploy project-local skills so your agent discovers them automatically:

```bash
terraform-ingest skills install --scope project --target cursor
terraform-ingest skills install --scope project --target claude_code
```

## Using with other agents

Agents that read project files can load `skills/<name>/SKILL.md` directly. MCP-connected agents should use MCP tools for query and runtime ingest after the setup skills complete.
