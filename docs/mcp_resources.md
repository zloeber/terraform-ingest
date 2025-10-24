# Native MCP Resources for Dynamic Module Document Lookup

## Overview

This feature implements native MCP (Model Context Protocol) resources for dynamic discovery and retrieval of full Terraform module documentation. Instead of storing metadata in configuration, we leverage MCP's resource system to expose module documents as discoverable, queryable resources that AI agents can access directly.

## Key Concepts

### What are MCP Resources?

Resources in the Model Context Protocol represent data that servers expose to clients. Think of them like GET endpoints in a REST API:

- **Standardized format**: Uses URIs (`module://repository/ref/path`) for unique identification
- **Discoverable**: Clients can list available resources and their parameters
- **Dynamic**: Supports parameterized URI templates with argument completion
- **Content-rich**: Resources can contain complex, multi-section documentation

### Resource URI Template

The terraform-ingest MCP server exposes modules as resources using the URI template:

```
module://{repository}/{ref}/{path}
```

Where:
- **repository**: Repository name (can be partial; matched against full repository URLs)
- **ref**: Git reference (branch, tag, or commit)
- **path**: Path within the repository (encoded with hyphens instead of slashes)
  - `.` (root module) is encoded as `-`
  - `modules/aws` becomes `modules-aws`

## Usage Patterns

### 1. Discovering Available Modules

Clients can discover all available module resources:

```python
# List all module resources
resources = await session.list_resources()

# Filter for module resources
module_resources = [r for r in resources.resources 
                   if r.uri.startswith("module://")]

# Example URIs available:
# - module://terraform-aws-vpc/main/-
# - module://terraform-aws-vpc/v5.0.0/-
# - module://terraform-aws-ec2/main/-
```

### 2. Reading Full Module Documentation

Access complete module documentation as a resource:

```python
from pydantic import AnyUrl

# Read a module resource
resource = await session.read_resource(
    AnyUrl("module://terraform-aws-vpc/v5.0.0/-")
)

# Get the documentation content
if resource.contents:
    doc = resource.contents[0]
    if isinstance(doc, TextContent):
        print(doc.text)  # Full module documentation
```

### 3. Argument Completion for Resource Parameters

The server supports argument completion, allowing clients to discover valid values:

```python
# Complete repository names starting with "terraform-aws"
completions = await session.complete(
    ref=ResourceTemplateReference(type="ref/resource", 
                                 uri="module://{repository}/{ref}/{path}"),
    argument={"name": "repository", "value": "terraform-aws"}
)
# Returns: ["terraform-aws-vpc", "terraform-aws-ec2", ...]

# Complete ref values
completions = await session.complete(
    argument={"name": "ref", "value": "v"}
)
# Returns: ["v5.0.0", "v5.1.0", ...]

# Complete path values  
completions = await session.complete(
    argument={"name": "path", "value": "modules-"}
)
# Returns: ["modules-aws", "modules-azure", ...]
```

## Content Structure

When you read a module resource, you receive comprehensive documentation including:

### Documentation Sections

1. **Header**
   - Module name
   - Repository URL
   - Ref (branch/tag)
   - Path within repository

2. **Description**
   - Module overview and purpose

3. **Resources**
   - List of AWS/cloud resources created by the module
   - Resource types and names

4. **Providers**
   - Required providers
   - Version constraints
   - Source URIs

5. **Input Variables**
   - Variable names and types
   - Required vs optional status
   - Default values
   - Descriptions and constraints

6. **Outputs**
   - Output names and descriptions
   - Sensitivity markers
   - Value type information

7. **Child Modules**
   - Names and sources
   - Version information
   - Purpose

8. **README**
   - Full README content if available
   - Usage examples and guidance

## Protocol Integration

### Resource Listing

The `list_resources()` operation returns metadata about available modules:

