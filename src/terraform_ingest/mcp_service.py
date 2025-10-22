"""FastMCP service for exposing ingested Terraform modules to AI agents."""

import json
import os
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastmcp import FastMCP

from terraform_ingest.models import TerraformModuleSummary, IngestConfig
from terraform_ingest.ingest import TerraformIngest

# Initialize FastMCP server
mcp = FastMCP("terraform-ingest")


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
                with open(json_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                    summaries.append(summary)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        return summaries

    def list_repositories(
        self, 
        filter_keyword: Optional[str] = None, 
        limit: int = 50
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
                r for r in result
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

    @staticmethod
    def _extract_repo_name(url: str) -> str:
        """Extract repository name from URL."""
        name = url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name


# Global service instance
_service: Optional[ModuleQueryService] = None


def get_service(output_dir: str = "./output") -> ModuleQueryService:
    """Get or create the module query service instance."""
    global _service
    if _service is None:
        _service = ModuleQueryService(output_dir)
    return _service


@mcp.tool()
def list_repositories(
    filter: Optional[str] = None,
    limit: int = 50,
    output_dir: str = "./output"
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
    output_dir: str = "./output"
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
    
    return service.search_modules(
        query=query,
        repo_urls=repo_urls,
        provider=provider
    )


# Testable wrapper functions (not decorated with @mcp.tool())
def _list_repositories_impl(
    filter: Optional[str] = None,
    limit: int = 50,
    output_dir: str = "./output"
) -> List[Dict[str, Any]]:
    """Implementation of list_repositories for testing."""
    service = ModuleQueryService(output_dir)
    limit = min(limit, 100)
    return service.list_repositories(filter_keyword=filter, limit=limit)


def _search_modules_impl(
    query: str,
    repo_urls: Optional[List[str]] = None,
    provider: Optional[str] = None,
    output_dir: str = "./output"
) -> List[Dict[str, Any]]:
    """Implementation of search_modules for testing."""
    service = ModuleQueryService(output_dir)
    return service.search_modules(
        query=query,
        repo_urls=repo_urls,
        provider=provider
    )


def _load_config_file(config_file: str = "config.yaml") -> Optional[IngestConfig]:
    """Load configuration file if it exists."""
    config_path = Path(config_file)
    if not config_path.exists():
        print(f"Config file {config_file} not found, skipping auto-ingestion")
        return None
    
    try:
        ingester = TerraformIngest.from_yaml(str(config_path))
        return ingester.config
    except Exception as e:
        print(f"Error loading config file {config_file}: {e}")
        return None


def _run_ingestion(config_file: str = "config.yaml"):
    """Run ingestion process from configuration file."""
    try:
        print(f"Starting auto-ingestion from {config_file}...")
        ingester = TerraformIngest.from_yaml(config_file)
        summaries = ingester.ingest()
        print(f"Auto-ingestion completed: {len(summaries)} modules processed")
    except Exception as e:
        print(f"Error during auto-ingestion: {e}")


def _start_periodic_ingestion(config: IngestConfig):
    """Start periodic ingestion in a background thread."""
    if not config.mcp or not config.mcp.refresh_interval_hours:
        return
    
    def periodic_runner():
        interval_seconds = config.mcp.refresh_interval_hours * 3600
        while True:
            time.sleep(interval_seconds)
            print(f"Running scheduled ingestion (every {config.mcp.refresh_interval_hours}h)")
            _run_ingestion(config.mcp.config_file)
    
    thread = threading.Thread(target=periodic_runner, daemon=True)
    thread.start()
    print(f"Started periodic ingestion thread (every {config.mcp.refresh_interval_hours}h)")


def main():
    """Run the FastMCP server."""
    # Check for MCP configuration and auto-ingestion
    config_file = os.getenv("TERRAFORM_INGEST_CONFIG", "config.yaml")
    config = _load_config_file(config_file)
    
    if config and config.mcp:
        mcp_config = config.mcp
        
        # Run ingestion on startup if enabled
        if mcp_config.auto_ingest and mcp_config.ingest_on_startup:
            print("MCP auto-ingestion enabled, running initial ingestion...")
            _run_ingestion(mcp_config.config_file)
        
        # Start periodic ingestion if configured
        if mcp_config.auto_ingest and mcp_config.refresh_interval_hours:
            _start_periodic_ingestion(config)
    else:
        print("No MCP configuration found or auto-ingestion disabled")
    
    print("Starting FastMCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
