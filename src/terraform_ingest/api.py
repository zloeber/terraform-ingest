"""FastAPI service endpoint for terraform-ingest."""

from typing import List, Optional
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel
import tempfile
import yaml

from .models import (
    IngestConfig,
    RepositoryConfig,
    TerraformModuleSummary,
)
from terraform_ingest.ingestion_runner import (
    IngestionRunOptions,
    get_ingestion_status,
    is_ingestion_active,
    run_ingestion_from_config,
    run_ingestion_from_yaml,
)


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
    cleanup: bool = False
    skip_existing: bool = False
    no_cache: bool = False


class IngestResponse(BaseModel):
    """Response model for ingestion."""

    summaries: List[TerraformModuleSummary]
    count: int
    message: str
    progress: dict


class IngestBackgroundRequest(BaseModel):
    """Request model for background ingestion from YAML config."""

    config_file: str = "config.yaml"
    cleanup: bool = False
    skip_existing: bool = False
    no_cache: bool = False


class IngestBackgroundResponse(BaseModel):
    """Response model for background ingestion requests."""

    success: bool
    message: str
    started_in_background: bool
    progress: dict
    error: Optional[str] = None


class IngestionStatusResponse(BaseModel):
    """Response model for ingestion progress polling."""

    progress: dict


class AnalyzeRequest(BaseModel):
    """Request model for analyzing a single repository."""

    repository_url: str
    branches: List[str] = ["main"]
    include_tags: bool = False
    max_tags: Optional[int] = 10
    path: str = "."
    cleanup: bool = False
    skip_existing: bool = False
    no_cache: bool = False


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


def _build_options(
    *,
    output_dir: Optional[str] = None,
    clone_dir: Optional[str] = None,
    cleanup: bool = False,
    skip_existing: bool = False,
    no_cache: bool = False,
    auto_install_deps: bool = True,
) -> IngestionRunOptions:
    """Create shared ingestion options for API handlers."""
    return IngestionRunOptions(
        auto_install_deps=auto_install_deps,
        skip_existing=skip_existing,
        cleanup=cleanup,
        no_cache=no_cache,
        notify_progress=True,
        output_dir=output_dir,
        clone_dir=clone_dir,
    )


def _result_to_response(result) -> IngestResponse:
    """Convert a shared ingestion result into an API response."""
    if not result.success:
        status_code = 409 if result.error == "ingestion_already_running" else 500
        raise HTTPException(
            status_code=status_code, detail=result.error or result.message
        )

    return IngestResponse(
        summaries=result.summaries,
        count=result.count,
        message=result.message,
        progress=result.progress,
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Terraform Ingest API",
        "version": "0.1.0",
        "description": "A terraform multi-repo module AI RAG ingestion engine",
        "endpoints": {
            "POST /ingest": "Ingest multiple repositories from configuration",
            "POST /ingest/background": "Start background ingestion from YAML config",
            "GET /ingestion/status": "Poll ingestion progress",
            "POST /analyze": "Analyze a single repository",
            "POST /search/vector": "Search modules using vector embeddings",
            "GET /health": "Health check endpoint",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/ingestion/status", response_model=IngestionStatusResponse)
async def ingestion_status():
    """Return the current ingestion progress snapshot."""
    return IngestionStatusResponse(progress=get_ingestion_status())


@app.post("/ingest/background", response_model=IngestBackgroundResponse)
async def ingest_background(
    request: IngestBackgroundRequest,
    background_tasks: BackgroundTasks,
    auto_install_deps: bool = True,
):
    """Start ingestion from a YAML config file without blocking the request."""
    if is_ingestion_active():
        return IngestBackgroundResponse(
            success=False,
            message="Ingestion is already in progress",
            started_in_background=True,
            progress=get_ingestion_status(),
            error="ingestion_already_running",
        )

    options = _build_options(
        cleanup=request.cleanup,
        skip_existing=request.skip_existing,
        no_cache=request.no_cache,
        auto_install_deps=auto_install_deps,
    )

    background_tasks.add_task(run_ingestion_from_yaml, request.config_file, options)

    return IngestBackgroundResponse(
        success=True,
        message=f"Background ingestion started from {request.config_file}",
        started_in_background=True,
        progress=get_ingestion_status(),
    )


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
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = request.output_dir or f"{temp_dir}/output"
            clone_dir = request.clone_dir or f"{temp_dir}/repos"

            config = IngestConfig(
                repositories=request.repositories,
                output_dir=output_dir,
                clone_dir=clone_dir,
            )

            options = _build_options(
                output_dir=output_dir,
                clone_dir=clone_dir,
                cleanup=request.cleanup,
                skip_existing=request.skip_existing,
                no_cache=request.no_cache,
                auto_install_deps=auto_install_deps,
            )
            result = run_ingestion_from_config(config, options)
            return _result_to_response(result)

    except HTTPException:
        raise
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

            options = _build_options(
                cleanup=request.cleanup,
                skip_existing=request.skip_existing,
                no_cache=request.no_cache,
                auto_install_deps=auto_install_deps,
            )
            result = run_ingestion_from_config(config, options)
            return _result_to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest-from-yaml")
async def ingest_from_yaml(
    yaml_content: str,
    background_tasks: BackgroundTasks,
    auto_install_deps: bool = True,
    background: bool = False,
    cleanup: bool = False,
    skip_existing: bool = False,
    no_cache: bool = False,
):
    """Ingest repositories from a YAML configuration string.

    This endpoint accepts a YAML configuration as a string and processes
    the repositories defined in it.

    Args:
        yaml_content: YAML configuration as a string
        auto_install_deps: Whether to automatically install missing dependencies
        background: Start ingestion in the background and return immediately
        cleanup: Remove cloned repositories after ingestion completes
        skip_existing: Skip git fetch when repositories already exist locally
        no_cache: Delete output and clone directories before ingestion

    Returns:
        IngestResponse or IngestBackgroundResponse depending on mode
    """
    try:
        config_dict = yaml.safe_load(yaml_content)

        with tempfile.TemporaryDirectory() as temp_dir:
            if "output_dir" not in config_dict:
                config_dict["output_dir"] = f"{temp_dir}/output"
            if "clone_dir" not in config_dict:
                config_dict["clone_dir"] = f"{temp_dir}/repos"

            config = IngestConfig(**config_dict)
            options = _build_options(
                output_dir=config.output_dir,
                clone_dir=config.clone_dir,
                cleanup=cleanup,
                skip_existing=skip_existing,
                no_cache=no_cache,
                auto_install_deps=auto_install_deps,
            )

            if background:
                if is_ingestion_active():
                    return IngestBackgroundResponse(
                        success=False,
                        message="Ingestion is already in progress",
                        started_in_background=True,
                        progress=get_ingestion_status(),
                        error="ingestion_already_running",
                    )

                background_tasks.add_task(run_ingestion_from_config, config, options)
                return IngestBackgroundResponse(
                    success=True,
                    message="Background ingestion started from YAML content",
                    started_in_background=True,
                    progress=get_ingestion_status(),
                )

            result = run_ingestion_from_config(config, options)
            return _result_to_response(result)

    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
    except HTTPException:
        raise
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
        from terraform_ingest.ingest import TerraformIngest

        ingester = TerraformIngest.from_yaml(request.config_file)

        if not ingester.vector_db:
            raise HTTPException(
                status_code=400,
                detail="Vector database is not enabled. Set 'embedding.enabled: true' in config.",
            )

        filters = {}
        if request.provider:
            filters["provider"] = request.provider
        if request.repository:
            filters["repository"] = request.repository

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
