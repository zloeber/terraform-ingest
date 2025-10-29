# Module Indexing Feature

## Overview

The Module Indexing feature provides fast, local lookup of Terraform modules using document IDs from vector search results. It creates and maintains a `module_index.json` file that maps vector search IDs to their corresponding module summary JSON files and metadata.

## Problem Solved

When performing vector searches, you receive a document ID that uniquely identifies a module. Previously, you would need to either:
1. Use the vector database to retrieve the full module
2. Manually reconstruct the filename from repository/ref/path information
3. Search through all JSON files to find the matching module

The Module Indexing feature solves this by maintaining a simple, fast index that lets you:
- Look up any module by its ID instantly
- Query modules by provider, tags, or repository
- Rebuild the index from existing JSON files
- Get statistics about your indexed modules

## How It Works

### Index Structure

The `module_index.json` file maintains a mapping of document IDs to module metadata:

```json
{
  "index_version": "1.0",
  "generated_at": "2025-10-28T12:00:00Z",
  "total_modules": 150,
  "modules": {
    "a1b2c3d4e5f6...": {
      "id": "a1b2c3d4e5f6...",
      "repository": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
      "ref": "v5.0.0",
      "path": ".",
      "summary_file": "output/terraform-aws-vpc_v5.0.0_src.json",
      "provider": "aws",
      "providers": "aws,hashicorp",
      "tags": ["aws", "vpc", "network"],
      "last_indexed": "2025-10-28T12:00:00Z"
    }
  }
}
```

### Document ID Generation

Document IDs are generated using SHA256 hash of `{repository}:{ref}:{path}`:
- **Deterministic**: Same module always produces same ID
- **Consistent**: Matches the ID returned by vector search
- **Safe**: Valid for use as database/filesystem identifiers

## Usage

### Automatic Index Generation

When you run `ingest`, the index is automatically created and maintained:

```bash
terraform-ingest ingest config.yaml
# Automatically creates/updates module_index.json
```

### CLI Commands

#### Rebuild Index

Rebuild the index from all JSON files in the output directory:

```bash
terraform-ingest index rebuild --output-dir ./output
```

#### View Statistics

Get index statistics:

```bash
terraform-ingest index stats
```

Output:
```
📊 Module Index Statistics:
  Total Modules: 150
  Unique Providers: 5
  Providers: aws, google, azurerm, consul, vault
  Unique Tags: 23
  Index File: ./output/module_index.json
```

#### Look Up Module by ID

Retrieve module information using a vector search ID:

```bash
terraform-ingest index lookup a1b2c3d4e5f6...
```

Output:
```
📦 Module: a1b2c3d4e5f6...
  Repository: https://github.com/terraform-aws-modules/terraform-aws-vpc
  Ref: v5.0.0
  Path: .
  Provider: aws
  Summary File: output/terraform-aws-vpc_v5.0.0_src.json
  Tags: aws, vpc, network
```

Get as JSON:
```bash
terraform-ingest index lookup a1b2c3d4e5f6... --json
```

#### Search by Provider

Find all modules for a specific provider:

```bash
terraform-ingest index by_provider aws
```

Or get as JSON:
```bash
terraform-ingest index by_provider aws --json
```

#### Search by Tag

Find modules with a specific tag:

```bash
terraform-ingest index by_tag vpc
```

## Programmatic Usage

### Python API

```python
from terraform_ingest.indexer import ModuleIndexer

# Initialize the indexer
indexer = ModuleIndexer("./output")

# Add a module to the index
from terraform_ingest.models import TerraformModuleSummary
doc_id = indexer.add_module(module_summary)

# Look up a module
module = indexer.get_module(doc_id)

# Get the path to the summary file
summary_path = indexer.get_module_summary_path(doc_id)
with open(summary_path) as f:
    summary_data = json.load(f)

# Search by provider
aws_modules = indexer.search_by_provider("aws")

# Search by tag
vpc_modules = indexer.search_by_tag("vpc")

# Search by repository
my_modules = indexer.search_by_repository("my-org")

# Get statistics
stats = indexer.get_stats()
print(f"Total modules: {stats['total_modules']}")
print(f"Providers: {stats['providers']}")

# Rebuild from files
count = indexer.rebuild_from_files()
print(f"Indexed {count} modules")

# Save the index
indexer.save()
```

### Integration with Vector Search

After performing a vector search:

```python
from terraform_ingest.embeddings import VectorDBManager
from terraform_ingest.indexer import ModuleIndexer

vector_db = VectorDBManager(config)
indexer = ModuleIndexer("./output")

# Search for modules
results = vector_db.search("AWS VPC module for networking")

# For each result, look up the full module details
for result in results:
    doc_id = result["id"]
    index_entry = indexer.get_module(doc_id)
    summary_path = indexer.get_module_summary_path(doc_id)
    
    print(f"Found: {index_entry['repository']} ({index_entry['ref']})")
    print(f"Summary: {summary_path}")
```

### MCP Tool Integration

The module index is exposed via MCP (Model Context Protocol) tool for AI agents:

**`get_module_by_index_id(doc_id, output_dir="./output")`**

Retrieves full module information by its index document ID.

```python
# Use the MCP tool programmatically
from terraform_ingest.mcp_service import get_module_by_index_id

# Get full module details from vector search result
vector_result = vector_db.search("VPC module")[0]
doc_id = vector_result["id"]

module_summary = get_module_by_index_id(doc_id)
print(f"Module: {module_summary['repository']}")
print(f"Variables: {[v['name'] for v in module_summary['variables']]}")
print(f"Outputs: {[o['name'] for o in module_summary['outputs']]}")
```

**Example Workflow with Vector Search:**

