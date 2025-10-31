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
from terraform_ingest.tty_logger import setup_tty_logger

logger = setup_tty_logger()

# Initialize FastMCP server with default instructions
# These will be updated when the config is loaded
mcp = FastMCP(
    name="terraform-ingest",
    instructions="Service for querying ingested Terraform modules from Git repositories.",
)


class MCPContext:
    """Singleton context for MCP server configuration and state.

    This class encapsulates all global state needed by the MCP server,
    providing a clean API without polluting the global namespace with
    individual variables.
    """

    _instance: Optional["MCPContext"] = None

    def __init__(
        self,
        ingester: Optional[TerraformIngest] = None,
        config: Optional[IngestConfig] = None,
        vector_db_enabled: bool = False,
        stdio_mode: bool = False,
    ):
        """Initialize the MCP context.

        Args:
            ingester: TerraformIngest instance for module operations
            config: IngestConfig instance with server configuration
            vector_db_enabled: Whether vector database functionality is enabled
            stdio_mode: Whether running in stdio mode (for output suppression)
        """
        self.ingester = ingester
        self.config = config
        self.vector_db_enabled = vector_db_enabled
        self.stdio_mode = stdio_mode

    @classmethod
    def get_instance(cls) -> "MCPContext":
        """Get or create the singleton instance.

        Returns:
            MCPContext singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set(
        cls,
        ingester: TerraformIngest,
        config: IngestConfig,
        vector_db_enabled: bool,
        stdio_mode: bool = False,
    ) -> None:
        """Set or reinitialize the context with new values.

        Args:
            ingester: TerraformIngest instance for module operations
            config: IngestConfig instance with server configuration
            vector_db_enabled: Whether vector database functionality is enabled
            stdio_mode: Whether running in stdio mode
        """
        cls._instance = cls(ingester, config, vector_db_enabled, stdio_mode)


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
                logger.error(f"Error loading {json_file}: {e}")

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
        include_readme: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve full details for a specific Terraform module.

        Args:
            repository: Git repository URL
            ref: Branch or tag name
            path: Path within the repository (default: "." for root)
            include_readme: Whether to include the readme_content in the response (default: False)

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
                # Remove readme_content if not requested
                if not include_readme and "readme_content" in summary:
                    summary_copy = summary.copy()
                    del summary_copy["readme_content"]
                    return summary_copy
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
        safe_path = path.replace("/", "-")
        safe_ref = ref.replace("/", "-")
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

    def list_module_versions(
        self, repository: str, path: str = "."
    ) -> List[Dict[str, Any]]:
        """Find all module versions for a target repository and path.

        Args:
            repository: Git repository URL
            path: Path within the repository (default: "." for root)

        Returns:
            List of module versions with:
            - ref: Branch or tag name
            - module_name: Name extracted from repository
            - index_id: Unique identifier for the module version (URI)
            - description: Module description
            - variables_count: Number of input variables
            - outputs_count: Number of outputs
            - resources_count: Number of resources
        """
        summaries = self._load_all_summaries()
        result = []

        for summary in summaries:
            # Match by repository and path
            if summary.get("repository") == repository and summary.get("path") == path:
                module_uri = self._generate_module_uri(
                    repository,
                    summary.get("ref", ""),
                    path,
                )
                result.append(
                    {
                        "ref": summary.get("ref", ""),
                        "module_name": self._extract_repo_name(repository),
                        "index_id": module_uri,
                        "description": summary.get("description", ""),
                        "variables_count": len(summary.get("variables", [])),
                        "outputs_count": len(summary.get("outputs", [])),
                        "resources_count": len(summary.get("resources", [])),
                    }
                )

        return result


# Global service instance for lazy initialization
_service: Optional[ModuleQueryService] = None


def set_mcp_context(
    ingester: TerraformIngest,
    config: IngestConfig,
    vector_db_enabled: bool,
    stdio_mode: bool = False,
) -> None:
    """Set the MCP context with server configuration.

    This function delegates to MCPContext singleton for state management
    and initializes custom prompt overrides from the configuration.

    Args:
        ingester: Configured TerraformIngest instance
        config: Loaded configuration
        vector_db_enabled: Whether vector database is enabled
        stdio_mode: Whether running in stdio mode (suppresses output)
    """
    global _service

    MCPContext.set(ingester, config, vector_db_enabled, stdio_mode)

    # Initialize the service with the output_dir from configuration
    output_dir = config.output_dir if config else "./output"
    _service = ModuleQueryService(output_dir)

    # Initialize custom prompts from configuration if available
    if config and config.mcp and config.mcp.prompts:
        set_custom_prompts(config.mcp.prompts)
        logger.info(
            f"Loaded {len(config.mcp.prompts)} custom prompt overrides from configuration"
        )

    # Log vector database status
    if vector_db_enabled:
        logger.info("Vector database enabled - search_modules_vector tool available")
    else:
        logger.info(
            "Vector database disabled - search_modules_vector will return error"
        )


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
    path: str,
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
def list_module_versions(
    repository: str,
    path: str = ".",
    output_dir: str = "./output",
) -> List[Dict[str, Any]]:
    """Finds all module versions for a target repository and path.

    This tool returns all available versions (branches/tags) of a specific module
    in a repository, including metadata about each version. Useful for understanding
    what versions of a module are available and selecting the right one.

    Args:
        repository: Git repository URL (e.g., "https://github.com/terraform-aws-modules/terraform-aws-vpc")
        path: Path within the repository where the module is located (default: "." for root)
        output_dir: Directory containing ingested JSON summaries (default: ./output)

    Returns:
        List of module versions with:
        - ref: Branch or tag name
        - module_name: Name extracted from repository
        - index_id: Unique identifier for the module version (URI for lookup)
        - description: Module description
        - variables_count: Number of input variables
        - outputs_count: Number of outputs
        - resources_count: Number of resources
    """
    service = get_service(output_dir)
    return service.list_module_versions(repository=repository, path=path)


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
    try:
        # Get the ingester from the MCP context
        ctx = MCPContext.get_instance()
        if not ctx.ingester or not ctx.ingester.vector_db:
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
        results = ctx.ingester.search_vector_db(
            query, filters=filters if filters else None, n_results=limit
        )

        return results

    except Exception as e:
        return [{"error": str(e), "message": "Failed to search vector database"}]


@mcp.tool()
def get_module_by_index_id(
    doc_id: str, output_dir: str = "./output"
) -> Optional[Dict[str, Any]]:
    """Retrieves full module information by its index document ID.

    This tool looks up module information using the document ID returned from
    vector search results. It returns the complete module summary including
    variables, outputs, providers, and README content.

    Args:
        doc_id: Document ID (SHA256 hash from vector search or index)
        output_dir: Directory containing module JSON files (default: ./output)

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
    try:
        from terraform_ingest.indexer import ModuleIndexer

        indexer = ModuleIndexer(output_dir)

        # Check if module exists in index
        module_entry = indexer.get_module(doc_id)
        if not module_entry:
            return {
                "error": f"Module with ID '{doc_id}' not found in index",
                "doc_id": doc_id,
            }

        # Get the path to the summary file
        summary_path = indexer.get_module_summary_path(doc_id)
        if not summary_path or not summary_path.exists():
            return {
                "error": f"Module summary file not found at {summary_path}",
                "doc_id": doc_id,
            }

        # Load and return the full module summary
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        return summary

    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON in module summary file",
            "doc_id": doc_id,
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve module: {str(e)}",
            "doc_id": doc_id,
        }