```json
{
  "resources": [
    {
      "uri": "module://terraform-aws-vpc/main/-",
      "name": "terraform-aws-vpc - .",
      "title": "terraform-aws-vpc - .",
      "description": "Terraform module from https://github.com/terraform-aws-modules/terraform-aws-vpc @ main",
      "mimeType": "text/markdown"
    },
    {
      "uri": "module://terraform-aws-vpc/v5.0.0/-",
      "name": "terraform-aws-vpc - .",
      "title": "terraform-aws-vpc - .",
      "description": "Terraform module from https://github.com/terraform-aws-modules/terraform-aws-vpc @ v5.0.0",
      "mimeType": "text/markdown"
    }
  ]
}
```

### Resource Reading

The `read_resource()` operation retrieves full documentation:

```json
{
  "contents": [
    {
      "uri": "module://terraform-aws-vpc/v5.0.0/-",
      "name": "terraform-aws-vpc - .",
      "mimeType": "text/markdown",
      "text": "# Terraform Module: terraform-aws-vpc\n\n**Repository:** https://github.com/terraform-aws-modules/terraform-aws-vpc\n**Ref:** v5.0.0\n**Path:** .\n\n## Description\n\nA Terraform module which creates VPC resources on AWS.\n\n... full documentation ..."
    }
  ]
}
```

### Resource Templates

The server declares resource templates during initialization:

```json
{
  "resourceTemplates": [
    {
      "uriTemplate": "module://{repository}/{ref}/{path}",
      "name": "Terraform Module Documentation",
      "description": "Access full Terraform module documentation with variables, outputs, and resources",
      "mimeType": "text/markdown"
    }
  ]
}
```

## Implementation Details

### Server-Side Functions

#### `get_module_resource(repository, ref, path)`
Main resource handler decorated with `@mcp.resource()`. Handles dynamic URI parameter extraction and returns formatted module documentation.

**Parameters:**
- `repository`: Repository name (partial match)
- `ref`: Git reference (exact match)
- `path`: Module path (hyphen-encoded)

**Returns:** Formatted Markdown documentation string

#### `list_module_resources_for_discovery()`
Returns all available module resources for MCP discovery.

**Returns:** List of resource metadata dicts with `uri`, `name`, `title`, `description`, and `mimeType`.

#### `get_argument_completions_for_resources(argument_name, argument_value)`
Provides argument completion suggestions for resource URI parameters.

**Parameters:**
- `argument_name`: One of "repository", "ref", or "path"
- `argument_value`: Current user input

**Returns:** List of matching completion suggestions (sorted)

### Dynamic Lookup Process

1. Client requests resource: `module://terraform-aws-vpc/v5.0.0/-`
2. Server extracts parameters: `repository="terraform-aws-vpc"`, `ref="v5.0.0"`, `path="-"`
3. Path is decoded: `-` → `.` (root module)
4. Server searches loaded module summaries for matching module
5. Matching criteria:
   - Exact `ref` match (branch/tag)
   - Path contains decoded path OR both are root (`.`)
   - Repository URL contains the provided repository name
6. Full module document is generated from matched summary
7. Returns formatted Markdown with all metadata

### Argument Completion Process

1. Client requests completions for parameter: `repository`, partial value: `terraform-aws`
2. Server iterates through all loaded module summaries
3. Extracts repository basenames from full URLs
4. Filters for matches containing the user input (case-insensitive)
5. Returns sorted list of unique matches

## Best Practices

### For Client Applications

1. **Use Resource Discovery**
   - List available resources before accessing specific modules
   - Display resource titles to users
   - Use descriptions for context

2. **Handle Partial Matches**
   - Repository names are matched as substrings
   - Use argument completion to find exact names
   - Provide feedback if no resources match

3. **Cache Resources**
   - Cache resource listings to reduce server calls
   - Update periodically based on your needs
   - Use the `mimeType` to validate content type

4. **Parse Documentation**
   - Use Markdown parsers for consistent handling
   - Extract specific sections programmatically
   - Handle missing sections gracefully

