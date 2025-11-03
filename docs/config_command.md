# Configuration Management

The `config` command group provides a convenient way to manage your `config.yaml` file from the command line without manually editing the YAML file.

## Overview

The config command group includes four subcommands:

- **`set`** - Update single configuration values
- **`get`** - Read configuration values
- **`add-repo`** - Add new repository entries
- **`remove-repo`** - Remove repository entries

## Basic Usage

### Setting Configuration Values

Use the `set` subcommand to update any configuration value using a dot-separated path:

```bash
# Set a simple value
terraform-ingest config set --target output_dir --value ./my-output

# Set a nested value
terraform-ingest config set --target embedding.enabled --value true

# Set an integer value
terraform-ingest config set --target mcp.port --value 8080

# Set a boolean value
terraform-ingest config set --target mcp.auto_ingest --value false
```

#### Value Type Conversion

The `set` command automatically converts values to the appropriate type:

- `true`, `yes`, `on`, `1` → boolean `True`
- `false`, `no`, `off`, `0` → boolean `False`
- Numeric strings → integers or floats
- Everything else → strings

#### Creating Nested Paths

If a nested path doesn't exist, it will be created automatically:

```bash
# This will create the 'new.nested' structure if it doesn't exist
terraform-ingest config set --target new.nested.value --value test
```

### Reading Configuration Values

Use the `get` subcommand to read configuration values:

```bash
# Get a simple value
terraform-ingest config get --target output_dir

# Get a nested value
terraform-ingest config get --target embedding.enabled

# Get an object as YAML (default)
terraform-ingest config get --target embedding

# Get an object as JSON
terraform-ingest config get --target embedding --json
```

### Managing Repositories

#### Adding a Repository

Use `add-repo` to add a new repository to your configuration:

```bash
# Basic repository addition
terraform-ingest config add-repo --url https://github.com/hashicorp/terraform-aws-vpc

# With full options
terraform-ingest config add-repo \
  --url https://github.com/terraform-aws-modules/terraform-aws-vpc \
  --name aws-vpc-module \
  --branches main,develop \
  --max-tags 5 \
  --recursive \
  --path ./modules
```

Available options for `add-repo`:

- `--url` (required) - Repository URL
- `--name` - Repository name (optional)
- `--branches` - Comma-separated list of branches to include
- `--include-tags` / `--no-include-tags` - Include git tags (default: true)
- `--max-tags` - Maximum number of tags to include (default: 1)
- `--path` - Base path for module scanning (default: ".")
- `--recursive` / `--no-recursive` - Recursively search for modules (default: false)

#### Removing a Repository

Use `remove-repo` to remove a repository from your configuration:

```bash
# Remove by URL
terraform-ingest config remove-repo --url https://github.com/hashicorp/terraform-aws-vpc

# Remove by name
terraform-ingest config remove-repo --name aws-vpc-module
```

You must specify either `--url` or `--name` to identify the repository to remove.

## Advanced Examples

### Workflow: Disable Embeddings and Change Output Directory

```bash
# Disable vector embeddings
terraform-ingest config set --target embedding.enabled --value false

# Change output directory
terraform-ingest config set --target output_dir --value /data/terraform-modules

# Verify changes
terraform-ingest config get --target embedding.enabled
terraform-ingest config get --target output_dir
```

### Workflow: Add Multiple Repositories

```bash
# Add first repository with tags
terraform-ingest config add-repo \
  --url https://github.com/terraform-aws-modules/terraform-aws-vpc \
  --name aws-vpc \
  --max-tags 3 \
  --branches main

# Add second repository with recursive scanning
terraform-ingest config add-repo \
  --url https://github.com/terraform-aws-modules/terraform-aws-ec2-instance \
  --name aws-ec2 \
  --recursive \
  --path ./

# List all repositories
terraform-ingest config get --target repositories
```

### Workflow: Update MCP Configuration

```bash
# Change MCP port
terraform-ingest config set --target mcp.port --value 3001

# Enable auto-ingestion
terraform-ingest config set --target mcp.auto_ingest --value true

# Set refresh interval (in hours)
terraform-ingest config set --target mcp.refresh_interval_hours --value 12

# View full MCP configuration as JSON
terraform-ingest config get --target mcp --json
```

## Configuration File Location

By default, all commands operate on `config.yaml` in the current directory. You can specify a different configuration file using the `--config` or `-c` option:

```bash
# Use a custom config file
terraform-ingest config get --config /path/to/my-config.yaml --target output_dir

# Set value in custom config
terraform-ingest config set --config ./configs/prod.yaml --target output_dir --value /prod/output
```

## Error Handling

The config commands provide clear error messages for common issues:

- **Configuration file not found**: Ensure the file exists before using `set`, `add-repo`, or `remove-repo`
- **Configuration key not found**: Check the target path is correct when using `get`
- **Duplicate repository URL**: The `add-repo` command prevents adding repositories with duplicate URLs
- **Repository not found**: Verify the URL or name when using `remove-repo`
- **Invalid nested path**: Ensure parent paths are dictionaries when setting nested values

## Integration with Other Commands

The `config` commands work seamlessly with other terraform-ingest commands:

```bash
# Configure your settings
terraform-ingest config set --target output_dir --value ./output
terraform-ingest config add-repo --url https://github.com/example/terraform-module

# Run ingestion with your configured settings
terraform-ingest ingest config.yaml

# Start MCP server with configured settings
terraform-ingest mcp --config config.yaml
```

## Best Practices

1. **Use version control**: Keep your `config.yaml` under version control to track changes
2. **Test configuration changes**: After modifying configuration, verify with `get` before running ingestion
3. **Use descriptive repository names**: When adding repositories, use clear names for easier management
4. **Backup before bulk changes**: Keep a backup of your config when making multiple changes
5. **Use the `--json` flag**: When integrating with scripts, use `--json` for easier parsing

## See Also

- [CLI Documentation](cli.md) - Complete CLI reference
- [Quickstart Guide](quickstart.md) - Getting started with terraform-ingest
- [Import Command](import.md) - Importing repositories from GitHub/GitLab
