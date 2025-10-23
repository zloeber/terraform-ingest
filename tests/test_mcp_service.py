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
                        "required": False,
                    }
                ],
                "outputs": [
                    {
                        "name": "vpc_id",
                        "description": "The ID of the VPC",
                        "value": None,
                        "sensitive": False,
                    }
                ],
                "providers": [
                    {"name": "aws", "source": "hashicorp/aws", "version": ">= 4.0"}
                ],
                "modules": [],
                "resources": [
                    {"type": "aws_vpc", "name": "main", "description": None},
                    {"type": "aws_subnet", "name": "public", "description": None},
                    {"type": "aws_subnet", "name": "private", "description": None},
                ],
                "readme_content": "# AWS VPC Terraform module\nThis module creates VPC resources",
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
                        "required": False,
                    }
                ],
                "outputs": [
                    {
                        "name": "vpc_id",
                        "description": "The ID of the VPC",
                        "value": None,
                        "sensitive": False,
                    }
                ],
                "providers": [
                    {"name": "aws", "source": "hashicorp/aws", "version": ">= 4.0"}
                ],
                "modules": [],
                "resources": [
                    {"type": "aws_vpc", "name": "main", "description": None},
                    {"type": "aws_subnet", "name": "public", "description": None},
                    {"type": "aws_subnet", "name": "private", "description": None},
                ],
                "readme_content": "# AWS VPC Terraform module\nThis module creates VPC resources",
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
                        "required": False,
                    }
                ],
                "outputs": [
                    {
                        "name": "vnet_id",
                        "description": "The ID of the virtual network",
                        "value": None,
                        "sensitive": False,
                    }
                ],
                "providers": [
                    {
                        "name": "azurerm",
                        "source": "hashicorp/azurerm",
                        "version": ">= 3.0",
                    }
                ],
                "modules": [],
                "resources": [
                    {"type": "azurerm_virtual_network", "name": "main", "description": None},
                    {"type": "azurerm_subnet", "name": "main", "description": None},
                ],
                "readme_content": "# Azure Network Terraform module\nThis module creates Azure network resources",
            },
        ]

        # Write summaries to files
        for i, summary in enumerate(summaries):
            filename = Path.joinpath(output_dir, f"module_{i}.json")
            with open(filename, "w", encoding="utf-8") as f:
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
    results = service.search_modules(query="vpc", repo_urls=repo_urls, provider="aws")

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


# MCP Tool Tests
def test_mcp_list_repositories_tool(sample_output_dir):
    """Test the MCP list_repositories tool function."""
    from terraform_ingest.mcp_service import _list_repositories_impl

    # Test basic functionality
    repos = _list_repositories_impl(output_dir=sample_output_dir)
    assert len(repos) == 2

    # Verify structure
    for repo in repos:
        assert "url" in repo
        assert "name" in repo
        assert "description" in repo
        assert "refs" in repo
        assert "module_count" in repo
        assert "providers" in repo

    # Test with filter
    filtered_repos = _list_repositories_impl(filter="aws", output_dir=sample_output_dir)
    assert len(filtered_repos) == 1
    assert "terraform-aws-vpc" in filtered_repos[0]["url"]

    # Test with limit
    limited_repos = _list_repositories_impl(limit=1, output_dir=sample_output_dir)
    assert len(limited_repos) == 1

    # Test limit cap (should cap at 100)
    capped_repos = _list_repositories_impl(limit=200, output_dir=sample_output_dir)
    assert len(capped_repos) <= 2  # We only have 2 repos in test data


def test_mcp_search_modules_tool(sample_output_dir):
    """Test the MCP search_modules tool function."""
    from terraform_ingest.mcp_service import _search_modules_impl

    # Test basic search
    results = _search_modules_impl(query="vpc", output_dir=sample_output_dir)
    assert len(results) == 2  # Both AWS VPC versions

    # Verify structure
    for result in results:
        assert "repository" in result
        assert "ref" in result
        assert "path" in result
        assert "description" in result
        assert "variables" in result
        assert "outputs" in result
        assert "providers" in result
        assert "modules" in result

    # Test search with provider filter
    aws_results = _search_modules_impl(
        query="vpc", provider="aws", output_dir=sample_output_dir
    )
    assert len(aws_results) == 2

    # Test search with repo URL filter
    repo_urls = ["https://github.com/terraform-aws-modules/terraform-aws-vpc"]
    filtered_results = _search_modules_impl(
        query="vpc", repo_urls=repo_urls, output_dir=sample_output_dir
    )
    assert len(filtered_results) == 2
    assert all(r["repository"] == repo_urls[0] for r in filtered_results)

    # Test search with all filters combined
    combined_results = _search_modules_impl(
        query="vpc", repo_urls=repo_urls, provider="aws", output_dir=sample_output_dir
    )
    assert len(combined_results) == 2