# @mcp.tool()
# def list_module_resource_uris(output_dir: str = "./output") -> List[Dict[str, Any]]:
#     """Lists all ingested modules with their MCP resource URIs.

#     This tool provides a mapping of all available modules to their resource URIs,
#     which can be used to access full module documentation as MCP resources.
#     Each module is assigned a unique URI that can be read to get complete module
#     information including variables, outputs, providers, resources, and README.

#     Args:
#         output_dir: Directory containing ingested JSON summaries (default: ./output)

#     Returns:
#         List of modules with:
#         - uri: MCP resource URI for the module (e.g., "module://terraform-aws-vpc/v5.0.0")
#         - repository: Git repository URL
#         - ref: Branch or tag name
#         - path: Path within repository
#         - name: Friendly name for the module
#         - description: Short description of the module
#     """
#     service = get_service(output_dir)
#     return service.list_module_resource_uris()


# Resource endpoints for full module documentation


@mcp.resource("module://{repository}/{ref}/{path}")
def get_module_resource(repository: str, ref: str, path: str = "-") -> str:
    """Get full Terraform module documentation as a resource.

    This resource provides comprehensive module information including description,
    all resources it creates, providers required, input variables with descriptions,
    outputs, child modules, and the full README content.

    The resource URI uses hyphens as path separators for compatibility with the URI
    specification (e.g., "-" for ".", "modules-aws" for "modules/aws").

    Module resources support dynamic lookup - provide repository name (or partial match),
    ref (branch/tag), and path to retrieve any ingested module's complete documentation.

    Args:
        repository: Module repository name (can be partial, will match against full URL)
        ref: Module ref (branch/tag name)
        path: Module path (hyphen-encoded, e.g., "-" for root, "modules-aws" for modules/aws)

    Returns:
        Full module documentation as formatted text with all metadata
    """
    return _get_module_resource_impl(repository, ref, path)


