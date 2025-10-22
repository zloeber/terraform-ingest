# terraform-ingest

A terraform multi-repo module AI RAG ingestion engine that accepts a YAML file of terraform git repository sources, downloads them locally using existing credentials, creates JSON summaries of their purpose, inputs, outputs, and providers on the main and git tag branches for ingestion via a RAG pipeline into a vector database.

<!---toc start-->

* [terraform-ingest](#terraform-ingest)
  * [Features](#features)
  * [Installation](#installation)
  * [Usage](#usage)
    * [CLI Interface](#cli-interface)
      * [Initialize a Configuration File](#initialize-a-configuration-file)
      * [Ingest Repositories from Configuration](#ingest-repositories-from-configuration)
      * [Analyze a Single Repository](#analyze-a-single-repository)
    * [MCP Service for AI Agents](#mcp-service-for-ai-agents)
      * [Start the MCP Server](#start-the-mcp-server)
      * [MCP Tools](#mcp-tools)
      * [Example MCP Usage](#example-mcp-usage)
      * [Configuring Output Directory](#configuring-output-directory)
    * [API Service](#api-service)
      * [Start the API Server](#start-the-api-server)
      * [API Endpoints](#api-endpoints)
      * [Example API Requests](#example-api-requests)
  * [Configuration File Format](#configuration-file-format)
    * [Configuration Options](#configuration-options)
  * [Output Format](#output-format)
  * [Use Cases](#use-cases)
    * [RAG Pipeline Integration](#rag-pipeline-integration)
    * [Example RAG Workflow](#example-rag-workflow)
  * [Development](#development)
    * [Running Tests](#running-tests)
    * [Code Quality](#code-quality)
  * [License](#license)
  * [Contributing](#contributing)

<!---toc end-->

## Features

- 📥 **Multi-Repository Ingestion**: Process multiple Terraform repositories from a single YAML configuration
- 🔍 **Comprehensive Analysis**: Extracts variables, outputs, providers, modules, and descriptions
- 🏷️ **Branch & Tag Support**: Analyzes both branches and git tags
- 🔌 **Dual Interface**: Use as a CLI tool (Click) or as a REST API service (FastAPI)
- 🤖 **MCP Integration**: FastMCP service for AI agent access to ingested modules
- 📊 **JSON Output**: Generates structured JSON summaries ready for RAG ingestion
- 🔐 **Credential Support**: Uses existing git credentials for private repositories

## Installation

```bash
uv sync
source .venv/bin/activate
```

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

### MCP Service for AI Agents

The FastMCP service exposes ingested Terraform modules to AI agents through the Model Context Protocol (MCP). This allows AI assistants to query and discover Terraform modules from your ingested repositories.

#### Start the MCP Server

```bash
terraform-ingest-mcp
```

The server will start and expose two tools:

1. **list_repositories**: Lists all accessible Git repositories containing Terraform modules
2. **search_modules**: Searches for Terraform modules by name, provider, or keywords

#### MCP Tools

**list_repositories**
```python
# Lists all repositories with metadata
list_repositories(
    filter="aws",           # Optional: filter by keyword
    limit=50,               # Optional: max results (default: 50)
    output_dir="./output"   # Optional: path to JSON summaries
)
```

Returns repository information including:
- URL and name
- Description
- Branches/tags analyzed
- Module count
- Providers used

**search_modules**
```python
# Search for modules
search_modules(
    query="vpc",                    # Required: search term
    repo_urls=["https://..."],      # Optional: specific repos
    provider="aws",                 # Optional: filter by provider
    output_dir="./output"           # Optional: path to JSON summaries
)
```

Returns detailed module information including:
- Repository and ref (branch/tag)
- Variables and outputs
- Providers and sub-modules
- README content

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

The MCP service reads from the directory where ingested JSON summaries are stored. By default, this is `./output`. You can specify a different directory:

```bash
# Set via environment variable
export TERRAFORM_INGEST_OUTPUT_DIR=/path/to/output

# Or pass directly to tools in MCP calls
list_repositories(output_dir="/custom/path")
```

### API Service

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
```

### Configuration Options

**Repository Options:**
- `url` (required): Git repository URL
- `name` (optional): Custom name for the repository
- `branches` (optional): List of branches to analyze (default: ["main"])
- `include_tags` (optional): Whether to include git tags (default: true)
- `max_tags` (optional): Maximum number of tags to process (default: 10)
- `path` (optional): Path within the repository to the Terraform module (default: ".")

**Global Options:**
- `output_dir` (optional): Directory for JSON output files (default: "./output")
- `clone_dir` (optional): Directory for cloning repositories (default: "./repos")

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

# Process for vector database
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
