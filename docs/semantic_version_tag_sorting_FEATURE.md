# Semantic Version Tag Sorting Feature

## Overview
The ingestion process now uses semantic versioning (like `git tag -l | sort -r -V`) to sort and select tags from repositories. This ensures that the latest tagged releases are prioritized correctly, regardless of commit dates.

## Changes Made

### 1. Updated `_get_tags()` Method
**File:** `src/terraform_ingest/repository.py`

The `_get_tags()` method now:
- Sorts tags by semantic version in descending order (latest first)
- Handles both valid semantic versions (e.g., `v1.2.3`, `2.0.0`) and non-version tags
- Respects the `max_tags` parameter to limit results
- Uses the `packaging.version.parse()` for proper semantic version comparison

**Key Features:**
- Valid semantic versions are sorted first using proper version comparison
- Pre-release versions (e.g., `v1.0.0-beta`) are correctly positioned relative to stable versions
- Invalid version strings (e.g., `release-2023-01-01`) are included at the end, sorted alphabetically in reverse order
- Error handling ensures graceful fallback if tag retrieval fails

### 2. Added `packaging` Dependency
**File:** `pyproject.toml`

Added `packaging>=24.0` to the project dependencies for reliable semantic version parsing.

## Usage

### Configuration Example
In your `config.yaml`:

```yaml
repositories:
  - url: https://github.com/example/terraform-module.git
    include_tags: true
    max_tags: 5  # Ingest the 5 latest versions
    branches: ["main"]
```

When `include_tags: true`, the system will:
1. Fetch all tags from the repository
2. Sort them by semantic version in descending order
3. Process up to `max_tags` of the latest versions

### Version Sorting Examples

#### Input Tags
```
v1.2.3
v1.10.0
v1.2.1
v2.0.0
v1.5.0
v1.0.0-beta
release-2023
```

#### Sorted Output (with max_tags=5)
```
v2.0.0        # Latest major version
v1.10.0       # Latest minor version of v1.x
v1.5.0
v1.2.3
v1.2.1
```

Non-version tags like `v1.0.0-beta` and `release-2023` are not included in this example due to `max_tags=5`.

## Benefits

1. **Semantic Accuracy**: Tags are sorted by version number, not commit date
2. **Latest-First**: Always ingests the most recent stable releases first
3. **Pre-release Handling**: Correctly places pre-release versions (e.g., alpha, beta, rc)
4. **Backwards Compatible**: Non-semantic tags are still processed, just sorted to the end
5. **Configurable**: Control the number of tags ingested with `max_tags` parameter

## Testing

The feature includes comprehensive test coverage:

```bash
pytest tests/test_repository.py -v
```

Test cases cover:
- Semantic version sorting in descending order
- Max tags limitation
- Mixed valid and invalid version tags
- Empty repositories
- Pre-release version handling

## Implementation Details

### Sorting Algorithm

1. **Parse All Tags**: Extract tag names from the repository
2. **Classify Tags**: Separate into valid semantic versions and non-versions
3. **Sort Valid Versions**: Use `packaging.version.parse()` for proper comparison
4. **Sort Non-Versions**: Alphabetically in reverse order
5. **Combine**: Valid versions first, then non-versions
6. **Apply Limit**: Return up to `max_tags` results

### Error Handling

The implementation gracefully handles:
- Repositories with no tags (returns empty list)
- Invalid version strings (includes them at the end)
- Git errors during tag retrieval (logs error, returns empty list)

## Related Configuration

- `include_tags: bool` - Enable/disable tag ingestion
- `max_tags: int` - Maximum number of tags to process (default: 10)
- `branches: List[str]` - Branch refs to also process (processed alongside tags)
