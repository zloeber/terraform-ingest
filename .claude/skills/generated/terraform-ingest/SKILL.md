---
name: terraform-ingest
description: "Skill for the Terraform_ingest area of terraform-ingest. 261 symbols across 23 files."
metadata:
  internal: true
---

# Terraform_ingest

261 symbols | 23 files | Cohesion: 82%

## When to Use

- Working with code in `src/`
- Understanding how rebuild, stats, ingestion_status work
- Modifying terraform_ingest-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/terraform_ingest/mcp_service.py` | _run_ingestion, periodic_runner, set, set_mcp_context, set_custom_prompts (+37) |
| `src/terraform_ingest/old-logging.py` | print_debug, print_agent_message, print_task_status, print_crew_status, print_input (+31) |
| `src/terraform_ingest/cli.py` | rebuild, stats, ingestion_run, analyze, ingestion_status (+17) |
| `tests/test_indexer.py` | test_add_module, test_add_module_creates_consistent_id, test_remove_module, test_remove_nonexistent_module, test_search_by_repository (+12) |
| `src/terraform_ingest/ingestion_progress.py` | to_dict, set_event_loop, is_active, get_ingestion_tracker, __init__ (+12) |
| `src/terraform_ingest/indexer.py` | _save_index, _get_summary_filename, add_module, _extract_tags, remove_module (+11) |
| `src/terraform_ingest/embeddings.py` | _initialize_chromadb, _generate_document_id, delete_module, get_collection_stats, EmbeddingStrategy (+10) |
| `src/terraform_ingest/mcp_ingestion.py` | get_startup_settings, _build_run_options, _run_ingestion_sync, _run_ingestion_background, schedule_background_ingestion (+8) |
| `src/terraform_ingest/ingestion_runner.py` | to_dict, get_ingestion_status, run_ingestion_from_yaml, resolve_config_file, schedule_background_ingestion_thread (+7) |
| `src/terraform_ingest/parser.py` | parse_module, _parse_variables, _parse_outputs, _parse_providers, _extract_providers_regex (+7) |

## Entry Points

Start here when exploring this area:

- **`rebuild`** (Function) — `src/terraform_ingest/cli.py:1380`
- **`stats`** (Function) — `src/terraform_ingest/cli.py:1398`
- **`ingestion_status`** (Function) — `src/terraform_ingest/api.py:167`
- **`ingestion_run`** (Function) — `src/terraform_ingest/cli.py:287`
- **`get_ingestion_tracker`** (Function) — `src/terraform_ingest/ingestion_progress.py:232`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `EmbeddingStrategy` | Class | `src/terraform_ingest/embeddings.py` | 12 |
| `OpenAIEmbeddingStrategy` | Class | `src/terraform_ingest/embeddings.py` | 28 |
| `ClaudeEmbeddingStrategy` | Class | `src/terraform_ingest/embeddings.py` | 55 |
| `SentenceTransformersStrategy` | Class | `src/terraform_ingest/embeddings.py` | 80 |
| `ChromaDBDefaultStrategy` | Class | `src/terraform_ingest/embeddings.py` | 112 |
| `RepositoryImporter` | Class | `src/terraform_ingest/importers.py` | 11 |
| `GitHubImporter` | Class | `src/terraform_ingest/importers.py` | 33 |
| `GitLabImporter` | Class | `src/terraform_ingest/importers.py` | 192 |
| `LoggerProtocol` | Class | `src/terraform_ingest/old-logging.py` | 144 |
| `UnifiedLogger` | Class | `src/terraform_ingest/old-logging.py` | 275 |
| `rebuild` | Function | `src/terraform_ingest/cli.py` | 1380 |
| `stats` | Function | `src/terraform_ingest/cli.py` | 1398 |
| `ingestion_status` | Function | `src/terraform_ingest/api.py` | 167 |
| `ingestion_run` | Function | `src/terraform_ingest/cli.py` | 287 |
| `get_ingestion_tracker` | Function | `src/terraform_ingest/ingestion_progress.py` | 232 |
| `get_ingestion_status` | Function | `src/terraform_ingest/ingestion_runner.py` | 66 |
| `run_ingestion_from_yaml` | Function | `src/terraform_ingest/ingestion_runner.py` | 163 |
| `resolve_config_file` | Function | `src/terraform_ingest/ingestion_runner.py` | 205 |
| `schedule_background_ingestion_thread` | Function | `src/terraform_ingest/ingestion_runner.py` | 213 |
| `get_startup_settings` | Function | `src/terraform_ingest/mcp_ingestion.py` | 48 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Run_blocking_startup_ingestion → _broadcast_log_message` | cross_community | 10 |
| `Periodic_runner → _broadcast_log_message` | cross_community | 10 |
| `_configure_mcp_startup → _broadcast_log_message` | cross_community | 10 |
| `_configure_mcp_startup → _schedule_client_notification` | cross_community | 10 |
| `Ingest_repositories → _broadcast_log_message` | cross_community | 9 |
| `Analyze_repository → _broadcast_log_message` | cross_community | 9 |
| `_target → _broadcast_log_message` | cross_community | 9 |
| `Ingest_from_yaml → _broadcast_log_message` | cross_community | 8 |
| `_configure_mcp_startup → _reset_unlocked` | cross_community | 8 |
| `_configure_mcp_startup → Add_modules` | cross_community | 8 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 21 calls |

## How to Explore

1. `gitnexus_context({name: "rebuild"})` — see callers and callees
2. `gitnexus_query({query: "terraform_ingest"})` — find related execution flows
3. Read key files listed above for implementation details
