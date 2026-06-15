---
name: terraform-ingest-configure
description: >-
  Builds and validates terraform-ingest config.yaml: repositories, output paths,
  embeddings, and MCP settings. Use when the user wants to configure
  terraform-ingest, add repositories, edit config.yaml, or enable vector search.
disable-model-invocation: true
---

# Terraform-Ingest Configure

Guide the user through `config.yaml` using CLI commands. Ask **one question at a time**.

## Progress checklist

```
Task Progress:
- [ ] Step 1: Confirm config file path
- [ ] Step 2: Set output and clone directories
- [ ] Step 3: Add repositories
- [ ] Step 4: Configure embeddings (optional)
- [ ] Step 5: Configure MCP behavior (optional)
- [ ] Step 6: Validate configuration
- [ ] Step 7: Hand off to terraform-ingest-ingest
```

## Step 1: Config file path

Default: `config.yaml` in the project root. Override with `--config` / `-c` on all commands.

```bash
terraform-ingest config get --target output_dir
```

## Step 2: Directories

```bash
terraform-ingest config set --target output_dir --value ./output
terraform-ingest config set --target clone_dir --value ./repos
```

Use absolute paths in production or container deployments.

## Step 3: Add repositories

Ask the user for each repo:

1. Git URL (HTTPS or SSH)
2. Branches to track (e.g. `main`) — empty list ingests default branch
3. Include tags? How many? (`max_tags`)
4. Module path (`path`, default `.`)
5. Recursive scan? (`--recursive` for monorepos)

**Single repo:**

```bash
terraform-ingest config add-repo \
  --url https://github.com/terraform-aws-modules/terraform-aws-vpc \
  --name aws-vpc \
  --branches main \
  --max-tags 3
```

**Monorepo with submodules:**

```bash
terraform-ingest config add-repo \
  --url git@github.com/myorg/terraform-modules.git \
  --name my-modules \
  --branches main \
  --recursive \
  --path modules
```

**Bulk import from GitHub org** (many repos):

```bash
export GITHUB_TOKEN=ghp_xxx   # if needed
terraform-ingest import github --org myorg --terraform-only
```

**Verify:**

```bash
terraform-ingest config get --target repositories
```

## Step 4: Embeddings (optional)

Enable for `search_modules_vector` in MCP:

```bash
terraform-ingest config set --target embedding.enabled --value true
terraform-ingest config set --target embedding.strategy --value chromadb-default
terraform-ingest install-deps --strategy chromadb-default
```

Strategies: `chromadb-default` (local, no API key), `sentence-transformers`, `openai`, `claude`.

Avoid `chromadb_path: ./chromadb` at the project root — it shadows the `chromadb` Python package. Prefer `./data/chromadb` or an absolute path outside the repo.

For OpenAI:

```bash
terraform-ingest config set --target embedding.strategy --value openai
# Set OPENAI_API_KEY in environment
```

## Step 5: MCP behavior (optional)

Tune for agents that will connect via MCP later:

```bash
terraform-ingest config set --target mcp.ingest_on_startup --value true
terraform-ingest config set --target mcp.auto_ingest --value true
terraform-ingest config set --target mcp.refresh_interval_hours --value 24
```

Customize agent behavior via `mcp.instructions` in config — see [MCP docs](../../docs/mcp.md). Do not paste full instructions into chat; edit the YAML field or use `config set` for nested paths.

## Step 6: Validate

Run before ingestion:

```bash
terraform-ingest skills validate-config config.yaml
```

Fix any reported errors. An empty `repositories` list warns but does not fail — confirm with the user before ingesting.

## Step 7: Hand off

Invoke **terraform-ingest-ingest** to run the first ingestion.

## Wizard questions (ask one at a time)

1. Which cloud provider or module sources? (URLs or GitHub org)
2. Public or private repositories?
3. Track branches, tags, or both?
4. Need semantic/vector search for module discovery?
5. Will an AI agent connect via MCP after ingest?

## See also

- [reference.md](reference.md) — full config schema
- [Config CLI docs](../../docs/config_command.md)
- [Import command](../../docs/import.md)
