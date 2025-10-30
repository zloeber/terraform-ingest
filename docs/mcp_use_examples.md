# MCP Usage Examples

Here are some practical use cases for this MCP server. 

## Example Project

[This project](https://github.com/zloeber/terraform-ingest-example) includes a practical terraform-ingest configuration example that gathers all the modules for a team of Terraform pros I happen to hold in the highest regards, [Cloudposse](https://cloudposse.com/).

They have produced almost 200 professional quality AWS terraform modules and more for the community. Here is how you would ingest all their modules to use as a basis for further terraform work via terraform-ingest.

## Idea - MCP Internal Service

This can be run as an internal MCP server for your pipelines and development teams as it includes the means to automatically update modules on a schedule. It should take little effort to run this container in your Kube clusters as a service.