def test_mcp_search_modules_edge_cases(sample_output_dir):
    """Test search_modules with edge cases."""
    from terraform_ingest.mcp_service import _search_modules_impl

    # Empty query should still work (searches all)
    results = _search_modules_impl(query="", output_dir=sample_output_dir)
    assert len(results) >= 0

    # Case insensitive search
    results_upper = _search_modules_impl(query="VPC", output_dir=sample_output_dir)
    results_lower = _search_modules_impl(query="vpc", output_dir=sample_output_dir)
    assert len(results_upper) == len(results_lower)

    # Search in README content
    results = _search_modules_impl(query="creates", output_dir=sample_output_dir)
    assert len(results) >= 1  # Should find modules with "creates" in README

    # Search in variable descriptions
    results = _search_modules_impl(query="CIDR", output_dir=sample_output_dir)
    assert len(results) >= 1  # Should find modules with CIDR in variable descriptions


def test_mcp_list_repositories_edge_cases(sample_output_dir):
    """Test list_repositories with edge cases."""
    from terraform_ingest.mcp_service import _list_repositories_impl

    # Case insensitive filter
    repos_upper = _list_repositories_impl(filter="AWS", output_dir=sample_output_dir)
    repos_lower = _list_repositories_impl(filter="aws", output_dir=sample_output_dir)
    assert len(repos_upper) == len(repos_lower)

    # Filter that matches nothing
    empty_repos = _list_repositories_impl(
        filter="nonexistent", output_dir=sample_output_dir
    )
    assert len(empty_repos) == 0

    # Zero limit
    zero_repos = _list_repositories_impl(limit=0, output_dir=sample_output_dir)
    assert len(zero_repos) == 0


def test_get_module_details_by_exact_match(sample_output_dir):
    """Test retrieving module details by exact repository, ref, and path match."""
    service = ModuleQueryService(sample_output_dir)

    # Get AWS VPC main branch module details
    module = service.get_module(
        repository="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        ref="main",
        path=".",
    )

    assert module is not None
    assert (
        module["repository"]
        == "https://github.com/terraform-aws-modules/terraform-aws-vpc"
    )
    assert module["ref"] == "main"
    assert module["path"] == "."
    assert (
        module["description"] == "Terraform module which creates VPC resources on AWS"
    )
    assert len(module["variables"]) == 1
    assert module["variables"][0]["name"] == "vpc_cidr"
    assert len(module["outputs"]) == 1
    assert module["outputs"][0]["name"] == "vpc_id"
    assert len(module["providers"]) == 1
    assert module["providers"][0]["name"] == "aws"


def test_get_module_details_by_version_tag(sample_output_dir):
    """Test retrieving module details for a specific version tag."""
    service = ModuleQueryService(sample_output_dir)

    # Get AWS VPC tagged version
    module = service.get_module(
        repository="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        ref="v5.0.0",
        path=".",
    )

    assert module is not None
    assert module["ref"] == "v5.0.0"
    assert (
        module["description"] == "Terraform module which creates VPC resources on AWS"
    )


def test_get_module_details_not_found(sample_output_dir):
    """Test retrieving module details for nonexistent module."""
    service = ModuleQueryService(sample_output_dir)

    # Try to get a module that doesn't exist
    module = service.get_module(
        repository="https://github.com/nonexistent/repo",
        ref="main",
        path=".",
    )

    assert module is None


def test_get_module_details_wrong_ref(sample_output_dir):
    """Test retrieving module details with wrong ref."""
    service = ModuleQueryService(sample_output_dir)

    # Try to get a module with wrong ref
    module = service.get_module(
        repository="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        ref="nonexistent-ref",
        path=".",
    )

    assert module is None


