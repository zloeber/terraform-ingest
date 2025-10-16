# TerraformIngest Recursive Implementation Summary

## Overview
Successfully updated TerraformIngest to respect the `recursive` setting and process each subdirectory in the target path for Terraform modules.

## Changes Made

### 1. Updated Models (`src/terraform_ingest/models.py`)
- Added `recursive: bool = True` field to `RepositoryConfig` class
- This field controls whether to search subdirectories for Terraform modules

### 2. Enhanced Repository Manager (`src/terraform_ingest/repository.py`)
- Modified `_process_ref()` method to return a list of summaries instead of a single summary
- Added `_find_module_paths()` helper method to recursively discover Terraform modules
- Updated `process_repository()` method to handle multiple summaries per reference
- Implemented recursive directory traversal when `recursive=True`

### 3. Updated Parser (`src/terraform_ingest/parser.py`)
- Modified `parse_module()` method to accept optional `relative_path` parameter
- Enhanced path handling to properly set relative paths in module summaries

### 4. Enhanced CLI (`src/terraform_ingest/cli.py`)
- Added `--recursive/--no-recursive` option to the `analyze` command
- Updated `RepositoryConfig` creation in CLI to include recursive setting
- Default is `--recursive` (enabled by default)

### 5. Updated Ingest Logic (`src/terraform_ingest/ingest.py`)
- Modified `_save_summary()` method to include module path in filenames
- Enhanced filename generation to avoid conflicts with multiple modules

## Features

### Recursive Mode (`recursive: true`)
- Searches all subdirectories for Terraform modules
- Finds modules in any nested directory structure
- Processes each module individually with correct relative paths

### Non-Recursive Mode (`recursive: false`)
- Only processes the specified `module_path` directory
- Does not search subdirectories
- Maintains backward compatibility for single-module repositories

## Testing Results

### Test Repository: `repos/aws-shared-terraform-modules`
- **Recursive Mode**: Found and processed 54 modules across all subdirectories
- **Non-Recursive Mode**: Found 0 modules (root directory has no Terraform files)

### Configuration File Testing
- Successfully processed 222 module versions across multiple branches and tags
- Each module gets its own JSON summary file with proper path identification

## Usage Examples

### CLI Usage
```bash
# Analyze with recursive search (default)
terraform-ingest analyze /path/to/repo --recursive

# Analyze without recursive search
terraform-ingest analyze /path/to/repo --no-recursive

# Using configuration file (respects recursive setting in YAML)
terraform-ingest ingest config.yaml
```

### Configuration File
```yaml
repositories:
  - url: "git@gitlab.com:example/terraform-modules.git"
    module_path: "."
    recursive: true    # Search all subdirectories
    branches: ["main"]
    include_tags: true
```

## Benefits
1. **Comprehensive Discovery**: Finds all Terraform modules in complex repository structures
2. **Flexible Configuration**: Can be enabled/disabled per repository
3. **Backward Compatibility**: Existing configurations continue to work
4. **Proper Path Handling**: Each module gets correct relative path identification
5. **CLI Integration**: Easy to use from command line with intuitive options

## File Naming Convention
When recursive mode finds multiple modules, each gets a unique filename:
- Format: `{repository}_{ref}_{module_path}.json`
- Example: `terraform-modules_main_modules_aws_s3.json`
- Conflicts are automatically avoided through path inclusion