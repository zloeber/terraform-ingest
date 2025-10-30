# Automatic Dependency Installation for Embeddings

## Overview

The application now automatically installs required embedding dependencies when they are used in the configuration. This eliminates the need for users to manually install optional packages like `sentence-transformers` and `chromadb`.

## How It Works

### Automatic Detection

The `DependencyInstaller` class automatically:

1. **Detects embedding configuration**: Checks if embeddings are enabled in the configuration
2. **Identifies required packages**: Based on the embedding strategy selected:
   - `sentence-transformers`: Installs `sentence-transformers` + `chromadb`
   - `openai`: Installs `openai` + `chromadb`
   - `claude`: Installs `voyageai` + `chromadb`
   - `chromadb-default`: Installs `chromadb`
3. **Checks installation status**: Determines which packages are missing
4. **Auto-installs**: Uses `uv` (preferred) or `pip` to install missing packages

### Default Behavior

By default, auto-installation is **enabled** in all entry points:
- CLI commands: `terraform-ingest ingest config.yaml`
- API endpoints: `POST /ingest`, `POST /analyze`, `POST /ingest-from-yaml`
- Programmatic usage: `TerraformIngest(config)`

## Usage Examples

### CLI with Auto-Installation (Default)

```bash
# Automatically installs embeddings packages if needed
terraform-ingest ingest config.yaml --enable-embeddings --embedding-strategy sentence-transformers
```

The application will:
1. Load the configuration
2. Detect that embeddings are enabled with `sentence-transformers` strategy
3. Check if `sentence-transformers` and `chromadb` are installed
4. If missing, install them using `uv pip install` or `pip install`
5. Proceed with ingestion

### CLI with Auto-Installation Disabled

```bash
# Disable auto-installation (useful in CI/CD with pre-installed dependencies)
terraform-ingest ingest config.yaml --no-auto-install-deps
```

### Programmatic Usage with Auto-Installation

```python
from terraform_ingest.ingest import TerraformIngest

# Auto-install is enabled by default
ingester = TerraformIngest.from_yaml("config.yaml", auto_install_deps=True)
summaries = ingester.ingest()
```

### Programmatic Usage Without Auto-Installation

```python
from terraform_ingest.ingest import TerraformIngest

# Disable auto-install (will raise ImportError if deps are missing)
ingester = TerraformIngest.from_yaml("config.yaml", auto_install_deps=False)
try:
    summaries = ingester.ingest()
except ImportError as e:
    print(f"Missing dependencies: {e}")
```

### API with Auto-Installation

```bash
curl -X POST http://localhost:8000/ingest-from-yaml \
  -H "Content-Type: application/json" \
  -d '{
    "yaml_content": "repositories: [...] \n embedding: {enabled: true, strategy: sentence-transformers}",
    "auto_install_deps": true
  }'
```

## Configuration Example

### config.yaml with Embeddings

```yaml
repositories:
  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc.git
    branches:
      - main

embedding:
  enabled: true
  strategy: sentence-transformers
  sentence_transformers_model: all-MiniLM-L6-v2
  chromadb_path: ./chromadb
```

When you run:
```bash
terraform-ingest ingest config.yaml
```

The application will:
1. Parse the configuration
2. Detect `embedding.enabled: true` with `strategy: sentence-transformers`
3. Automatically install `sentence-transformers` and `chromadb` if missing
4. Initialize the vector database
5. Begin processing repositories

## API Integration

### Dependency Installer Class

The core functionality is provided by the `DependencyInstaller` class in `dependency_installer.py`:

```python
from terraform_ingest.dependency_installer import DependencyInstaller

# Check if a package is installed
is_installed = DependencyInstaller.check_package_installed("chromadb")

# Get missing packages from a list
missing = DependencyInstaller.get_missing_packages(
    ["sentence-transformers", "chromadb"]
)

# Install packages
success = DependencyInstaller.install_packages(
    ["sentence-transformers", "chromadb"],
    use_uv=True
)

# Ensure embedding packages for a strategy
success = DependencyInstaller.ensure_embedding_packages(
    strategy="sentence-transformers",
    auto_install=True
)
```

### Convenience Function

