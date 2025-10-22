# Instructions for terraform-ingest

**Project Type:** FastAPI Backend Application
**Primary Language:** Python (100% of codebase)

## Project Overview
A FastAPI/Click-based Python application that ingests multiple Terraform repositories from YAML configuration, analyzes modules across branches/tags, and outputs JSON summaries for AI RAG systems. Also exposes an MCP (Model Context Protocol) service for AI agents.

## Rules
- Before running any command, check the current terminal context and use that same terminal ID for all subsequent commands.
- All documentation created to meet a specific feature request must be created in the ./docs folder with a filename that matches the feature request title in snake_case and ends with _FEATURE.md. For example, a feature request titled "Add User Authentication" would have documentation created in ./docs/add_user_authentication_FEATURE.md.
- When you need to use the `run_in_terminal` tool always use isBackground=false.

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

## Architecture Components

### Core Data Flow
1. **Configuration** (`config.yaml`) → **TerraformIngest** (`ingest.py`) → **RepositoryManager** (`repository.py`) → **TerraformParser** (`parser.py`) → **JSON Output**
2. **MCP Service** (`mcp_service.py`) reads JSON outputs and exposes them to AI agents via FastMCP

### Key Models (models.py)
- `RepositoryConfig`: Git repo settings (url, branches, recursive)  
- `TerraformModuleSummary`: Parsed module data (variables, outputs, providers, modules)
- `IngestConfig`: Top-level configuration container

## Architecture

**Key Frameworks & Libraries:**
- FastAPI - backend API server
- FastMCP - backend MCP server
- Click - CLI

**Project Structure:**
- `docs/` - Documentation
- `src/` - Source code
- `src/terraform_ingest/` - Project files
- `examples/ - example scripts`

## Key Files

**Configuration:**
- `pyproject.toml` - Build file, requirements
- `config.yaml` - Configuration file

**Documentation:**
- `README.md`
- `docs/*.md`

## Commands

Install: `uv sync`
Build: `uv build`
Test: `python -m pytest`

