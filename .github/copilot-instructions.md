# Copilot Instructions for terraform-ingest

## Project Overview
A FastAPI/Click-based Python application that ingests multiple Terraform repositories from YAML configuration, analyzes modules across branches/tags, and outputs JSON summaries for AI RAG systems. Also exposes an MCP (Model Context Protocol) service for AI agents.

## Architecture Components

### Core Data Flow
1. **Configuration** (`config.yaml`) → **TerraformIngest** (`ingest.py`) → **RepositoryManager** (`repository.py`) → **TerraformParser** (`parser.py`) → **JSON Output**
2. **MCP Service** (`mcp_service.py`) reads JSON outputs and exposes them to AI agents via FastMCP

### Key Models (models.py)
- `RepositoryConfig`: Git repo settings (url, branches, recursive, ignore_default_branch)  
- `TerraformModuleSummary`: Parsed module data (variables, outputs, providers, modules)
- `IngestConfig`: Top-level configuration container

### Configuration Patterns
```yaml
repositories:
  - url: git@example.com/terraform-modules.git
    recursive: true              # Search subdirectories for modules
    ignore_default_branch: true  # Skip repository's default branch
    path: modules/aws           # Start scanning from this path
    branches: ["main", "dev"]
    include_tags: true
```

## Development Workflows

### Setup & Testing
```bash
uv sync                    # Install dependencies (uses uv, not pip)
python -m pytest          # Run tests
python -m terraform_ingest.cli --help  # CLI access
```

### CLI Commands
```bash
# Single repo analysis
terraform-ingest analyze https://github.com/user/terraform-module --recursive --ignore-default-branch

# Batch processing from config
terraform-ingest ingest config.yaml --cleanup

# Start MCP service for AI agents
terraform-ingest-mcp
```

## Critical Implementation Details

### Recursive Module Discovery
- `RepositoryManager._find_module_paths()` walks directories when `recursive=true`
- Each discovered module gets separate JSON output: `{repo}_{ref}_{module_path}.json`

### Default Branch Handling  
- `_get_default_branch()` detects via origin/HEAD, falls back to common names (main, master)
- When `ignore_default_branch=true`, skips processing the detected default branch

### File Naming Convention
- Output: `{repository_name}_{ref}_{path}.json` (path omitted for root modules)
- Paths sanitized: `/` → `_`, handles Windows paths

### MCP Integration
- FastMCP service reads from `output_dir` (default: `./output`)
- Exposes `list_repositories` and `search_modules` tools
- JSON files must follow `TerraformModuleSummary` schema

## Testing Patterns
- Pydantic model validation in `test_models.py`  
- Use `pytest` fixtures for sample configurations
- Mock git operations for reproducible tests

## Tool Usage Notes
- When using 'run_in_terminal' tool the parameter 'isBackground' should always be set to false if it is available.