def list_module_resources_for_discovery() -> List[Dict[str, Any]]:
    """List all available module resources for MCP discovery.

    This function provides the resource listing that enables clients to discover
    available module resources before accessing them.

    Returns:
        List of available module resources with URI, name, and description
    """
    service = get_service()
    resources = []

    for module_info in service.list_module_resource_uris():
        uri = module_info.get("uri", "")
        name = module_info.get("name", "")
        description = module_info.get("description", "")
        repository = module_info.get("repository", "")
        ref = module_info.get("ref", "")
        path = module_info.get("path", ".")

        resources.append(
            {
                "uri": uri,
                "name": name,
                "title": f"{name} - {path}",
                "description": description
                or f"Terraform module from {repository} @ {ref}",
                "mimeType": "text/markdown",
            }
        )

    return resources


def get_argument_completions_for_resources(
    argument_name: str, argument_value: Optional[str] = None
) -> List[str]:
    """Get argument completion suggestions for module resource URIs.

    This function supports argument completion for the dynamic resource template,
    allowing clients to discover valid values for repository, ref, and path parameters.

    Args:
        argument_name: Name of the argument being completed (repository, ref, or path)
        argument_value: Current value the user is typing (optional)

    Returns:
        List of matching completion suggestions
    """
    service = get_service()
    summaries = service._load_all_summaries()

    # Handle None or empty argument_value
    search_value = (argument_value or "").lower()

    if argument_name == "repository":
        # Suggest repository names (basename from URL)
        repos = set()
        for summary in summaries:
            repo_url = summary.get("repository", "")
            if repo_url:
                # Extract basename and remove .git suffix
                repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
                if search_value in repo_name.lower():
                    repos.add(repo_name)
        return sorted(list(repos))

    elif argument_name == "ref":
        # Suggest ref names (branches/tags)
        refs = set()
        for summary in summaries:
            ref = summary.get("ref", "")
            if ref and search_value in ref.lower():
                refs.add(ref)
        return sorted(list(refs))

    elif argument_name == "path":
        # Suggest paths
        paths = set()
        for summary in summaries:
            path = summary.get("path", ".")
            # Encode path for URI (replace / with -)
            encoded_path = path.replace("/", "-").replace(".", "-")
            if search_value in encoded_path.lower():
                paths.add(encoded_path)
        return sorted(list(paths))

    return []


# Prompt customization support
# Store custom prompt overrides from configuration
_custom_prompts: Dict[str, str] = {}


