"""FastAPI service endpoint for terraform-ingest."""

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tempfile
import yaml

from .models import (
    IngestConfig,
    RepositoryConfig,
    TerraformModuleSummary,
)
from terraform_ingest.ingest import TerraformIngest


app = FastAPI(
    title="Terraform Ingest API",
    description="A terraform multi-repo module AI RAG ingestion engine API",
    version="0.1.0",
)


class IngestRequest(BaseModel):
    """Request model for ingestion."""

    repositories: List[RepositoryConfig]
    output_dir: Optional[str] = None
    clone_dir: Optional[str] = None


class IngestResponse(BaseModel):
    """Response model for ingestion."""

    summaries: List[TerraformModuleSummary]
    count: int
    message: str


class AnalyzeRequest(BaseModel):
    """Request model for analyzing a single repository."""

    repository_url: str
    branches: List[str] = ["main"]
    include_tags: bool = False
    max_tags: Optional[int] = 10
    path: str = "."


class VectorSearchRequest(BaseModel):
    """Request model for vector search."""

    query: str
    provider: Optional[str] = None
    repository: Optional[str] = None
    limit: int = 10
    config_file: str = "config.yaml"


class VectorSearchResponse(BaseModel):
    """Response model for vector search."""

    results: List[dict]
    count: int
    query: str


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Terraform Ingest API",
        "version": "0.1.0",
        "description": "A terraform multi-repo module AI RAG ingestion engine",
        "endpoints": {
            "POST /ingest": "Ingest multiple repositories from configuration",
            "POST /analyze": "Analyze a single repository",
            "POST /search/vector": "Search modules using vector embeddings",
            "GET /health": "Health check endpoint",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_repositories(request: IngestRequest, auto_install_deps: bool = True):
    """Ingest multiple terraform repositories.

    This endpoint accepts a list of repository configurations and processes
    them to generate JSON summaries suitable for RAG ingestion.

    Args:
        request: IngestRequest containing repository configurations
        auto_install_deps: Whether to automatically install missing dependencies

    Returns:
        IngestResponse with summaries and metadata
    """
    try:
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = request.output_dir or f"{temp_dir}/output"
            clone_dir = request.clone_dir or f"{temp_dir}/repos"

            config = IngestConfig(
                repositories=request.repositories,
                output_dir=output_dir,
                clone_dir=clone_dir,
            )

            ingester = TerraformIngest(config, auto_install_deps=auto_install_deps)
            summaries = ingester.ingest()

            return IngestResponse(
                summaries=summaries,
                count=len(summaries),
                message=f"Successfully ingested {len(summaries)} module(s)",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=IngestResponse)
async def analyze_repository(request: AnalyzeRequest, auto_install_deps: bool = True):
    """Analyze a single terraform repository.

    This endpoint accepts a repository URL and configuration, then analyzes
    the terraform module and returns summaries for the specified branches/tags.

    Args:
        request: AnalyzeRequest with repository URL and configuration
        auto_install_deps: Whether to automatically install missing dependencies

    Returns:
        IngestResponse with summaries and metadata
    """
    try:
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_config = RepositoryConfig(
                url=request.repository_url,
                branches=request.branches,
                include_tags=request.include_tags,
                max_tags=request.max_tags,
                path=request.path,
            )

            config = IngestConfig(
                repositories=[repo_config],
                output_dir=f"{temp_dir}/output",
                clone_dir=f"{temp_dir}/repos",
            )

            ingester = TerraformIngest(config, auto_install_deps=auto_install_deps)
            summaries = ingester.ingest()

            return IngestResponse(
                summaries=summaries,
                count=len(summaries),
                message=f"Successfully analyzed {len(summaries)} version(s)",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest-from-yaml")
async def ingest_from_yaml(yaml_content: str, auto_install_deps: bool = True):
    """Ingest repositories from a YAML configuration string.

    This endpoint accepts a YAML configuration as a string and processes
    the repositories defined in it.

    Args:
        yaml_content: YAML configuration as a string
        auto_install_deps: Whether to automatically install missing dependencies

    Returns:
        IngestResponse with summaries and metadata
    """
    try:
        # Parse YAML
        config_dict = yaml.safe_load(yaml_content)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Override directories to use temp
            if "output_dir" not in config_dict:
                config_dict["output_dir"] = f"{temp_dir}/output"
            if "clone_dir" not in config_dict:
                config_dict["clone_dir"] = f"{temp_dir}/repos"

            config = IngestConfig(**config_dict)
            ingester = TerraformIngest(config, auto_install_deps=auto_install_deps)
            summaries = ingester.ingest()

            return IngestResponse(
                summaries=summaries,
                count=len(summaries),
                message=f"Successfully ingested {len(summaries)} module(s) from YAML",
            )

    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/vector", response_model=VectorSearchResponse)
async def search_vector(request: VectorSearchRequest):
    """Search for Terraform modules using vector embeddings.

    This endpoint uses semantic search to find modules based on natural
    language queries. Vector database must be enabled in the configuration.

    Args:
        request: VectorSearchRequest with query and filters

    Returns:
        VectorSearchResponse with matching modules and relevance scores
    """
    try:
        # Load config to get vector DB settings
        ingester = TerraformIngest.from_yaml(request.config_file)

        if not ingester.vector_db:
            raise HTTPException(
                status_code=400,
                detail="Vector database is not enabled. Set 'embedding.enabled: true' in config.",
            )

        # Prepare filters
        filters = {}
        if request.provider:
            filters["provider"] = request.provider
        if request.repository:
            filters["repository"] = request.repository

        # Search
        results = ingester.search_vector_db(
            request.query, filters=filters if filters else None, n_results=request.limit
        )

        return VectorSearchResponse(
            results=results, count=len(results), query=request.query
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
