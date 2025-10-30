# Import Command

The `import` command allows you to automatically discover and import Terraform repositories from external sources into your configuration file.

## Overview

Instead of manually maintaining a list of repositories in your `config.yaml`, you can use the import command to:

- Fetch all repositories from a GitHub organization
- Filter repositories by specific criteria (e.g., Terraform-only)
- Merge new repositories with existing configuration or replace it entirely
- Support for future expansion to other providers (GitLab, Bitbucket, etc.)

## Usage

### Basic Import from GitHub

Import all public repositories from a GitHub organization:

```bash
terraform-ingest import github --org hashicorp
```

This will:
1. Fetch all public repositories from the `hashicorp` organization
2. Filter out archived repositories
3. Merge the repositories with your existing `config.yaml` (if it exists)
4. Create default configuration for each repository

### Import with Authentication

For private repositories or to avoid rate limits, provide a GitHub token:

```bash
# Using command line option
terraform-ingest import github --org myorg --token ghp_xxxxxxxxxxxxx

# Using environment variable
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
terraform-ingest import github --org myorg
```

### Filter Terraform Repositories Only

Only import repositories that contain Terraform files:

```bash
terraform-ingest import github --org myorg --terraform-only
```

### Replace Existing Repositories

Replace all existing repositories in your configuration:

```bash
terraform-ingest import github --org myorg --replace
```

### Custom Configuration File

Specify a different configuration file:

```bash
terraform-ingest import github --org myorg --config my-config.yaml
```

### Include Private Repositories

Import both public and private repositories (requires authentication):

```bash
terraform-ingest import github --org myorg --token ghp_xxx --include-private
```

### Custom Base Path

Specify a custom base path for module scanning:

```bash
terraform-ingest import github --org myorg --base-path ./modules
```

## Merge vs Replace

### Merge Mode (Default)

By default, the import command **merges** new repositories with existing ones:

```bash
terraform-ingest import github --org myorg
```

**Behavior:**
- Existing repositories in `config.yaml` are preserved
- New repositories are added
- Duplicate repositories (by URL) are not added again
- Other configuration settings (output_dir, clone_dir, etc.) remain unchanged

**Example:**

Before:
```yaml
repositories:
  - url: https://github.com/existing/repo1.git
    name: repo1
```

After import:
```yaml
repositories:
  - url: https://github.com/existing/repo1.git
    name: repo1
  - url: https://github.com/myorg/repo2.git
    name: repo2
  - url: https://github.com/myorg/repo3.git
    name: repo3
```

### Replace Mode

Using the `--replace` flag completely replaces your repository list:

```bash
terraform-ingest import github --org myorg --replace
```

**Behavior:**
- All existing repositories are removed
- Only newly imported repositories remain
- Other configuration settings are preserved

**Example:**

Before:
```yaml
repositories:
  - url: https://github.com/existing/repo1.git
    name: repo1
```

After import with `--replace`:
```yaml
repositories:
  - url: https://github.com/myorg/repo2.git
    name: repo2
  - url: https://github.com/myorg/repo3.git
    name: repo3
```

## Default Repository Configuration

Imported repositories receive the following default configuration:

```yaml
repositories:
  - url: https://github.com/org/repo-name.git
    name: repo-name
    branches: []                    # No specific branches (uses default)
    include_tags: true             # Include git tags
    max_tags: 1                    # Process latest tag only
    path: ./src                    # Base path for scanning
    recursive: false               # Don't scan subdirectories
    exclude_paths: []              # No exclusions
```

You can manually edit these settings after import to customize behavior for specific repositories.

## Complete Options

```bash
terraform-ingest import github [OPTIONS]

Options:
  --org TEXT         GitHub organization name [required]
  --token TEXT       GitHub personal access token (or set GITHUB_TOKEN env var)
  -c, --config PATH  Configuration file to update (default: config.yaml)
  --include-private  Include private repositories (requires authentication)
  --terraform-only   Only include repositories that contain Terraform files
  --base-path TEXT   Base path for module scanning (default: ./src)
  --replace          Replace existing repositories instead of merging
  --help             Show this message and exit
```

## Examples

### Example 1: Import HashiCorp Modules

Import all public Terraform modules from HashiCorp:

```bash
terraform-ingest import github --org hashicorp --terraform-only
```

### Example 2: Import Organization Repos

Import all repositories from your organization with authentication:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
terraform-ingest import github --org my-company --include-private
```

### Example 3: Start Fresh Configuration

Create a new configuration from scratch:

```bash
terraform-ingest import github --org terraform-aws-modules \
  --terraform-only \
  --config new-config.yaml \
  --base-path .
```

### Example 4: Update Existing Configuration

Add new repositories to existing configuration:

```bash
# First import from one org
terraform-ingest import github --org hashicorp --terraform-only

# Add more from another org (merge mode)
terraform-ingest import github --org terraform-aws-modules --terraform-only
```

## Future Providers

The import command is designed to be extensible. Future versions may include:

- `terraform-ingest import gitlab --group mygroup`
- `terraform-ingest import bitbucket --workspace myworkspace`
- `terraform-ingest import azure-devops --organization myorg --project myproject`

Each provider will follow the same pattern of merge/replace logic and configuration management.

## Troubleshooting

### Rate Limiting

GitHub API has rate limits for unauthenticated requests (60 requests/hour). Use a token to increase limits:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
terraform-ingest import github --org myorg
```

### Terraform Detection

The `--terraform-only` flag uses GitHub's code search API to detect `.tf` files. This may:
- Be slower for large organizations
- Be unavailable without authentication
- Have its own rate limits

If detection fails, repositories are included by default to avoid false negatives.

### Private Repositories

Private repositories require authentication:

```bash
terraform-ingest import github --org myorg --token ghp_xxx --include-private
```

### No Repositories Found

If no repositories are found:
1. Verify the organization name is correct
2. Check if authentication is required
3. Try without `--terraform-only` to see all repositories
4. Verify your token has appropriate permissions

## See Also

- [CLI Reference](cli.md) - Complete CLI documentation
- [Configuration](quickstart.md) - Configuration file format
- [Getting Started](index.md) - General usage guide
