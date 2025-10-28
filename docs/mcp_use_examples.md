# MCP Usage Examples

Here are some practical use cases for this MCP server. 

## Example Module Set - CloudePosse

This project includes a practical terraform-ingest configuration example that gathers all the modules for a team of Terraform professionals I happen to hold in the highest regards, Cloudposse.

They have produced almost 200 professional quality AWS terraform modules and more for the community. The example configuration file is `./examples/cloudposse.yaml` and shows how you would ingest all their modules to then use as a basis for further terraform work.

### The Setup

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

## Example 1 - Full Greenfield Deployment

Now we can use the MCP server to search and use our ingested modules with an AI agent via Copilot prompts (or any other agent). The `.vscode/mcp.json` file I've setup for this example is pretty easy and includes terraform-ingest, The official Hashicorp terraform, interactive enhanced interface, and the AWS documentation MCP servers.

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

You can then use GitHub Copilot in Agent mode and run this prompt via `/terraform-aws-bootstrap` to kick off an interactive question/answer session to gather your project requirements and generate new terraform using your custom modules as a focus.

## Example 2 - A Migration

You can reference the existing modules in your collection with your agent to do things like convert an existing codebase to start using your modules or perform more surgical work such as validating possible input/output issues for upgrading existing module calls to newer versions. Here is an example of a prompt to migrate an existing code base to use your modules.

```
Create a document of possible terraform modules to use for the terraform code in ./terraform. Use search_modules_vector to find as many relevant modules as possible for this folder. If applicable modules are found, use get_module_details to get information needed to create the terraform module blocks need to use them. Ensure you create code for the modules that use the ssh git url format and repository ref as the version. Create a CONVERSION.md of the modules you would create and how you would convert the project.
```

## Example 3 - On Demand Documentation

Probably the easiest use case for this MCP server is readily accessing your modules requirements.

With several dozen modules spread across repositories it can be a pain to recall the inputs/output for each module when you are authoring new or existing Terraform. To get around this, you can use terraform-ingest as a means to quickly get these details and generate example module blocks to use them.

```bash
# Generate example module call for one of your custom modules
Generate an example terraform module call for aws-kms using the source format for ssh git

# Get expected inputs for one of your modules
What are the expected inputs for the aws-argocd-github-repo terraform module?
```

With the last prompt in copilot it will use the search_modules tool to get the module information, provide all required and optional inputs in a table, AND provide example usage. Nifty!

### Example 3 - Output

Let me search for the aws-argocd-github-repo module to get its expected inputs. 

Ran `search_modules` 
Completed with input: {
  "query": "aws-argocd-github-repo"
}

Based on the search results, here are the **expected inputs for the aws-argocd-github-repo Terraform module** (version v2.2.0):

#### Required Inputs

| Variable | Type | Description |
|----------|------|-------------|
| `region` | string | AWS Region |
| `description` | string | The description of the repository |
| `gitignore_entries` | list(string) | List of .gitignore entries (e.g., `[".idea/", ".vscode/"]`) |
| `github_base_url` | string | GitHub base API endpoint (required for Enterprise) |
| `github_codeowner_teams` | list(string) | List of teams for CODEOWNERS file (e.g., `["@ACME/cloud-admins"]`) |
| `github_user` | string | GitHub username |
| `github_user_email` | string | GitHub user email |
| `github_organization` | string | GitHub Organization name |
| `github_token_override` | string | GitHub API token (can use SSM instead) |

#### Optional Inputs

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `environments` | list(object) | `[]` | Environments for ArgoCD applicationset and deploy keys |
| `permissions` | list(object) | `[]` | Repository permission objects for team access |
| `create_repo` | bool | `true` | Whether to create the repository or use existing |
| `deploy_keys_enabled` | bool | `true` | Enable GitHub deploy keys for ArgoCD syncing |
| `required_pull_request_reviews` | bool | `true` | Enforce PR review restrictions |
| `push_restrictions_enabled` | bool | `true` | Enforce push restrictions on main branch |
| `vulnerability_alerts_enabled` | bool | `false` | Enable security alerts |
| `web_commit_signoff_required` | bool | `false` | Require commit sign-off |
| `manifest_kubernetes_namespace` | string | `"argocd"` | Kubernetes namespace for ArgoCD |
| `ssm_github_api_key` | string | `"/argocd/github/api_key"` | SSM path to GitHub API key |
| `ssm_github_deploy_key_format` | string | `"/argocd/deploy_keys/%s"` | SSM path format for deploy keys |
| `slack_notifications_channel` | string | `""` | Slack channel for notifications |
| `use_local_github_credentials` | bool | `false` | Use environment variables instead of SSM |

#### Example Usage

```hcl
module "argocd_github_repo" {
  source = "git::ssh://git@github.com/cloudposse-terraform-components/aws-argocd-github-repo.git//src?ref=v2.2.0"

  region                  = "us-east-1"
  description             = "ArgoCD desired state repository"
  github_user             = "ci-acme"
  github_user_email       = "ci@acme.com"
  github_organization     = "ACME"
  github_base_url         = "https://github.com/"
  github_codeowner_teams  = ["@ACME/cloud-admins", "@ACME/cloud-posse"]
  gitignore_entries       = [".idea/", ".vscode/", "*.tfvars"]
  
  permissions = [
    {
      team_slug  = "admins"
      permission = "admin"
    },
    {
      team_slug  = "engineering"
      permission = "push"
    }
  ]

  environments = [
    {
      tenant      = "mgmt"
      environment = "uw2"
      stage       = "sandbox"
      auto-sync   = true
    }
  ]

  deploy_keys_enabled            = true
  required_pull_request_reviews  = true
  push_restrictions_enabled      = true
  vulnerability_alerts_enabled   = false
}
```