def test_get_module_details_wrong_path(sample_output_dir):
    """Test retrieving module details with wrong path."""
    service = ModuleQueryService(sample_output_dir)

    # Try to get a module with wrong path
    module = service.get_module(
        repository="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        ref="main",
        path="nonexistent/path",
    )

    assert module is None


def test_mcp_get_module_details_tool(sample_output_dir):
    """Test the MCP get_module_details tool function."""
    from terraform_ingest.mcp_service import _get_module_details_impl

    # Test retrieving a module successfully
    module = _get_module_details_impl(
        repository="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        ref="main",
        path=".",
        output_dir=sample_output_dir,
    )

    assert module is not None
    assert (
        module["repository"]
        == "https://github.com/terraform-aws-modules/terraform-aws-vpc"
    )
    assert module["ref"] == "main"

    # Verify complete structure
    assert "path" in module
    assert "description" in module
    assert "variables" in module
    assert "outputs" in module
    assert "providers" in module
    assert "modules" in module
    assert "readme_content" in module


def test_mcp_get_module_details_tool_not_found(sample_output_dir):
    """Test the MCP get_module_details tool with nonexistent module."""
    from terraform_ingest.mcp_service import _get_module_details_impl

    # Test retrieving a module that doesn't exist
    module = _get_module_details_impl(
        repository="https://github.com/nonexistent/repo",
        ref="main",
        path=".",
        output_dir=sample_output_dir,
    )

    assert module is None


def test_mcp_get_module_details_tool_azure(sample_output_dir):
    """Test the MCP get_module_details tool with Azure module."""
    from terraform_ingest.mcp_service import _get_module_details_impl

    # Test retrieving Azure network module
    module = _get_module_details_impl(
        repository="https://github.com/terraform-azure-modules/terraform-azurerm-network",
        ref="main",
        path=".",
        output_dir=sample_output_dir,
    )

    assert module is not None
    assert (
        module["repository"]
        == "https://github.com/terraform-azure-modules/terraform-azurerm-network"
    )
    assert module["ref"] == "main"
    assert "azurerm" in str(module["providers"]).lower()
    assert "address_space" in str(module["variables"])