def set_custom_prompts(prompts: Optional[Dict[str, str]]) -> None:
    """Set custom prompt overrides from configuration.

    This allows the configuration file to override default prompt content
    for terraform_best_practices, security_checklist, and generate_module_docs.

    Args:
        prompts: Dict mapping prompt names to custom content strings
    """
    global _custom_prompts
    _custom_prompts = prompts or {}


def get_custom_prompt(name: str) -> Optional[str]:
    """Get a custom prompt override if it exists.

    Args:
        name: Name of the prompt (e.g., "terraform_best_practices", "security_checklist")

    Returns:
        Custom prompt content if defined, None otherwise
    """
    return _custom_prompts.get(name)


# Internal implementations for testable prompt functions
def _terraform_best_practices_impl(module_type: str = "general") -> str:
    """Generate a prompt with Terraform best practices.

    This is the internal implementation that can be overridden via custom prompts.

    Args:
        module_type: Type of module (general, networking, compute, storage, security)

    Returns:
        Best practices prompt for the specified module type
    """
    # Check for custom override
    custom = get_custom_prompt("terraform_best_practices")
    if custom:
        return custom

    base_practices = """
Follow these Terraform best practices when generating infrastructure code:

1. Code Organization & Structure
   - Use meaningful variable names and descriptions
   - Keep modules focused on single responsibilities
   - Define all variables with types
   - Always provide descriptions for variables and outputs

2. Version Management
   - Always specify versions for providers and modules
   - Use version constraints appropriately (>= for stability, ~> for minor updates)
   - Use local module sources for internal modules
   - Document version compatibility requirements

3. Documentation
   - Document all outputs with descriptions
   - Include README files with usage examples
   - Add comments for complex logic
   - Maintain a changelog for module updates

4. Configuration Best Practices
   - Use data sources instead of hardcoding values
   - Implement appropriate tagging strategy
   - Surface all variable assignments in terraform.tfvars files
   - Use sensitive variables for credentials and secrets
   - Never hardcode credentials or secrets
"""

    module_specific = {
        "networking": """
5. Networking-Specific
   - Use VPCs for network isolation
   - Implement proper security groups and NACLs
   - Use private subnets for sensitive resources
   - Implement VPC endpoints where appropriate
   - Document network topology
""",
        "compute": """
5. Compute-Specific
   - Use auto-scaling groups for availability
   - Implement health checks
   - Use latest stable AMIs
   - Tag resources for cost tracking
   - Set appropriate timeout values
""",
        "storage": """
5. Storage-Specific
   - Enable encryption for data at rest
   - Enable versioning for important buckets
   - Implement lifecycle policies
   - Use appropriate storage classes
   - Document backup strategies
""",
        "security": """
5. Security-Specific
   - Implement least privilege access
   - Use IAM roles instead of access keys
   - Enable audit logging
   - Implement network segmentation
   - Regular security assessments
""",
    }

    return base_practices + module_specific.get(module_type.lower(), "")


def _security_checklist_impl() -> list:
    """Generate a comprehensive security review checklist prompt.

    This is the internal implementation that can be overridden via custom prompts.

    Returns:
        List of messages that guide users through a security review
    """
    from mcp.server.fastmcp.prompts.base import UserMessage

    # Check for custom override
    custom = get_custom_prompt("security_checklist")
    if custom:
        return [UserMessage(custom)]

    return [
        UserMessage(
            """
Please review the following Terraform configuration for security compliance.

Use this checklist:

ACCESS CONTROL:
- [ ] IAM roles follow least privilege principle
- [ ] Root account not used for daily operations
- [ ] MFA enabled for sensitive operations
- [ ] Service accounts have minimal required permissions
- [ ] Cross-account access properly scoped

ENCRYPTION:
- [ ] Data at rest encrypted with appropriate KMS keys
- [ ] Data in transit uses TLS/SSL (version >= 1.2)
- [ ] Secrets stored in secrets manager, not configs
- [ ] Encryption keys properly rotated
- [ ] Database encryption enabled

LOGGING & MONITORING:
- [ ] CloudTrail enabled for API auditing
- [ ] Application logs centralized and retained
- [ ] Alerts configured for suspicious activity
- [ ] VPC Flow Logs enabled
- [ ] CloudWatch monitoring for key metrics

NETWORK SECURITY:
- [ ] Security groups restrict inbound traffic
- [ ] Network ACLs properly configured
- [ ] Private subnets used for sensitive resources
- [ ] VPC endpoints implemented
- [ ] Network segmentation implemented

COMPLIANCE & GOVERNANCE:
- [ ] Resource tagging strategy implemented
- [ ] Change management documented
- [ ] Incident response plan in place
- [ ] Regular backups configured
- [ ] Disaster recovery tested

Provide feedback on any findings and recommendations for remediation.
"""
        )
    ]