### For Server Configuration

1. **Ingestion Strategy**
   - Configure `ingest_on_startup` to populate modules at startup
   - Enable `auto_ingest` for periodic refreshes
   - Set appropriate `refresh_interval_hours` for your use case

2. **Repository URLs**
   - Use consistent repository naming conventions
   - Include full GitHub/GitLab/other URLs
   - Use HTTPS URLs for better compatibility

3. **Reference Management**
   - Ingest both branches and tags for flexibility
   - Use semantic versioning tags when available
   - Document branch naming conventions

## Example: Complete Resource Lookup Flow

```python
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import AnyUrl

async def access_terraform_module():
    # Connect to terraform-ingest MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "terraform_ingest.cli", "mcp"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Step 1: Get argument completion suggestions
            suggestions = await session.complete(
                ref={
                    "type": "ref/resource",
                    "uri": "module://{repository}/{ref}/{path}"
                },
                argument={"name": "repository", "value": "terraform-aws"}
            )
            print("Available repositories:", suggestions.completion.values)
            # Output: ["terraform-aws-vpc", "terraform-aws-ec2", ...]
            
            # Step 2: List all resources
            resources = await session.list_resources()
            module_resources = [r for r in resources.resources 
                              if r.uri.startswith("module://")]
            print(f"Found {len(module_resources)} module resources")
            
            # Step 3: Read specific module documentation
            module_uri = AnyUrl("module://terraform-aws-vpc/v5.0.0/-")
            doc = await session.read_resource(module_uri)
            
            if doc.contents:
                content = doc.contents[0]
                print("Module Documentation:")
                print(content.text)  # Full Markdown documentation
```

## Comparison: Configuration vs Native Resources

### Configuration-Based Approach (Previous)
- ❌ Custom prompts stored in YAML config
- ❌ No protocol-standard discovery
- ❌ Limited to configuration keys
- ❌ Requires custom parsing

### Native MCP Resources (Current)
- ✅ Protocol-native resource system
- ✅ Built-in discovery via `list_resources()`
- ✅ Parameterized URI templates
- ✅ Argument completion support
- ✅ Standardized MCP integration
- ✅ Full Markdown documentation
- ✅ Dynamic lookup by repository/ref/path

## Troubleshooting

### Issue: Module not found in resources

**Cause:** Module hasn't been ingested yet

**Solution:**
1. Ensure `ingest_on_startup: true` in config
2. Or run manual ingestion: `terraform-ingest ingest config.yaml`
3. Verify JSON files exist in `output_dir`

### Issue: Argument completion returns empty list

**Cause:** No modules match the filter

**Solution:**
1. Verify repositories are configured in `config.yaml`
2. Check that ingestion has completed
3. Adjust search terms (use partial matches)

### Issue: Module resource returns documentation but path is wrong

**Cause:** Path encoding/decoding mismatch

**Solution:**
1. Remember that `/` is encoded as `-`
2. Root module `.` is encoded as `-`
3. Use `list_module_resources_for_discovery()` to see correct URIs

## Future Enhancements

Potential improvements for resource functionality:

- **Resource Subscriptions**: Clients subscribe to resource updates
- **Resource Versioning**: Track documentation versions over time
- **Search Filters**: Advanced filtering by provider, tags, requirements
- **Content Caching**: Optimize performance for large module collections
- **Change Notifications**: Real-time updates when modules change
- **Collaborative Annotations**: User notes and ratings on resources
- **Multi-format Export**: Support JSON, HCL, other formats alongside Markdown

## References

- [MCP Protocol Specification - Resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)
- [FastMCP Python SDK - Resources](https://github.com/modelcontextprotocol/python-sdk)
- [terraform-ingest Configuration Guide](./QUICKSTART.md)
- [MCP Prompts Feature](./mcp_prompts_FEATURE.md)
