# terraform-ingest

A terraform multi-repo module AI RAG ingestion engine that accepts a YAML file of terraform git repository sources, downloads them locally using existing credentials, creates JSON summaries of their purpose, inputs, outputs, and providers for branches or tagged releases you specify for ingestion via a RAG pipeline into a vector database. Includes an easy to use cli, API, or MCP server.

## Features

- 📥 **Multi-Repository Ingestion**: Process multiple Terraform repositories from a single YAML configuration
- 🔍 **Comprehensive Analysis**: Extracts variables, outputs, providers, modules, and descriptions
- 🏷️ **Branch & Tag Support**: Analyzes both branches and git tags
- 🔌 **Dual Interface**: Use as a CLI tool (Click) or as a REST API service (FastAPI)
- 🤖 **[MCP Integration](./mcp.md)**: FastMCP service for AI agent access to ingested modules
- 📊 **JSON Output**: Generates structured JSON summaries ready for RAG ingestion
- 🔐 **Credential Support**: Uses existing git credentials for private repositories
- 🧠 **Vector Database Embeddings**: Semantic search with ChromaDB, OpenAI, Claude, or sentence-transformers

## Installation

This application can be run locally as a CLI, API service, or MCP server using uv or docker.

```bash
# simple pip install
pip install terraform-ingest

## UV (preferred)
# Create a config
uv run terraform-ingest init config.yaml

# Update your config.yaml file to include your terraform module information and mcp config then preform the initial ingestion
uv run terraform-ingest ingest

# Run a quick cli search to test things out
uv run terraform-ingest search "vpc module for aws"
```

### Optional: Install with Vector Database Support

For semantic search with ChromaDB embeddings:

```bash
# Default and already included in the install
uv add chromadb sentence-transformers

# Or for all embedding options (OpenAI, Claude/Voyage)
uv add openai voyageai
```

See [Vector Database Embeddings](./embeddings.md) for detailed setup instructions.

## Usage

### CLI Interface

#### Initialize a Configuration File

```bash
terraform-ingest init config.yaml
```

#### Ingest Repositories from Configuration

```bash
terraform-ingest ingest config.yaml
```

With custom output and clone directories:

```bash
terraform-ingest ingest config.yaml -o ./my-output -c ./my-repos
```

With cleanup after ingestion:

```bash
terraform-ingest ingest config.yaml --cleanup
```

#### Analyze a Single Repository

```bash
terraform-ingest analyze https://github.com/terraform-aws-modules/terraform-aws-vpc
```

With branch specification and tags:

```bash
terraform-ingest analyze https://github.com/user/terraform-module -b develop --include-tags --max-tags 5
```

Save output to file:

```bash
terraform-ingest analyze https://github.com/user/terraform-module -o output.json
```

#### Search with Vector Database

Search for modules using semantic search (requires embeddings to be enabled):

```bash
# Basic semantic search
terraform-ingest search "vpc module for aws"

# Filter by provider
terraform-ingest search "kubernetes cluster" --provider aws

# Filter by repository and limit results
terraform-ingest search "security group" --repository https://github.com/terraform-aws-modules/terraform-aws-vpc --limit 5
```

See [Vector Database Embeddings](./embeddings.md) for configuration and advanced usage.

## MCP

The FastMCP service exposes ingested Terraform modules to AI agents through the Model Context Protocol (MCP). This allows AI assistants to query and discover Terraform modules from your ingested repositories.

### Start the MCP Server

```bash
terraform-ingest-mcp

# Or via streamable-http and a custom configuration file
uv run terraform-ingest mcp -c config.client.yaml --transport streamable-http

# Or via sse
uv run terraform-ingest mcp --transport sse
```

### MCP Client Configuration

VSCode:

```json
{
  "servers": {
    "terraform-ingest-mcp": {
      "command": "uvx",
      "args": ["terraform-ingest@latest" , "mcp", "-c", "examples/cloudposse.yaml"]
    },
  }
}
```

