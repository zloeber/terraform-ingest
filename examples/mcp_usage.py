#!/usr/bin/env python3
"""Example usage of the terraform-ingest MCP service.

This script demonstrates how to use the MCP service tools programmatically.
In a real MCP environment, AI agents would call these tools directly.
"""

import sys
import os

# Adjust path to find the module if running from examples directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from terraform_ingest.mcp_service import ModuleQueryService


def main():
    """Demonstrate MCP service functionality."""

    # Initialize the service with the output directory
    # This directory should contain the JSON summaries from ingestion
    output_dir = "./output"
    service = ModuleQueryService(output_dir)

    print("=" * 80)
    print("Terraform Ingest MCP Service - Example Usage")
    print("=" * 80)
    print()

    # Example 1: List all repositories
    print("Example 1: List all repositories")
    print("-" * 80)
    repos = service.list_repositories(limit=10)
    print(f"Found {len(repos)} repositories:\n")
    for i, repo in enumerate(repos, 1):
        print(f"{i}. {repo['name']}")
        print(f"   URL: {repo['url']}")
        print(f"   Description: {repo['description'][:80]}...")
        print(f"   Providers: {', '.join(repo['providers'])}")
        print(f"   Refs: {', '.join(repo['refs'])}")
        print()

    # Example 2: Find AWS-related repositories
    print("\nExample 2: Find AWS-related repositories")
    print("-" * 80)
    aws_repos = service.list_repositories(filter_keyword="aws", limit=5)
    print(f"Found {len(aws_repos)} AWS repositories:\n")
    for repo in aws_repos:
        print(f"  • {repo['name']}")

    # Example 3: Search for VPC modules
    print("\n\nExample 3: Search for VPC modules")
    print("-" * 80)
    vpc_modules = service.search_modules(query="vpc")
    print(f"Found {len(vpc_modules)} modules related to VPC:\n")
    for mod in vpc_modules[:5]:  # Limit to first 5 for brevity
        print(f"  • {mod['repository']}")
        print(f"    Ref: {mod['ref']}")
        print(f"    Path: {mod['path']}")
        print(f"    Variables: {len(mod.get('variables', []))}")
        print(f"    Outputs: {len(mod.get('outputs', []))}")
        print()

    # Example 4: Search for modules using a specific provider
    print("\nExample 4: Search for modules using AWS provider")
    print("-" * 80)
    aws_modules = service.search_modules(query="", provider="aws")
    print(f"Found {len(aws_modules)} modules using AWS provider")

    # Example 5: Search within specific repository
    print("\n\nExample 5: Search within a specific repository")
    print("-" * 80)
    if repos:
        repo_url = repos[0]["url"]
        print(f"Searching in: {repo_url}\n")
        modules = service.search_modules(query="", repo_urls=[repo_url])
        print(f"Found {len(modules)} modules in this repository:")
        for mod in modules:
            print(f"  • {mod['ref']}: {mod.get('description', 'No description')[:60]}")

    # Example 6: Combined search - security-related AWS modules
    print("\n\nExample 6: Find security-related AWS modules")
    print("-" * 80)
    security_modules = service.search_modules(query="security", provider="aws")
    print(f"Found {len(security_modules)} security-related AWS modules:")
    for mod in security_modules[:3]:
        print(f"\n  • {mod['repository']}")
        print(f"    Description: {mod.get('description', 'N/A')[:70]}...")
        print(
            f"    Variables: {', '.join([v['name'] for v in mod.get('variables', [])[:3]])}"
        )

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