1. AI agent performs vector search for VPC modules
2. Gets results with document IDs
3. Calls `get_module_by_index_id(doc_id)` to retrieve full module details
4. Analyzes variables, outputs, and README to generate Terraform code

```python
# Typical AI agent workflow
search_results = search_modules_vector("VPC with subnets and NAT gateway")

for result in search_results:
    doc_id = result["id"]
    module = get_module_by_index_id(doc_id)
    
    # Now the agent has full module information
    print(f"Repository: {module['repository']}")
    print(f"Version: {module['ref']}")
    print(f"Required Inputs: {[v['name'] for v in module['variables'] if v['required']]}")
    print(f"Available Outputs: {[o['name'] for o in module['outputs']]}")
    
    # Use this to generate Terraform code...
```

## Module Index Structure

### ModuleIndexer Class

Main class for managing the module index.

**Methods:**

- `add_module(summary: TerraformModuleSummary) -> str`: Add/update module, returns ID
- `get_module(doc_id: str) -> Optional[Dict]`: Get module entry by ID
- `remove_module(doc_id: str) -> bool`: Remove module from index
- `get_module_summary_path(doc_id: str) -> Optional[Path]`: Get path to summary JSON
- `search_by_provider(provider: str) -> List[Dict]`: Find modules by provider
- `search_by_tag(tag: str) -> List[Dict]`: Find modules by tag
- `search_by_repository(repository: str) -> List[Dict]`: Find modules by repository
- `list_all() -> List[Dict]`: Get all module entries
- `rebuild_from_files() -> int`: Rebuild from JSON files
- `clear() -> None`: Clear all entries
- `save() -> None`: Save index to file
- `get_stats() -> Dict`: Get index statistics

## Integration with TerraformIngest

The indexer is automatically initialized and used by `TerraformIngest`:

```python
from terraform_ingest.ingest import TerraformIngest

ingester = TerraformIngest.from_yaml("config.yaml")
summaries = ingester.ingest()  # Automatically creates index

# Access the indexer
module = ingester.indexer.get_module(doc_id)
stats = ingester.indexer.get_stats()
```

## Advanced Usage

### Custom Index Location

Specify a custom index filename:

```python
indexer = ModuleIndexer(
    output_dir="./output",
    index_filename="my_custom_index.json"
)
```

### Batch Operations

Rebuild and get statistics:

```python
# Rebuild from files
count = indexer.rebuild_from_files()

# Get comprehensive stats
stats = indexer.get_stats()

# Export all entries
all_entries = indexer.list_all()
```

### Filtering and Pagination

Search with multiple filters:

```python
# Get AWS modules
aws_modules = indexer.search_by_provider("aws")

# Get network-related AWS modules
network_modules = [
    m for m in aws_modules 
    if "network" in m.get("tags", [])
]

# Get from specific repository
vpc_modules = [
    m for m in aws_modules
    if "vpc" in m["repository"].lower()
]
```

## Performance Characteristics

- **Index Creation**: O(n) where n is number of modules
- **Lookup by ID**: O(1) dictionary lookup
- **Search by Provider**: O(n) linear scan with string matching
- **Memory Usage**: ~1-2KB per module entry
- **File Size**: ~100-200KB for 1000 modules

For 100+ modules, consider:
- Loading index once and reusing in memory
- Implementing caching for frequent searches
- Rebuilding index periodically as new modules are added

## Troubleshooting

### Index File Not Found

Ensure ingestion completed successfully:
```bash
terraform-ingest ingest config.yaml
ls -la ./output/module_index.json
```

### Module Not Found in Index

Rebuild the index:
```bash
terraform-ingest index rebuild
```

### Stale Index

The index is updated automatically during ingest. To force a rebuild:
```bash
rm ./output/module_index.json
terraform-ingest index rebuild
```

### Vector Search ID Not in Index

Ensure:
1. Vector search was performed after modules were indexed
2. You're using the correct output directory
3. The module still exists in the JSON files

## Examples

### Example 1: Find Module from Vector Search

```python
# Perform vector search
results = vector_db.search("VPC with subnets", n_results=5)

# Look up first result
best_match = results[0]
module_info = indexer.get_module(best_match["id"])

print(f"Best match: {module_info['repository']}")
print(f"Version: {module_info['ref']}")

# Get the full summary
summary_path = indexer.get_module_summary_path(best_match["id"])
with open(summary_path) as f:
    summary = json.load(f)
    print(f"Inputs: {[v['name'] for v in summary['variables']]}")
```

### Example 2: Organize Modules by Provider

```python
indexer = ModuleIndexer("./output")

# Group all modules by provider
by_provider = {}
for module in indexer.list_all():
    provider = module["provider"]
    if provider not in by_provider:
        by_provider[provider] = []
    by_provider[provider].append(module)

# Print summary
for provider, modules in sorted(by_provider.items()):
    print(f"{provider}: {len(modules)} modules")
    for m in modules:
        print(f"  • {m['repository']} ({m['ref']})")
```

### Example 3: Export Index for Analysis

```python
import json

indexer = ModuleIndexer("./output")

# Export as CSV for spreadsheet analysis
modules = indexer.list_all()
with open("module_export.csv", "w") as f:
    f.write("Repository,Ref,Path,Provider,Tags\n")
    for m in modules:
        f.write(f"{m['repository']},{m['ref']},{m['path']},{m['provider']},{' '.join(m['tags'])}\n")
```

## See Also

- [Vector Database Guide](./vectordb.md) - Learn about vector embeddings
- [MCP Service](./mcp.md) - Expose modules to AI agents
- [Architecture](./docker_arch.md) - System architecture overview
