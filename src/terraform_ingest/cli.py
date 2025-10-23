"""Command-line interface for terraform-ingest."""

import os
import click
import json
import shutil
import yaml

from pathlib import Path
from terraform_ingest.models import RepositoryConfig
from terraform_ingest.ingest import TerraformIngest
from terraform_ingest.models import IngestConfig
from terraform_ingest import __version__, CONFIG_PATH
from terraform_ingest.mcp_service import start as mcp_main


@click.group()
@click.version_option(version=__version__)
def cli():
    """Terraform Ingest - A terraform multi-repo module AI RAG ingestion engine.

    This tool accepts a YAML file of terraform git repository sources,
    downloads them locally, and creates JSON summaries for RAG ingestion.
    """
    pass


@cli.command()
@click.argument("config_file", type=click.Path(exists=True), default=CONFIG_PATH)
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="Directory to save JSON summaries",
)
@click.option(
    "--clone-dir",
    "-c",
    default=None,
    help="Directory to clone repositories",
)
@click.option(
    "--cleanup/--no-cleanup",
    default=False,
    help="Clean up cloned repositories after ingestion",
)
@click.option(
    "--no-cache/--cache",
    default=False,
    help="Disable caching for module analysis",
)
@click.option(
    "--enable-embeddings/--no-embeddings",
    default=None,
    help="Enable or disable vector database embeddings (overrides config)",
)
@click.option(
    "--embedding-strategy",
    type=click.Choice(
        ["openai", "claude", "sentence-transformers", "chromadb-default"]
    ),
    default=None,
    help="Embedding strategy to use (overrides config)",
)
def ingest(
    config_file,
    output_dir,
    clone_dir,
    cleanup,
    no_cache,
    enable_embeddings,
    embedding_strategy,
):
    """Ingest terraform repositories from a YAML configuration file.

    CONFIG_FILE: Path to the YAML configuration file containing repository sources.

    Example:

        terraform-ingest ingest config.yaml

        terraform-ingest ingest config.yaml -o ./my-output -c ./my-repos

        terraform-ingest ingest config.yaml --enable-embeddings --embedding-strategy sentence-transformers
    """
    click.echo(f"Loading configuration from {config_file}")

    try:
        ingester = TerraformIngest.from_yaml(config_file)

        # Override config if command-line options are provided
        if output_dir is not None:
            ingester.config.output_dir = output_dir
            ingester.output_dir = Path(output_dir)

        if clone_dir is not None:
            ingester.config.clone_dir = clone_dir
            ingester.repo_manager.clone_dir = Path(clone_dir)

        # Override embedding config if provided
        if enable_embeddings is not None:
            if ingester.config.embedding is None:
                from terraform_ingest.models import EmbeddingConfig

                ingester.config.embedding = EmbeddingConfig()
            ingester.config.embedding.enabled = enable_embeddings

        if embedding_strategy is not None:
            if ingester.config.embedding is None:
                from terraform_ingest.models import EmbeddingConfig

                ingester.config.embedding = EmbeddingConfig()
            ingester.config.embedding.strategy = embedding_strategy

        # Reinitialize vector DB if embedding config was overridden
        if (
            (enable_embeddings is not None or embedding_strategy is not None)
            and ingester.config.embedding
            and ingester.config.embedding.enabled
        ):
            from terraform_ingest.embeddings import VectorDBManager

            ingester.vector_db = VectorDBManager(ingester.config.embedding)

        if no_cache:
            shutil.rmtree(ingester.output_dir, ignore_errors=True)
            shutil.rmtree(ingester.repo_manager.clone_dir, ignore_errors=True)

        ingester.output_dir.mkdir(parents=True, exist_ok=True)
        ingester.repo_manager.clone_dir.mkdir(parents=True, exist_ok=True)

        click.echo("Starting ingestion...")
        summaries = ingester.ingest()

        click.echo("\nIngestion complete!")
        click.echo(f"Processed {len(summaries)} module(s)")
        click.echo(f"Summaries saved to {ingester.output_dir}")

        # Show vector DB stats if enabled
        if ingester.vector_db:
            stats = ingester.get_vector_db_stats()
            if stats.get("enabled"):
                click.echo("\nVector Database Statistics:")
                click.echo(f"  Collection: {stats.get('collection_name')}")
                click.echo(f"  Documents: {stats.get('document_count')}")
                click.echo(f"  Strategy: {stats.get('embedding_strategy')}")

        if cleanup:
            click.echo("Cleaning up cloned repositories...")
            ingester.cleanup()

    except Exception as e:
        click.echo(f"Error during ingestion: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("repository_url")
@click.option(
    "--branch",
    "-b",
    default="main",
    help="Branch to analyze",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for the summary (default: stdout)",
)
@click.option(
    "--include-tags/--no-tags",
    default=False,
    help="Include git tags in analysis",
)
@click.option(
    "--max-tags",
    type=int,
    default=10,
    help="Maximum number of tags to process",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Recursively search for terraform modules in subdirectories",
)
def analyze(
    repository_url,
    branch,
    output,
    include_tags,
    max_tags,
    recursive,
):
    """Analyze a single terraform repository.

    REPOSITORY_URL: Git URL of the repository to analyze.

    Example:

        terraform-ingest analyze https://github.com/user/terraform-module

        terraform-ingest analyze https://github.com/user/terraform-module -b develop --include-tags
    """
    click.echo(f"Analyzing repository: {repository_url}")

    try:
        # Create a temporary config
        repo_config = RepositoryConfig(
            url=repository_url,
            branches=[branch],
            include_tags=include_tags,
            max_tags=max_tags,
            recursive=recursive,
        )

        config = IngestConfig(
            repositories=[repo_config],
            output_dir="./output",
            clone_dir="./repos",
        )

        ingester = TerraformIngest(config)
        summaries = ingester.ingest()

        if output:
            output_path = Path(output)
            with open(output_path, "w") as f:
                json.dump([s.model_dump() for s in summaries], f, indent=2, default=str)
            click.echo(f"\nAnalysis saved to {output_path}")
        else:
            for summary in summaries:
                click.echo(json.dumps(summary.model_dump(), indent=2, default=str))

        click.echo(f"\nAnalyzed {len(summaries)} module version(s)")

    except Exception as e:
        click.echo(f"Error during analysis: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("config_file", type=click.Path())
def init(config_file):
    """Initialize a sample configuration file.

    CONFIG_FILE: Path where the configuration file should be created.

    Example:

        terraform-ingest init config.yaml
    """
    config_path = Path(config_file)

    if config_path.exists():
        click.echo(f"Error: {config_file} already exists", err=True)
        raise click.Abort()

    sample_config = {
        "repositories": [
            {
                "url": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
                "name": "terraform-aws-vpc",
                "branches": ["main", "develop"],
                "include_tags": True,
                "max_tags": 1,
                "path": ".",
                "recursive": False,
            },
            {
                "url": "https://github.com/terraform-aws-modules/terraform-aws-ec2-instance",
                "name": "terraform-aws-ec2-instance",
                "branches": ["main"],
                "include_tags": True,
                "max_tags": 3,
                "path": ".",
                "recursive": True,
            },
        ],
        "output_dir": "./output",
        "clone_dir": "./repos",
        "mcp": {
            "auto_ingest": False,
            "ingest_on_startup": False,
            "refresh_interval_hours": None,
        },
        "embedding": {
            "enabled": False,
            "strategy": "chromadb-default",
            "openai_api_key": None,
            "anthropic_api_key": None,
            "openai_model": "text-embedding-3-small",
            "anthropic_model": "claude-3-haiku-20240307",
            "sentence_transformers_model": "all-MiniLM-L6-v2",
            "chromadb_host": None,
            "chromadb_port": 8000,
            "chromadb_path": "./chromadb",
            "collection_name": "terraform_modules",
            "include_description": True,
            "include_readme": True,
            "include_variables": True,
            "include_outputs": True,
            "include_resource_types": True,
            "enable_hybrid_search": True,
            "keyword_weight": 0.3,
            "vector_weight": 0.7,
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(sample_config, f, default_flow_style=False, sort_keys=False)

    click.echo(f"Created sample configuration at {config_file}")
    click.echo("\nConfiguration includes:")
    click.echo("  • Multiple repositories with different branch/tag settings")
    click.echo("  • Output and clone directories")
    click.echo("  • MCP service configuration options")
    click.echo("  • Comprehensive embedding configuration with multiple strategies")
    click.echo("\nEdit this file to customize for your needs, then run:")
    click.echo(f"  terraform-ingest ingest {config_file}")


@cli.command()
@click.argument("query")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="config.yaml",
    help="Configuration file with vector DB settings",
)
@click.option(
    "--provider",
    "-p",
    default=None,
    help="Filter by provider",
)
@click.option(
    "--repository",
    "-r",
    default=None,
    help="Filter by repository",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=10,
    help="Number of results to return",
)
def search(query, config, provider, repository, limit):
    """Search the vector database for Terraform modules.

    QUERY: Search query (natural language or keywords)

    Example:

        terraform-ingest search "vpc module for aws"

        terraform-ingest search "kubernetes" --provider aws --limit 5
    """
    click.echo(f"Searching for: {query}")

    try:
        # Load config to get vector DB settings
        ingester = TerraformIngest.from_yaml(config)

        if not ingester.vector_db:
            click.echo(
                "Error: Vector database is not enabled in the configuration", err=True
            )
            click.echo(
                "Enable it by setting 'embedding.enabled: true' in your config file",
                err=True,
            )
            raise click.Abort()

        # Prepare filters
        filters = {}
        if provider:
            filters["provider"] = provider
        if repository:
            filters["repository"] = repository

        # Search
        results = ingester.search_vector_db(
            query, filters=filters if filters else None, n_results=limit
        )

        if not results:
            click.echo("No results found")
            return

        click.echo(f"\nFound {len(results)} result(s):\n")

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            click.echo(f"{i}. {metadata.get('repository', 'Unknown')}")
            click.echo(f"   Ref: {metadata.get('ref', 'Unknown')}")
            click.echo(f"   Path: {metadata.get('path', '.')}")
            click.echo(f"   Provider: {metadata.get('provider', 'Unknown')}")
            if result.get("distance") is not None:
                click.echo(f"   Relevance: {1.0 - result['distance']:.3f}")
            click.echo()

    except Exception as e:
        click.echo(f"Error during search: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind the server to",
)
@click.option(
    "--port",
    "-p",
    default=8000,
    type=int,
    help="Port to bind the server to",
)
def serve(host, port):
    """Start the FastAPI server.

    Example:

        terraform-ingest serve

        terraform-ingest serve --host 127.0.0.1 --port 8080
    """
    import uvicorn
    from .api import app

    click.echo(f"Starting Terraform Ingest API server on {host}:{port}")
    click.echo("Press CTRL+C to quit")

    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.option(
    "--config",
    "-c",
    default=None,
    help="Configuration file for auto-ingestion settings",
)
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "http-streamable", "sse"]),
    default=None,
    help="Transport mode (stdio, http-streamable, or sse)",
)
@click.option(
    "--host",
    "-h",
    default=None,
    help="Host to bind to (for http-streamable and sse transports)",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=None,
    help="Port to bind to (for http-streamable and sse transports)",
)
@click.option(
    "--ingest-on-startup/--no-ingest-on-startup",
    default=None,
    help="Run ingestion immediately on startup (overrides config)",
)
def mcp(config, transport, host, port, ingest_on_startup):
    """Start the MCP (Model Context Protocol) server.

    The MCP server exposes ingested Terraform modules to AI agents and supports
    auto-ingestion based on configuration settings.

    Supported transports:
    - stdio (default): Standard input/output communication
    - http-streamable: HTTP with streaming support
    - sse: Server-Sent Events over HTTP

    Example:

        terraform-ingest mcp

        terraform-ingest mcp --config my-config.yaml

        terraform-ingest mcp --ingest-on-startup

        terraform-ingest mcp --transport http-streamable --host 0.0.0.0 --port 3000

        terraform-ingest mcp --transport sse --host localhost --port 8000 --ingest-on-startup
    """
    # Set the config file environment variable if provided
    if config is not None:
        os.environ["TERRAFORM_INGEST_CONFIG"] = config
    else:
        config = os.getenv("TERRAFORM_INGEST_CONFIG", "config.yaml")
        os.environ["TERRAFORM_INGEST_CONFIG"] = config

    if transport != "stdio" and transport is not None:
        click.echo(f"Transport: {transport}")
        click.echo(f"Address: {host or '127.0.0.1'}:{port or 3000}")
        if ingest_on_startup is not None:
            click.echo(f"Ingest on startup: {ingest_on_startup}")
        click.echo("Press CTRL+C to quit")

    try:
        mcp_main(
            config_file=config,
            transport=transport,
            host=host,
            port=port,
            ingest_on_startup=ingest_on_startup,
        )
    except KeyboardInterrupt:
        click.echo("\nMCP server stopped")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
