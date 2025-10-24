# MCP Prompts Feature

## Overview

The terraform-ingest MCP service provides built-in prompts for AI agents to access domain-specific Terraform guidance. These prompts are implemented using MCP's native `@mcp.prompt()` decorator pattern, providing a standardized, discoverable interface for AI agents to access reusable prompt templates.

Unlike storing prompts in configuration, native MCP prompts are first-class citizens in the protocol, allowing clients to:

- **Discover available prompts** via the MCP protocol
- **Accept dynamic arguments** for prompt customization  
- **Receive structured responses** (text or message sequences)
- **Integrate seamlessly** with MCP-compatible clients and LLM applications

## Motivation

AI agents often benefit from standardized guidance when working with Terraform infrastructure. By using MCP's native prompt system, these prompts become:

- **Discoverable**: Clients can list and explore available prompts
- **Parameterized**: Prompts can accept arguments for dynamic content
- **Structured**: Return either text or structured message sequences
- **Protocol-native**: Built on MCP's standard prompt mechanism
- **Version-aware**: Prompt content can evolve without configuration changes

## Available Prompts

### 1. Terraform Best Practices

**Name**: `terraform_best_practices`  
**Title**: "Terraform Best Practices"  
**Parameters**:
- `module_type` (optional): Type of module - `general` (default), `networking`, `compute`, `storage`, or `security`

**Purpose**: Provides standardized best practices for creating and maintaining Terraform infrastructure code.

**Content**:
- Code organization and structure
- Version management strategies
- Documentation requirements
- Configuration best practices
- Module-type-specific guidance

**Example Usage**:
```python
# Get general best practices
prompt = await session.get_prompt("terraform_best_practices")

# Get networking-specific practices
prompt = await session.get_prompt("terraform_best_practices", arguments={"module_type": "networking"})
```

### 2. Security Review Checklist

**Name**: `security_checklist`  
**Title**: "Security Review Checklist"  
**Parameters**: None

**Purpose**: Provides a comprehensive security review checklist for Terraform configurations.

**Content**:
- Access control considerations
- Encryption and data protection
- Logging and monitoring setup
- Network security implementation
- Compliance and governance checks

**Format**: Returns a structured message sequence guiding users through security reviews.

**Example Usage**:
```python
prompt = await session.get_prompt("security_checklist")
```

### 3. Module Documentation Generator

**Name**: `generate_module_docs`  
**Title**: "Module Documentation Generator"  
**Parameters**:
- `module_name` (optional): Name of the module
- `module_purpose` (optional): The purpose/function of the module

**Purpose**: Generates a comprehensive documentation structure template for Terraform modules.

**Content Sections**:
- Overview and use cases
- Requirements and dependencies
- Module structure explanation
- Input variables documentation
- Outputs documentation
- Usage examples
- Advanced usage patterns
- Troubleshooting guide
- Contributing guidelines

**Example Usage**:
```python
# Generate docs for a VPC module
prompt = await session.get_prompt("generate_module_docs", arguments={
    "module_name": "terraform-aws-vpc",
    "module_purpose": "AWS VPC creation and management"
})
```

## Protocol Integration

### Discovering Prompts

Clients can discover available prompts using the MCP protocol:

```python
prompts_response = await session.list_prompts()
for prompt in prompts_response.prompts:
    print(f"Prompt: {prompt.name}")
    print(f"  Title: {prompt.title}")
    if prompt.arguments:
        print(f"  Arguments: {[arg.name for arg in prompt.arguments]}")
```

### Retrieving Prompts

Get a specific prompt with optional arguments:

```python
result = await session.get_prompt(
    name="terraform_best_practices",
    arguments={"module_type": "compute"}
)

# Result contains messages that can be sent to an LLM
for message in result.messages:
    print(message.content.text)
```

### Using with LLM Sampling

Incorporate prompt content into LLM interactions:

```python
# Get the prompt
prompt_result = await session.get_prompt("security_checklist")

# Use in LLM sampling
response = await session.create_message(
    messages=[
        *prompt_result.messages,
        UserMessage("Please review my Terraform configuration: ..."),
    ],
    max_tokens=2000
)
```

## Implementation Details

### Adding New Prompts

To add a new prompt to the MCP service:

1. **Define the prompt function** in `src/terraform_ingest/mcp_service.py`:

```python
@mcp.prompt(title="My Custom Prompt")
def my_prompt(arg1: str = "default") -> str:
    """Generate a custom prompt.
    
    Args:
        arg1: Description of the argument
    
    Returns:
        The prompt text
    """
    return f"Prompt content with {arg1}"
```

2. **Document the prompt** in this file

3. **Test the prompt** by running the MCP server and listing prompts

4. **Update documentation** with examples

### Prompt Return Types

Prompts can return:

- **`str`**: Plain text prompt content
- **`list[Message]`**: Structured sequence of user/assistant messages (use `UserMessage`, `AssistantMessage` from `mcp.server.fastmcp.prompts.base`)

### Argument Handling

Prompts can accept optional arguments:

```python
@mcp.prompt()
def my_prompt(required_arg: str, optional_arg: str = "default") -> str:
    """Prompt with arguments."""
    ...
```

Arguments must be:
- Type-hinted
- Simple types (str, int, bool) or optional variants
- Properly documented

## Usage Patterns

