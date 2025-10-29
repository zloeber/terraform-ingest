# Fix: Automatic Dependency Installation for uv Tool

## Issue

When `terraform-ingest` was installed as a `uv` tool using `uv tool install terraform-ingest`, attempts to auto-install embedding dependencies would fail with:

```
WARNING  | dependency_installer - Failed to install with uv: 
error: No virtual environment found; run `uv venv` to create an environment, 
or pass `--system` to install into a non-virtual environment
```

## Root Cause

When running as a `uv` tool, the application runs in a managed environment without an active Python virtual environment. The `uv pip install` command requires the `--system` flag to install packages into the tool's environment.

## Solution

Updated the `DependencyInstaller` class in `src/terraform_ingest/dependency_installer.py` to:

1. **Try `uv pip install --system` first** - Installs into the tool's environment (handles uv tool installations)
2. **Fall back to `uv pip install` (without --system)** - For traditional virtual environments
3. **Fall back to pip** - Multiple pip approaches as before

### Code Changes

**File:** `src/terraform_ingest/dependency_installer.py`

```python
# Try uv first if it's available
if use_uv:
    uv_approaches = [
        # Approach 1: uv pip install with --system (for uv tool installations)
        ["uv", "pip", "install", "--system"] + still_missing,
        # Approach 2: uv pip install without --system (for venv)
        ["uv", "pip", "install"] + still_missing,
    ]
    
    for uv_cmd in uv_approaches:
        try:
            logger.debug(f"Using '{' '.join(uv_cmd[:3])}' to install packages")
            _ = subprocess.run(
                uv_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            logger.info("Successfully installed packages using uv")
            return True
        except subprocess.CalledProcessError as e:
            logger.debug(f"uv approach failed: {e.stderr}")
            continue
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.debug(f"uv command not available or timed out")
            break
    
    logger.debug("All uv approaches failed, falling back to pip")
```

### Error Message Improvement

Updated the final fallback error message to provide all available options:

```
Option 1 (pip):
  pip install <packages>

Option 2 (uv with system packages):
  uv pip install --system <packages>

Option 3 (uv add via pyproject):
  uv add <packages>

Option 4 (reinstall tool with extras):
  uv tool install --force terraform-ingest[embeddings]
```

## Testing

Added comprehensive tests in `tests/test_dependency_installer.py`:

1. **test_install_packages_with_uv_system_flag_success** - Verifies `--system` flag is used
2. **test_install_packages_with_uv_fallback_to_pip** - Verifies fallback between uv approaches
3. **Updated existing tests** - All 24 tests pass

Run tests with:
```bash
python -m pytest tests/test_dependency_installer.py -v
```

## Usage

No changes needed! The fix is transparent:

```bash
# Install as uv tool
uv tool install terraform-ingest

# Run normally - dependencies auto-install now
terraform-ingest ingest config.yaml \
  --enable-embeddings \
  --embedding-strategy sentence-transformers
```

## Backward Compatibility

✅ **Fully backward compatible**
- Traditional virtual environments still work with `uv pip install`
- pip fallback mechanisms unchanged
- CLI interface unchanged
- Configuration format unchanged
- Programmatic API unchanged

## Files Modified

1. **src/terraform_ingest/dependency_installer.py** - Updated `install_packages()` method
2. **tests/test_dependency_installer.py** - Added new tests, imported subprocess
3. **docs/uv_tool_installation.md** - Updated documentation with `--system` flag explanation

## Impact

Users installing `terraform-ingest` as a `uv` tool can now:
- ✅ Enable embeddings without manual setup
- ✅ Auto-install missing dependencies seamlessly
- ✅ Use any embedding strategy (sentence-transformers, openai, claude, chromadb-default)
- ✅ See helpful fallback options if auto-install fails

## Related Documentation

- [Using terraform-ingest as a uv Tool](./uv_tool_installation.md) - Full usage guide
- [Automatic Dependency Installation](./automatic_dependency_installation.md) - Technical details
