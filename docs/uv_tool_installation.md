# Using terraform-ingest as a uv Tool with Automatic Dependencies

## Overview

When installing `terraform-ingest` as a `uv` tool (using `uv tool install`), the application has built-in support for automatically installing optional dependencies like embedding packages. This guide explains how to enable and use this functionality.

## Installation as a uv Tool

### Basic Installation

```bash
uv tool install terraform-ingest
```

This installs `terraform-ingest` commands globally using `uv`:
- `terraform-ingest` - Main CLI tool
- `terraform-ingest-mcp` - MCP service for AI agents

### Installation from GitHub (Development)

```bash
uv tool install git+https://github.com/zloeber/terraform-ingest.git
```

### Installation from Local Path

```bash
uv tool install -e /path/to/terraform-ingest
```

## How Automatic Dependency Installation Works

### Default Behavior

When `terraform-ingest` is installed as a `uv` tool, automatic dependency installation is **enabled by default**. The application uses the `DependencyInstaller` class to:

1. **Detect** which optional packages are needed (based on your configuration)
2. **Check** if they're already installed
3. **Install** missing packages automatically using smart detection
4. **Fallback** through multiple methods to ensure success

### Supported Package Installation Methods

The auto-installer tries methods in this order:

1. **`uv pip install --system`** (preferred for uv tool installations - installs system-wide)
2. **`uv pip install`** (for virtual environments)
3. **`pip` module** (`python -m pip install`)
4. **`pip` command** (direct executable)
5. **`pip3` command** (direct executable)

The `--system` flag is crucial when running as a `uv` tool because it bypasses the requirement for an active virtual environment.

## Usage Scenarios

### Scenario 1: Auto-Install Embeddings (Default)

Run the ingestion with embeddings enabled, and dependencies install automatically:

```bash
terraform-ingest ingest config.yaml \
  --enable-embeddings \
  --embedding-strategy sentence-transformers
```

**What happens:**
1. Configuration is loaded
2. Application detects embeddings are enabled with `sentence-transformers`
3. Checks if `sentence-transformers` and `chromadb` are installed
4. If missing, automatically installs them using `uv pip install`
5. Proceeds with ingestion

### Scenario 2: Disable Auto-Installation (Pre-Installed Dependencies)

If you've pre-installed dependencies and want to skip the auto-install check:

```bash
terraform-ingest ingest config.yaml \
  --no-auto-install-deps \
  --enable-embeddings \
  --embedding-strategy openai
```

### Scenario 3: Using Different Embedding Strategies

Each strategy has specific package requirements. The auto-installer handles all of them:

#### OpenAI Strategy
```bash
terraform-ingest ingest config.yaml \
  --enable-embeddings \
  --embedding-strategy openai
```
**Installs:** `openai`, `chromadb`

#### Claude Strategy (Voyage AI)
```bash
terraform-ingest ingest config.yaml \
  --enable-embeddings \
  --embedding-strategy claude
```
**Installs:** `voyageai`, `chromadb`

#### Sentence Transformers Strategy
```bash
terraform-ingest ingest config.yaml \
  --enable-embeddings \
  --embedding-strategy sentence-transformers
```
**Installs:** `sentence-transformers`, `chromadb`

#### ChromaDB Default (No Embeddings Model)
```bash
terraform-ingest ingest config.yaml \
  --enable-embeddings \
  --embedding-strategy chromadb-default
```
**Installs:** `chromadb` only

## Configuration File Examples

### config.yaml with Auto-Installable Embeddings

```yaml
repositories:
  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc.git
    branches:
      - main
    recursive: true

embedding:
  enabled: true
  strategy: sentence-transformers
  sentence_transformers_model: all-MiniLM-L6-v2
  chromadb_path: ./chromadb
  output_dir: ./embeddings-output
```

Run with:
```bash
terraform-ingest ingest config.yaml
```

The embedding packages will install automatically.

### config.yaml with OpenAI API Key

```yaml
repositories:
  - url: https://github.com/cloudposse/terraform-aws-components.git
    branches:
      - main
    recursive: true

embedding:
  enabled: true
  strategy: openai
  openai_api_key: ${OPENAI_API_KEY}
  chromadb_path: ./chromadb
  output_dir: ./embeddings-output
```

Ensure your API key is set:
```bash
export OPENAI_API_KEY="sk-..."
terraform-ingest ingest config.yaml
```

The `openai` and `chromadb` packages will install automatically.

## Programmatic Usage

If you're using `terraform-ingest` as a library in your Python code:

### With Auto-Installation Enabled (Default)

```python
from terraform_ingest.ingest import TerraformIngest

# Auto-install is enabled by default
ingester = TerraformIngest.from_yaml(
    "config.yaml",
    auto_install_deps=True  # Explicit, but True is default
)
summaries = ingester.ingest()
```

### With Auto-Installation Disabled

```python
from terraform_ingest.ingest import TerraformIngest

ingester = TerraformIngest.from_yaml(
    "config.yaml",
    auto_install_deps=False  # Skip auto-install
)
try:
    summaries = ingester.ingest()
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Install with: uv add terraform-ingest[embeddings]")
```

### Handling Installation Errors

```python
from terraform_ingest.ingest import TerraformIngest
from loguru import logger

try:
    ingester = TerraformIngest.from_yaml(
        "config.yaml",
        auto_install_deps=True
    )
    summaries = ingester.ingest()
except Exception as e:
    logger.error(f"Ingestion failed: {e}")
    # Check logs to see if it was a dependency installation issue
```

