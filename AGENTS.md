# AGENTS.md

AI coding agent instructions for **terraform-ingest**

## Project Overview

A terraform multi-repo module AI RAG ingestion engine that accepts a YAML file of terraform git repository sources, downloads them locally using existing credentials, creates JSON summaries of their purpose, inputs, outputs, and providers on the main and git tag branches for ingestion via a RAG pipeline into a vector database.

**Project Type:** FastAPI Backend Application
**Primary Language:** Python (100% of codebase)

## Architecture

**Key Frameworks & Libraries:**
- FastAPI - backend
- FastMCP - backend
- Click - CLI

**Project Structure:**
- `docs/` - Documentation
- `src/` - Source code
- `src/terraform_ingest/` - Project files
- `examples/ - example scripts`

## Key Files

**Configuration:**
- `pyproject.toml` - Configuration file, requirements

**Documentation:**
- `README.md`
- `docs/*.md`

## Development Commands

**Install:**
```bash
uv sync
```

**Test:**
```bash
python -m pytest
```

## Code Style Guidelines

- Follow PEP 8 style guide
- Use snake_case for variables and functions
- Use PascalCase for classes
- Include docstrings for functions and classes
- Use type hints where appropriate

## Testing

**Run Tests:**
```bash
python -m pytest
```

**Test Files:**
- `pytest.ini`
- `tests/__init__.py`
- `tests/test_api.py`
- `tests/test_mcp_service.py`
- `tests/test_models.py`

## AI Coding Assistance Notes

**Tool Use**
- When using 'run_in_terminal' tool the parameter 'isBackground' should always be set to false if it is available.

**Important Considerations:**
- Check virtual environment setup before running commands
- Be mindful of Python version compatibility
- Follow import organization (stdlib, third-party, local)
- Project has 37 files across 7 directories

---
