# Quick Start Guide

This guide will help you get started with terraform-ingest in just a few minutes.

## Installation

```bash
# Clone the repository
git clone https://github.com/zloeber/terraform-ingest.git
cd terraform-ingest

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Basic Usage

### 1. Initialize a Configuration File

```bash
terraform-ingest init my-config.yaml
```

This creates a sample configuration file that you can edit.

### 2. Edit the Configuration

Edit `my-config.yaml` to add your terraform repositories:

```yaml
repositories:
  - url: https://github.com/your-org/terraform-module
    name: my-terraform-module
    branches:
      - main
      - develop
    include_tags: true
    max_tags: 5
    path: .

output_dir: ./output
clone_dir: ./repos
```

### 3. Run the Ingestion

```bash
terraform-ingest ingest my-config.yaml
```

The tool will:
1. Clone each repository
2. Checkout each specified branch and tag
3. Parse the Terraform files
4. Generate JSON summaries in the output directory

### 4. Review the Output

Check the `./output` directory for JSON files:

```bash
ls -lh ./output/
cat ./output/my-terraform-module_main.json
```

Each JSON file contains:
- Module description
- Input variables with types, descriptions, and defaults
- Output values
- Required providers
- Module dependencies

## Using as a Service

### Start the API Server

```bash
terraform-ingest serve --port 8000
```

Or using uvicorn directly:

```bash
uvicorn terraform_ingest.api:app --host 0.0.0.0 --port 8000
```

### Make API Requests

**Check API status:**
```bash
curl http://localhost:8000/
```

**Analyze a single repository:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
    "branches": ["main"],
    "include_tags": false
  }'
```

**Ingest multiple repositories:**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
        "branches": ["main"]
      }
    ]
  }'
```

## Quick Commands Reference

```bash
# Show help
terraform-ingest --help

# Initialize config file
terraform-ingest init config.yaml

# Ingest from config file
terraform-ingest ingest config.yaml

# Ingest with custom directories
terraform-ingest ingest config.yaml -o ./my-output -c ./my-repos

# Analyze a single repository
terraform-ingest analyze https://github.com/user/terraform-module

# Analyze with tags
terraform-ingest analyze https://github.com/user/terraform-module --include-tags

# Start API server
terraform-ingest serve

# Start API server on custom port
terraform-ingest serve --port 8080
```

## Working with Private Repositories

For private repositories, ensure you have git credentials configured:

```bash
# Using SSH (recommended)
ssh-add ~/.ssh/id_rsa

# Or using HTTPS with credential helper
git config --global credential.helper store
```

The tool will use your existing git credentials when cloning repositories.

## RAG Pipeline Integration

The JSON output is designed for ingestion into vector databases for RAG applications:

```python
import json
from terraform_ingest import TerraformIngest

# Process modules
ingester = TerraformIngest.from_yaml('config.yaml')
summaries = ingester.ingest()

# Prepare for vector database
for summary in summaries:
    # Create searchable text
    text = f"""
    Repository: {summary.repository}
    Description: {summary.description}
    Providers: {', '.join(p.name for p in summary.providers)}
    Variables: {', '.join(v.name for v in summary.variables)}
    """
    
    # Create metadata
    metadata = {
        "repo": summary.repository,
        "ref": summary.ref,
        "variables": len(summary.variables),
        "outputs": len(summary.outputs),
    }
    
    # Store in your vector database
    # vector_db.add(text, metadata)
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check out [examples/](examples/) for more usage examples
- Run tests: `pytest tests/`
- View API documentation: Start the server and visit `http://localhost:8000/docs`