## API Usage with Auto-Installation

If running the FastAPI server:

```bash
terraform-ingest-api
```

### POST to /ingest-from-yaml with Auto-Install

```bash
curl -X POST http://localhost:8000/ingest-from-yaml \
  -H "Content-Type: application/json" \
  -d '{
    "yaml_content": "repositories:\n  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc.git\nembedding:\n  enabled: true\n  strategy: sentence-transformers",
    "auto_install_deps": true,
    "output_dir": "./output"
  }'
```

## Troubleshooting

### Problem: "No virtual environment found" Error

**Symptom:** Error message:
```
WARNING  | dependency_installer - Failed to install with uv: error: No virtual environment found; 
run `uv venv` to create an environment, or pass `--system` to install into a non-virtual environment
```

**Root Cause:** When installed as a `uv` tool, the application runs in a managed environment without an active Python virtual environment. The `uv pip install` command needs the `--system` flag to work.

**Solution:** This is now automatically handled! The updated installer tries `uv pip install --system` first, which allows installation into the tool's managed environment. 

If you still see this error after updating:
1. Update to the latest version
2. Try manually installing with the `--system` flag:
   ```bash
   uv pip install --system sentence-transformers chromadb
   ```
3. Or reinstall the tool with embedded dependencies:
   ```bash
   uv tool install --force terraform-ingest[embeddings]
   ```

### Problem: "uv pip install" Not Found

**Symptom:** When auto-install tries to use `uv pip install`, it fails with "command not found"

**Solution:** When installed as a `uv` tool, `uv` itself may not be in the PATH for subprocess calls. The installer automatically falls back to `pip`:

```bash
# Verify uv is installed
uv --version

# Manually install missing packages if auto-install fails
uv add terraform-ingest[embeddings]

# Or with pip
pip install terraform-ingest[embeddings]
```

### Problem: Permission Denied Installing Packages

**Symptom:** `Permission denied` when trying to install packages

**Solution:** 

Option 1: Use user install
```bash
pip install --user terraform-ingest[embeddings]
```

Option 2: Use a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
uv tool install terraform-ingest
```

### Problem: Wrong Python Version

**Symptom:** Installed packages are in a different Python environment than the tool

**Solution:** Check which Python the tool is using:
```bash
which terraform-ingest
# Shows the tool location

# Force reinstall with specific Python
uv tool install --python /path/to/python terraform-ingest
```

### Problem: Dependencies Already Installed But Still Installing

**Symptom:** Auto-installer keeps trying to install already-installed packages

**Solution:** This usually means the package import name differs from the pip name. You can manually install and disable auto-install:

```bash
# Install once
uv add sentence-transformers chromadb

# Then disable auto-install
terraform-ingest ingest config.yaml --no-auto-install-deps
```

## Best Practices

### 1. Use Configuration Files for Reproducibility

Instead of relying on CLI flags, put embedding config in `config.yaml`:

```yaml
embedding:
  enabled: true
  strategy: sentence-transformers
```

Then run simply:
```bash
terraform-ingest ingest config.yaml
```

### 2. Pre-Install in CI/CD Pipelines

For CI/CD environments, install dependencies upfront and disable auto-install:

```bash
# In CI/CD setup
uv add terraform-ingest[embeddings]

# In CI/CD job
terraform-ingest ingest config.yaml --no-auto-install-deps
```

### 3. Use Optional Dependencies for Clean Installation

If you always want embeddings, specify them during installation:

```bash
uv tool install terraform-ingest[embeddings]
```

This pre-installs all embedding packages, so auto-install has nothing to do.

### 4. Enable Logging for Debugging

Set log level to see what auto-install is doing:

```bash
export TERRAFORM_INGEST_LOG_LEVEL=DEBUG
terraform-ingest ingest config.yaml --enable-embeddings
```

The logs will show:
- Which packages are being checked
- Which are missing
- Which installer method is being used
- Success or failure of installation

### 5. Verify Installation After Setup

Test that auto-install works:

```bash
# Run a quick test
terraform-ingest ingest config.yaml --enable-embeddings --embedding-strategy sentence-transformers 2>&1 | head -20
```

## Environment Variables

### TERRAFORM_INGEST_LOG_LEVEL

Controls logging verbosity:
```bash
export TERRAFORM_INGEST_LOG_LEVEL=DEBUG
terraform-ingest ingest config.yaml
```

Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### TERRAFORM_INGEST_OUTPUT_DIR

Override default output directory:
```bash
export TERRAFORM_INGEST_OUTPUT_DIR=/custom/path
terraform-ingest ingest config.yaml
```

## Related Documentation

- [Automatic Dependency Installation](./automatic_dependency_installation.md) - Detailed technical documentation
- [Embeddings Configuration](./embeddings.md) - Embedding strategy details
- [CLI Reference](./cli.md) - Full CLI command documentation
- [API Reference](./docker_complete.md) - FastAPI endpoint documentation

## Summary

When `terraform-ingest` is installed as a `uv` tool:
- ✅ Optional dependencies are **automatically installed** by default
- ✅ Installation uses **`uv pip install`** (preferred) with fallback to **`pip`**
- ✅ Works with **all embedding strategies**: sentence-transformers, openai, claude, chromadb-default
- ✅ Can be **disabled** with `--no-auto-install-deps` flag
- ✅ Supports **configuration file** and **CLI flags** for customization
- ✅ Provides **detailed logging** for troubleshooting

This means users can install once with `uv tool install terraform-ingest` and use embeddings immediately without additional setup!