def _generate_module_docs_impl(module_name: str = "", module_purpose: str = "") -> str:
    """Generate documentation structure for a Terraform module.

    This is the internal implementation that can be overridden via custom prompts.

    Args:
        module_name: Name of the module
        module_purpose: The purpose/function of the module

    Returns:
        Template for module documentation
    """
    # Check for custom override
    custom = get_custom_prompt("generate_module_docs")
    if custom:
        return custom

    return f"""
Generate comprehensive documentation for the Terraform module: {module_name}

Purpose: {module_purpose}

Create documentation with the following sections:

## Overview
- Description of what the module does
- Use cases and scenarios
- Key benefits

## Requirements
- Terraform version requirements
- Provider requirements and versions
- External dependencies

## Module Structure
- Directory layout explanation
- Key files and their purposes
- Input and output interfaces

## Inputs (Variables)
- List all input variables
- Document type, default, and constraints
- Provide examples

## Outputs
- List all outputs
- Explain what each output represents
- Show example usage

## Usage Example
- Provide a minimal working example
- Show how to call the module
- Document variable input

## Advanced Usage
- Advanced configuration options
- Integration patterns
- Performance tuning

## Troubleshooting
- Common issues and solutions
- Debug approaches
- Support information

## Contributing
- How to contribute improvements
- Testing requirements
- Release process

## License
- License information
- Copyright notice
"""


# Prompts for AI agents
@mcp.prompt(title="Find Terraform Module")
def find_terraform_module_prompt(keywords: str, provider: str) -> str:
    """Generate a prompt to help find a Terraform module.
    This prompt guides users in searching for relevant Terraform modules
    based on their requirements.

    Args:
        keywords: Keywords describing the desired Terraform module
        provider: Cloud provider for the Terraform module

    Returns:
        Prompt string for finding Terraform modules
    """
    return f"""Use the search_modules_vector tool to find the top 5 Terraform modules related to the following query: {keywords}
for the {provider} provider. Use the get_module_by_index_id tool to retrieve detailed information about each module found.
Summarize the key features of each module and determine which, if any, best fits the requirements for the given keywords and provider.
Return the module repository URL, ref, path, variable details, and a brief summary of why it is a good fit.
"""


@mcp.prompt(title="Update Module")
def update_terraform_module_prompt(url: str, ref: str, path: str) -> str:
    """Generate a prompt to help find updates for a Terraform module.
    This prompt guides users on checking for newer versions or updates
    to an existing Terraform module and assessing the impact of those updates.
    Args:
        url: Git repository URL of the Terraform module
        ref: Branch or tag name of the Terraform module
    Returns:
        Prompt string for finding Terraform module updates and assessing impact
    """
    return f"""Use the list_module_versions tool to retrieve all available versions of the Terraform module located at {url} in path {path}.
Compare the current version {ref} with the latest available version.
Use the get_module_resource resource template for the current module version and the latest version found to fetch details of both.
Analyze the differences in variables, outputs, and resources between the two versions.
Provide a summary of the changes, potential impacts on existing infrastructure,
and recommendations for upgrading to the latest version. Use this information to guide 
the update process for your target module block to the latest version.
"""