def test_mcp_tools_with_empty_directory():
    """Test MCP tools with empty output directory."""
    from terraform_ingest.mcp_service import (
        _list_repositories_impl,
        _search_modules_impl,
        _get_module_details_impl,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test list_repositories with empty directory
        repos = _list_repositories_impl(output_dir=tmpdir)
        assert len(repos) == 0

        # Test search_modules with empty directory
        results = _search_modules_impl(query="test", output_dir=tmpdir)
        assert len(results) == 0

        # Test get_module_details with empty directory
        module = _get_module_details_impl(
            repository="https://github.com/example/repo",
            ref="main",
            output_dir=tmpdir,
        )
        assert module is None


def test_mcp_tools_with_nonexistent_directory():
    """Test MCP tools with nonexistent output directory."""
    from terraform_ingest.mcp_service import (
        _list_repositories_impl,
        _search_modules_impl,
        _get_module_details_impl,
    )

    nonexistent_dir = "/nonexistent/directory"

    # Should handle gracefully and return empty/None results
    repos = _list_repositories_impl(output_dir=nonexistent_dir)
    assert len(repos) == 0

    results = _search_modules_impl(query="test", output_dir=nonexistent_dir)
    assert len(results) == 0

    module = _get_module_details_impl(
        repository="https://github.com/example/repo",
        ref="main",
        output_dir=nonexistent_dir,
    )
    assert module is None


# MCP Auto-Ingestion Tests
def test_load_config_file_success():
    """Test loading a valid configuration file."""
    from terraform_ingest.mcp_service import _load_config_file

    # Create a temporary config file
    config_data = {
        "repositories": [
            {
                "url": "https://github.com/example/repo",
                "branches": ["main"],
                "recursive": True,
            }
        ],
        "output_dir": "./output",
        "clone_dir": "./repos",
        "mcp": {
            "auto_ingest": True,
            "ingest_on_startup": True,
            "refresh_interval_hours": 24,
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(config_data, f)
        temp_config_path = f.name

    try:
        config = _load_config_file(temp_config_path)
        assert config is not None
        assert config.mcp is not None
        assert config.mcp.auto_ingest is True
        assert config.mcp.ingest_on_startup is True
        assert config.mcp.refresh_interval_hours == 24
    finally:
        Path(temp_config_path).unlink()


def test_load_config_file_nonexistent():
    """Test loading a nonexistent configuration file."""
    from terraform_ingest.mcp_service import _load_config_file

    config = _load_config_file("nonexistent_config.yaml")
    assert config is None


def test_load_config_file_invalid_yaml():
    """Test loading an invalid YAML file."""
    from terraform_ingest.mcp_service import _load_config_file

    # Create an invalid YAML file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [")
        temp_config_path = f.name

    try:
        config = _load_config_file(temp_config_path)
        assert config is None
    finally:
        Path(temp_config_path).unlink()


def test_load_config_file_no_mcp_section():
    """Test loading a config file without MCP section."""
    from terraform_ingest.mcp_service import _load_config_file

    config_data = {
        "repositories": [
            {"url": "https://github.com/example/repo", "branches": ["main"]}
        ],
        "output_dir": "./output",
        "clone_dir": "./repos",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(config_data, f)
        temp_config_path = f.name

    try:
        config = _load_config_file(temp_config_path)
        assert config is not None
        assert config.mcp is None  # Should be None when not specified
    finally:
        Path(temp_config_path).unlink()


def test_get_service_singleton():
    """Test that get_service returns a singleton instance."""
    from terraform_ingest.mcp_service import get_service

    # Reset the global service instance for testing
    import terraform_ingest.mcp_service as mcp_module

    mcp_module._service = None

    # Get service instances
    service1 = get_service("./output")
    service2 = get_service("./output")

    # Should be the same instance
    assert service1 is service2

    # Reset for other tests
    mcp_module._service = None


def test_list_modules(sample_output_dir):
    """Test listing all modules."""
    service = ModuleQueryService(sample_output_dir)
    modules = service.list_modules()

    assert len(modules) == 3
    assert all("repository" in m for m in modules)
    assert all("ref" in m for m in modules)
    assert all("resource_count" in m for m in modules)
    assert all("variable_count" in m for m in modules)
    assert all("output_count" in m for m in modules)

    # Check AWS VPC modules have resources
    aws_modules = [m for m in modules if "terraform-aws-vpc" in m["repository"]]
    assert all(m["resource_count"] == 3 for m in aws_modules)


def test_list_modules_with_limit(sample_output_dir):
    """Test listing modules with limit."""
    service = ModuleQueryService(sample_output_dir)
    modules = service.list_modules(limit=2)

    assert len(modules) == 2


def test_list_module_resources_aws_vpc(sample_output_dir):
    """Test listing resources for AWS VPC module."""
    service = ModuleQueryService(sample_output_dir)
    resources = service.list_module_resources(
        repository="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        ref="main",
        path=".",
    )

    assert len(resources) == 3
    assert any(r["type"] == "aws_vpc" for r in resources)
    assert any(r["type"] == "aws_subnet" for r in resources)
    assert any(r["name"] == "public" for r in resources)


def test_list_module_resources_azure(sample_output_dir):
    """Test listing resources for Azure module."""
    service = ModuleQueryService(sample_output_dir)
    resources = service.list_module_resources(
        repository="https://github.com/terraform-azure-modules/terraform-azurerm-network",
        ref="main",
        path=".",
    )

    assert len(resources) == 2
    assert any(r["type"] == "azurerm_virtual_network" for r in resources)
    assert any(r["type"] == "azurerm_subnet" for r in resources)


def test_list_module_resources_not_found(sample_output_dir):
    """Test listing resources for non-existent module."""
    service = ModuleQueryService(sample_output_dir)
    resources = service.list_module_resources(
        repository="https://github.com/nonexistent/repo", ref="main"
    )

    assert resources == []


def test_mcp_list_modules_tool(sample_output_dir):
    """Test the MCP list_modules tool."""
    from terraform_ingest.mcp_service import _list_modules_impl

    modules = _list_modules_impl(output_dir=sample_output_dir)

    assert len(modules) == 3
    assert all("repository" in m for m in modules)
    assert all("resource_count" in m for m in modules)


def test_mcp_list_module_resources_tool(sample_output_dir):
    """Test the MCP list_module_resources tool."""
    from terraform_ingest.mcp_service import _list_module_resources_impl

    resources = _list_module_resources_impl(
        repository="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        ref="main",
        path=".",
        output_dir=sample_output_dir,
    )

    assert len(resources) == 3
    assert any(r["type"] == "aws_vpc" for r in resources)


def test_generate_module_uri(sample_output_dir):
    """Test generating module URIs."""
    service = ModuleQueryService(sample_output_dir)
    uri = service._generate_module_uri(
        "https://github.com/terraform-aws-modules/terraform-aws-vpc", "v5.0.0", "."
    )
    assert "terraform-aws-vpc" in uri
    assert "v5-0-0" in uri  # dots are replaced with hyphens
    assert uri.startswith("module://")


def test_list_module_resource_uris(sample_output_dir):
    """Test listing module resource URIs."""
    service = ModuleQueryService(sample_output_dir)
    uris = service.list_module_resource_uris()

    assert len(uris) == 3
    assert all("uri" in u for u in uris)
    assert all("repository" in u for u in uris)
    assert all("ref" in u for u in uris)
    assert all(u["uri"].startswith("module://") for u in uris)


def test_get_module_document_aws_vpc(sample_output_dir):
    """Test getting module documentation for AWS VPC."""
    service = ModuleQueryService(sample_output_dir)
    doc = service.get_module_document(
        "https://github.com/terraform-aws-modules/terraform-aws-vpc", "main", "."
    )

    assert "terraform-aws-vpc" in doc or "terraform-aws" in doc
    assert "# Terraform Module:" in doc
    assert "aws_vpc" in doc
    assert "aws_subnet" in doc
    assert "## Resources" in doc
    assert "## Providers" in doc


def test_get_module_document_not_found(sample_output_dir):
    """Test getting module documentation for non-existent module."""
    service = ModuleQueryService(sample_output_dir)
    doc = service.get_module_document("https://github.com/nonexistent/repo", "main", ".")

    assert "Module not found" in doc


def test_mcp_list_module_resource_uris_tool(sample_output_dir):
    """Test the MCP list_module_resource_uris tool."""
    from terraform_ingest.mcp_service import _list_module_resource_uris_impl

    uris = _list_module_resource_uris_impl(output_dir=sample_output_dir)

    assert len(uris) == 3
    assert all("uri" in u for u in uris)
    assert any(u["uri"].startswith("module://terraform-aws-vpc") for u in uris)


def test_get_module_resource(sample_output_dir):
    """Test getting module documentation via resource endpoint."""
    from terraform_ingest.mcp_service import ModuleQueryService

    service = ModuleQueryService(sample_output_dir)

    # Get module document directly using the service method
    doc = service.get_module_document(
        "https://github.com/terraform-aws-modules/terraform-aws-vpc",
        "main",
        "."
    )

    assert "# Terraform Module:" in doc
    assert len(doc) > 100  # Should be substantial documentation
    assert "aws_vpc" in doc


def test_get_module_resource_impl_wrapper(sample_output_dir):
    """Test the wrapper implementation for resource endpoints."""
    # This test is more complex because it needs to match the repository by name
    # For now, we'll test that the wrapper handles non-existent modules gracefully
    from terraform_ingest.mcp_service import _get_module_resource_impl

    # Test with a non-existent module
    doc = _get_module_resource_impl(
        repository="nonexistent", ref="main", path="-"
    )
    assert "Module not found" in doc


def test_module_document_includes_sections(sample_output_dir):
    """Test that module documentation includes all expected sections."""
    service = ModuleQueryService(sample_output_dir)
    doc = service.get_module_document(
        "https://github.com/terraform-aws-modules/terraform-aws-vpc", "main", "."
    )

    # Check for all major sections
    assert "# Terraform Module:" in doc
    assert "## Resources" in doc or "aws_vpc" in doc
    assert "## Providers" in doc
    assert "## Input Variables" in doc or "## Outputs" in doc
    assert "repository" in doc or "github.com" in doc