> **NOTE** If you have many modules and automatic import enabled it may take a while to get started. You may wish to pre-ingest the modules.

#### Example MCP Usage

Once the MCP server is running, AI agents can use it to:

1. **Discover Available Modules**:
   - "What Terraform modules are available for AWS?"
   - "Show me all modules that use the azurerm provider"

2. **Search for Specific Functionality**:
   - "Find modules that create VPCs"
   - "Search for modules with security group configurations"

3. **Analyze Module Details**:
   - "What are the inputs for the AWS VPC module?"
   - "Show me the outputs from the network module"

#### Configuring Output Directory

The MCP service caches ingested JSON summaries locally in an target folder. By default, this is `./output`. You can specify a different directory:

```bash
# Set via environment variable
export TERRAFORM_INGEST_OUTPUT_DIR=/path/to/output

# Or pass directly to tools in MCP calls
list_repositories(output_dir="/custom/path")
```

### API Service

While this has been included it is not thoroughly tested. MCP server usage is preferred.

#### Start the API Server

```bash
uvicorn terraform_ingest.api:app --host 0.0.0.0 --port 8000
```

Or run directly:

```bash
python -m terraform_ingest.api
```

#### API Endpoints

- `GET /` - API information and available endpoints
- `GET /health` - Health check
- `POST /ingest` - Ingest multiple repositories
- `POST /analyze` - Analyze a single repository
- `POST /ingest-from-yaml` - Ingest from YAML configuration string
- `POST /search/vector` - Search modules using vector embeddings

#### Example API Requests

**Analyze a single repository:**

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
    "branches": ["main"],
    "include_tags": true,
    "max_tags": 3
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
        "branches": ["main"],
        "include_tags": true,
        "max_tags": 5
      }
    ]
  }'
```

**Search with vector embeddings:**

```bash
curl -X POST http://localhost:8000/search/vector \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vpc module with public and private subnets",
    "provider": "aws",
    "limit": 5,
    "config_file": "config.yaml"
  }'
```

## Configuration File Format

The YAML configuration file defines repositories to process:

```yaml
repositories:
  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc
    name: terraform-aws-vpc
    branches:
      - main
      - master
    include_tags: true
    max_tags: 5
    path: .

  - url: https://github.com/user/another-module
    name: another-module
    branches:
      - main
    include_tags: false
    path: modules/submodule

output_dir: ./output
clone_dir: ./repos

# Optional: Vector database configuration for semantic search
embedding:
  enabled: true
  strategy: chromadb-default  # or: openai, claude, sentence-transformers
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

### Configuration Options

**Repository Options:**
- `url` (required): Git repository URL
- `name` (optional): Custom name for the repository
- `branches` (optional): List of branches to analyze (default: [])
- `include_tags` (optional): Whether to include git tags (default: true)
- `max_tags` (optional): Maximum number of tags to process (default: 1)
- `path` (optional): Path within the repository to the Terraform module (default: ".")

**Global Options:**
- `output_dir` (optional): Directory for JSON output files (default: "./output")
- `clone_dir` (optional): Directory for cloning repositories (default: "./repos")

**Embedding Options**:
- `embedding.enabled` (optional): Enable vector database embeddings (default: false)
- `embedding.strategy` (optional): Embedding strategy - "chromadb-default", "openai", "claude", or "sentence-transformers" (default: "chromadb-default")
- `embedding.chromadb_path` (optional): Path to ChromaDB storage (default: "./chromadb")
- `embedding.collection_name` (optional): ChromaDB collection name (default: "terraform_modules")

See [Vector Database Embeddings](./embeddings.md) for complete embedding configuration options.

## Output Format

Each processed module version generates a JSON file with the following structure:

