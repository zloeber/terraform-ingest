"""Tests for the MCP service."""

import json
import tempfile
from pathlib import Path
import pytest

from terraform_ingest.mcp_service import ModuleQueryService


@pytest.fixture
def sample_output_dir():
    """Create a temporary directory with sample module summaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Create sample module summaries
        summaries = [
            {
                "repository": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
                "ref": "main",
                "path": ".",
                "description": "Terraform module which creates VPC resources on AWS",
                "variables": [
                    {
                        "name": "vpc_cidr",
                        "type": "string",
                        "description": "The CIDR block for the VPC",
                        "default": "10.0.0.0/16",
                        "required": False
                    }
                ],
                "outputs": [
                    {
                        "name": "vpc_id",
                        "description": "The ID of the VPC",
                        "value": None,
                        "sensitive": False
                    }
                ],
                "providers": [
                    {
                        "name": "aws",
                        "source": "hashicorp/aws",
                        "version": ">= 4.0"
                    }
                ],
                "modules": [],
                "readme_content": "# AWS VPC Terraform module\nThis module creates VPC resources"
            },
            {
                "repository": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
                "ref": "v5.0.0",
                "path": ".",
                "description": "Terraform module which creates VPC resources on AWS",
                "variables": [
                    {
                        "name": "vpc_cidr",
                        "type": "string",
                        "description": "The CIDR block for the VPC",
                        "default": "10.0.0.0/16",
                        "required": False
                    }
                ],
                "outputs": [
                    {
                        "name": "vpc_id",
                        "description": "The ID of the VPC",
                        "value": None,
                        "sensitive": False
                    }
                ],
                "providers": [
                    {
                        "name": "aws",
                        "source": "hashicorp/aws",
                        "version": ">= 4.0"
                    }
                ],
                "modules": [],
                "readme_content": "# AWS VPC Terraform module\nThis module creates VPC resources"
            },
            {
                "repository": "https://github.com/terraform-azure-modules/terraform-azurerm-network",
                "ref": "main",
                "path": ".",
                "description": "Terraform module for Azure virtual network",
                "variables": [
                    {
                        "name": "address_space",
                        "type": "list(string)",
                        "description": "The address space for the virtual network",
                        "default": ["10.0.0.0/16"],
                        "required": False
                    }
                ],
                "outputs": [
                    {
                        "name": "vnet_id",
                        "description": "The ID of the virtual network",
                        "value": None,
                        "sensitive": False
                    }
                ],
                "providers": [
                    {
                        "name": "azurerm",
                        "source": "hashicorp/azurerm",
                        "version": ">= 3.0"
                    }
                ],
                "modules": [],
                "readme_content": "# Azure Network Terraform module\nThis module creates Azure network resources"
            }
        ]
        
        # Write summaries to files
        for i, summary in enumerate(summaries):
            filename = output_dir / f"module_{i}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
        
        yield str(output_dir)


def test_list_repositories(sample_output_dir):
    """Test listing repositories."""
    service = ModuleQueryService(sample_output_dir)
    repos = service.list_repositories()
    
    assert len(repos) == 2
    
    # Check AWS VPC repo
    aws_repo = next(r for r in repos if "terraform-aws-vpc" in r["url"])
    assert aws_repo["name"] == "terraform-aws-vpc"
    assert "VPC" in aws_repo["description"]
    assert len(aws_repo["refs"]) == 2  # main and v5.0.0
    assert aws_repo["module_count"] == 2
    assert "aws" in aws_repo["providers"]


def test_list_repositories_with_filter(sample_output_dir):
    """Test listing repositories with filter."""
    service = ModuleQueryService(sample_output_dir)
    
    # Filter by AWS
    repos = service.list_repositories(filter_keyword="aws")
    assert len(repos) == 1
    assert "terraform-aws-vpc" in repos[0]["url"]
    
    # Filter by Azure
    repos = service.list_repositories(filter_keyword="azure")
    assert len(repos) == 1
    assert "terraform-azurerm-network" in repos[0]["url"]
    
    # Filter by VPC
    repos = service.list_repositories(filter_keyword="vpc")
    assert len(repos) == 1


def test_list_repositories_with_limit(sample_output_dir):
    """Test listing repositories with limit."""
    service = ModuleQueryService(sample_output_dir)
    repos = service.list_repositories(limit=1)
    
    assert len(repos) == 1


def test_search_modules_by_query(sample_output_dir):
    """Test searching modules by query."""
    service = ModuleQueryService(sample_output_dir)
    
    # Search by "VPC"
    results = service.search_modules(query="vpc")
    assert len(results) == 2  # Both AWS VPC versions
    
    # Search by "network"
    results = service.search_modules(query="network")
    assert len(results) >= 1  # Should find Azure network module
    
    # Search by variable name
    results = service.search_modules(query="vpc_cidr")
    assert len(results) == 2


def test_search_modules_by_provider(sample_output_dir):
    """Test searching modules by provider."""
    service = ModuleQueryService(sample_output_dir)
    
    # Search for AWS provider
    results = service.search_modules(query="", provider="aws")
    assert len(results) == 2
    assert all("aws" in str(r.get("providers", [])).lower() for r in results)
    
    # Search for Azure provider
    results = service.search_modules(query="", provider="azurerm")
    assert len(results) == 1
    assert "azurerm" in str(results[0].get("providers", [])).lower()


def test_search_modules_by_repo_url(sample_output_dir):
    """Test searching modules by repository URL."""
    service = ModuleQueryService(sample_output_dir)
    
    repo_urls = ["https://github.com/terraform-aws-modules/terraform-aws-vpc"]
    results = service.search_modules(query="", repo_urls=repo_urls)
    
    assert len(results) == 2  # main and v5.0.0
    assert all(r["repository"] == repo_urls[0] for r in results)


def test_search_modules_combined_filters(sample_output_dir):
    """Test searching modules with combined filters."""
    service = ModuleQueryService(sample_output_dir)
    
    # Search for AWS VPC specifically
    repo_urls = ["https://github.com/terraform-aws-modules/terraform-aws-vpc"]
    results = service.search_modules(
        query="vpc",
        repo_urls=repo_urls,
        provider="aws"
    )
    
    assert len(results) == 2
    assert all(r["repository"] == repo_urls[0] for r in results)
    assert all("aws" in str(r.get("providers", [])).lower() for r in results)


def test_empty_output_dir():
    """Test with empty output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ModuleQueryService(tmpdir)
        
        repos = service.list_repositories()
        assert len(repos) == 0
        
        results = service.search_modules(query="test")
        assert len(results) == 0


def test_extract_repo_name():
    """Test repository name extraction."""
    service = ModuleQueryService(".")
    
    assert service._extract_repo_name("https://github.com/user/repo.git") == "repo"
    assert service._extract_repo_name("https://github.com/user/repo") == "repo"
    assert service._extract_repo_name("git@github.com:user/repo.git") == "repo"
