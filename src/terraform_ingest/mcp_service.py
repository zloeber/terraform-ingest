"""FastMCP service for exposing ingested Terraform modules to AI agents."""

import json
import os
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP

from terraform_ingest.models import IngestConfig
from terraform_ingest.ingest import TerraformIngest

# Initialize FastMCP server with default instructions
# These will be updated when the config is loaded
mcp = FastMCP(
    name="terraform-ingest",
    instructions="Service for querying ingested Terraform modules from Git repositories.",
)


class ModuleQueryService:
    """Service for querying ingested Terraform module data."""

    def __init__(self, output_dir: str = "./output"):
        """Initialize the query service.

        Args:
            output_dir: Directory containing ingested JSON summaries
        """
        self.output_dir = Path(output_dir)

    def _load_all_summaries(self) -> List[Dict[str, Any]]:
        """Load all module summaries from the output directory."""
        summaries = []

        if not self.output_dir.exists():
            return summaries

        for json_file in self.output_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    summary = json.load(f)
                    summaries.append(summary)
            except Exception as e:
                _log(f"Error loading {json_file}: {e}")

        return summaries

    def list_repositories(
        self, filter_keyword: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List all accessible Git repositories containing Terraform modules.

        Args:
            filter_keyword: Optional keyword to filter by repo name or description
            limit: Maximum number of repositories to return (default: 50)

        Returns:
            List of repository metadata dictionaries
        """
        summaries = self._load_all_summaries()

        # Group by repository URL
        repos: Dict[str, Dict[str, Any]] = {}

        for summary in summaries:
            repo_url = summary.get("repository", "")

            if repo_url not in repos:
                repos[repo_url] = {
                    "url": repo_url,
                    "name": self._extract_repo_name(repo_url),
                    "description": summary.get("description", ""),
                    "refs": [],
                    "module_count": 0,
                    "providers": set(),
                }

            # Add ref information
            ref = summary.get("ref", "")
            if ref not in repos[repo_url]["refs"]:
                repos[repo_url]["refs"].append(ref)

            repos[repo_url]["module_count"] += 1

            # Collect providers
            for provider in summary.get("providers", []):
                provider_name = provider.get("name", "")
                if provider_name:
                    repos[repo_url]["providers"].add(provider_name)

        # Convert sets to lists for JSON serialization
        result = []
        for repo_data in repos.values():
            repo_data["providers"] = list(repo_data["providers"])
            result.append(repo_data)

        # Apply filter if provided
        if filter_keyword:
            keyword_lower = filter_keyword.lower()
            result = [
                r
                for r in result
                if keyword_lower in r["name"].lower()
                or keyword_lower in r["description"].lower()
                or keyword_lower in r["url"].lower()
            ]

        # Apply limit
        result = result[:limit]

        return result

    def search_modules(
        self,
        query: str,
        repo_urls: Optional[List[str]] = None,
        provider: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for Terraform modules across repositories.

        Args:
            query: Search term (e.g., "aws_vpc" or "provider:aws")
            repo_urls: Optional list of Git repo URLs to search; defaults to all
            provider: Optional filter by target provider (e.g., "hashicorp/aws" or "aws")

        Returns:
            List of matching module summaries
        """
        summaries = self._load_all_summaries()
        results = []

        query_lower = query.lower()

        for summary in summaries:
            # Filter by repository URLs if specified
            if repo_urls and summary.get("repository") not in repo_urls:
                continue

            # Filter by provider if specified
            if provider:
                provider_lower = provider.lower()
                module_providers = summary.get("providers", [])
                provider_match = False

                for p in module_providers:
                    p_name = p.get("name", "").lower()
                    p_source = p.get("source", "").lower()
                    if provider_lower in p_name or provider_lower in p_source:
                        provider_match = True
                        break

                if not provider_match:
                    continue

            # Search in various fields
            search_fields = [
                summary.get("description", ""),
                summary.get("repository", ""),
                summary.get("path", ""),
                summary.get("readme_content", ""),
            ]

            # Add variable names and descriptions
            for var in summary.get("variables", []):
                search_fields.append(var.get("name", ""))
                search_fields.append(var.get("description", ""))

            # Add output names and descriptions
            for out in summary.get("outputs", []):
                search_fields.append(out.get("name", ""))
                search_fields.append(out.get("description", ""))

            # Add provider names
            for prov in summary.get("providers", []):
                search_fields.append(prov.get("name", ""))
                search_fields.append(prov.get("source", ""))

            # Check if query matches any field
            if any(query_lower in str(field).lower() for field in search_fields):
                results.append(summary)

        return results

    def get_module(
        self,
        repository: str,
        ref: str,
        path: str = ".",
    ) -> Optional[Dict[str, Any]]:
        """Retrieve full details for a specific Terraform module.

        Args:
            repository: Git repository URL
            ref: Branch or tag name
            path: Path within the repository (default: "." for root)

        Returns:
            Complete module summary dictionary, or None if not found
        """
        summaries = self._load_all_summaries()

        for summary in summaries:
            if (
                summary.get("repository") == repository
                and summary.get("ref") == ref
                and summary.get("path") == path
            ):
                return summary

        return None

    @staticmethod
    def _extract_repo_name(url: str) -> str:
        """Extract repository name from URL."""
        name = url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name

    def list_modules(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all ingested Terraform modules with their basic information.

        Args:
            limit: Maximum number of modules to return (default: 100)

        Returns:
            List of module metadata including repository, ref, path, and resource count
        """
        summaries = self._load_all_summaries()
        result = []

        for summary in summaries:
            module_info = {
                "repository": summary.get("repository", ""),
                "ref": summary.get("ref", ""),
                "path": summary.get("path", "."),
                "description": summary.get("description", ""),
                "resource_count": len(summary.get("resources", [])),
                "variable_count": len(summary.get("variables", [])),
                "output_count": len(summary.get("outputs", [])),
                "provider_count": len(summary.get("providers", [])),
                "module_count": len(summary.get("modules", [])),
            }
            result.append(module_info)

        return result[:limit]

    def list_module_resources(
        self, repository: str, ref: str, path: str = "."
    ) -> List[Dict[str, Any]]:
        """List all resources for a specific Terraform module.

        Args:
            repository: Git repository URL
            ref: Branch or tag name
            path: Path within the repository (default: "." for root)

        Returns:
            List of resources with type and name
        """
        module = self.get_module(repository, ref, path)
        if not module:
            return []

        resources = module.get("resources", [])
        return [
            {"type": r.get("type", ""), "name": r.get("name", "")} for r in resources
        ]

    @staticmethod
    def _generate_module_uri(repository: str, ref: str, path: str = ".") -> str:
        """Generate a URI for a module resource.

        Args:
            repository: Git repository URL
            ref: Branch or tag name
            path: Path within the repository

        Returns:
            URI string for the module resource
        """
        # Encode path separators for use in URI
        safe_path = path.replace("/", "-").replace(".", "-")
        safe_ref = ref.replace("/", "-").replace(".", "-")
        safe_repo = (
            repository.rstrip("/").split("/")[-1].replace(".git", "").replace("/", "-")
        )

        return f"module://{safe_repo}/{safe_ref}/{safe_path}".rstrip("/")

    def get_module_document(self, repository: str, ref: str, path: str = ".") -> str:
        """Get full module documentation as formatted text.

        Args:
            repository: Git repository URL
            ref: Branch or tag name
            path: Path within the repository (default: "." for root)

        Returns:
            Formatted module documentation string
        """
        module = self.get_module(repository, ref, path)
        if not module:
            return f"Module not found: {repository} @ {ref} ({path})"

        lines = []

        # Header
        lines.append(f"# Terraform Module: {self._extract_repo_name(repository)}")
        lines.append(f"\n**Repository:** {repository}")
        lines.append(f"**Ref:** {ref}")
        lines.append(f"**Path:** {path}\n")

        # Description
        if module.get("description"):
            lines.append(f"## Description\n{module.get('description')}\n")

        # Resources
        resources = module.get("resources", [])
        if resources:
            lines.append("## Resources\n")
            for resource in resources:
                lines.append(f"- **{resource.get('type')}** - `{resource.get('name')}`")
            lines.append("")

        # Providers
        providers = module.get("providers", [])
        if providers:
            lines.append("## Providers\n")
            for provider in providers:
                version_info = ""
                if provider.get("version"):
                    version_info = f" (v{provider.get('version')})"
                lines.append(
                    f"- **{provider.get('name')}**: {provider.get('source', 'N/A')}{version_info}"
                )
            lines.append("")

        # Variables
        variables = module.get("variables", [])
        if variables:
            lines.append("## Input Variables\n")
            for var in variables:
                required_str = "**Required**" if var.get("required") else "Optional"
                lines.append(f"### {var.get('name')} ({required_str})")
                lines.append(f"Type: `{var.get('type', 'N/A')}`")
                if var.get("description"):
                    lines.append(f"Description: {var.get('description')}")
                if var.get("default") is not None:
                    lines.append(f"Default: `{var.get('default')}`")
                lines.append("")

        # Outputs
        outputs = module.get("outputs", [])
        if outputs:
            lines.append("## Outputs\n")
            for output in outputs:
                lines.append(f"### {output.get('name')}")
                if output.get("description"):
                    lines.append(f"Description: {output.get('description')}")
                if output.get("sensitive"):
                    lines.append("Sensitive: Yes")
                lines.append("")

        # Modules
        modules = module.get("modules", [])
        if modules:
            lines.append("## Child Modules\n")
            for mod in modules:
                lines.append(f"- **{mod.get('name')}**: {mod.get('source')}")
                if mod.get("version"):
                    lines.append(f"  Version: {mod.get('version')}")
            lines.append("")

        # README
        if module.get("readme_content"):
            lines.append("## README\n")
            lines.append(module.get("readme_content"))

        return "\n".join(lines)

    def list_module_resource_uris(self) -> List[Dict[str, Any]]:
        """List all module resources with their URIs.

        Returns:
            List of dicts with module info and URI
        """
        summaries = self._load_all_summaries()
        result = []

        for summary in summaries:
            uri = self._generate_module_uri(
                summary.get("repository", ""),
                summary.get("ref", ""),
                summary.get("path", "."),
            )
            result.append(
                {
                    "uri": uri,
                    "repository": summary.get("repository", ""),
                    "ref": summary.get("ref", ""),
                    "path": summary.get("path", "."),
                    "name": f"{self._extract_repo_name(summary.get('repository', ''))} - {summary.get('ref')}",
                    "description": summary.get("description", ""),
                }
            )

        return result


# Global service instance
_service: Optional[ModuleQueryService] = None

# Global context for MCP server
_ingester: Optional[TerraformIngest] = None
_config: Optional[IngestConfig] = None
_vector_db_enabled: bool = False
_stdio_mode: bool = False  # Flag to suppress output in stdio mode


def _log(message: str) -> None:
    """Print message only if not in stdio mode.

    Args:
        message: Message to print
    """
    global _stdio_mode
    if not _stdio_mode:
        print(message)


def set_mcp_context(
    ingester: TerraformIngest,
    config: IngestConfig,
    vector_db_enabled: bool,
    stdio_mode: bool = False,
) -> None:
    """Set the global MCP context with server configuration.

    Args:
        ingester: Configured TerraformIngest instance
        config: Loaded configuration
        vector_db_enabled: Whether vector database is enabled
        stdio_mode: Whether running in stdio mode (suppresses output)
    """
    global _ingester, _config, _vector_db_enabled, _stdio_mode
    _ingester = ingester
    _config = config
    _vector_db_enabled = vector_db_enabled
    _stdio_mode = stdio_mode

    # Conditionally register the search_modules_vector tool
    if vector_db_enabled:
        # Register the tool if not already registered
        try:
            mcp.register_tool(search_modules_vector)
            _log("Vector database enabled - search_modules_vector tool registered")
        except Exception as e:
            # Tool might already be registered, which is fine
            _log(
                f"Vector database enabled - search_modules_vector tool (already registered or skipped: {e})"
            )
    else:
        _log("Vector database disabled - search_modules_vector tool not registered")


def get_service(output_dir: str = "./output") -> ModuleQueryService:
    """Get or create the module query service instance."""
    global _service
    if _service is None:
        _service = ModuleQueryService(output_dir)
    return _service


@mcp.tool()
def list_repositories(
    filter: Optional[str] = None, limit: int = 50, output_dir: str = "./output"
) -> List[Dict[str, Any]]:
    """Lists all accessible Git repositories containing Terraform modules.

    This tool discovers where Terraform modules live by scanning the ingested
    module summaries and providing basic metadata about each repository.

    Args:
        filter: Optional keyword to filter by repo name or description
        limit: Maximum number of repositories to return (default: 50, max: 100)
        output_dir: Directory containing ingested JSON summaries (default: ./output)

    Returns:
        List of repository metadata including:
        - url: Repository URL
        - name: Repository name
        - description: Module description
        - refs: List of branches/tags analyzed
        - module_count: Number of module versions
        - providers: List of Terraform providers used
    """
    service = get_service(output_dir)

    # Cap limit at 100
    limit = min(limit, 100)

    return service.list_repositories(filter_keyword=filter, limit=limit)


@mcp.tool()
def search_modules(
    query: str,
    repo_urls: Optional[List[str]] = None,
    provider: Optional[str] = None,
    output_dir: str = "./output",
) -> List[Dict[str, Any]]:
    """Searches for Terraform modules across Git repositories.

    This tool allows searching for modules by name, provider, or keywords found
    in README files or HCL configuration. It's useful for discovering relevant
    modules for specific use cases.

    Args:
        query: Search term (e.g., "aws_vpc", "network", "security group")
        repo_urls: Optional list of Git repo URLs to search; defaults to all accessible repos
        provider: Optional filter by target provider (e.g., "hashicorp/aws", "aws", "azurerm")
        output_dir: Directory containing ingested JSON summaries (default: ./output)

    Returns:
        List of matching module summaries with full details including:
        - repository: Git repository URL
        - ref: Branch or tag name
        - path: Path within repository
        - description: Module description
        - variables: Input variables
        - outputs: Output values
        - providers: Required Terraform providers
        - modules: Sub-modules used
        - readme_content: README file content
    """
    service = get_service(output_dir)

    return service.search_modules(query=query, repo_urls=repo_urls, provider=provider)


@mcp.tool()
def get_module_details(
    repository: str,
    ref: str,
    path: str = ".",
    output_dir: str = "./output",
) -> Optional[Dict[str, Any]]:
    """Retrieves full details for a specific ingested Terraform module.

    This tool returns the complete module summary including all variables,
    outputs, providers, sub-modules, and README content for a specific module
    version. Useful when you know the exact module you want and need all its details.

    Args:
        repository: Git repository URL (e.g., "https://github.com/terraform-aws-modules/terraform-aws-vpc")
        ref: Branch or tag name (e.g., "main", "v5.0.0")
        path: Path within the repository where the module is located (default: "." for root)
        output_dir: Directory containing ingested JSON summaries (default: ./output)

    Returns:
        Complete module summary dictionary including:
        - repository: Git repository URL
        - ref: Branch or tag name
        - path: Path within repository
        - description: Module description
        - variables: List of input variables with type, default, and description
        - outputs: List of outputs with description and sensitive flag
        - providers: List of required Terraform providers with versions
        - modules: List of sub-modules used
        - readme_content: Full README file content
        Or None if the module is not found.
    """
    service = get_service(output_dir)
    return service.get_module(repository=repository, ref=ref, path=path)


@mcp.tool()
def list_modules(
    limit: int = 100, output_dir: str = "./output"
) -> List[Dict[str, Any]]:
    """Lists all ingested Terraform modules with their metadata.

    This tool provides an overview of all available modules including their
    location, the number of resources, variables, outputs, providers, and
    sub-modules they contain. Useful for discovering what modules are available.

    Args:
        limit: Maximum number of modules to return (default: 100, max: 500)
        output_dir: Directory containing ingested JSON summaries (default: ./output)

    Returns:
        List of module metadata including:
        - repository: Git repository URL
        - ref: Branch or tag name
        - path: Path within repository
        - description: Module description
        - resource_count: Number of resources defined
        - variable_count: Number of input variables
        - output_count: Number of outputs
        - provider_count: Number of required providers
        - module_count: Number of sub-modules
    """
    service = get_service(output_dir)
    # Cap limit at 500
    limit = min(limit, 500)
    return service.list_modules(limit=limit)


@mcp.tool()
def list_module_resources(
    repository: str,
    ref: str,
    path: str = ".",
    output_dir: str = "./output",
) -> List[Dict[str, Any]]:
    """Lists all Terraform resources defined in a specific module.

    This tool shows all the AWS, Azure, GCP, and other resources that a
    Terraform module creates or manages. Each resource is identified by its
    type (e.g., aws_vpc, aws_security_group) and name.

    Args:
        repository: Git repository URL (e.g., "https://github.com/terraform-aws-modules/terraform-aws-vpc")
        ref: Branch or tag name (e.g., "main", "v5.0.0")
        path: Path within the repository where the module is located (default: "." for root)
        output_dir: Directory containing ingested JSON summaries (default: ./output)

    Returns:
        List of resources with:
        - type: Resource type (e.g., "aws_vpc", "aws_security_group")
        - name: Resource name as defined in the module
    """
    service = get_service(output_dir)
    return service.list_module_resources(repository=repository, ref=ref, path=path)


@mcp.tool()
def search_modules_vector(
    query: str,
    provider: Optional[str] = None,
    repository: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Searches for Terraform modules using semantic vector search.

    This tool uses vector embeddings to find semantically similar modules based
    on natural language queries. It's more powerful than keyword search for
    understanding user intent.

    Args:
        query: Natural language search query (e.g., "module for creating VPCs in AWS")
        provider: Optional filter by provider (e.g., "aws", "azurerm", "google")
        repository: Optional filter by repository URL
        limit: Maximum number of results to return (default: 10)

    Returns:
        List of matching modules with relevance scores including:
        - id: Unique document ID
        - metadata: Module metadata (repository, ref, path, provider, tags, last_updated)
        - document: Embedded text content
        - distance: Similarity score (lower is better)
    """
    global _ingester

    try:
        # Use the ingester from the running context
        if not _ingester or not _ingester.vector_db:
            return [
                {
                    "error": "Vector database is not enabled",
                    "message": "Enable it by setting 'embedding.enabled: true' in your config file",
                }
            ]

        # Prepare filters
        filters = {}
        if provider:
            filters["provider"] = provider
        if repository:
            filters["repository"] = repository

        # Search
        results = _ingester.search_vector_db(
            query, filters=filters if filters else None, n_results=limit
        )

        return results

    except Exception as e:
        return [{"error": str(e), "message": "Failed to search vector database"}]


@mcp.tool()
def list_module_resource_uris(output_dir: str = "./output") -> List[Dict[str, Any]]:
    """Lists all ingested modules with their MCP resource URIs.

    This tool provides a mapping of all available modules to their resource URIs,
    which can be used to access full module documentation as MCP resources.
    Each module is assigned a unique URI that can be read to get complete module
    information including variables, outputs, providers, resources, and README.

    Args:
        output_dir: Directory containing ingested JSON summaries (default: ./output)

    Returns:
        List of modules with:
        - uri: MCP resource URI for the module (e.g., "module://terraform-aws-vpc/v5.0.0")
        - repository: Git repository URL
        - ref: Branch or tag name
        - path: Path within repository
        - name: Friendly name for the module
        - description: Short description of the module
    """
    service = get_service(output_dir)
    return service.list_module_resource_uris()


# Resource endpoints for full module documentation


@mcp.resource("module://{repository}/{ref}/{path}")
def get_module_resource(repository: str, ref: str, path: str = "-") -> str:
    """Get full Terraform module documentation as a resource.

    This resource provides comprehensive module information including description,
    all resources it creates, providers required, input variables with descriptions,
    outputs, child modules, and the full README content.

    The path parameter uses hyphens instead of slashes in the URI (e.g., "-" for ".",
    "modules-aws" for "modules/aws"). Use list_module_resource_uris to get valid URIs.

    Args:
        repository: Module repository name from the resource URI
        ref: Module ref (branch/tag) from the resource URI
        path: Module path from the resource URI (hyphens will be converted to slashes)

    Returns:
        Full module documentation as formatted text
    """
    service = get_service()

    # Decode path: hyphens back to slashes
    decoded_path = path.replace("-", "/")
    if decoded_path == "/":
        decoded_path = "."

    # Try to reconstruct the repository URL
    # The repository name in the URI is just the basename, so we need to search for matching modules
    summaries = service._load_all_summaries()
    for summary in summaries:
        summary_ref = summary.get("ref")
        summary_path = summary.get("path", ".")
        summary_repo = summary.get("repository", "")

        # Check if this summary matches our criteria
        ref_matches = summary_ref == ref
        path_matches = (decoded_path == "." and summary_path == ".") or (
            decoded_path != "." and decoded_path in summary_path
        )
        repo_matches = repository in summary_repo

        if ref_matches and path_matches and repo_matches:
            return service.get_module_document(summary_repo, ref, summary_path)

    return f"Module not found: {repository} @ {ref} ({decoded_path})"


# Testable wrapper functions (not decorated with @mcp.tool())
def _list_repositories_impl(
    filter: Optional[str] = None, limit: int = 50, output_dir: str = "./output"
) -> List[Dict[str, Any]]:
    """Implementation of list_repositories for testing."""
    service = ModuleQueryService(output_dir)
    limit = min(limit, 100)
    return service.list_repositories(filter_keyword=filter, limit=limit)


def _search_modules_impl(
    query: str,
    repo_urls: Optional[List[str]] = None,
    provider: Optional[str] = None,
    output_dir: str = "./output",
) -> List[Dict[str, Any]]:
    """Implementation of search_modules for testing."""
    service = ModuleQueryService(output_dir)
    return service.search_modules(query=query, repo_urls=repo_urls, provider=provider)


def _get_module_details_impl(
    repository: str,
    ref: str,
    path: str = ".",
    output_dir: str = "./output",
) -> Optional[Dict[str, Any]]:
    """Implementation of get_module_details for testing."""
    service = ModuleQueryService(output_dir)
    return service.get_module(repository=repository, ref=ref, path=path)


def _list_modules_impl(
    limit: int = 100, output_dir: str = "./output"
) -> List[Dict[str, Any]]:
    """Implementation of list_modules for testing."""
    service = ModuleQueryService(output_dir)
    limit = min(limit, 500)
    return service.list_modules(limit=limit)


def _list_module_resources_impl(
    repository: str,
    ref: str,
    path: str = ".",
    output_dir: str = "./output",
) -> List[Dict[str, Any]]:
    """Implementation of list_module_resources for testing."""
    service = ModuleQueryService(output_dir)
    return service.list_module_resources(repository=repository, ref=ref, path=path)


def _list_module_resource_uris_impl(
    output_dir: str = "./output",
) -> List[Dict[str, Any]]:
    """Implementation of list_module_resource_uris for testing."""
    service = ModuleQueryService(output_dir)
    return service.list_module_resource_uris()


def _get_module_resource_impl(repository: str, ref: str, path: str = "-") -> str:
    """Implementation of get_module_resource for testing."""
    service = get_service()

    # Decode path: hyphens back to slashes
    decoded_path = path.replace("-", "/")
    if decoded_path == "/":
        decoded_path = "."

    # Try to reconstruct the repository URL
    # The repository name in the URI is just the basename, so we need to search for matching modules
    summaries = service._load_all_summaries()
    for summary in summaries:
        if (
            summary.get("ref") == ref
            and (
                decoded_path == "."
                and summary.get("path") == "."
                or decoded_path in summary.get("path", "")
            )
            and repository in summary.get("repository", "")
        ):
            full_repo_url = summary.get("repository", "")
            full_path = summary.get("path", ".")
            return service.get_module_document(full_repo_url, ref, full_path)

    return f"Module not found: {repository} @ {ref} ({decoded_path})"


def _load_config_file(config_file: str = "config.yaml") -> Optional[IngestConfig]:
    """Load configuration file if it exists."""
    config_path = Path(config_file)
    if not config_path.exists():
        _log(f"Config file {config_file} not found, skipping auto-ingestion")
        return None

    try:
        ingester = TerraformIngest.from_yaml(str(config_path))
        return ingester.config
    except Exception as e:
        _log(f"Error loading config file {config_file}: {e}")
        return None


def _update_mcp_instructions(config: Optional[IngestConfig]):
    """Update FastMCP server instructions from configuration.

    Args:
        config: Loaded IngestConfig, or None to use default instructions
    """
    global mcp

    if config and config.mcp and config.mcp.instructions:
        mcp.instructions = config.mcp.instructions
    else:
        mcp.instructions = (
            "Service for querying ingested Terraform modules from Git repositories."
        )


def _run_ingestion(config_file: str = "config.yaml", silent: bool = False):
    """Run ingestion process from configuration file."""
    try:
        if not silent:
            _log(f"Starting auto-ingestion from {config_file}...")
        ingester = TerraformIngest.from_yaml(config_file)
        summaries = ingester.ingest(silent=silent)
        if not silent:
            _log(f"Auto-ingestion completed: {len(summaries)} modules processed")
    except Exception as e:
        _log(f"Error during auto-ingestion: {e}")


def _start_periodic_ingestion(
    config: IngestConfig, config_file: str, silent: bool = False
):
    """Start periodic ingestion in a background thread."""
    if not config.mcp or not config.mcp.refresh_interval_hours:
        return

    def periodic_runner():
        interval_seconds = config.mcp.refresh_interval_hours * 3600
        while True:
            time.sleep(interval_seconds)
            if not silent:
                _log(
                    f"Running scheduled ingestion (every {config.mcp.refresh_interval_hours}h)"
                )
            _run_ingestion(config_file, silent=silent)

    thread = threading.Thread(target=periodic_runner, daemon=True)
    thread.start()
    if not silent:
        _log(
            f"Started periodic ingestion thread (every {config.mcp.refresh_interval_hours}h)"
        )


def start(
    config_file: str = None,
    transport: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    ingest_on_startup: Optional[bool] = None,
):
    """Run the FastMCP server.

    Args:
        config_file: Path to the configuration file (default: TERRAFORM_INGEST_CONFIG env var or "config.yaml")
        transport: Transport mode (stdio, http-streamable, sse) - overrides config
        host: Host to bind to (for http-streamable and sse) - overrides config
        port: Port to bind to (for http-streamable and sse) - overrides config
        ingest_on_startup: Run ingestion on startup - overrides config
    """
    # Check for MCP configuration and auto-ingestion
    if config_file is None:
        config_file = os.getenv("TERRAFORM_INGEST_CONFIG", "config.yaml")

    config = _load_config_file(config_file)

    # Update MCP instructions from configuration
    _update_mcp_instructions(config)

    # Determine transport settings (CLI args override config)
    mcp_config = config.mcp if config and config.mcp else None
    transport_mode = (
        transport if transport else (mcp_config.transport if mcp_config else "stdio")
    )
    stdio_mode = transport_mode == "stdio"

    # Initialize the TerraformIngest instance and set MCP context
    ingester = TerraformIngest.from_yaml(config_file)
    vector_db_enabled = (config and config.embedding and config.embedding.enabled) or (
        ingester.vector_db is not None
    )
    set_mcp_context(ingester, config, vector_db_enabled, stdio_mode=stdio_mode)

    bind_host = host if host else (mcp_config.host if mcp_config else "127.0.0.1")
    bind_port = port if port else (mcp_config.port if mcp_config else 3000)

    if transport_mode != "stdio":
        _log(f"Transport: {transport_mode}")
        _log(f"Listening on {bind_host}:{bind_port}")

    # Determine ingest_on_startup setting (CLI args override config)
    should_ingest_on_startup = (
        ingest_on_startup
        if ingest_on_startup is not None
        else (mcp_config.ingest_on_startup if mcp_config else False)
    )

    # Run ingestion on startup if enabled
    if should_ingest_on_startup:
        _log("Running ingestion on startup...")
        _run_ingestion(config_file, silent=stdio_mode)

    # Start periodic ingestion if configured
    if mcp_config and mcp_config.auto_ingest and mcp_config.refresh_interval_hours:
        _start_periodic_ingestion(config, config_file, silent=stdio_mode)

    # Run with appropriate transport
    if transport_mode == "stdio":
        mcp.run()
    elif transport_mode == "http-streamable":
        mcp.run(transport="http-streamable", bind_address=(bind_host, bind_port))
    elif transport_mode == "sse":
        mcp.run(transport="sse", bind_address=(bind_host, bind_port))
    else:
        raise ValueError(f"Unknown transport mode: {transport_mode}")


def main():
    """Run the FastMCP server."""
    # Check for MCP configuration and auto-ingestion
    config_file = os.getenv("TERRAFORM_INGEST_CONFIG", "config.yaml")
    config = _load_config_file(config_file)

    # Update MCP instructions from configuration
    _update_mcp_instructions(config)

    # Initialize the TerraformIngest instance and set MCP context
    ingester = TerraformIngest.from_yaml(config_file)
    vector_db_enabled = (config and config.embedding and config.embedding.enabled) or (
        ingester.vector_db is not None
    )

    # Determine transport from config or defaults
    mcp_config = config.mcp if config and config.mcp else None
    transport_mode = mcp_config.transport if mcp_config else "stdio"
    stdio_mode = transport_mode == "stdio"

    set_mcp_context(ingester, config, vector_db_enabled, stdio_mode=stdio_mode)

    bind_host = mcp_config.host if mcp_config else "127.0.0.1"
    bind_port = mcp_config.port if mcp_config else 3000

    if mcp_config:
        # Run ingestion on startup if enabled
        if mcp_config.ingest_on_startup:
            _log("MCP auto-ingestion enabled, running initial ingestion...")
            _run_ingestion(config_file, silent=stdio_mode)

        # Start periodic ingestion if configured
        if mcp_config.auto_ingest and mcp_config.refresh_interval_hours:
            _start_periodic_ingestion(config, config_file, silent=stdio_mode)

    if transport_mode != "stdio":
        _log(f"Listening on {bind_host}:{bind_port}")

    # Run with appropriate transport
    if transport_mode == "stdio":
        mcp.run()
    elif transport_mode == "http-streamable":
        mcp.run(transport="http-streamable", bind_address=(bind_host, bind_port))
    elif transport_mode == "sse":
        mcp.run(transport="sse", bind_address=(bind_host, bind_port))
    else:
        raise ValueError(f"Unknown transport mode: {transport_mode}")


if __name__ == "__main__":
    main()
