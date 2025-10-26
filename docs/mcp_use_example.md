# MCP Usage

This project includes a practical MCP usage example for a team of Terraform professionals I happen to hold in the highest regards, Cloudposse.

They have produced almost 200 profesional quality AWS terraform modules and more for the community. This example shows how you would ingest them all to then use as a basis to create a terraform deployment using GitHub Copilot prompts and vscode.

## The Setup

I used a custom script that uses my GitHub token to list out all the repositories for a target organization in a format I can then use in the configuration file for terraform-ingest (`./scripts/get-github-repos.py`). Using this output I created a custom yaml configuration for terraform-ingest in (`./examples/cloudposse.yaml`). Because Cloudposse is really good with standardized modules and tagged releases I'm purposefully targeting the latest tagged releases only and the `./src` path for each module repository for ingestion. 

```yaml
...
- name: aws-access-analyzer
  url: https://github.com/cloudposse-terraform-components/aws-access-analyzer.git
  recursive: false
  branches: []
  include_tags: true
  max_tags: 1
  path: ./src
  exclude_paths: []
...
```

As there are so many modules I found it best to ingest them all ahead of starting the mcp server. This is easily done with the following command: 

`terraform-ingest ingest examples/cloudposse.yaml`

This takes a minute or two and ends with a summary of ingested modules.

```
...
Ingestion complete!
Processed 167 module(s)
Summaries saved to output

Vector Database Statistics:
  Collection: terraform_modules
  Documents: 167
  Strategy: chromadb-default
```

Now we can use the MCP server to search and use these modules with an AI agent via Copilot prompts (or any other agent). The `.vscode/mcp.json` file I've setup for this example is pretty easy and includes terraform-ingest, The official Hashicorp terraform, and interactive enchanced interface, and the AWS documentation MCP servers.

```json
{
  "servers": {
    "terraform-ingest-mcp": {
      "command": "uvx",
      "args": ["terraform-ingest" , "mcp", "-c", "examples/cloudposse.yaml", "--no-ingest-on-startup"]
    },
    "terraform": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "hashicorp/terraform-mcp-server"
      ],
      "type": "stdio"
    },
    "mcp-feedback-enhanced": {
      "command": "uvx",
      "args": ["mcp-feedback-enhanced@latest"]
    },
    "aws-knowledge": {
        "url": "https://knowledge-mcp.global.api.aws",
        "type": "http"
    }
  },
  "inputs": []
}
```

With this in place we can setup a prompt to guide someone through the process of defining their requirements that then get transformed into an AWS terraform manifest that uses Cloudposse's modules where possible. This is defined in `./.vscode/prompts/terraform-aws-bootstrap.prompt.md`

```
---
mode: 'agent'
description: 'Create AWS terraform code for given requirements with interactive feedback.'
---

Create AWS Terraform code that best fits the given requirements with step-by-step reasoning and interactive feedback.

First use the interactive_feedback tool to ask for the location of an existing project requirements document if one exists. If the user does not have one then to gather additional information from the user about what they need to accomplish. Start with the basic goal then ask clarifying questions to refine the requirements, one at a time, until you have a clear understanding of what is needed. Summarize the refined requirements in bullet point format. Create a markdown file with the summary of the refined requirements and the project details and save it to `./terraform/REQUIREMENTS.md`.

With this collected data then use the aws-knowledge MCP tool to research best practices, compliance standards, and AWS service options that align with the refined requirements.

Then proceed to create the terraform project structure and necessary configuration files in `./terraform` for AWS infrastructure based on the refined requirements. Use search_modules_vector to find as many relevant modules as possible for this project, if applicable modules are found, use get_module_details to get information needed to create the terraform module blocks need to use them. When looking for modules use the found repository ref as the version and target the url in ssh git format.

Always try to use existing Terraform modules where possible to meet the requirements. If you cannot find suitable modules, create custom Terraform resources as needed. When searching for modules, consider their compatibility with the provider version and ensure they adhere to best practices. If they are missing critical features, inputs, or outputs, include this in a summary for the user in a final markdown file with why the module was not used.

Follow these Rules:
    - Generate the complete Terraform code in HCL syntax, ensuring it adheres to best practices for structure, security, and compliance.
    - Always use Terraform modules from the terraform-ingest-mcp server where possible to meet the requirements.
    - Ensure all AWS resources comply with best practices and security standards.
    - Terraform should be written using HCL (HashiCorp Configuration Language) syntax.
    - Use the latest AWS provider version compatible with the required resources.
    - Follow best practices for Terraform code structure, including the use of variables, outputs, and modules.
    - Ensure that the generated code is well-documented with comments explaining the purpose of each resource and configuration.
    - Always try to use implicit dependencies over explicit dependencies where possible in Terraform.
    - When generating Terraform resource names, ensure they are unique and descriptive, lower-case, and snake_case.
    - Be sure to include any necessary provider configurations, backend settings, and required variables in the generated code.
    - Ensure the generated terraform code always includes appropriate tags for resource identification and management find and use an apprpopriate tagging module from the terraform-ingest-mcp server if needed.
    - Ensure that sensitive information such as passwords, API keys, and secrets are not hardcoded in the Terraform code. Use variables and secret management solutions instead.
    - Do not ask for AWS specific information like instance types, instead focus on high level requirements and attempt to map them to AWS services for the user.
    - Create an appropriate README.md file in the ./terraform directory that explains the purpose of the infrastructure, how to deploy it, and any prerequisites or dependencies.
    - If terraform state management is needed, include backend configuration using a suitable remote backend like S3 with DynamoDB for state locking.
    - If multiple state environments are needed, set up workspaces or separate folders for each environment (e.g., dev, staging, prod) with appropriate configurations.
```

This prompt would walk through a greenfield deployment. But you can also simply reference the existing modules in your collection with your agent to do things like convert an existing codebase to your modules or perform more surgical work such as validating possible input/output issues for upgrading existing module calls to newer versions. Here is an example of a prompt to migrate current code to use your modules.

```prompt
Create a document of possible terraform modules to use for the terraform code in ./terraform. Use search_modules_vector to find as many relevant modules as possible for this folder. If applicable modules are found, use get_module_details to get information needed to create the terraform module blocks need to use them. Ensure you create code for the modules that use the ssh git url format and repository ref as the version. Create a CONVERSION.md of the modules you would create and how you would convert the project.
```