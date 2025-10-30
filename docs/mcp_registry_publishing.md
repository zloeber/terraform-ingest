# MCP Registry Publishing Guide

This document describes how the Terraform Ingest MCP server is published to the Model Context Protocol (MCP) Registry.

## Overview

The Terraform Ingest project is configured for **automated publishing** to the MCP registry using GitHub Actions with GitHub OIDC authentication. This approach requires no secrets and leverages GitHub's built-in trust model.

## Publishing Configuration

### 1. Server Configuration (`server.json`)

The `server.json` file describes the MCP server to the registry:

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json",
  "name": "io.github.zloeber/terraform-ingest-mcp",
  "title": "Terraform Ingest MCP",
  "description": "Ingest and analyze Terraform modules from multiple repositories for AI RAG systems",
  "version": "0.0.1",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "terraform-ingest",
      "version": "0.0.1",
      "transport": {
        "type": "stdio"
      }
    }
  ]
}
```

**Key Fields:**
- **`name`**: Uses GitHub namespace format `io.github.username/server-name` (requires GitHub OIDC authentication)
- **`packages`**: Defines PyPI package deployment
  - `registryType: "pypi"`: Package is on PyPI
  - `identifier`: The PyPI package name (`terraform-ingest`)
  - `transport.type: "stdio"`: Server runs as a CLI command via stdin/stdout

### 2. Package Verification (`README.md`)

For PyPI packages, the registry verifies ownership by checking for an `mcp-name` marker in the package's README file on PyPI:

```markdown
<!-- mcp-name: io.github.zloeber/terraform-ingest-mcp -->
```

This marker is hidden in an HTML comment and proves that the PyPI package maintainer has explicitly authorized this server name in the registry.

### 3. Automated Publishing Workflow

**File:** `.github/workflows/publish-mcp.yml`

The GitHub Actions workflow automatically publishes to the MCP registry when you push a version tag.

#### Workflow Trigger
```yaml
on:
  push:
    tags: ["v*"]  # e.g., v1.0.0, v1.2.3
```

#### Key Steps

1. **Checkout Code**
   - Uses `actions/checkout@v5`

2. **Install MCP Publisher**
   - Downloads the official `mcp-publisher` CLI binary
   - Supports macOS, Linux, and Windows architectures

3. **Validate server.json**
   - Validates JSON syntax
   - Checks all required fields exist
   - Validates the name format
   - Ensures description is under 100 characters
   - Verifies at least one deployment method (packages or remotes)

4. **Update Version**
   - Automatically updates `server.json` version to match the git tag
   - Ensures version consistency: if you tag `v1.2.3`, the server.json becomes version `1.2.3`

5. **Authenticate with GitHub OIDC**
   ```bash
   ./mcp-publisher login github-oidc
   ```
   - Uses GitHub's OpenID Connect (OIDC) tokens
   - No secrets needed
   - GitHub automatically signs tokens with its private key
   - The MCP registry trusts GitHub's public key

6. **Publish to Registry**
   ```bash
   ./mcp-publisher publish
   ```
   - Reads `server.json`
   - Verifies PyPI package contains the `mcp-name` marker
   - Publishes server to the MCP registry
   - Server becomes discoverable at `https://registry.modelcontextprotocol.io`

7. **Verify Publication**
   - Queries the registry API to confirm successful publication
   - Example: `GET /v0/servers?search=io.github.zloeber/terraform-ingest-mcp`

## Publishing a New Version

### Step 1: Ensure PyPI Package is Published

The workflow publishes to PyPI via the existing `release.yaml` workflow or manually:

```bash
uv build
uv publish  # or use PyPI token
```

### Step 2: Tag the Release

Create a version tag to trigger the publishing workflow:

```bash
git tag v1.2.3
git push origin v1.2.3
```

The tag format should be `v<major>.<minor>.<patch>` (semantic versioning).

### Step 3: Monitor the Workflow

Check the GitHub Actions tab to monitor the publishing workflow. Once complete, verify at:
```
https://registry.modelcontextprotocol.io/v0/servers?search=io.github.zloeber/terraform-ingest-mcp
```

## Manual Publishing (If Needed)

If the workflow fails or you need to publish manually:

### Step 1: Install mcp-publisher

```bash
# macOS with Homebrew
brew install mcp-publisher

# Or download binary from releases
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_Darwin_arm64.tar.gz" | tar xz
```

### Step 2: Authenticate

```bash
# Using GitHub OIDC (recommended, requires GitHub CLI)
mcp-publisher login github-oidc

# Or using GitHub Personal Access Token
mcp-publisher login github --token YOUR_TOKEN
```

### Step 3: Update server.json Version

```bash
VERSION="1.2.3"
jq --arg v "$VERSION" '.version = $v | .packages[].version = $v' server.json > tmp && mv tmp server.json
```

### Step 4: Publish

```bash
mcp-publisher publish
```

## Validation

### Validate server.json

Use the included validation script:

```bash
uv run python3 validate_server.py
```

This script:
- Fetches the official JSON schema from the MCP registry
- Validates your `server.json` against the schema
- Checks for required fields
- Verifies format constraints (name, description length, etc.)
- Reports detailed errors if validation fails

### Manual Validation with jq

```bash
# Check if server.json is valid JSON
jq empty server.json

# Display the configuration
jq . server.json

# Extract specific fields
jq '.name' server.json
jq '.packages[0]' server.json
```

## Troubleshooting

### "Package validation failed"
- Ensure the PyPI package is already published
- Check that `terraform-ingest` package on PyPI contains the mcp-name marker in its README
- Verify the marker format: `<!-- mcp-name: io.github.zloeber/terraform-ingest-mcp -->`

### "Authentication failed"
- For OIDC: Ensure you have GitHub CLI installed and are logged in
- For token: Check that the token has `read:org` and `read:user` scopes
- Verify the GitHub username is correct (`zloeber`)

### "Namespace not authorized"
- Ensure the server name matches your GitHub username: `io.github.zloeber/*`
- For organization servers, use `io.github.<org-name>/*` and authenticate as the organization

### Version Mismatch
- The workflow automatically updates server.json version to match the git tag
- If publishing fails with version mismatch, manually update and retry:
  ```bash
  jq --arg v "1.2.3" '.version = $v | .packages[].version = $v' server.json > tmp && mv tmp server.json
  ```

## Additional Resources

- [MCP Publishing Guide](https://modelcontextprotocol.io/docs/guides/publishing/)
- [MCP Registry](https://registry.modelcontextprotocol.io/)
- [MCP Publisher CLI Reference](https://github.com/modelcontextprotocol/registry/tree/main/publisher)
- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)

## Next Steps

1. **Prepare for Release**: Ensure all features are tested and documentation is updated
2. **Tag Release**: Create a version tag when ready to publish
3. **Monitor Publication**: Watch the GitHub Actions workflow for completion
4. **Verify**: Confirm the server appears in the MCP registry

---

For questions or issues, refer to the [MCP Registry documentation](https://modelcontextprotocol.io/docs/guides/publishing/) or the [Terraform Ingest project issues](https://github.com/zloeber/terraform-ingest/issues).
