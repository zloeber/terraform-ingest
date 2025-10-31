# Instructions for terraform-ingest

## Project Overview
A FastMCP/FastAPI/Click-based Python application that ingests multiple Terraform repositories from YAML configuration, analyzes modules across branches/tags, and outputs JSON summaries for AI RAG systems. Also exposes an MCP (Model Context Protocol) service for AI agents.

## Rules
- Before running any command, check the current terminal context and use that same terminal ID for all subsequent commands.
- All documentation created must be created in the ./docs folder and should be added to the ./mkdocs.yml file for inclusion in the site.
- When you need to use the `run_in_terminal` tool always use isBackground=false.
- Do not run multiple line python commands in a single execution, instead create temporary scripts if needed and run them as single commands.
- **Always run tests and linting** before committing changes to ensure code quality.
- Use `uv` package manager instead of `pip` for dependency management.

## Code Style Guidelines
- Follow PEP 8 style guide
- Use snake_case for variables and functions
- Use PascalCase for classes
- Include docstrings for functions and classes
- Use type hints where appropriate
- Use f-strings for string formatting
- Use `pathlib.Path` for file system operations
- Use `click` for CLI commands and options
- Use `pydantic` for data models and validation
- All imports should be at the top of the file, grouped by standard library, third-party, and local imports
- Using global variables should always be a last resort approved by the user

## Architecture Components

### Core Data Flow
1. **Configuration** (`config.yaml`) → **TerraformIngest** (`ingest.py`) → **RepositoryManager** (`repository.py`) → **TerraformParser** (`parser.py`) → **JSON Output**
2. **MCP Service** (`mcp_service.py`) reads JSON outputs and exposes them to AI agents via FastMCP

### Key Models (models.py)
- `RepositoryConfig`: Git repo settings (url, branches, recursive)  
- `TerraformModuleSummary`: Parsed module data (variables, outputs, providers, modules)
- `IngestConfig`: Top-level configuration container

### Configuration Patterns
```yaml
repositories:
  - url: git@example.com/terraform-modules.git
    recursive: true              # Search subdirectories for modules
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
terraform-ingest analyze https://github.com/user/terraform-module --recursive

# Batch processing from config
terraform-ingest ingest config.yaml --cleanup

# Start MCP service for AI agents
terraform-ingest-mcp
```

## Critical Implementation Details

### Recursive Module Discovery
- `RepositoryManager._find_module_paths()` walks directories when `recursive=true`
- Each discovered module gets separate JSON output: `{repo}_{ref}_{module_path}.json`

### File Naming Convention
- Output: `{repository_name}_{ref}_{path}.json` (path omitted for root modules)
- Paths sanitized: `/` → `_`, handles Windows paths

### MCP Integration
- FastMCP service reads from `output_dir` (default: `./output`)
- Exposes multiple tools and prompts
- Exposes dynamic resource urls
- JSON files must follow `TerraformModuleSummary` schema

## Testing Patterns
- Pydantic model validation in `test_models.py`  
- Use `pytest` fixtures for sample configurations
- Mock git operations for reproducible tests
- Run tests with: `uv run pytest --maxfail=1 --disable-warnings -v tests`
- Test coverage: 41 tests across models, API, MCP service, and parser

## Linting & Formatting
```bash
# Check formatting (required before commit)
uv run black --check src/terraform_ingest
uv run ruff format --check src/terraform_ingest

# Auto-fix formatting (required before commit)
uv run black src/terraform_ingest
uv run ruff format src/terraform_ingest

# Linting with ruff (required before commit)
uv run ruff check src/terraform_ingest
uv run ruff check --fix src/terraform_ingest
```

## Build & Distribution
```bash
# Build package
uv build

# Install in development mode
uv sync

# Install with specific extras
uv pip install -e ".[test]"    # Test dependencies
uv pip install -e ".[dev]"     # Dev dependencies (ruff, black, mypy)
uv pip install -e ".[docs]"    # Documentation dependencies
```

## Dependency Management
```bash
# Add a new dependency (automatically updates pyproject.toml)
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Update all dependencies
uv sync --upgrade

# Lock dependencies
uv lock

# Remove a dependency
uv remove <package-name>
```

**Important:** After adding dependencies:
1. Run `uv sync` to install them
2. Run tests to ensure compatibility
3. Commit both `pyproject.toml` and `uv.lock` files

## Environment Variables
- `TERRAFORM_INGEST_OUTPUT_DIR`: Default output directory for JSON summaries (default: `./output`)
- Git credentials automatically detected from system for private repositories
- No required environment variables for basic operation

## Project Structure
```
.
├── .github/
│   ├── copilot-instructions.md    # Copilot guidance
│   └── workflows/                 # CI/CD pipelines
├── docs/                          # Documentation files
├── examples/                      # Example configurations
├── src/terraform_ingest/
│   ├── __init__.py
│   ├── api.py                    # FastAPI server
│   ├── cli.py                    # Click CLI interface
│   ├── ingest.py                 # Main ingestion logic
│   ├── mcp_service.py            # MCP server for AI agents
│   ├── models.py                 # Pydantic data models
│   ├── parser.py                 # Terraform file parser
│   └── repository.py             # Git repository manager
├── tests/                        # Test suite
├── config.yaml                   # Example configuration
├── pyproject.toml               # Project metadata & dependencies
└── Taskfile.yml                 # Task automation
```

## Common Tasks
```bash
# Run all tests
task test

# Run linting
task lint

# Auto-fix linting issues
task lint:fix

# Format code
task format

# Build documentation
task docs

# Clean build artifacts
task clean

# Install dependencies
task install
```

## Troubleshooting
- **Import errors**: Run `uv sync` to ensure all dependencies are installed
- **Git authentication**: Ensure SSH keys or credential helpers are configured
- **Test failures**: Check if git is available on PATH for repository tests
- **Module not found**: Verify you're running commands from project root with activated venv
- **MCP server issues**: Check `TERRAFORM_INGEST_OUTPUT_DIR` points to valid directory with JSON files

## Git Workflow
- Branch naming: `feature/description`, `fix/description`, `docs/description`
- Commit messages: Use conventional commits (feat:, fix:, docs:, test:, chore:)
- Pre-commit: Ensure tests pass and code is formatted
- PRs: Include tests for new features, update documentation as needed