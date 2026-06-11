---
name: tests
description: "Skill for the Tests area of terraform-ingest. 112 symbols across 15 files."
---

# Tests

112 symbols | 15 files | Cohesion: 79%

## When to Use

- Working with code in `tests/`
- Understanding how search_vector, search, test_list_module_resources_for_discovery work
- Modifying tests-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/test_mcp_service.py` | test_list_module_resources_for_discovery, test_get_argument_completions_for_repositories, test_get_argument_completions_for_refs, test_get_argument_completions_for_paths, test_get_argument_completions_for_resources_with_none (+27) |
| `tests/test_dependency_installer.py` | test_check_package_installed_existing_package, test_check_package_installed_missing_package, test_get_missing_packages_all_present, test_get_missing_packages_some_missing, test_get_missing_packages_all_missing (+10) |
| `src/terraform_ingest/mcp_service.py` | search_modules, search_modules, _search_modules_impl, get_module, _get_module_details_impl (+8) |
| `tests/test_importers.py` | test_fetch_repositories, test_fetch_repositories_with_error, test_has_terraform_files_found, test_has_terraform_files_not_found, test_has_terraform_files_rate_limited (+6) |
| `tests/test_embeddings.py` | test_prepare_document_text_full, test_prepare_document_text_partial, test_prepare_metadata, test_prepare_metadata_no_providers, test_upsert_module_disabled (+5) |
| `src/terraform_ingest/dependency_installer.py` | check_package_installed, get_missing_packages, _refresh_sys_path, install_packages, ensure_embedding_packages |
| `src/terraform_ingest/importers.py` | fetch_repositories, _has_terraform_files, fetch_repositories, _fetch_group_projects, _has_terraform_files |
| `tests/test_repository.py` | test_get_tags_semantic_version_sorting, test_get_tags_with_max_tags, test_get_tags_mixed_valid_and_invalid_versions, test_get_tags_empty_repo, test_get_tags_pre_release_versions |
| `src/terraform_ingest/embeddings.py` | _prepare_document_text, _prepare_metadata, upsert_module, search_modules |
| `tests/test_indexer.py` | test_get_module, test_get_nonexistent_module, test_get_module_summary_path, test_module_entry_has_required_fields |

## Entry Points

Start here when exploring this area:

- **`search_vector`** (Function) — `src/terraform_ingest/api.py:367`
- **`search`** (Function) — `src/terraform_ingest/cli.py:697`
- **`test_list_module_resources_for_discovery`** (Function) — `tests/test_mcp_service.py:1117`
- **`test_get_argument_completions_for_repositories`** (Function) — `tests/test_mcp_service.py:1143`
- **`test_get_argument_completions_for_refs`** (Function) — `tests/test_mcp_service.py:1164`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `search_vector` | Function | `src/terraform_ingest/api.py` | 367 |
| `search` | Function | `src/terraform_ingest/cli.py` | 697 |
| `test_list_module_resources_for_discovery` | Function | `tests/test_mcp_service.py` | 1117 |
| `test_get_argument_completions_for_repositories` | Function | `tests/test_mcp_service.py` | 1143 |
| `test_get_argument_completions_for_refs` | Function | `tests/test_mcp_service.py` | 1164 |
| `test_get_argument_completions_for_paths` | Function | `tests/test_mcp_service.py` | 1185 |
| `test_get_argument_completions_for_resources_with_none` | Function | `tests/test_mcp_service.py` | 1206 |
| `test_custom_prompts_in_mcp_context` | Function | `tests/test_mcp_service.py` | 1372 |
| `test_prepare_document_text_full` | Function | `tests/test_embeddings.py` | 179 |
| `test_prepare_document_text_partial` | Function | `tests/test_embeddings.py` | 230 |
| `test_prepare_metadata` | Function | `tests/test_embeddings.py` | 272 |
| `test_prepare_metadata_no_providers` | Function | `tests/test_embeddings.py` | 303 |
| `test_upsert_module_disabled` | Function | `tests/test_embeddings.py` | 320 |
| `test_upsert_module_new_document` | Function | `tests/test_embeddings.py` | 335 |
| `test_upsert_module_update_existing` | Function | `tests/test_embeddings.py` | 368 |
| `search_modules` | Function | `src/terraform_ingest/mcp_service.py` | 687 |
| `test_search_modules_by_query` | Function | `tests/test_mcp_service.py` | 178 |
| `test_search_modules_by_provider` | Function | `tests/test_mcp_service.py` | 195 |
| `test_search_modules_by_repo_url` | Function | `tests/test_mcp_service.py` | 210 |
| `test_search_modules_combined_filters` | Function | `tests/test_mcp_service.py` | 221 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Ingest → Check_package_installed` | cross_community | 6 |
| `Mcp → Check_package_installed` | cross_community | 6 |
| `__init__ → Check_package_installed` | cross_community | 6 |
| `Ingest → _refresh_sys_path` | cross_community | 5 |
| `Mcp → _refresh_sys_path` | cross_community | 5 |
| `__init__ → _refresh_sys_path` | cross_community | 5 |
| `_configure_mcp_startup → From_yaml` | cross_community | 5 |
| `Module → Get_module` | cross_community | 4 |
| `Install_deps → Check_package_installed` | cross_community | 4 |
| `Install_deps → Get_module` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Terraform_ingest | 25 calls |

## How to Explore

1. `gitnexus_context({name: "search_vector"})` — see callers and callees
2. `gitnexus_query({query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details