@mcp.prompt(title="Terraform Best Practices")
def terraform_best_practices(
    module_type: str = "general",
) -> str:
    """Generate a prompt with Terraform best practices.

    This prompt provides standardized best practices for creating and
    maintaining Terraform infrastructure code. Can be overridden via
    mcp.prompts.terraform_best_practices in the configuration file.

    Args:
        module_type: Type of module (general, networking, compute, storage, security)

    Returns:
        Best practices prompt for the specified module type
    """
    return _terraform_best_practices_impl(module_type)


@mcp.prompt(title="Security Review Checklist")
def security_checklist() -> list:
    """Generate a comprehensive security review checklist prompt.

    Can be overridden via mcp.prompts.security_checklist in the configuration file.

    Returns a list of messages that guide users through a security review
    of their Terraform configurations.
    """
    return _security_checklist_impl()


@mcp.prompt(title="Module Documentation Generator")
def generate_module_docs(
    module_name: str = "",
    module_purpose: str = "",
) -> str:
    """Generate documentation structure for a Terraform module.

    Can be overridden via mcp.prompts.generate_module_docs in the configuration file.

    This prompt helps create comprehensive documentation for modules.

    Args:
        module_name: Name of the module
        module_purpose: The purpose/function of the module

    Returns:
        Template for module documentation
    """
    return _generate_module_docs_impl(module_name, module_purpose)


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

    # Decode path: hyphens back to slashes, then to underscores for filename
    decoded_path = path.replace("-", "/")

    # Reconstruct the filename from the parts
    # Filename format: {repository}_{ref}_{path}.json
    # For root path (.), the filename is: {repository}_{ref}_src.json
    if decoded_path == "/" or decoded_path == ".":
        filename = f"{repository}_{ref}.json"
    else:
        # Replace slashes with underscores in path for filename
        safe_path = decoded_path.replace("/", "_")
        filename = f"{repository}_{ref}_{safe_path}.json"

    # Read the JSON file directly
    json_file = service.output_dir / filename

    if not json_file.exists():
        return f"Module not found: {repository} @ {ref} ({decoded_path})"

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            module_data = json.load(f)
            # Return as JSON string
            return json.dumps(module_data, indent=2, default=str)
    except Exception as e:
        return f"Error reading module resource: {e}"


def _load_config_file(config_file: str = "config.yaml") -> Optional[IngestConfig]:
    """Load configuration file if it exists."""
    config_path = Path(config_file)
    if not config_path.exists():
        logger.warning(f"Config file {config_file} not found, skipping auto-ingestion")
        return None

    try:
        ingester = TerraformIngest.from_yaml(str(config_path))
        return ingester.config
    except Exception as e:
        logger.error(f"Error loading config file {config_file}: {e}")
        return None


def _update_mcp_instructions(config: Optional[IngestConfig]):
    """Update FastMCP server instructions from configuration.

    Args:
        config: Loaded IngestConfig, or None to use default instructions
    """
    if config and config.mcp and config.mcp.instructions:
        mcp.instructions = config.mcp.instructions
    else:
        mcp.instructions = (
            "Service for querying ingested Terraform modules from Git repositories."
        )


def _run_ingestion(config_file: str = "config.yaml"):
    """Run ingestion process from configuration file."""
    try:
        logger.info(f"Starting auto-ingestion from {config_file}...")
        ingester = TerraformIngest.from_yaml(config_file, logger=logger)
        summaries = ingester.ingest()
        logger.info(f"Auto-ingestion completed: {len(summaries)} modules processed")
    except Exception as e:
        logger.error(f"Error during auto-ingestion: {e}")


