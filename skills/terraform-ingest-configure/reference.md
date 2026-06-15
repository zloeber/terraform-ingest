# Config.yaml Reference

Pydantic models in `src/terraform_ingest/models.py`. Minimal field guide for agents.

## Top-level (`IngestConfig`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `repositories` | list | required | Git sources to ingest |
| `output_dir` | string | `./output` | JSON summary output |
| `clone_dir` | string | `./repos` | Local git clone cache |
| `mcp` | object | optional | MCP server settings |
| `embedding` | object | optional | Vector search settings |

## `repositories[]` (`RepositoryConfig`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | required | Git repository URL |
| `name` | string | optional | Display name; derived from URL if omitted |
| `branches` | list[string] | `[]` | Branches to analyze |
| `include_tags` | bool | `true` | Include git tags |
| `max_tags` | int | `1` | Max tags per repo |
| `path` | string | `.` | Start path for module scan |
| `recursive` | bool | `false` | Walk subdirs for modules |
| `exclude_paths` | list[string] | `[]` | Glob patterns to skip |

## `mcp` (`McpConfig`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `auto_ingest` | bool | `false` | Scheduled re-ingestion |
| `ingest_on_startup` | bool | `false` | Ingest when MCP server starts |
| `refresh_interval_hours` | int | null | Hours between auto refresh |
| `blocking_ingest_on_startup` | bool | `false` | Block MCP until ingest completes |
| `notify_ingestion_progress` | bool | `true` | MCP log notifications |
| `transport` | string | `stdio` | `stdio`, `streamable-http`, or `sse` |
| `host` | string | `127.0.0.1` | HTTP transport bind |
| `port` | int | `3000` | HTTP transport port |
| `instructions` | string | (built-in) | Agent system instructions when MCP connects |
| `prompts` | dict | optional | Override MCP prompt templates |

## `embedding` (`EmbeddingConfig`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Build ChromaDB index on ingest |
| `strategy` | string | `chromadb-default` | `openai`, `claude`, `sentence-transformers`, `chromadb-default` |
| `chromadb_path` | string | `./chromadb` | Local vector DB path |
| `collection_name` | string | `terraform_modules` | Chroma collection |
| `enable_hybrid_search` | bool | `true` | Keyword + vector blend |
| `keyword_weight` | float | `0.3` | Hybrid search weight |
| `vector_weight` | float | `0.7` | Hybrid search weight |

## Example minimal config

```yaml
repositories:
  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc
    name: aws-vpc
    branches:
      - main
    include_tags: true
    max_tags: 2

output_dir: ./output
clone_dir: ./repos

embedding:
  enabled: true
  strategy: chromadb-default
  chromadb_path: ./chromadb

mcp:
  ingest_on_startup: true
  auto_ingest: true
  refresh_interval_hours: 24
```

## CLI quick reference

```bash
terraform-ingest config set --target <dot.path> --value <value>
terraform-ingest config get --target <dot.path> [--json]
terraform-ingest config add-repo --url <url> [options]
terraform-ingest config remove-repo --url <url>
terraform-ingest skills validate-config config.yaml
```
