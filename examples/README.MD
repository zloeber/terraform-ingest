# Examples

## Terraform-Project1

Initially generated a bunch of terraform for an AWS fictitious low cost ordering system that uses native AWS terraform. I then prompted Copilot to use terraform-ingest after ingesting the ./examples/cloudeposse.yaml configuration and starting the MCP server to create a conversion doc from the manifests to use Cloudposse modules as much as possible.

```prompt
Create a document of possible terraform modules to use for the terraform code in ./terraform. Use search_modules_vector to find as many relevant modules as possible for this folder. If applicable modules are found, use get_module_details to get information needed to create the terraform module blocks need to use them. Ensure you create code for the modules that use the ssh git url format and repository ref as the version. Create a CONVERSION.md of the modules you would create and how you would convert the project.
```

You can see the result of this [here](./terraform-project1/CONVERSION.md) where it properly found applicable modules to use and gave a phased approach to migrating to them.