def _start_periodic_ingestion(config: IngestConfig, config_file: str):
    """Start periodic ingestion in a background thread."""
    if not config.mcp or not config.mcp.refresh_interval_hours:
        return

    def periodic_runner():
        interval_seconds = config.mcp.refresh_interval_hours * 3600
        while True:
            time.sleep(interval_seconds)
            logger.info(
                f"Running scheduled ingestion (every {config.mcp.refresh_interval_hours}h)"
            )
            _run_ingestion(config_file)

    thread = threading.Thread(target=periodic_runner, daemon=True)
    thread.start()
    logger.info(
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
        transport: Transport mode (stdio, streamable-http, sse) - overrides config
        host: Host to bind to (for streamable-http and sse) - overrides config
        port: Port to bind to (for streamable-http and sse) - overrides config
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
    ingester = TerraformIngest.from_yaml(config_file, logger=logger)
    vector_db_enabled = (config and config.embedding and config.embedding.enabled) or (
        ingester.vector_db is not None
    )
    set_mcp_context(ingester, config, vector_db_enabled, stdio_mode=stdio_mode)

    bind_host = host if host else (mcp_config.host if mcp_config else "127.0.0.1")
    bind_port = port if port else (mcp_config.port if mcp_config else 3000)
    logger.info(f"Transport: {transport_mode}")

    if transport_mode != "stdio":
        logger.info(f"Listening on {bind_host}:{bind_port}")

    # Determine ingest_on_startup setting (CLI args override config)
    should_ingest_on_startup = (
        ingest_on_startup
        if ingest_on_startup is not None
        else (mcp_config.ingest_on_startup if mcp_config else False)
    )

    # Run ingestion on startup if enabled
    if should_ingest_on_startup:
        logger.info("Running ingestion on startup...")
        _run_ingestion(config_file)

    # Start periodic ingestion if configured
    if mcp_config and mcp_config.auto_ingest and mcp_config.refresh_interval_hours:
        _start_periodic_ingestion(config, config_file)

    # Run with appropriate transport
    if transport_mode == "stdio":
        mcp.run()
    elif transport_mode == "streamable-http":
        mcp.run(transport="streamable-http", host=bind_host, port=bind_port)
    elif transport_mode == "sse":
        mcp.run(transport="sse", host=bind_host, port=bind_port)
    else:
        raise ValueError(f"Unknown transport mode: {transport_mode}")


def main():
    """Run the FastMCP server."""
    # Check for MCP configuration and auto-ingestion
    config_file = os.getenv("TERRAFORM_INGEST_CONFIG", "config.yaml")
    config = _load_config_file(config_file)

    # Determine transport mode early so we can suppress logs in stdio mode
    mcp_config = config.mcp if config and config.mcp else None
    transport_mode = mcp_config.transport if mcp_config else "stdio"
    stdio_mode = transport_mode == "stdio"

    # Initialize MCPContext early with stdio_mode
    MCPContext.set(
        ingester=None,  # type: ignore
        config=config,
        vector_db_enabled=False,
        stdio_mode=stdio_mode,
    )

    # Update MCP instructions from configuration
    _update_mcp_instructions(config)

    # Initialize the TerraformIngest instance and set MCP context
    ingester = TerraformIngest.from_yaml(config_file, logger=logger)
    vector_db_enabled = (config and config.embedding and config.embedding.enabled) or (
        ingester.vector_db is not None
    )

    set_mcp_context(ingester, config, vector_db_enabled, stdio_mode=stdio_mode)

    bind_host = mcp_config.host if mcp_config else "127.0.0.1"
    bind_port = mcp_config.port if mcp_config else 3000

    if mcp_config:
        # Run ingestion on startup if enabled
        if mcp_config.ingest_on_startup:
            logger.info("MCP auto-ingestion enabled, running initial ingestion...")
            _run_ingestion(config_file)

        # Start periodic ingestion if configured
        if mcp_config.auto_ingest and mcp_config.refresh_interval_hours:
            _start_periodic_ingestion(config, config_file)

    if transport_mode != "stdio":
        logger.info(f"Listening on {bind_host}:{bind_port}")

    # Run with appropriate transport
    if transport_mode == "stdio":
        mcp.run()
    elif transport_mode == "streamable-http":
        mcp.run(transport="streamable-http", bind_address=(bind_host, bind_port))
    elif transport_mode == "sse":
        mcp.run(transport="sse", bind_address=(bind_host, bind_port))
    else:
        raise ValueError(f"Unknown transport mode: {transport_mode}")


if __name__ == "__main__":
    main()
