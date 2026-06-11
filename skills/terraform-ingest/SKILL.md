---
name: terraform-ingest
description: >-
  Routes AI agents through terraform-ingest workflows: install, configure,
  ingest, and module discovery. Use when the user mentions terraform-ingest,
  setting up a Terraform module library, ingesting modules, or getting started
  with this project.
---

# Terraform-Ingest Agent Hub

Use this skill to pick the right workflow skill and interface (MCP, CLI, or API).

## Which skill to use

| User intent | Skill |
|-------------|-------|
| Install, first-time setup, prerequisites | [terraform-ingest-setup](../terraform-ingest-setup/SKILL.md) |
| Edit config.yaml, add repos, enable embeddings | [terraform-ingest-configure](../terraform-ingest-configure/SKILL.md) |
| Run ingestion, monitor progress, verify output | [terraform-ingest-ingest](../terraform-ingest-ingest/SKILL.md) |
| Connect an agent to MCP (Phase 2) | See `docs/mcp.md` |
| Find or recommend modules (Phase 2) | Use MCP `search_modules_vector` after ingest |

## Recommended first-time flow

```
1. terraform-ingest-setup    → install + init config.yaml
2. terraform-ingest-configure → add repositories, validate
3. terraform-ingest-ingest   → run ingest, verify output
4. (optional) docs/mcp.md    → connect MCP for module queries
```

## Interface selection

```
User request
    │
    ├─ MCP connected? ──yes──► MCP tools (run_ingestion, get_ingestion_status, search_*)
    │
    └─ no ──► Shell access? ──yes──► terraform-ingest CLI
                  │
                  └─ no ──► Guide user with manual steps; API via curl if HTTP server running
```

| Task | MCP tool | CLI command |
|------|----------|-------------|
| Start ingest | `run_ingestion` | `terraform-ingest ingest config.yaml` |
| Background ingest | `run_ingestion(background=true)` | `terraform-ingest ingestion run --background` |
| Poll progress | `get_ingestion_status` | `terraform-ingest ingestion status` |
| Add repository | — | `terraform-ingest config add-repo --url ...` |
| Validate config | — | `terraform-ingest skills validate-config config.yaml` |
| Deploy skills | — | `terraform-ingest skills install --target cursor` |

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `TERRAFORM_INGEST_CONFIG` | Path to YAML config | `config.yaml` |
| `TERRAFORM_INGEST_OUTPUT_DIR` | JSON summaries directory | `./output` |
| `GITHUB_TOKEN` | GitHub import / private repos | — |
| `OPENAI_API_KEY` | OpenAI embedding strategy | — |

## Documentation

- [Quickstart](../../docs/quickstart.md)
- [MCP guide](../../docs/mcp.md)
- [Config CLI](../../docs/config_command.md)
- [Agent skills overview](../../docs/agent_skills.md)

## Rules

1. Run **setup → configure → ingest** in order for new users; do not skip validation.
2. Prefer CLI `config` commands over hand-editing YAML unless the user explicitly wants to edit the file.
3. Use **foreground ingest** on first run so errors surface immediately.
4. Do not duplicate `mcp.instructions` from config — point users to customize that field after MCP is connected.
