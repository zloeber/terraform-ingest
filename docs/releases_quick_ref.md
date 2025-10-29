# Quick Reference: Semantic Release

## Common Commit Messages

```bash
# Feature (Minor bump: 1.2.3 → 1.3.0)
git commit -m "feat: add vectordb support"

# Bug fix (Patch bump: 1.2.3 → 1.2.4)
git commit -m "fix: resolve parsing error"

# Breaking change (Major bump: 1.2.3 → 2.0.0)
git commit -m "feat!: redesign module API"

# With scope
git commit -m "feat(mcp): add streaming support"

# With description and body
git commit -m "feat: add module filtering

Users can now filter modules by provider"

# With breaking change footer
git commit -m "feat: upgrade HCL2 parser

BREAKING CHANGE: Requires Python 3.12+
"
```

## Version Calculation

| Commit Type | Bump | Example |
|---|---|---|
| `feat:` | Minor | 1.2.3 → 1.3.0 |
| `fix:` | Patch | 1.2.3 → 1.2.4 |
| `refactor:` | Patch | 1.2.3 → 1.2.4 |
| `perf:` | Patch | 1.2.3 → 1.2.4 |
| `feat!:` | Major | 1.2.3 → 2.0.0 |
| `BREAKING CHANGE:` | Major | 1.2.3 → 2.0.0 |
| `docs:` | - | No release |
| `test:` | - | No release |

## Workflow

```
git commit -m "feat: ..."     ← Use conventional commit
                    ↓
git push origin main          ← Push to main branch
                    ↓
[Semantic Release runs]       ← Automatic
                    ↓
git tag v1.3.0                ← Tag created
                    ↓
[Release workflow runs]       ← Automatic
                    ↓
PyPI + GitHub Release         ← Done!
```

## Checking Version

```bash
# View latest tag
git describe --tags

# List all tags
git tag -l --sort=-version:refname

# View specific tag
git show v1.2.3

# Get commit log with tags
git log --oneline --decorate
```

## Troubleshooting

| Issue | Check |
|---|---|
| No tag created | `git log -1 --pretty=%B` (check commit format) |
| Wrong version | `git log --oneline -10` (check all commits) |
| Tag exists | `git tag -l v*` (check for duplicates) |
| Release failed | GitHub Actions tab → Release workflow logs |

## Manual Release

```bash
# Manual trigger (if needed)
# Go to: GitHub Actions → Semantic Release → "Run workflow"
# Or use workflow_dispatch trigger

# View Actions status
# https://github.com/zloeber/terraform-ingest/actions
```

## First Time Setup

After pushing first merge to main:

1. ✅ Check Actions tab for "Semantic Release" workflow
2. ✅ Verify tag created: `git pull --tags && git tag -l`
3. ✅ Check GitHub Releases page
4. ✅ Verify PyPI publication: https://pypi.org/project/terraform-ingest/

## Tips

- 📝 Keep commits focused (one feature/fix per commit)
- ✨ Use lowercase for commit types
- 🔗 Reference issues: `Fixes #123`
- 📌 Use imperative mood: "add" not "added"
- ⚠️ Mark breaking changes clearly
- 🚫 Don't force-push to main

## Documentation Links

- Full guide: [Semantic Release Pipeline](./docs/semantic_release_FEATURE.md)
- Commit format: [Commit Conventions](./docs/commit_conventions.md)
- All workflows: [CI/CD Pipeline](./docs/cicd_pipeline.md)
- Implementation: [Setup Details](./SEMANTIC_RELEASE_SETUP.md)
