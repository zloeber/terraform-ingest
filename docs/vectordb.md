# Vector Database Embeddings for Terraform Modules

This document describes the vector database embedding feature for terraform-ingest, which enables semantic search and AI-powered module discovery using ChromaDB.

## Overview

The embedding feature allows you to:
- Automatically embed Terraform module data into a vector database (ChromaDB)
- Use semantic search to find modules based on natural language queries
- Filter by metadata (provider, repository, tags)
- Combine vector search with keyword matching for hybrid search
- Incrementally update module embeddings as repositories are re-processed

## Configuration

### Basic Configuration

Add an `embedding` section to your `config.yaml`:

```yaml
repositories:
  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc
    name: terraform-aws-vpc
    branches:
      - main
    include_tags: true
    max_tags: 5

output_dir: ./output
clone_dir: ./repos

# Vector database embedding configuration
embedding:
  enabled: true
  strategy: chromadb-default  # or: openai, claude, sentence-transformers
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

### Embedding Strategies

Four embedding strategies are supported:

#### 1. ChromaDB Default (Recommended for Getting Started)

Uses ChromaDB's built-in embedding function (sentence-transformers based):

```yaml
embedding:
  enabled: true
  strategy: chromadb-default
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

**Installation:**
```bash
pip install chromadb
```

#### 2. Sentence Transformers (Local, No API Keys)

Uses local sentence-transformers models:

```yaml
embedding:
  enabled: true
  strategy: sentence-transformers
  sentence_transformers_model: all-MiniLM-L6-v2  # or: all-mpnet-base-v2
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

**Installation:**
```bash
pip install chromadb sentence-transformers
```

#### 3. OpenAI Embeddings (Best Quality)

Uses OpenAI's embedding API:

```yaml
embedding:
  enabled: true
  strategy: openai
  openai_api_key: sk-...  # Or set OPENAI_API_KEY env var
  openai_model: text-embedding-3-small  # or: text-embedding-3-large
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

**Installation:**
```bash
pip install chromadb openai
```

#### 4. Claude/Voyage Embeddings

Uses Voyage AI embeddings (recommended by Anthropic):

```yaml
embedding:
  enabled: true
  strategy: claude
  anthropic_api_key: va_...  # Voyage AI key
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

**Installation:**
```bash
pip install chromadb voyageai
```

### Advanced Configuration

#### Content Configuration

Control what content is embedded:

```yaml
embedding:
  enabled: true
  strategy: sentence-transformers
  
  # What to include in embeddings
  include_description: true
  include_readme: true
  include_variables: true
  include_outputs: true
  include_resource_types: true
  
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

#### Hybrid Search Configuration

Configure the balance between vector and keyword search:

```yaml
embedding:
  enabled: true
  strategy: sentence-transformers
  
  # Hybrid search settings
  enable_hybrid_search: true
  keyword_weight: 0.3  # Weight for keyword matching (0.0 to 1.0)
  vector_weight: 0.7   # Weight for semantic similarity (0.0 to 1.0)
  
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

#### Client/Server Mode

Use ChromaDB in client/server mode:

```yaml
embedding:
  enabled: true
  strategy: sentence-transformers
  chromadb_host: localhost
  chromadb_port: 8000
  collection_name: terraform_modules
```

Start ChromaDB server separately:
```bash
chroma run --host localhost --port 8000 --path ./chromadb
```

## Usage

### CLI Usage

#### Ingest with Embeddings

Enable embeddings from your config file:

```bash
terraform-ingest ingest config.yaml
```

Override config to enable embeddings:

```bash
terraform-ingest ingest config.yaml --enable-embeddings --embedding-strategy sentence-transformers
```

#### Search Vector Database

Search using natural language queries:

```bash
# Basic search
terraform-ingest search "vpc module for aws"

# Filter by provider
terraform-ingest search "kubernetes cluster" --provider aws

# Filter by repository
terraform-ingest search "networking" --repository https://github.com/terraform-aws-modules/terraform-aws-vpc

# Limit results
terraform-ingest search "security group" --limit 5

# Use custom config file
terraform-ingest search "vpc" --config my-config.yaml
```

### API Usage

#### Search Endpoint

**POST /search/vector**

Search using vector embeddings:

```bash
curl -X POST http://localhost:8000/search/vector \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vpc module for aws with public and private subnets",
    "provider": "aws",
    "limit": 5,
    "config_file": "config.yaml"
  }'
```

Response:
```json
{
  "results": [
    {
      "id": "abc123...",
      "metadata": {
        "repository": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
        "ref": "main",
        "path": ".",
        "provider": "aws",
        "providers": "aws",
        "tags": "aws,vpc,networking",
        "last_updated": "2025-10-22T22:00:00"
      },
      "document": "Description: Terraform module to create VPC resources...",
      "distance": 0.15
    }
  ],
  "count": 1,
  "query": "vpc module for aws with public and private subnets"
}
```

### MCP Service Usage

The MCP service includes a new `search_modules_vector` tool:

```python
# Using the MCP tool
search_modules_vector(
    query="vpc module for aws",
    provider="aws",
    limit=10,
    config_file="config.yaml"
)
```

AI agents can use this for semantic search:
- "Find modules for creating VPCs in AWS"
- "Search for Kubernetes cluster modules"
- "Show me modules that manage security groups"

## Metadata and Filtering

### Stored Metadata

Each embedded module includes the following metadata for filtering:

- `repository`: Git repository URL
- `ref`: Branch or tag name
- `path`: Path within the repository
- `provider`: Primary provider (normalized)
- `providers`: Comma-separated list of all providers
- `tags`: Extracted tags (from path, provider names)
- `last_updated`: ISO timestamp of last ingestion

### Filtering Examples

Filter by provider:
```bash
terraform-ingest search "networking" --provider aws
```

Filter by repository:
```bash
terraform-ingest search "vpc" --repository https://github.com/terraform-aws-modules/terraform-aws-vpc
```

## Incremental Updates

The system automatically handles incremental updates:

### Unique IDs

Each module is assigned a unique ID based on:
```
SHA256(repository:ref:path)
```

This ensures that re-processing a repository updates existing entries rather than creating duplicates.

### Update Behavior

When you re-run ingestion:
1. Existing modules are updated with new embeddings
2. New modules are added
3. The `last_updated` timestamp is refreshed
4. Old versions are preserved if their ref/path combination is unique

Example:
```bash
# Initial ingestion
terraform-ingest ingest config.yaml

