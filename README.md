# terraform-ingest

A terraform multi-repo module AI RAG ingestion engine that accepts a YAML file of terraform git repository sources, downloads them locally using existing credentials, creates JSON summaries of their purpose, inputs, outputs, and providers for branches or tagged releases you specify for ingestion via a RAG pipeline into a vector database. Includes an easy to use cli, API, or MCP server.

## Features

- 📥 **Multi-Repository Ingestion**: Process multiple Terraform repositories from a single YAML configuration
- 🔍 **Comprehensive Analysis**: Extracts variables, outputs, providers, modules, and descriptions
- 🏷️ **Branch & Tag Support**: Analyzes both branches and git tags
- 🔌 **Dual Interface**: Use as a CLI tool (Click) or as a REST API service (FastAPI)
- 🤖 **MCP Integration**: FastMCP service for AI agent access to ingested modules
- 📊 **JSON Output**: Generates structured JSON summaries ready for RAG ingestion
- 🔐 **Credential Support**: Uses existing git credentials for private repositories
- 🧠 **Vector Database Embeddings**: Semantic search with ChromaDB, OpenAI, Claude, or sentence-transformers

Further documentation found [here](https://zloeber.github.io/terraform-ingest/)

Or, if you just want the goods on using this as an MCP server along with some examples check [this](./docs/mcp_use_examples.md) out.

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

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
