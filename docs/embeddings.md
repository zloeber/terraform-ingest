# Quick Start: Vector Database Embeddings

This guide helps you get started with vector database embeddings in terraform-ingest in under 5 minutes.

## 1. Install Dependencies

```bash
# Install ChromaDB for vector database
pip install chromadb

# Optional: Install sentence-transformers for better local embeddings
pip install sentence-transformers
```

## 2. Enable Embeddings in Config

Edit your `config.yaml` and add:

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

# Add this section
embedding:
  enabled: true
  strategy: chromadb-default  # Easiest to start with
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

## 3. Ingest Modules

```bash
terraform-ingest ingest config.yaml
```

You should see output like:
```
Processing repository: https://github.com/terraform-aws-modules/terraform-aws-vpc
Saved summary to ./output/terraform-aws-vpc_main.json
Upserted to vector database with ID: abc123...
```

## 4. Search for Modules

```bash
# Basic search
terraform-ingest search "vpc module for aws"

# Filter by provider
terraform-ingest search "kubernetes cluster" --provider aws

# Limit results
terraform-ingest search "security group" --limit 3
```

## Example Output

```
Searching for: vpc module for aws

Found 1 result(s):

1. https://github.com/terraform-aws-modules/terraform-aws-vpc
   Ref: main
   Path: .
   Provider: aws
   Relevance: 0.850
```

## Advanced: Use Different Embedding Strategies

### OpenAI (Best Quality)

```yaml
embedding:
  enabled: true
  strategy: openai
  openai_api_key: sk-...  # Or set OPENAI_API_KEY env var
  openai_model: text-embedding-3-small
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

```bash
pip install openai
```

### Local Sentence Transformers (Free, No API)

```yaml
embedding:
  enabled: true
  strategy: sentence-transformers
  sentence_transformers_model: all-MiniLM-L6-v2
  chromadb_path: ./chromadb
  collection_name: terraform_modules
```

```bash
pip install sentence-transformers
```

## Using from Python

```python
from terraform_ingest import TerraformIngest

# Load and ingest
ingester = TerraformIngest.from_yaml('config.yaml')
summaries = ingester.ingest()

# Search
results = ingester.search_vector_db(
    "vpc module with private subnets",
    filters={"provider": "aws"},
    n_results=5
)

for result in results:
    print(f"Found: {result['metadata']['repository']}")
```

## Using the API

Start the server:
```bash
terraform-ingest serve
```

Search via HTTP:
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

## Troubleshooting

### "chromadb not found"
```bash
pip install chromadb
```

### "Vector database is not enabled"
Make sure `embedding.enabled: true` is in your config.yaml

### Model download takes a while
First run downloads models (~100MB). This is normal.

### Search returns no results
1. Make sure you've run ingestion first
2. Check that modules were upserted: look for "Upserted to vector database" messages
3. Try a broader query

## Common Use Cases

### Find modules for a specific cloud provider
```bash
terraform-ingest search "storage" --provider gcp
```

### Find modules in a specific repository
```bash
terraform-ingest search "networking" --repository https://github.com/terraform-aws-modules/terraform-aws-vpc
```

### Natural language queries
```bash
terraform-ingest search "module for creating kubernetes clusters with autoscaling"
terraform-ingest search "database with automated backups and replication"
terraform-ingest search "vpc with vpn and direct connect support"
```

## Performance Tips

1. **Start with ChromaDB default** - easiest to set up
2. **Use filters** - narrow results with `--provider` or `--repository`
3. **Adjust result limit** - use `--limit 3` for faster results
4. **Use local models** - sentence-transformers avoids API costs
5. **Enable only needed content** - set `include_readme: false` if not needed