The `ensure_embeddings_available()` function simplifies checking and installing for a configuration:

```python
from terraform_ingest.dependency_installer import ensure_embeddings_available
from terraform_ingest.models import EmbeddingConfig

config = EmbeddingConfig(enabled=True, strategy="sentence-transformers")

# Auto-install if needed
success = ensure_embeddings_available(config, auto_install=True)

# Or raise error if missing (with auto_install=False)
try:
    ensure_embeddings_available(config, auto_install=False)
except ImportError as e:
    print(f"Setup required: {e}")
```

## Installation Methods

The system uses these methods in order:

### 1. **uv** (Preferred)
```bash
python -m uv pip install sentence-transformers chromadb
```
- Faster installation
- Better dependency resolution
- Preferred if available

### 2. **pip** (Fallback)
```bash
python -m pip install sentence-transformers chromadb
```
- Used if `uv` is not available
- Standard Python package manager

## Error Handling

### Missing Dependencies (auto_install=False)

If `auto_install_deps=False` and packages are missing:

```python
ImportError: Missing dependencies for embedding strategy 'sentence-transformers'.
Install with: pip install terraform-ingest[embeddings]
```

### Installation Failure

If auto-installation fails:

```
Failed to install packages: [error details]
Please install manually with:
  pip install sentence-transformers chromadb
Or with uv:
  uv add sentence-transformers chromadb
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Setup dependencies
  run: |
    python -m pip install terraform-ingest[embeddings]

- name: Run ingestion
  run: |
    terraform-ingest ingest config.yaml --no-auto-install-deps
```

### Docker Example

```dockerfile
# Pre-install embeddings in Docker
RUN pip install terraform-ingest[embeddings]

# Or use the embeddings image variant
FROM ghcr.io/zloeber/terraform-ingest:embeddings-latest
```

## Performance Considerations

### First-Run Installation

First-time auto-installation takes longer due to:
- Package downloads (~100-500MB for embeddings)
- Compilation of native extensions
- Model downloads for sentence-transformers

**Expected time**: 2-5 minutes

### Subsequent Runs

If packages are already installed:
- Installation check completes in < 1 second
- No download or compilation overhead
- Full ingestion proceeds immediately

### Disable Auto-Install for Speed

If you frequently run with known-good environments:

```bash
terraform-ingest ingest config.yaml --no-auto-install-deps
```

Saves ~1-2 seconds per run on package checking.

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'sentence_transformers'"

**Solution**: Enable auto-installation:
```bash
terraform-ingest ingest config.yaml  # auto_install_deps is True by default
```

### Issue: Installation appears stuck

**Solution**: The system might be downloading large models. Wait or increase timeout:
```bash
# Verbose output to see what's happening
python -m pip install -v sentence-transformers chromadb
```

### Issue: Permission denied during installation

**Solution**: Either:
1. Use a virtual environment: `python -m venv venv && source venv/bin/activate`
2. Install system-wide: `pip install --user terraform-ingest[embeddings]`
3. Use Docker for isolation

### Issue: Wrong package installed

**Solution**: Reinstall with specific version:
```bash
pip install --force-reinstall terraform-ingest[embeddings]
```

## Configuration Options

### Disable Auto-Install Globally

Set environment variable:
```bash
export TERRAFORM_INGEST_AUTO_INSTALL_DEPS=false
terraform-ingest ingest config.yaml
```

### Prefer pip over uv

```python
from terraform_ingest.dependency_installer import DependencyInstaller

DependencyInstaller.install_packages(
    ["sentence-transformers"],
    use_uv=False  # Use pip instead
)
```

## Testing

The feature is tested with:
- Unit tests for `DependencyInstaller` class
- Integration tests for CLI and API
- Tests for different embedding strategies
- Tests for missing package scenarios

Run tests:
```bash
pytest tests/test_dependency_installer.py
```

## See Also

- `src/terraform_ingest/dependency_installer.py` - Implementation
- `src/terraform_ingest/ingest.py` - TerraformIngest with auto-install integration
- `src/terraform_ingest/cli.py` - CLI with `--auto-install-deps` flag
- `src/terraform_ingest/api.py` - API with auto-install support
- `docs/embeddings.md` - Embeddings configuration guide