### Pattern 1: Direct LLM Guidance

Use prompts to provide guidance to LLMs:

```python
# Agent asks for best practices
prompt = await session.get_prompt("terraform_best_practices")

# LLM uses this guidance when generating code
generate_terraform(prompt_guidance=prompt.messages[0].content.text)
```

### Pattern 2: Interactive Workflows

Use prompts to guide user interactions:

```python
# Present security checklist to user
checklist = await session.get_prompt("security_checklist")
print(checklist.messages[0].content.text)

# User provides configuration for review
user_config = input("Paste your Terraform config:")
```

### Pattern 3: Module Generation

Use documentation generator for new modules:

```python
# Generate template for new module
docs = await session.get_prompt("generate_module_docs", 
    arguments={
        "module_name": "my-module",
        "module_purpose": "Custom resource management"
    }
)

# Create README with template
with open("README.md", "w") as f:
    f.write(docs.messages[0].content.text)
```

## Best Practices

### Prompt Design

1. **Keep prompts focused**: Each prompt should address a specific topic
2. **Use clear structure**: Organize with sections, bullet points, numbering
3. **Provide examples**: Include concrete examples when helpful
4. **Document assumptions**: State any prerequisites clearly
5. **Make them actionable**: Provide guidance users can implement

### Prompt Arguments

1. **Use meaningful names**: Choose clear, descriptive parameter names
2. **Provide defaults**: Most arguments should have sensible defaults
3. **Document options**: Explain valid values for enum-like arguments
4. **Validate input**: Handle invalid arguments gracefully

### Integration

1. **Version prompts appropriately**: Consider versioning in prompt content if needed
2. **Test thoroughly**: Verify prompts work with different LLM backends
3. **Monitor usage**: Track which prompts are most useful
4. **Gather feedback**: Iterate based on user feedback

## MCP Protocol Specification

Prompts follow the [MCP Prompts specification](https://spec.modelcontextprotocol.io/latest/spec/server/features/prompts/):

- **List Prompts**: Discover available prompts and their metadata
- **Get Prompt**: Retrieve prompt content with optional arguments
- **Structured responses**: Support for both text and message sequences
- **Argument validation**: Type-safe parameter handling

## Configuration

No configuration needed! Prompts are defined in code and automatically registered with the MCP service when it starts.

To use prompts, simply:

1. **Start the MCP server**: `terraform-ingest-mcp`
2. **List available prompts**: Use MCP client to call `list_prompts`
3. **Get prompt content**: Call `get_prompt` with prompt name and optional arguments

## Examples

### Example 1: Using Best Practices in Code Generation

```python
# Client code
session = await connect_to_mcp()
practices = await session.get_prompt("terraform_best_practices",
    arguments={"module_type": "networking"})

# Send to LLM
response = await llm.generate(
    system="You are a Terraform expert. Follow these best practices:",
    prompt_content=practices.messages[0].content.text,
    user_request="Generate a VPC module"
)
```

### Example 2: Security Review Workflow

```python
# Get checklist
checklist = await session.get_prompt("security_checklist")

# Present to user/LLM
print(checklist.messages[0].content.text)

# Collect review results
review_results = collect_user_input()

# Generate compliance report
generate_report(checklist=checklist, results=review_results)
```

### Example 3: Module Documentation

```python
# Generate documentation template
template = await session.get_prompt("generate_module_docs",
    arguments={
        "module_name": "aws-vpc",
        "module_purpose": "VPC and networking infrastructure"
    })

# Use template to create initial documentation
write_file("README.md", template.messages[0].content.text)
```

## Testing

The MCP server includes prompts in its capabilities declaration. To test:

```bash
# Start MCP server
terraform-ingest-mcp

# In another terminal, use MCP Inspector
mcp dev
```

Then browse available prompts and test them interactively.

## Troubleshooting

### Prompts Not Listed

1. Verify MCP server is running
2. Check server logs for errors during initialization
3. Ensure prompts are properly decorated with `@mcp.prompt()`

### Prompt Arguments Not Working

1. Verify argument names match function parameters
2. Check argument types are simple (str, int, bool)
3. Ensure optional arguments have default values
4. Test with explicit argument values

### Content Not Displaying

1. Check message format is correct
2. Verify text content is properly formatted
3. Test with different MCP clients if available
4. Check server logs for formatting errors

## Future Enhancements

Potential improvements:

- Dynamic prompt generation from templates
- Prompt versioning and history
- Multi-language prompt support
- Prompt performance analytics
- User rating and feedback system
- Integration with external knowledge bases
- Real-time prompt updates without server restart

## Related Documentation

- [MCP Protocol Specification - Prompts](https://spec.modelcontextprotocol.io/latest/spec/server/features/prompts/)
- [FastMCP Prompts Documentation](https://modelcontextprotocol.github.io/python-sdk/)
- [terraform-ingest MCP Service](./MCP.md)
- [Architecture Overview](./DEVELOPMENT.md)

## Contributing

To contribute new prompts:

1. Add the prompt function to `src/terraform_ingest/mcp_service.py`
2. Follow the prompt design best practices
3. Add tests if needed
4. Update this documentation
5. Submit a pull request

## See Also

- [MCP Service Implementation](../src/terraform_ingest/mcp_service.py)
- [Models](../src/terraform_ingest/models.py)
- [Test Suite](../tests/)