```json
{
  "repository": "https://github.com/user/terraform-module",
  "ref": "main",
  "path": ".",
  "description": "Module description from README or comments",
  "variables": [
    {
      "name": "vpc_cidr",
      "type": "string",
      "description": "CIDR block for VPC",
      "default": "10.0.0.0/16",
      "required": false
    }
  ],
  "outputs": [
    {
      "name": "vpc_id",
      "description": "ID of the VPC",
      "value": null,
      "sensitive": false
    }
  ],
  "providers": [
    {
      "name": "aws",
      "source": "hashicorp/aws",
      "version": ">= 4.0"
    }
  ],
  "modules": [
    {
      "name": "subnets",
      "source": "./modules/subnets",
      "version": null
    }
  ],
  "readme_content": "# Terraform Module\n..."
}
```

## Use Cases

### RAG Pipeline Integration

The JSON output is structured for easy ingestion into vector databases:

1. **Semantic Search**: Find relevant Terraform modules based on natural language queries
2. **Module Discovery**: Discover modules with specific inputs, outputs, or providers
3. **Version Analysis**: Compare module versions across branches and tags
4. **Documentation Enhancement**: Augment module documentation with AI-generated insights

### Example RAG Workflow

```python
from terraform_ingest import TerraformIngest

# Ingest modules
ingester = TerraformIngest.from_yaml('config.yaml')
summaries = ingester.ingest()

# Process for vector database (automatic if embeddings enabled in config)
# Or manually process JSON summaries for your own vector database
for summary in summaries:
    # Create embeddings from description, variables, outputs
    text = f"{summary.description} Inputs: {summary.variables} Outputs: {summary.outputs}"
    
    # Store in vector database with metadata
    metadata = {
        "repository": summary.repository,
        "ref": summary.ref,
        "providers": [p.name for p in summary.providers]
    }
    # vector_db.store(text, metadata)

# With built-in embeddings enabled, search semantically
if ingester.vector_db:
    results = ingester.search_vector_db(
        "vpc module with private subnets",
        filters={"provider": "aws"},
        n_results=5
    )
    for result in results:
        print(f"Found: {result['metadata']['repository']}")
```

## Vector Database Embeddings

Terraform-ingest supports semantic search through vector database embeddings with ChromaDB. This enables natural language queries and AI-powered module discovery.

### Quick Start

1. **Install ChromaDB**:
   ```bash
   pip install chromadb
   ```

2. **Enable in config**:
   ```yaml
   embedding:
     enabled: true
     strategy: chromadb-default
     chromadb_path: ./chromadb
     collection_name: terraform_modules
   ```

3. **Ingest and search**:
   ```bash
   terraform-ingest ingest config.yaml
   terraform-ingest search "vpc module for aws"
   ```

### Features

- 🎯 **Semantic Search**: Natural language queries like "vpc with private subnets"
- 🔌 **Multiple Strategies**: ChromaDB default, OpenAI, Claude, or sentence-transformers
- 🏷️ **Metadata Filtering**: Filter by provider, repository, tags
- 🔄 **Incremental Updates**: Automatically update embeddings on re-ingestion
- 🎛️ **Hybrid Search**: Combine vector similarity with keyword matching

### Embedding Strategies

| Strategy | Description | Setup |
|----------|-------------|-------|
| `chromadb-default` | Built-in ChromaDB embeddings | `pip install chromadb` |
| `sentence-transformers` | Local models, no API | `pip install sentence-transformers` |
| `openai` | Best quality, requires API key | `pip install openai` |
| `claude` | Voyage AI embeddings | `pip install voyageai` |

### Example Queries

```bash
# Natural language
terraform-ingest search "module for creating kubernetes clusters with autoscaling"

# With filters
terraform-ingest search "database with replication" --provider aws --limit 3

# Via API
curl -X POST http://localhost:8000/search/vector \
  -H "Content-Type: application/json" \
  -d '{"query": "vpc with vpn support", "provider": "aws"}'
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
black src/
flake8 src/
mypy src/
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
