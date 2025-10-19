# ignore_default_branch Configuration Feature

## Overview
Added support for `ignore_default_branch` configuration option that allows skipping the repository's default branch during ingestion processing.

## Changes Made

### 1. Updated Models (`src/terraform_ingest/models.py`)
- Added `ignore_default_branch: bool = False` field to `RepositoryConfig` class
- Default value is `False` to maintain backward compatibility

### 2. Enhanced Repository Manager (`src/terraform_ingest/repository.py`)
- Added `_get_default_branch()` method to detect the repository's default branch
- Modified `process_repository()` method to skip default branch when `ignore_default_branch=True`
- Enhanced branch processing logic with default branch detection and conditional skipping

### 3. Updated CLI (`src/terraform_ingest/cli.py`)
- Added `--ignore-default-branch/--include-default-branch` option to the `analyze` command
- Default is `--include-default-branch` (disabled) to maintain existing behavior
- Updated `RepositoryConfig` creation to include the `ignore_default_branch` setting

### 4. Updated Configuration Files
- Updated main `config.yaml` with example `ignore_default_branch: false` setting and comment
- Enhanced `examples/config.yaml` with comprehensive examples showing both use cases

## Features

### Default Branch Detection
The system automatically detects the repository's default branch using:
1. `origin/HEAD` reference (most reliable)
2. Common default branch names (`main`, `master`, `develop`, `dev`)
3. Active branch as fallback

### Configuration Options
- `ignore_default_branch: false` (default) - Process all specified branches including default
- `ignore_default_branch: true` - Skip the repository's default branch during processing

## Usage Examples

### Configuration File
```yaml
repositories:
  # Standard processing (includes default branch)
  - url: https://github.com/example/terraform-modules
    branches: ["main", "develop"]
    ignore_default_branch: false  # Process all specified branches

  # Skip default branch processing  
  - url: https://github.com/example/terraform-modules
    branches: ["main", "develop"] 
    ignore_default_branch: true   # Skip repository's default branch
```

### CLI Usage
```bash
# Include default branch (default behavior)
terraform-ingest analyze https://github.com/example/repo --include-default-branch

# Ignore default branch
terraform-ingest analyze https://github.com/example/repo --ignore-default-branch
```

## Testing Results

### Test Repository: `repos/aws-shared-terraform-modules`
- **Default Branch Detected**: `main`
- **With ignore_default_branch=false**: Processed 37 modules from main branch
- **With ignore_default_branch=true**: Skipped main branch, processed 0 modules

### CLI Testing
- `--ignore-default-branch` option properly skips default branch
- `--include-default-branch` option processes all specified branches
- Help text displays correctly with new option

## Benefits

1. **Flexible Branch Processing**: Allows excluding default branches from analysis
2. **Automated Detection**: Automatically identifies repository default branches
3. **Backward Compatibility**: Default behavior unchanged (includes default branch)
4. **CLI Integration**: Easy command-line access to the feature
5. **Clear Logging**: Provides feedback when default branch is detected and skipped

## Use Cases

- **Development Focus**: Skip stable default branches, focus on development branches
- **Avoiding Duplicates**: Prevent processing default branch when it matches other specified branches
- **Workflow Optimization**: Reduce processing time by excluding default branches
- **Selective Analysis**: Target specific non-default branches for analysis

## Implementation Details

### Default Branch Detection Logic
1. Checks `origin/HEAD` for definitive default branch reference
2. Falls back to checking common default branch names
3. Uses active branch as last resort
4. Returns `None` if detection fails (no skipping occurs)

### Processing Flow
1. Repository cloned/updated
2. If `ignore_default_branch=true`, detect default branch
3. For each specified branch:
   - Skip if it matches detected default branch
   - Process normally otherwise
4. Continue with tag processing if enabled

The feature seamlessly integrates with existing recursive processing and all other configuration options.