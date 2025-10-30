# FastMCP Service Configuration Guide

This guide explains how to configure and use the terraform-ingest FastMCP service with AI agents.

## Overview

The terraform-ingest MCP service exposes ingested Terraform module data to AI agents through the Model Context Protocol (MCP) by exposing several tools including:

1. **list_repositories**: Discover available Terraform repositories
2. **search_modules**: Find specific modules by criteria
3. **search_modules_vector**: Search for appropriate modules using vector similarity

## Prerequisites

1. Install terraform-ingest with fastMCP support:
   ```bash
   pip install terraform-ingest
   ```

2. Ingest Terraform repositories to create JSON summaries:
   ```bash
   terraform-ingest ingest config.yaml
   ```

   This creates JSON files in the output directory (default: `./output`)

## Starting the MCP Server

### Method 1: Command Line

```bash
terraform-ingest-mcp
```

The server will start and listen for MCP connections.

### Method 2: Programmatic

```python
from terraform_ingest.mcp_service import main

main()
```

## Available Tools

### list_repositories

Lists all accessible Git repositories containing Terraform modules.

**Parameters:**
- `filter` (string, optional): Keyword to filter by repo name or description
- `limit` (integer, optional, default: 50): Maximum number of repositories to return
- `output_dir` (string, optional, default: "./output"): Path to JSON summaries

**Returns:**
- List of repository metadata including:
  - `url`: Repository URL
  - `name`: Repository name
  - `description`: Module description
  - `refs`: List of branches/tags analyzed
  - `module_count`: Number of module versions
  - `providers`: List of Terraform providers used

**Example queries for AI agents:**
- "List all Terraform repositories"
- "Show me repositories related to AWS"
- "What Terraform modules are available?"

### search_modules

Searches for Terraform modules across repositories by criteria.

**Parameters:**
- `query` (string, required): Search term (e.g., "aws_vpc", "network", "security group")
- `repo_urls` (array of strings, optional): List of Git repo URLs to search; defaults to all
- `provider` (string, optional): Filter by target provider (e.g., "hashicorp/aws", "aws")
- `output_dir` (string, optional, default: "./output"): Path to JSON summaries

**Returns:**
- List of matching module summaries with full details including:
  - `repository`: Git repository URL
  - `ref`: Branch or tag name
  - `path`: Path within repository
  - `description`: Module description
  - `variables`: Input variables
  - `outputs`: Output values
  - `providers`: Required Terraform providers
  - `modules`: Sub-modules used
  - `readme_content`: README file content

**Example queries for AI agents:**
- "Find modules for creating VPCs"
- "Search for security group modules that use AWS"
- "Show me Azure network modules"
- "What modules are available in the terraform-aws-modules repository?"

## Configuration

### Output Directory

The MCP service reads from the directory containing ingested JSON summaries. Configure this in several ways:

1. **Environment Variable** (recommended for production):
   ```bash
   export TERRAFORM_INGEST_OUTPUT_DIR=/path/to/output
   terraform-ingest-mcp
   ```

2. **Per-tool Parameter**:
   When calling tools, pass the `output_dir` parameter:
   ```python
   list_repositories(output_dir="/custom/path")
   search_modules(query="vpc", output_dir="/custom/path")
   ```

3. **Default**: Uses `./output` relative to the current directory

### MCP Client Configuration

To use this MCP server with an MCP client (like Claude Desktop), add it to your MCP settings:

```json
{
  "mcpServers": {
    "terraform-ingest": {
      "command": "terraform-ingest-mcp",
      "env": {
        "TERRAFORM_INGEST_OUTPUT_DIR": "/path/to/output"
      }
    }
  }
}
```

## Usage Examples

### Example 1: Discover Available Modules

**User**: "What Terraform modules are available for AWS?"

**AI Agent**: Uses `list_repositories(filter="aws")` to find AWS-related repositories, then can use `search_modules(provider="aws")` to get detailed module information.

### Example 2: Find Specific Functionality

**User**: "I need to create a VPC in AWS. What modules can help?"

**AI Agent**: Uses `search_modules(query="vpc", provider="aws")` to find relevant VPC modules with AWS provider.

### Example 3: Explore Module Details

**User**: "Show me the inputs for the terraform-aws-vpc module"

**AI Agent**: 
1. Uses `search_modules(query="terraform-aws-vpc")` to find the module
2. Returns the `variables` array from the module summary
3. Presents the input variables with their descriptions, types, and defaults

### Example 4: Compare Versions

**User**: "What changed between versions of the VPC module?"

**AI Agent**:
1. Uses `search_modules(repo_urls=["https://github.com/terraform-aws-modules/terraform-aws-vpc"])` 
2. Gets all versions (different `ref` values)
3. Compares the `variables`, `outputs`, and other metadata between versions

## Best Practices

1. **Regular Ingestion**: Keep module data fresh by regularly re-ingesting repositories:
   ```bash
   # Add to cron or CI/CD pipeline
   terraform-ingest ingest config.yaml --cleanup
   ```

2. **Organize Output**: Use descriptive directory names for different environments or teams:
   ```bash
   terraform-ingest ingest prod-config.yaml -o ./output/production
   terraform-ingest ingest dev-config.yaml -o ./output/development
   ```

3. **Filter Effectively**: Use the `filter` parameter in `list_repositories` to narrow down results before detailed searches.

4. **Combine Filters**: Use multiple parameters in `search_modules` for precise results:
   ```python
   search_modules(
       query="network",
       provider="aws",
       repo_urls=["https://github.com/terraform-aws-modules/..."]
   )
   ```

## Troubleshooting

### No Results Returned

**Issue**: Tools return empty results

**Solutions**:
- Verify the output directory path is correct
- Ensure JSON summaries exist in the directory
- Check that ingestion completed successfully
- Verify file permissions on the output directory

### Slow Performance

**Issue**: Searches take a long time

**Solutions**:
- Limit the number of repositories ingested
- Use specific `repo_urls` filters instead of searching all repositories
- Reduce the `limit` parameter for `list_repositories`
- Consider organizing modules into multiple output directories by category

### Stale Data

**Issue**: Module information is outdated

**Solutions**:
- Re-run ingestion to update module summaries
- Set up automated ingestion pipeline
- Use `--cleanup` flag to remove old cloned repositories

## Integration with RAG Systems

The MCP service complements RAG (Retrieval-Augmented Generation) systems by:

1. **Structured Queries**: Provides precise, structured data instead of semantic search
2. **Metadata Access**: Exposes detailed metadata not typically in embeddings
3. **Real-time Filtering**: Allows dynamic filtering by provider, repository, etc.
4. **Hybrid Approach**: Can work alongside vector search for comprehensive results

### Recommended Workflow

1. Use MCP tools for precise queries and metadata retrieval
2. Use RAG/vector search for semantic understanding and code examples
3. Combine both for comprehensive Terraform assistance

For more information, see the main README.md file.
