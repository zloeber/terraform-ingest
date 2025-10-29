# CI/CD Pipeline Overview

This document provides a quick overview of the GitHub Actions workflows that automate testing, building, and releasing terraform-ingest.

## Available Workflows

### 1. Test Workflow (test.yaml)
**Triggers:** Push to any branch, Pull Requests

Runs comprehensive testing on multiple platforms:
- **Platforms**: Ubuntu, macOS, Windows
- **Python Versions**: 3.13
- **Tasks**:
  - Unit tests with pytest
  - Code formatting checks (black, ruff)
  - Build verification

**Status Badge**: Check GitHub Actions for latest status

### 2. Semantic Release Workflow (semantic-release.yaml) ✨ **NEW**
**Triggers:** Push to `main` branch

Automatically generates semantic version tags and releases:
- Analyzes commit messages for conventional commits
- Calculates version bumps (major/minor/patch)
- Creates annotated git tags
- Publishes GitHub releases with auto-generated changelogs
- Triggers PyPI publishing

**Key Features**:
- ✅ No manual versioning required
- ✅ Automatic changelog generation
- ✅ Integrates with existing release workflow
- ✅ Prevents duplicate releases

**See**: [Semantic Release Documentation](./semantic_release_FEATURE.md)

### 3. Release Workflow (release.yaml)
**Triggers:** When version tags are created (e.g., v1.2.3)

Publishes packages to package registries:
- **PyPI**: Official Python package index
- **TestPyPI**: Test repository for validation
- **GitHub Releases**: Creates release notes

**Requirements**:
- Must have valid version tag in format `v*.*.*`
- PyPI credentials configured in GitHub Secrets

### 4. Docker Workflow (docker.yaml)
**Triggers:** Pushes to `main`, Pull Requests, manual trigger

Builds and pushes Docker images:
- **Registry**: GitHub Container Registry (ghcr.io)
- **Images**: 
  - `ghcr.io/zloeber/terraform-ingest:latest`
  - `ghcr.io/zloeber/terraform-ingest:v*.*.*`

### 5. Documentation Workflow (docs.yaml)
**Triggers:** Changes to `docs/` folder or `mkdocs.yml`

Builds and deploys MkDocs documentation:
- Generates static site from Markdown
- Deploys to GitHub Pages
- URL: `https://zloeber.github.io/terraform-ingest/`

## Workflow Architecture

```
┌─────────────────────────────────────────────┐
│  Developer commits with conventional commit │
│  message (feat:, fix:, feat!:, etc.)        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Create Pull Request to main branch         │
│  (Triggers: test.yaml)                      │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │ Run unit tests      │
        │ Check formatting    │
        │ Verify build        │
        └──────────┬──────────┘
                   │
                   ▼
        ┌──────────────────┐
        │ Approve & merge  │
        │ to main          │
        └──────────┬───────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ Semantic Release (main push) │
    │ (Triggers: semantic-release) │
    └──────────┬───────────────────┘
               │
    ┌──────────▼────────────┐
    │ Analyze commits       │
    │ Calculate version     │
    │ Create git tag        │
    │ Push tag to GitHub    │
    └──────────┬────────────┘
               │
    ┌──────────▼────────────┐
    │ Release (tag push)    │
    │ (Triggers: release)   │
    └──────────┬────────────┘
               │
    ┌──────────▼────────────────────┐
    │ Build & Publish               │
    │ - PyPI                         │
    │ - TestPyPI                     │
    │ - GitHub Releases              │
    └────────────────────────────────┘
```

## Quick Start for Contributors

### 1. Making Changes

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make your changes
# ... edit files ...

# Stage and commit with conventional commit format
git add .
git commit -m "feat: description of feature"
# or
git commit -m "fix: description of fix"
# or
git commit -m "BREAKING CHANGE: description"
```

### 2. Submit Pull Request

```bash
# Push to GitHub
git push origin feature/my-feature

# Create Pull Request on GitHub
# - Tests run automatically
# - Wait for green checkmarks
# - Request review
```

### 3. Merge to Main

```bash
# Once approved, merge to main
# GitHub Actions will:
# 1. Run tests one more time
# 2. Run semantic release workflow
# 3. Auto-tag with new version
# 4. Publish to PyPI
```

## Commit Message Guide

### Version Bump Examples

| Commit Message | Before | After | Bump |
|---|---|---|---|
| `fix: resolve parsing bug` | 1.2.3 | 1.2.4 | Patch |
| `feat: add new feature` | 1.2.3 | 1.3.0 | Minor |
| `feat!: redesign API` | 1.2.3 | 2.0.0 | Major |
| `BREAKING CHANGE: ...` | 1.2.3 | 2.0.0 | Major |

See [Commit Conventions](./commit_conventions.md) for detailed guide.

## Checking Workflow Status

### In GitHub UI
1. Go to repository → Actions tab
2. Click workflow name (Semantic Release, Release, etc.)
3. View recent runs and their logs

### In Terminal
```bash
# View recent tags
git tag -l --sort=-version:refname | head -10

# View tag details
git show v1.2.3

# View commit log with tags
git log --oneline --graph --decorate
```

## Troubleshooting

### Release didn't trigger after merge
- Check if commit messages follow conventional format
- Verify push was to `main` branch (not feature branch)
- Check GitHub Actions tab for workflow errors
- Manually trigger: Actions → Semantic Release → "Run workflow"

### Wrong version was calculated
- Check recent commits: `git log --oneline -10`
- Verify commit message format (e.g., `feat:` not `feature:`)
- Check workflow logs for details

### PyPI publish failed
- Check PyPI credentials in GitHub Secrets
- Verify package name is unique on PyPI
- Check version doesn't already exist

### Tests failed on PR
- Review test output in Actions tab
- Run tests locally: `python -m pytest`
- Check code formatting: `uv run black --check src/`

## Environment Setup for Local Testing

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest --maxfail=1 --disable-warnings -v tests

# Check formatting
uv run black --check src/terraform_ingest
uv run ruff format --check src/terraform_ingest

# Auto-fix formatting
uv run black src/terraform_ingest
uv run ruff format src/terraform_ingest
```

## Related Documentation

- [Semantic Release Pipeline](./semantic_release_FEATURE.md)
- [Commit Message Conventions](./commit_conventions.md)
- [Development Setup](./development.md)
- [Testing Guide](./testing.md)

## Support

For issues or questions about CI/CD:
1. Check GitHub Actions logs
2. Review this documentation
3. Open an issue on GitHub
4. Ask in discussions
