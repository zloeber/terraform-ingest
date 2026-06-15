---
name: terraform-ingest-ingest
description: >-
  Runs and monitors terraform-ingest repository ingestion from YAML config,
  verifies JSON output, and interprets progress status. Use when the user wants
  to ingest modules, run first ingestion, refresh the module index, or check
  ingestion progress.
disable-model-invocation: true
---

# Terraform-Ingest Ingestion

Run ingestion and confirm modules were indexed successfully.

## Progress checklist

```
Task Progress:
- [ ] Step 1: Validate config
- [ ] Step 2: Choose ingest mode
- [ ] Step 3: Start ingestion
- [ ] Step 4: Monitor progress (if background)
- [ ] Step 5: Verify output
- [ ] Step 6: Summarize results for user
```

## Step 1: Validate config

```bash
terraform-ingest skills validate-config config.yaml
```

Do not ingest if validation returns errors.

## Step 2: Choose ingest mode

| Mode | When to use |
|------|-------------|
| **Foreground** (default) | First ingestion; user needs clear error output |
| **Background** | MCP server or agent should stay responsive; poll status |

**Flags:**

| Flag | Effect |
|------|--------|
| `--cleanup` | Remove cloned repos after ingest |
| `--skip-existing` | Skip git fetch if clone already exists |
| `--no-cache` | Delete output + clone dirs before ingest |
| `--enable-embeddings` | Override config to enable embeddings |
| `--no-embeddings` | Override config to disable embeddings |

## Step 3: Start ingestion

### CLI — foreground (recommended for first run)

```bash
terraform-ingest ingest config.yaml
```

With options:

```bash
terraform-ingest ingest config.yaml --cleanup --skip-existing
```

### CLI — background

```bash
terraform-ingest ingestion run --background -c config.yaml
```

### MCP (when connected)

```
run_ingestion(config_file="config.yaml", background=true)
```

For synchronous MCP ingest: `background=false`.

## Step 4: Monitor progress

### CLI

```bash
terraform-ingest ingestion status
terraform-ingest ingestion status --format text
```

### MCP

```
get_ingestion_status()
```

Or read resource `ingestion://status`.

### Status interpretation

| `status` | Agent action |
|----------|--------------|
| `idle` | No job running; offer to start ingest |
| `starting` / `running` | Report `phase`, `current`/`total`, `message`; poll every 10–30s |
| `complete` | Report `modules_processed`; proceed to verification |
| `failed` | Show `message` and recent errors; check git auth and repo URLs |

Example progress fields: `phase` (`cloning`, `parsing`, `embedding`), `modules_processed`, `recent_messages`.

## Step 5: Verify output

```bash
ls -la ./output/
```

Expect JSON files named `{repo}_{ref}_{path}.json`. Spot-check one:

```bash
terraform-ingest module \
  --repository https://github.com/terraform-aws-modules/terraform-aws-vpc \
  --ref main \
  --path .
```

Or list modules:

```bash
terraform-ingest search "vpc" --limit 3
```

If embeddings enabled, confirm ChromaDB path exists (default `./chromadb`).

## Step 6: Summarize for user

Report:

- Number of repositories ingested
- Module count (from status or `ls output | wc -l`)
- Output directory path
- Whether embeddings were built
- Next step: connect MCP (`docs/mcp.md`) or search for modules

## Re-ingestion / refresh

```bash
# Full refresh (wipe cache)
terraform-ingest ingest config.yaml --no-cache

# Scheduled via MCP config
terraform-ingest config set --target mcp.refresh_interval_hours --value 24
```

## Common issues

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Git clone failed | Auth or bad URL | Verify SSH/HTTPS credentials |
| Empty `./output` | No repos in config | Run configure skill |
| Embeddings failed | Missing deps | `terraform-ingest install-deps` |
| MCP tools return empty | Wrong `TERRAFORM_INGEST_OUTPUT_DIR` | Align env var with `output_dir` |

## See also

- [terraform-ingest hub](../terraform-ingest/SKILL.md)
- [MCP ingestion progress](../../docs/mcp_ingestion_progress.md)
- [Quickstart](../../docs/quickstart.md)
