<!-- mcp-name: io.github.zloeber/terraform-ingest -->
# Terraform Ingest

A Terraform RAG ingestion engine that accepts a YAML file of terraform git repository sources, downloads them locally using existing credentials, creates JSON summaries of their purpose, inputs, outputs, and providers for branches or tagged releases you specify and embeds them into a vector database for similarity searches. Includes an easy to use cli, API, or MCP server.

## Features

- 📥 **Multi-Repository Ingestion**: Process multiple Terraform repositories from a single YAML configuration
- 🔄 **Auto-Import**: Import repositories from GitHub organizations and GitLab groups (Bitbucket support coming soon)
- 🔍 **Comprehensive Analysis**: Extracts variables, outputs, providers, modules, and descriptions
- 🏷️ **Branch & Tag Support**: Analyzes both branches and git tags of your choosing
- 🔌 **Dual Interface**: Use as a CLI tool (Click) or as a REST API service (FastAPI)
- 🤖 **MCP Integration**: MCP service for AI agent access to ingested modules via STDIO, SSE, or Streamable-http
- 📊 **JSON Output**: Generates structured JSON summaries ready for RAG ingestion
- 🔐 **Credential Support**: Uses existing git credentials for private repositories
- 🧠 **Vector Database Embeddings**: Semantic search with ChromaDB, OpenAI, Claude, or sentence-transformers

Further documentation found [here](https://zloeber.github.io/terraform-ingest/)

Or, if you just want the TLDR on using this as an MCP server (along with some examples) check [this](./docs/mcp_use_examples.md) out.

An example project repo with a large list of custom modules for kicking the tires can be found [here](https://github.com/zloeber/terraform-ingest-example)

## Installation

This application can be run locally using uv or docker.

> **NOTE** `uv` is required for lazy-loading some large dependencies.

```bash
uv tool install terraform-ingest

# Create a config
uv run terraform-ingest init config.yaml

# Or import repositories from a GitHub organization
uv run terraform-ingest import github --org terraform-aws-modules --terraform-only

# Or import repositories from a GitLab group
uv run terraform-ingest import gitlab --group mygroup --recursive --terraform-only

# Update your config.yaml file to include your terraform module information and mcp config then preform the initial ingestion
uv run terraform-ingest ingest config.yaml

# Run a quick cli search to test things out
uv run terraform-ingest search "vpc module for aws"

## Docker
docker pull ghcr.io/zloeber/terraform-ingest:latest

# Run with volume mount for persistence, ingest modules from local config.yaml file
docker run -v $(pwd)/repos:/app/repos -v $(pwd)/output:/app/output -v $(pwd)/config.yaml:/app/config.yaml ghcr.io/zloeber/terraform-ingest:latest ingest /app/config.yaml

# Run as MCP server
docker run -v $(pwd)/repos:/app/repos -v $(pwd)/output:/app/output -v $(pwd)/config.yaml:/app/config.yaml -p 8000:8000 ghcr.io/zloeber/terraform-ingest:latest mcp -c /app/config.yaml

# Search for modules and get the first result, show all details
terraform-ingest search "vpc module for aws" -l 1 -j | jq -r '.results[0].id' | xargs -I {} terraform-ingest index get {}
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.