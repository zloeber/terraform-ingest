---
name: terraform-ingest-setup
description: >-
  Installs terraform-ingest and prepares a fresh environment: dependencies,
  config initialization, and git credential checks. Use when the user wants to
  install terraform-ingest, get started, set up for the first time, or prepare
  before configuration and ingestion.
disable-model-invocation: true
---

# Terraform-Ingest Setup

Walk the user through installation and environment preparation.

## Progress checklist

```
Task Progress:
- [ ] Step 1: Verify prerequisites
- [ ] Step 2: Install terraform-ingest
- [ ] Step 3: Initialize config.yaml
- [ ] Step 4: Verify git access (if using private or SSH repos)
- [ ] Step 5: Hand off to terraform-ingest-configure
```

## Step 1: Verify prerequisites

Confirm before installing:

- **git** on PATH (`git --version`)
- **Python 3.11+** (`python --version` or `python3 --version`)
- **uv** for development from source (`uv --version`), or pip for package install

## Step 2: Install

**From source (this repo):**

```bash
cd /path/to/terraform-ingest
uv sync
uv run terraform-ingest --version
```

**From PyPI (end users):**

```bash
pip install terraform-ingest
terraform-ingest --version
```

**Gate:** Do not proceed until `terraform-ingest --version` prints a version string.

## Step 3: Initialize configuration

```bash
terraform-ingest init config.yaml
```

This creates `config.yaml` with empty `repositories`, default `output_dir` (`./output`), `clone_dir` (`./repos`), and MCP/embedding sections.

If `config.yaml` already exists, skip init and proceed to configure.

## Step 4: Git credentials (when needed)

Skip for public HTTPS repos. Check when the user will ingest private repos or SSH URLs:

```bash
# SSH
ssh -T git@github.com

# HTTPS — ensure credential helper or token is configured
git config --global credential.helper
```

For GitHub org import later, set `GITHUB_TOKEN` in the environment or `.env`.

## Step 5: Optional embedding dependencies

If the user wants semantic module search, install embedding deps before configure:

```bash
terraform-ingest install-deps --strategy chromadb-default
```

Or defer until configure when `embedding.enabled` is set.

## Step 6: Deploy agent skills (optional)

Install workflow skills for your AI agent:

```bash
terraform-ingest skills install --scope project --target cursor
terraform-ingest skills list
```

## Hand off

After setup completes, invoke **terraform-ingest-configure** to add repositories and tune settings.

## Common issues

| Error | Fix |
|-------|-----|
| `command not found: terraform-ingest` | Run `uv sync` and use `uv run terraform-ingest`, or `pip install -e .` |
| `config.yaml already exists` on init | Use existing file; run configure instead |
| SSH `Permission denied` | Add SSH key (`ssh-add`) or switch repo URL to HTTPS |

## See also

- [terraform-ingest hub](../terraform-ingest/SKILL.md)
- [Quickstart](../../docs/quickstart.md)
