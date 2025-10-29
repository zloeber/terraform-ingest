# Development

I use [task](https://taskfile.dev) along with [mise](https://mise.jdx.dev) for everything locally. You can setup mise by running `./configure.sh` or just install the binaries used if you already have mise in your path via `mise install -y`

# CICD

Github Actions pipeline documentation found [here](./cicd_pipeline.md)

# Semantic Releases

This project follows conventional commits to automatically cut versioned releases upon merge to main.

## Semantic Versioning Format

The project uses [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes, incompatible API changes
- **MINOR**: New features, backwards compatible enhancements
- **PATCH**: Bug fixes, performance improvements, refactoring

## Conventional Commits

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types and Version Bumps

| Type | Version Bump | Example | Use Case |
|------|--------------|---------|----------|
| `feat` | MINOR | `feat: add AWS module support` | New feature or enhancement |
| `fix` | PATCH | `fix: resolve parsing error` | Bug fix |
| `refactor` | PATCH | `refactor: reorganize module structure` | Code refactoring (non-functional) |
| `perf` | PATCH | `perf: optimize JSON generation` | Performance improvement |
| `docs` | None | `docs: update README` | Documentation changes |
| `test` | None | `test: add unit tests` | Test additions/modifications |
| `chore` | None | `chore: update dependencies` | Maintenance tasks |
| `ci` | None | `ci: add GitHub Actions workflow` | CI/CD changes |
| `style` | None | `style: fix formatting` | Code style changes (no logic) |

### Breaking Changes → MAJOR Version Bump

Breaking changes can be indicated in two ways:

**Method 1: Append `!` to type**
```
feat!: redesign module API
fix!: change database schema
```

**Method 2: Include `BREAKING CHANGE:` footer**
```
feat: remove deprecated endpoint

BREAKING CHANGE: /v1/api endpoint is no longer supported, use /v2/api instead
```

## Examples

### Example 1: Bug Fix (Patch Bump)
```
fix: resolve HCL2 parser error with nested blocks

The parser was failing on deeply nested terraform blocks.
Fixed by improving the recursive parsing logic.

Fixes #123
```
**Result**: `1.2.3` → `1.2.4`

### Example 2: New Feature (Minor Bump)
```
feat: add support for local Terraform modules

Users can now reference local modules in addition to git repositories.
Added new `local_path` configuration option.
```
**Result**: `1.2.3` → `1.3.0`

### Example 3: Breaking Change (Major Bump)
```
feat!: restructure JSON output format

BREAKING CHANGE: The JSON output format has been redesigned:
- Renamed `module_vars` to `variables`
- Changed `module_outs` to `outputs`
- Added new `resources` field

See migration guide in docs/migration.md
```
**Result**: `1.2.3` → `2.0.0`

### Example 4: Multiple Changes
```
feat: add vectordb support
fix: resolve concurrent parsing issues
refactor: simplify MCP service code

Multiple improvements in this release:
- VectorDB integration for RAG systems
- Fixed race condition in repository manager
- Cleaned up MCP service implementation
```
**Result**: `1.2.3` → `1.3.0` (takes highest bump type)

## Best Practices

✅ **Do:**
- Use lowercase for type and scope
- Keep subject line concise (50 chars or less)
- Use imperative mood ("add" not "added")
- Reference issue numbers: `Fixes #123` or `Closes #456`
- Include detailed explanation in body for complex changes
- Be consistent with formatting

❌ **Don't:**
- Use vague messages: "fix stuff", "update", "changes"
- Mix multiple semantic types in one commit
- Use period at end of subject line
- Forget breaking change indicators

## Commit Message Tools

### Pre-commit Hook (Optional)

Use commitizen or similar tools to ensure consistency:

```bash
# Install commitizen
pip install commitizen

# Make commits interactively
git cz commit
```

### Git Aliases

Add to your `.gitconfig`:

```ini
[alias]
    feat = commit -m
    fix = commit -m
    chore = commit -m
```

Usage:
```bash
git feat "add new module"
# Equivalent to: git commit -m "feat: add new module"
```

## Integration with Release Pipeline

The semantic release workflow automatically:

1. Scans commits since last tag
2. Identifies commit types
3. Calculates version bump
4. Creates annotated git tag
5. Publishes to PyPI (via existing release workflow)
6. Creates GitHub release with changelog

**No manual intervention required!**

## Reverting Version Bumps

If you accidentally created commits with wrong types:

1. Amend the last commit:
   ```bash
   git commit --amend -m "fix: correct message"
   git push --force-with-lease
   ```

2. Or manually delete the tag and push:
   ```bash
   git tag -d v1.2.3
   git push --delete origin v1.2.3
   ```

## Troubleshooting

### Tag wasn't created for my commits
- Check commit messages follow conventional format (e.g., `feat:` not `feature:`)
- Ensure commits are on the `main` branch
- Verify GitHub Actions workflow ran (check Actions tab)

### Wrong version was calculated
- Check commit messages in git log
- Verify semantic release workflow output in Actions
- Check for conflicting tags manually: `git tag -l`

### Release published but not to main branch
- Semantic release only runs on `main` branch pushes
- Ensure PR is merged to main, not to a feature branch

## Additional Resources

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

# Building

This project uses uv + hatch + hatch-vcs for building and automatic versioning. You can build the local docker image using `task build:image` if that's your thing. Otherwise run `uv build` to build locally.


# Pull Request Preparation

Before submitting a pull request run the following and clean any errors that come up:

```bash
task test format lint:fix
```