# Update after repository changes
terraform-ingest ingest config.yaml  # Updates existing entries
```

## What Gets Embedded

The embedding text is constructed from:

1. **Module Description**: From README or HCL comments
2. **README Content**: First 2000 characters
3. **Variable Definitions**: Names, descriptions, and types
4. **Output Definitions**: Names and descriptions
5. **Resource Types**: Provider names and module sources

Example embedded text:
```
Description: Terraform module to create VPC resources on AWS

README: # AWS VPC Terraform module
This module creates a VPC with public and private subnets...

Variables: vpc_cidr: CIDR block for VPC (type: string), 
enable_nat_gateway: Enable NAT Gateway (type: bool)...

Outputs: vpc_id: ID of the VPC, 
private_subnet_ids: List of private subnet IDs...

Resources: aws provider, module: terraform-aws-modules/subnets/aws
```

## Installation

### Install Core Package

```bash
pip install terraform-ingest
```

### Install with Embedding Support

Choose based on your embedding strategy:

```bash
# ChromaDB default (recommended)
pip install terraform-ingest chromadb

# Local sentence-transformers
pip install terraform-ingest chromadb sentence-transformers

# OpenAI embeddings
pip install terraform-ingest chromadb openai

# Claude/Voyage embeddings
pip install terraform-ingest chromadb voyageai

# All embedding options
pip install terraform-ingest[embeddings]
```

## Performance Considerations

### Embedding Generation Time

- **ChromaDB Default**: ~1-2 seconds per module (local)
- **Sentence Transformers**: ~1-2 seconds per module (local)
- **OpenAI**: ~0.5-1 seconds per module (API call)
- **Voyage**: ~0.5-1 seconds per module (API call)

### Storage Requirements

- **Vector Database**: ~10-50 MB per 100 modules (depends on strategy)
- **JSON Summaries**: ~10-100 KB per module

### Search Performance

- **Vector Search**: Sub-second for collections < 10,000 modules
- **Hybrid Search**: Slightly slower but more accurate

## Troubleshooting

### ChromaDB Not Found

```bash
pip install chromadb
```

### Sentence Transformers Model Download

First run downloads models (~100 MB). Set cache directory:
```bash
export SENTENCE_TRANSFORMERS_HOME=/path/to/cache
```

### OpenAI API Errors

Check your API key:
```bash
export OPENAI_API_KEY=sk-...
```

Or set in config:
```yaml
embedding:
  openai_api_key: sk-...
```

### Memory Issues

For large repositories, limit concurrent processing or use a smaller embedding model:
```yaml
embedding:
  strategy: sentence-transformers
  sentence_transformers_model: all-MiniLM-L6-v2  # Smaller, faster
```

## Example Queries

### Natural Language Queries

Good queries for semantic search:

- "module for creating VPCs with public and private subnets"
- "kubernetes cluster on AWS with autoscaling"
- "security group for web applications"
- "database module with automated backups"
- "networking module with VPN support"

### Keyword + Semantic

Combine keywords with semantic meaning:

- "eks cluster production-ready" + filter provider=aws
- "vpc peering cross-region" + filter provider=aws
- "multi-region deployment" + filter provider=google

## Migration Guide

### From JSON-only to Embeddings

1. Update your config.yaml to add the `embedding` section
2. Run ingestion to populate the vector database:
   ```bash
   terraform-ingest ingest config.yaml --enable-embeddings
   ```
3. Start using vector search:
   ```bash
   terraform-ingest search "your query"
   ```

### Switching Embedding Strategies

1. Update the `strategy` in config.yaml
2. Delete the old ChromaDB directory
3. Re-run ingestion to rebuild embeddings

```bash
rm -rf ./chromadb
terraform-ingest ingest config.yaml
```

## Best Practices

1. **Start with ChromaDB Default**: Easiest to set up, no API keys needed
2. **Use OpenAI for Production**: Best quality if API costs are acceptable
3. **Enable All Content Types**: Include description, README, variables, outputs
4. **Set Reasonable Limits**: Start with 10 results, adjust based on needs
5. **Use Metadata Filters**: Narrow results by provider or repository
6. **Monitor Storage**: Clean up old embeddings periodically
7. **Version Your Config**: Keep embedding config in version control

## Future Enhancements

Potential improvements:

- [ ] Support for additional vector databases (Pinecone, Weaviate, Qdrant)
- [ ] Reranking for improved hybrid search
- [ ] Multi-modal embeddings (code + documentation)
- [ ] Automatic query expansion
- [ ] Relevance feedback learning
- [ ] Distributed embedding generation
