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
from terraform_ingest.mcp_service import _get_module_resource_impl, ModuleQueryService
from terraform_ingest.indexer import ModuleIndexer
from terraform_ingest.importers import (
    GitHubImporter,
    GitLabImporter,
    update_config_file,
)
from terraform_ingest.dependency_installer import DependencyInstaller

# from terraform_ingest.logging import get_logger

# logger = get_logger(__name__)
from terraform_ingest.tty_logger import setup_tty_logger

logger = setup_tty_logger()


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
@click.option(
    "--auto-install-deps/--no-auto-install-deps",
    default=True,
    help="Automatically install missing embedding dependencies",
)
@click.option(
    "--skip-existing/--no-skip-existing",
    default=False,
    help="Skip cloning if repository already exists in local cache",
)
def ingest(
    config_file,
    output_dir,
    clone_dir,
    cleanup,
    no_cache,
    enable_embeddings,
    embedding_strategy,
    auto_install_deps,
    skip_existing,
):
    """Ingest terraform repositories from a YAML configuration file.

    CONFIG_FILE: Path to the YAML configuration file containing repository sources.

    Example:

        terraform-ingest ingest config.yaml

        terraform-ingest ingest config.yaml -o ./my-output -c ./my-repos

        terraform-ingest ingest config.yaml --enable-embeddings --embedding-strategy sentence-transformers

        terraform-ingest ingest config.yaml --skip-existing
    """
    click.echo(f"Loading configuration from {config_file}")

    try:
        ingester = TerraformIngest.from_yaml(
            config_file,
            auto_install_deps=auto_install_deps,
            skip_existing=skip_existing,
        )

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
            from terraform_ingest.dependency_installer import (
                ensure_embeddings_available,
            )

            # Ensure dependencies for the new strategy are installed
            ensure_embeddings_available(
                ingester.config.embedding,
                logger=ingester.logger,
                auto_install=auto_install_deps,
            )
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
        "repositories": [],
        #     {
        #         "url": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
        #         "name": "terraform-aws-vpc",
        #         "branches": ["main", "develop"],
        #         "include_tags": True,
        #         "max_tags": 1,
        #         "path": ".",
        #         "recursive": False,
        #     },
        #     {
        #         "url": "https://github.com/terraform-aws-modules/terraform-aws-ec2-instance",
        #         "name": "terraform-aws-ec2-instance",
        #         "branches": ["main"],
        #         "include_tags": True,
        #         "max_tags": 3,
        #         "path": ".",
        #         "recursive": True,
        #     },
        # ],
        "output_dir": "./output",
        "clone_dir": "./repos",
        "mcp": {
            "auto_ingest": False,
            "ingest_on_startup": False,
            "refresh_interval_hours": None,
            "instructions": """
    You have access to a comprehensive Terraform module library via the terraform-ingest MCP service.
    
    When a user asks you to find or recommend the best Terraform module for a specific use case:
    1. First, understand their requirements by asking clarifying questions about:
       - The cloud provider (aws, azure, gcp, etc.)
       - The resource type or infrastructure component needed (networking, compute, security, etc.)
       - Any specific features or constraints
    
    2. Then use the "Find Terraform Module" prompt with:
       - keywords: A concise description of what they need (e.g., "VPC with security groups and NAT gateway")
       - provider: The cloud provider (e.g., "aws")
    
    3. This prompt will guide you to:
       - Search for relevant modules using search_modules_vector
       - Retrieve detailed information about each candidate
       - Compare and recommend the best fit
       - Provide the module URL, version, variables, and usage summary
    
    Use this prompt whenever you're tasked with finding, recommending, or selecting a module.
""",
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
@click.argument(
    "config_file", type=click.Path(exists=True), default=None, required=False
)
@click.option(
    "--strategy",
    type=click.Choice(
        ["openai", "claude", "sentence-transformers", "chromadb-default", "all"]
    ),
    default=None,
    help="Embedding strategy to install dependencies for (overrides config file)",
)
@click.option(
    "--no-auto-install/--auto-install",
    default=False,
    help="Skip automatic installation (only report missing packages)",
)
def install_deps(config_file, strategy, no_auto_install):
    """Install optional dependencies for embedding strategies.

    This command manages installation of packages needed for vector database
    and embedding functionality. It can read from a configuration file or use
    explicit strategy options.

    If CONFIG_FILE is provided, dependencies will be installed based on the
    embedding configuration in that file. Otherwise, use --strategy to specify.

    Example:

        # From config file
        terraform-ingest install-deps config.yaml

        # Explicit strategy
        terraform-ingest install-deps --strategy sentence-transformers

        # All strategies
        terraform-ingest install-deps --strategy all

        # Report only (no install)
        terraform-ingest install-deps config.yaml --no-auto-install
    """

    try:
        packages_to_install = []
        embedding_strategy = None

        # Determine which packages to install
        if config_file:
            # Load from config file
            click.echo(f"Loading configuration from {config_file}")
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f)

            embedding_config = config_data.get("embedding", {})

            if not embedding_config or not embedding_config.get("enabled", False):
                click.echo("✓ Embeddings are not enabled in the configuration")
                return

            embedding_strategy = embedding_config.get("strategy", "chromadb-default")
            click.echo(f"Embeddings enabled with strategy: {embedding_strategy}")

            # Get packages for the configured strategy
            packages_to_install = DependencyInstaller.STRATEGY_PACKAGES.get(
                embedding_strategy, []
            )
            if not packages_to_install:
                click.echo(
                    f"Error: Unknown embedding strategy '{embedding_strategy}' in config",
                    err=True,
                )
                raise click.Abort()

            # Always include chromadb if a strategy is enabled
            if "chromadb" not in packages_to_install:
                packages_to_install = list(packages_to_install) + ["chromadb"]

        elif strategy:
            # Use explicit strategy
            if strategy == "all":
                # Install all embedding packages
                packages_to_install = DependencyInstaller.EMBEDDING_PACKAGES
                click.echo("Checking packages for all embedding strategies...")
            else:
                # Install packages for specific strategy
                packages_to_install = DependencyInstaller.STRATEGY_PACKAGES.get(
                    strategy, []
                )
                if not packages_to_install:
                    click.echo(f"Error: Unknown strategy '{strategy}'", err=True)
                    raise click.Abort()
                click.echo(f"Checking packages for '{strategy}' embedding strategy...")
        else:
            # No config and no strategy specified - default to all
            packages_to_install = DependencyInstaller.EMBEDDING_PACKAGES
            click.echo("No config or strategy specified, checking all packages...")

        # Check for missing packages
        missing = DependencyInstaller.get_missing_packages(packages_to_install)

        if not missing:
            click.echo("✓ All required packages are already installed")
            for pkg in packages_to_install:
                click.echo(f"  • {pkg}")
            return

        click.echo(f"\nMissing packages: {', '.join(missing)}")
        for pkg in missing:
            click.echo(f"  • {pkg}")

        if no_auto_install:
            click.echo("\nSkipping automatic installation (--no-auto-install flag set)")
            click.echo("\nInstall manually with:")
            click.echo(f"  pip install {' '.join(missing)}")
            return

        click.echo(f"\nInstalling {len(missing)} package(s)...")
        success = DependencyInstaller.install_packages(
            missing,
            logger=logger,
            use_uv=True,
        )

        if success:
            click.echo("✓ Successfully installed all packages")
            # Verify installation
            # Uses importlib.metadata for robust detection across different
            # installation methods including UV tool environments.
            still_missing = DependencyInstaller.get_missing_packages(
                packages_to_install
            )
            if not still_missing:
                click.echo("✓ All packages verified")
                for pkg in packages_to_install:
                    click.echo(f"  • {pkg}")
            else:
                # If packages were installed but not found, log for troubleshooting
                click.echo(
                    f"⚠ Warning: Some packages not immediately detected: {', '.join(still_missing)}"
                )
                click.echo(
                    "ℹ This may be a detection issue. Try rerunning the command or restarting your shell."
                )
        else:
            click.echo("✗ Installation failed", err=True)
            click.echo("\nTry installing manually with:", err=True)
            click.echo(f"  pip install {' '.join(missing)}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


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
@click.option(
    "--json",
    "-j",
    "output_json",
    is_flag=True,
    default=False,
    help="Output results in JSON format",
)
def search(query, config, provider, repository, limit, output_json):
    """Search the vector database for Terraform modules.

    QUERY: Search query (natural language or keywords)

    Example:

        terraform-ingest search "vpc module for aws"

        terraform-ingest search "kubernetes" --provider aws --limit 5

        terraform-ingest search "vpc" --json
    """
    try:
        # Load config to get vector DB settings
        ingester = TerraformIngest.from_yaml(config)

        if not ingester.vector_db:
            error_msg = "Error: Vector database is not enabled in the configuration"
            if output_json:
                click.echo(json.dumps({"error": error_msg}))
            else:
                click.echo(error_msg, err=True)
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
            if output_json:
                click.echo(json.dumps({"results": [], "count": 0}))
            else:
                click.echo("No results found")
            return

        if output_json:
            # Output as JSON
            json_output = {
                "query": query,
                "count": len(results),
                "results": results,
            }
            click.echo(json.dumps(json_output, indent=2))
        else:
            # Output as formatted text
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
        if output_json:
            click.echo(json.dumps({"error": str(e)}))
        else:
            click.echo(f"Error during search: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("repository")
@click.argument("ref")
@click.option(
    "--path",
    "-p",
    default=".",
    help="Module path within the repository (default: root)",
)
@click.option(
    "--json",
    "-j",
    "output_json",
    is_flag=True,
    default=False,
    help="Output results in JSON format",
)
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="Directory containing ingested JSON modules (default: ./output)",
)
def module(repository, ref, path, output_json, output_dir):
    """Display ingested module data.

    REPOSITORY: Repository name or URL identifier
    REF: Git reference (branch, tag, or commit)

    Example:

        terraform-ingest module terraform-aws-vpc v5.0.0

        terraform-ingest module aws-s3 main --path ./modules/bucket

        terraform-ingest module terraform-aws-vpc v5.0.0 --json

        terraform-ingest module terraform-aws-vpc v5.0.0 -o /path/to/output
    """
    try:
        # Determine output directory
        if output_dir is None:
            output_dir = os.getenv("TERRAFORM_INGEST_OUTPUT_DIR", "./output")

        output_path = Path(output_dir)
        if not output_path.exists():
            error_msg = f"Output directory not found: {output_dir}"
            if output_json:
                click.echo(json.dumps({"error": error_msg}))
            else:
                click.echo(error_msg, err=True)
            raise click.Abort()

        # Create a module query service
        service = ModuleQueryService(output_dir=output_dir)

        # Get the module data
        module_data = service.get_module(repository, ref, path, include_readme=False)

        if module_data is None:
            error_msg = f"Module not found: {repository} @ {ref} (path: {path})"
            if output_json:
                click.echo(json.dumps({"error": error_msg}))
            else:
                click.echo(error_msg, err=True)
            raise click.Abort()

        if output_json:
            # Output as JSON
            click.echo(json.dumps(module_data, indent=2, default=str))
        else:
            # Output as formatted text
            # Display module information
            click.echo(f"\n📦 Module: {module_data.get('repository', 'Unknown')}")
            click.echo(f"📍 Ref: {module_data.get('ref', 'Unknown')}")
            if module_data.get("path") and module_data.get("path") != ".":
                click.echo(f"📂 Path: {module_data.get('path', 'Unknown')}")
            click.echo()

            # Display description if available
            if "description" in module_data and module_data["description"]:
                click.echo(f"Description: {module_data['description']}\n")

            # Display providers
            if "providers" in module_data and module_data["providers"]:
                click.echo("Providers:")
                for provider in module_data["providers"]:
                    provider_name = provider.get("name", "Unknown")
                    provider_version = provider.get("version", "Unknown")
                    click.echo(f"  - {provider_name} ({provider_version})")
                click.echo()

            # Display variables
            if "variables" in module_data and module_data["variables"]:
                click.echo("Input Variables:")
                for var in module_data["variables"]:
                    var_name = var.get("name", "Unknown")
                    var_type = var.get("type", "Unknown")
                    var_desc = var.get("description", "")
                    default = var.get("default")
                    required = var.get("required", False)
                    click.echo(
                        f"  - {var_name} ({var_type})"
                        + (" [required]" if required else "")
                    )
                    if var_desc:
                        click.echo(f"    {var_desc}")
                    if default is not None:
                        click.echo(f"    Default: {default}")
                click.echo()

            # Display outputs
            if "outputs" in module_data and module_data["outputs"]:
                click.echo("Outputs:")
                for output in module_data["outputs"]:
                    output_name = output.get("name", "Unknown")
                    output_desc = output.get("description", "")
                    click.echo(f"  - {output_name}")
                    if output_desc:
                        click.echo(f"    {output_desc}")
                click.echo()

            # Display modules (sub-modules)
            if "modules" in module_data and module_data["modules"]:
                click.echo("Sub-modules:")
                for submod in module_data["modules"]:
                    submod_name = submod.get("name", "Unknown")
                    submod_source = submod.get("source", "Unknown")
                    click.echo(f"  - {submod_name}: {submod_source}")
                click.echo()

            # Display resources summary
            if "resources" in module_data and module_data["resources"]:
                click.echo(
                    f"Resources: {len(module_data['resources'])} managed resource(s)"
                )
                click.echo()

    except Exception as e:
        error_msg = f"Error retrieving module: {e}"
        if output_json:
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(error_msg, err=True)
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
    type=click.Choice(["stdio", "streamable-http", "sse"]),
    default=None,
    help="Transport mode (stdio, streamable-http, or sse)",
)
@click.option(
    "--host",
    "-h",
    default=None,
    help="Host to bind to (for streamable-http and sse transports)",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=None,
    help="Port to bind to (for streamable-http and sse transports)",
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
    - streamable-http: HTTP with streaming support
    - sse: Server-Sent Events over HTTP

    Example:

        terraform-ingest mcp

        terraform-ingest mcp --config my-config.yaml

        terraform-ingest mcp --ingest-on-startup

        terraform-ingest mcp --transport streamable-http --host 0.0.0.0 --port 3000

        terraform-ingest mcp --transport sse --host localhost --port 8000 --ingest-on-startup
    """
    # Set the config file environment variable if provided
    if config is not None:
        os.environ["TERRAFORM_INGEST_CONFIG"] = config
    else:
        config = os.getenv("TERRAFORM_INGEST_CONFIG", "config.yaml")
        os.environ["TERRAFORM_INGEST_CONFIG"] = config

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


@cli.group()
def function():
    """Manage MCP functions and operations.

    This group provides commands to interact with MCP (Model Context Protocol)
    functions, including showing available functions and executing them.

    Example:

        terraform-ingest function show

        terraform-ingest function exec my-function --arg value
    """
    pass


@function.command()
@click.option(
    "--output-dir",
    "-o",
    default="./output",
    help="Directory containing ingested module summaries",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "list"]),
    default="table",
    help="Output format for function list",
)
def show(output_dir, format):
    """Show available MCP functions and their details.

    This command displays information about all available MCP functions
    that can be executed against ingested Terraform modules.

    Example:

        terraform-ingest function show

        terraform-ingest function show --output-dir ./my-output --format json
    """
    try:
        # Import the MCP instance to get exposed functions
        from terraform_ingest.mcp_service import mcp

        # Dynamically detect exposed MCP functions from the tool manager
        functions = []
        if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
            tools_dict = mcp._tool_manager._tools
            for tool_name, tool in tools_dict.items():
                # Extract function information from the tool
                func_info = {
                    "name": tool_name,
                    "description": tool.description or "No description available",
                    "parameters": [],
                }

                # Extract parameters from tool's parameter schema
                if hasattr(tool, "parameters") and tool.parameters:
                    params_schema = tool.parameters
                    if (
                        isinstance(params_schema, dict)
                        and "properties" in params_schema
                    ):
                        func_info["parameters"] = list(
                            params_schema["properties"].keys()
                        )

                functions.append(func_info)

        # Sort functions by name for consistent output
        functions.sort(key=lambda x: x["name"])

        if format == "json":
            click.echo(json.dumps(functions, indent=2))
        elif format == "list":
            if functions:
                for func in functions:
                    click.echo(f"• {func['name']}")
            else:
                click.echo("No MCP functions found")
        else:  # table format
            if functions:
                click.echo("Available MCP Functions:")
                click.echo("-" * 80)
                for func in functions:
                    click.echo(f"\nFunction: {func['name']}")
                    click.echo(f"Description: {func['description']}")
                    if func["parameters"]:
                        click.echo(f"Parameters: {', '.join(func['parameters'])}")
                    else:
                        click.echo("Parameters: (none)")
            else:
                click.echo("No MCP functions found")

    except Exception as e:
        click.echo(f"Error showing functions: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("resource_path")
@click.option(
    "--output-dir",
    "-o",
    default="./output",
    help="Directory containing ingested module summaries",
)
def resource(resource_path, output_dir):
    """Retrieve and display an MCP resource by its path.

    RESOURCE_PATH: MCP resource path in the format 'module://repository/ref/path'

    This command retrieves a specific Terraform module resource and returns
    its JSON summary including variables, outputs, providers, and README.

    Example:

        terraform-ingest resource module://terraform-aws-vpc/v5.0.0

        terraform-ingest resource module://terraform-aws-ec2/main

        terraform-ingest resource module://terraform-aws-vpc/v5.0.0/modules-networking
    """
    try:
        # Parse the resource path
        # Expected format: module://repository/ref/path
        if not resource_path.startswith("module://"):
            click.echo(
                "Error: Resource path must start with 'module://' (e.g., module://terraform-aws-vpc/v5.0.0)",
                err=True,
            )
            raise click.Abort()

        # Remove the 'module://' prefix and split
        path_parts = resource_path[9:].split("/")

        if len(path_parts) < 2:
            click.echo(
                "Error: Resource path must include repository and ref (e.g., module://repository/ref)",
                err=True,
            )
            click.echo(
                "Optional path parameter: module://repository/ref/path",
                err=True,
            )
            raise click.Abort()

        repository_name = path_parts[0]
        ref = path_parts[1]
        resource_subpath = "/".join(path_parts[2:]) if len(path_parts) > 2 else "-"

        # Use the MCP implementation to get the resource
        result = _get_module_resource_impl(repository_name, ref, resource_subpath)

        click.echo(result)

    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"Error retrieving resource: {e}", err=True)
        raise click.Abort()


@function.command()
@click.argument("function_name")
@click.option(
    "--arg",
    "-a",
    multiple=True,
    nargs=2,
    help="Function arguments as key-value pairs (use multiple times for multiple args)",
)
@click.option(
    "--output-dir",
    "-o",
    default="./output",
    help="Directory containing ingested module summaries",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "text"]),
    default="json",
    help="Output format for function results",
)
def exec(function_name, arg, output_dir, format):
    """Execute an MCP function.

    FUNCTION_NAME: Name of the function to execute.

    This command executes a specific MCP function with the provided arguments
    and returns the results.

    Example:

        terraform-ingest function exec list_modules

        terraform-ingest function exec search_modules -a query "aws vpc" -a provider "aws"

        terraform-ingest function exec get_module_details -a repository "https://github.com/..." -a ref "main"
    """
    try:
        # Convert arguments to dictionary
        args_dict = {}
        for key, value in arg:
            args_dict[key] = value

        # Add output_dir to arguments if not already present
        if "output_dir" not in args_dict and function_name != "search_modules_vector":
            args_dict["output_dir"] = output_dir

        # click.echo(f"Executing function: {function_name}")
        # click.echo(f"Arguments: {args_dict}")

        # Import the ModuleQueryService
        from terraform_ingest.mcp_service import ModuleQueryService, MCPContext

        # Map function names to methods
        if function_name == "search_modules_vector":
            # This function needs the MCPContext for vector DB access
            ctx = MCPContext.get_instance()
            if not ctx.ingester or not ctx.ingester.vector_db:
                click.echo("Error: Vector database is not enabled", err=True)
                raise click.Abort()
            result = ctx.ingester.search_vector_db(
                args_dict.get("query", ""),
                filters={
                    k: v
                    for k, v in args_dict.items()
                    if k in ["provider", "repository"]
                },
                n_results=int(args_dict.get("limit", 10)),
            )
        else:
            # Use ModuleQueryService for other functions
            service = ModuleQueryService(
                output_dir=args_dict.get("output_dir", "./output")
            )

            if function_name == "list_repositories":
                result = service.list_repositories(
                    filter_keyword=args_dict.get("filter"),
                    limit=int(args_dict.get("limit", 50)),
                )
            elif function_name == "search_modules":
                repo_urls = None
                if "repo_urls" in args_dict:
                    # Handle comma-separated or list-style repo URLs
                    repo_urls = (
                        args_dict["repo_urls"].split(",")
                        if isinstance(args_dict["repo_urls"], str)
                        else args_dict["repo_urls"]
                    )
                result = service.search_modules(
                    query=args_dict.get("query", ""),
                    repo_urls=repo_urls,
                    provider=args_dict.get("provider"),
                )
            elif function_name == "get_module_details":
                # Parse 'all' argument as boolean (default: False)
                include_readme = args_dict.get("all", "false").lower() in (
                    "true",
                    "1",
                    "yes",
                )
                result = service.get_module(
                    repository=args_dict.get("repository", ""),
                    ref=args_dict.get("ref", ""),
                    path=args_dict.get("path", "."),
                    include_readme=include_readme,
                )
            elif function_name == "list_modules":
                result = service.list_modules(limit=int(args_dict.get("limit", 100)))
            elif function_name == "list_module_resources":
                result = service.list_module_resources(
                    repository=args_dict.get("repository", ""),
                    ref=args_dict.get("ref", ""),
                    path=args_dict.get("path", "."),
                )
            else:
                click.echo(f"Error: Unknown function '{function_name}'", err=True)
                raise click.Abort()

        # Output the result
        if format == "json":
            click.echo(json.dumps(result, indent=2, default=str))
        else:  # text format
            click.echo(json.dumps(result, indent=2, default=str))

    except Exception as e:
        click.echo(f"Error executing function '{function_name}': {e}", err=True)
        raise click.Abort()


@cli.group()
def index():
    """Manage the module index for fast lookups."""
    pass


@index.command()
@click.option(
    "--output-dir",
    default="./output",
    type=click.Path(),
    help="Output directory with module JSON files",
)
def rebuild(output_dir):
    """Rebuild the module index from all JSON files."""
    try:
        indexer = ModuleIndexer(output_dir)
        count = indexer.rebuild_from_files()
        click.echo(f"✓ Index rebuilt with {count} modules")
    except Exception as e:
        click.echo(f"Error rebuilding index: {e}", err=True)
        raise click.Abort()


@index.command()
@click.option(
    "--output-dir",
    default="./output",
    type=click.Path(),
    help="Output directory with module JSON files",
)
def stats(output_dir):
    """Show module index statistics."""
    try:
        indexer = ModuleIndexer(output_dir)
        stats_data = indexer.get_stats()
        click.echo("\n📊 Module Index Statistics:")
        click.echo(f"  Total Modules: {stats_data['total_modules']}")
        click.echo(f"  Unique Providers: {stats_data['unique_providers']}")
        if stats_data["providers"]:
            click.echo(f"  Providers: {', '.join(stats_data['providers'])}")
        click.echo(f"  Unique Tags: {stats_data['unique_tags']}")
        click.echo(f"  Index File: {stats_data['index_file']}\n")
    except Exception as e:
        click.echo(f"Error getting index stats: {e}", err=True)
        raise click.Abort()


@index.command()
@click.argument("doc_id")
@click.option(
    "--output-dir",
    default="./output",
    type=click.Path(),
    help="Output directory with module JSON files",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def lookup(doc_id, output_dir, output_json):
    """Look up a module by its document ID."""
    try:
        indexer = ModuleIndexer(output_dir)
        module = indexer.get_module(doc_id)

        if not module:
            click.echo(f"Error: Module with ID '{doc_id}' not found", err=True)
            raise click.Abort()

        if output_json:
            click.echo(json.dumps(module, indent=2))
        else:
            click.echo(f"\n📦 Module: {doc_id}")
            click.echo(f"  Repository: {module['repository']}")
            click.echo(f"  Ref: {module['ref']}")
            click.echo(f"  Path: {module['path']}")
            click.echo(f"  Provider: {module['provider']}")
            click.echo(f"  Summary File: {module['summary_file']}")
            if module.get("tags"):
                click.echo(f"  Tags: {', '.join(module['tags'])}")
            click.echo()
    except Exception as e:
        click.echo(f"Error looking up module: {e}", err=True)
        raise click.Abort()


@index.command()
@click.argument("provider")
@click.option(
    "--output-dir",
    default="./output",
    type=click.Path(),
    help="Output directory with module JSON files",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def by_provider(provider, output_dir, output_json):
    """Search modules by provider."""
    try:
        indexer = ModuleIndexer(output_dir)
        results = indexer.search_by_provider(provider)

        if not results:
            click.echo(f"No modules found for provider '{provider}'")
            return

        if output_json:
            click.echo(json.dumps(results, indent=2))
        else:
            click.echo(
                f"\n🔍 Found {len(results)} module(s) for provider '{provider}':\n"
            )
            for module in results:
                click.echo(f"  • {module['repository']} ({module['ref']})")
                click.echo(f"    Path: {module['path']}")
                click.echo(f"    ID: {module['id']}\n")
    except Exception as e:
        click.echo(f"Error searching by provider: {e}", err=True)
        raise click.Abort()


@index.command()
@click.argument("tag")
@click.option(
    "--output-dir",
    default="./output",
    type=click.Path(),
    help="Output directory with module JSON files",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def by_tag(tag, output_dir, output_json):
    """Search modules by tag."""
    try:
        indexer = ModuleIndexer(output_dir)
        results = indexer.search_by_tag(tag)

        if not results:
            click.echo(f"No modules found with tag '{tag}'")
            return

        if output_json:
            click.echo(json.dumps(results, indent=2))
        else:
            click.echo(f"\n🏷️  Found {len(results)} module(s) with tag '{tag}':\n")
            for module in results:
                click.echo(f"  • {module['repository']} ({module['ref']})")
                click.echo(f"    Path: {module['path']}")
                click.echo(f"    ID: {module['id']}\n")
    except Exception as e:
        click.echo(f"Error searching by tag: {e}", err=True)
        raise click.Abort()


@index.command()
@click.argument("doc_id")
@click.option(
    "--output-dir",
    default="./output",
    type=click.Path(),
    help="Output directory with module JSON files",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def get(doc_id, output_dir, output_json):
    """Get full module summary by index ID."""
    try:
        indexer = ModuleIndexer(output_dir)
        module_entry = indexer.get_module(doc_id)

        if not module_entry:
            click.echo(f"Error: Module with ID '{doc_id}' not found in index", err=True)
            raise click.Abort()

        # Get the path to the summary file
        summary_path = indexer.get_module_summary_path(doc_id)

        if not summary_path or not summary_path.exists():
            click.echo(
                f"Error: Module index entry found but summary file not found at {summary_path}",
                err=True,
            )
            raise click.Abort()

        # Load the full module summary
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        if output_json:
            click.echo(json.dumps(summary, indent=2))
        else:
            click.echo(f"\n📄 Module Summary for ID: {doc_id}\n")
            click.echo(f"Repository: {summary.get('repository', 'N/A')}")
            click.echo(f"Ref: {summary.get('ref', 'N/A')}")
            click.echo(f"Path: {summary.get('path', 'N/A')}")
            click.echo(f"Description: {summary.get('description', 'N/A')}\n")

            # Show providers
            if summary.get("providers"):
                click.echo("Providers:")
                for provider in summary["providers"]:
                    click.echo(
                        f"  • {provider.get('name', 'unknown')} "
                        f"({provider.get('source', 'unknown')})"
                    )
                click.echo()

            # Show variables
            if summary.get("variables"):
                click.echo(f"Variables ({len(summary['variables'])}):")
                for var in summary["variables"]:
                    required = " (required)" if var.get("required") else ""
                    click.echo(f"  • {var.get('name', 'unknown')}{required}")
                    if var.get("description"):
                        click.echo(f"    Description: {var['description']}")
                    if var.get("type"):
                        click.echo(f"    Type: {var['type']}")
                click.echo()

            # Show outputs
            if summary.get("outputs"):
                click.echo(f"Outputs ({len(summary['outputs'])}):")
                for output in summary["outputs"]:
                    click.echo(f"  • {output.get('name', 'unknown')}")
                    if output.get("description"):
                        click.echo(f"    Description: {output['description']}")
                click.echo()

            # Show README preview
            if summary.get("readme_content"):
                readme = summary["readme_content"]
                lines = readme.split("\n")[:10]
                click.echo("README Preview:")
                for line in lines:
                    click.echo(f"  {line}")
                if len(summary["readme_content"].split("\n")) > 10:
                    click.echo("  ...")
                click.echo()

    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON in module summary file", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error retrieving module summary: {e}", err=True)
        raise click.Abort()


@cli.group()
def import_cmd():
    """Import repositories from external sources into configuration.

    This command group allows importing repositories from various sources
    (GitHub, GitLab, etc.) and updating your configuration file.

    Example:

        terraform-ingest import github --org hashicorp --config config.yaml

        terraform-ingest import github --org myorg --terraform-only --replace
    """
    pass


# Rename the group in the CLI to avoid conflict with Python's import keyword
import_cmd.name = "import"


@import_cmd.command()
@click.option("--org", required=True, help="GitHub organization name")
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    help="GitHub personal access token (or set GITHUB_TOKEN env var)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default="config.yaml",
    help="Configuration file to update (default: config.yaml)",
)
@click.option(
    "--include-private",
    is_flag=True,
    help="Include private repositories (requires authentication)",
)
@click.option(
    "--terraform-only",
    is_flag=True,
    help="Only include repositories that contain Terraform files",
)
@click.option(
    "--base-path",
    default=".",
    help="Base path for module scanning (default: .)",
)
@click.option(
    "--replace",
    is_flag=True,
    help="Replace existing repositories instead of merging",
)
@click.option(
    "--max-tags",
    type=int,
    default=1,
    help="Maximum number of tags to include per repository (default: 1)",
)
@click.option(
    "--branches",
    type=str,
    default="",
    help="Comma-separated list of branches to include (default: empty)",
)
def github(
    org: str,
    token: str,
    config: str,
    include_private: bool,
    terraform_only: bool,
    base_path: str,
    replace: bool,
    max_tags: int,
    branches: str,
) -> None:
    """Import repositories from a GitHub organization.

    This command fetches all repositories from a GitHub organization and
    adds them to your configuration file. By default, it merges with existing
    repositories. Use --replace to override the existing list.

    Example:

        terraform-ingest import github --org hashicorp

        terraform-ingest import github --org myorg --token ghp_xxx --terraform-only

        terraform-ingest import github --org myorg --replace --config my-config.yaml

        terraform-ingest import github --org myorg --max-tags 5 --branches main,develop
    """
    try:
        config_path = Path(config)

        # Parse branches from comma-separated string
        branches_list = [b.strip() for b in branches.split(",") if b.strip()]

        # Create importer
        importer = GitHubImporter(
            org=org,
            token=token,
            include_private=include_private,
            terraform_only=terraform_only,
            base_path=base_path,
        )

        # Fetch repositories
        repos = importer.fetch_repositories()

        if not repos:
            click.echo("No repositories found matching criteria", err=True)
            return

        # Apply max_tags and branches to all repositories
        for repo in repos:
            repo.max_tags = max_tags
            repo.branches = branches_list

        # Update configuration file
        update_config_file(config_path, repos, replace=replace)

        mode = "Replaced" if replace else "Merged"
        click.echo(f"{mode} {len(repos)} repositories in {config_path}")

    except Exception as e:
        click.echo(f"Error importing repositories: {e}", err=True)
        raise click.Abort()


@import_cmd.command()
@click.option("--group", required=True, help="GitLab group name or ID")
@click.option(
    "--token",
    envvar="GITLAB_TOKEN",
    help="GitLab personal access token (or set GITLAB_TOKEN env var)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default="config.yaml",
    help="Configuration file to update (default: config.yaml)",
)
@click.option(
    "--include-private",
    is_flag=True,
    help="Include private repositories (requires authentication)",
)
@click.option(
    "--terraform-only",
    is_flag=True,
    help="Only include repositories that contain Terraform files",
)
@click.option(
    "--base-path",
    default=".",
    help="Base path for module scanning (default: .)",
)
@click.option(
    "--replace",
    is_flag=True,
    help="Replace existing repositories instead of merging",
)
@click.option(
    "--max-tags",
    type=int,
    default=1,
    help="Maximum number of tags to include per repository (default: 1)",
)
@click.option(
    "--branches",
    type=str,
    default="",
    help="Comma-separated list of branches to include (default: empty)",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Recursively fetch repositories from subgroups (default: true)",
)
@click.option(
    "--gitlab-url",
    default="https://gitlab.com",
    help="GitLab instance URL (default: https://gitlab.com)",
)
def gitlab(
    group: str,
    token: str,
    config: str,
    include_private: bool,
    terraform_only: bool,
    base_path: str,
    replace: bool,
    max_tags: int,
    branches: str,
    recursive: bool,
    gitlab_url: str,
) -> None:
    """Import repositories from a GitLab group.

    This command fetches all repositories from a GitLab group (optionally
    including subgroups) and adds them to your configuration file. By default,
    it merges with existing repositories. Use --replace to override the existing list.

    Example:

        terraform-ingest import gitlab --group mygroup

        terraform-ingest import gitlab --group mygroup --token glpat-xxx --terraform-only

        terraform-ingest import gitlab --group mygroup --replace --config my-config.yaml

        terraform-ingest import gitlab --group mygroup --max-tags 5 --branches main,develop

        terraform-ingest import gitlab --group mygroup --recursive --gitlab-url https://gitlab.example.com
    """
    try:
        config_path = Path(config)

        # Parse branches from comma-separated string
        branches_list = [b.strip() for b in branches.split(",") if b.strip()]

        # Create importer
        importer = GitLabImporter(
            group=group,
            token=token,
            include_private=include_private,
            terraform_only=terraform_only,
            base_path=base_path,
            recursive=recursive,
            gitlab_url=gitlab_url,
        )

        # Fetch repositories
        repos = importer.fetch_repositories()

        if not repos:
            click.echo("No repositories found matching criteria", err=True)
            return

        # Apply max_tags and branches to all repositories
        for repo in repos:
            repo.max_tags = max_tags
            repo.branches = branches_list

        # Update configuration file
        update_config_file(config_path, repos, replace=replace)

        mode = "Replaced" if replace else "Merged"
        click.echo(f"{mode} {len(repos)} repositories in {config_path}")

    except Exception as e:
        click.echo(f"Error importing repositories: {e}", err=True)
        raise click.Abort()


@cli.group()
def config():
    """Manage configuration file settings.

    This command group provides tools to read and update configuration files.
    Use 'set' and 'get' for single values, and 'add-repo' or 'remove-repo'
    for managing repository entries.

    Example:

        terraform-ingest config set --target output_dir --value ./my-output

        terraform-ingest config get --target clone_dir

        terraform-ingest config add-repo --url https://github.com/org/repo

        terraform-ingest config remove-repo --url https://github.com/org/repo
    """
    pass


@config.command(name="set")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default="config.yaml",
    help="Configuration file to update (default: config.yaml)",
)
@click.option(
    "--target",
    "-t",
    required=True,
    help="Configuration path to set (e.g., 'output_dir', 'embedding.enabled')",
)
@click.option(
    "--value",
    "-v",
    required=True,
    help="Value to set (use 'true'/'false' for booleans, numbers for integers)",
)
def config_set(config, target, value):
    """Set a configuration value.

    TARGET should be a dot-separated path to the configuration key.
    For nested values, use dots to separate levels (e.g., 'embedding.enabled').

    VALUE will be automatically converted to the appropriate type:
    - 'true' or 'false' becomes boolean
    - Numeric strings become integers or floats
    - Everything else remains a string

    Example:

        terraform-ingest config set --target output_dir --value ./output

        terraform-ingest config set --target embedding.enabled --value true

        terraform-ingest config set --target mcp.port --value 3000
    """
    try:
        config_path = Path(config)

        # Load existing configuration
        if not config_path.exists():
            click.echo(f"Error: Configuration file not found: {config}", err=True)
            raise click.Abort()

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        # Parse the target path
        path_parts = target.split(".")

        # Convert value to appropriate type
        converted_value = _convert_value(value)

        # Navigate to the target location and set the value
        current = config_data
        for i, part in enumerate(path_parts[:-1]):
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                click.echo(
                    f"Error: Cannot set nested value - '{'.'.join(path_parts[: i + 1])}' is not a dictionary",
                    err=True,
                )
                raise click.Abort()
            current = current[part]

        # Set the final value
        current[path_parts[-1]] = converted_value

        # Write back to file
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        click.echo(f"✓ Set {target} = {converted_value}")

    except Exception as e:
        click.echo(f"Error setting configuration value: {e}", err=True)
        raise click.Abort()


@config.command(name="get")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="config.yaml",
    help="Configuration file to read (default: config.yaml)",
)
@click.option(
    "--target",
    "-t",
    required=True,
    help="Configuration path to get (e.g., 'output_dir', 'embedding.enabled')",
)
@click.option(
    "--json",
    "-j",
    "output_json",
    is_flag=True,
    default=False,
    help="Output as JSON",
)
def config_get(config, target, output_json):
    """Get a configuration value.

    TARGET should be a dot-separated path to the configuration key.
    For nested values, use dots to separate levels (e.g., 'embedding.enabled').

    Example:

        terraform-ingest config get --target output_dir

        terraform-ingest config get --target embedding.enabled

        terraform-ingest config get --target mcp --json
    """
    try:
        config_path = Path(config)

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        # Parse the target path
        path_parts = target.split(".")

        # Navigate to the target location
        current = config_data
        for part in path_parts:
            if not isinstance(current, dict) or part not in current:
                click.echo(f"Error: Configuration key not found: {target}", err=True)
                raise click.Abort()
            current = current[part]

        # Output the value
        if output_json:
            click.echo(json.dumps(current, indent=2, default=str))
        else:
            if isinstance(current, (dict, list)):
                click.echo(yaml.dump(current, default_flow_style=False))
            else:
                click.echo(current)

    except Exception as e:
        click.echo(f"Error getting configuration value: {e}", err=True)
        raise click.Abort()


@config.command(name="add-repo")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default="config.yaml",
    help="Configuration file to update (default: config.yaml)",
)
@click.option(
    "--url",
    required=True,
    help="Repository URL",
)
@click.option(
    "--name",
    default=None,
    help="Repository name (optional)",
)
@click.option(
    "--branches",
    default="",
    help="Comma-separated list of branches to include",
)
@click.option(
    "--include-tags/--no-include-tags",
    default=True,
    help="Include git tags in analysis",
)
@click.option(
    "--max-tags",
    type=int,
    default=1,
    help="Maximum number of tags to include",
)
@click.option(
    "--path",
    default=".",
    help="Base path for module scanning",
)
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Recursively search for terraform modules",
)
def config_add_repo(
    config, url, name, branches, include_tags, max_tags, path, recursive
):
    """Add a repository to the configuration.

    This command adds a new repository entry to the repositories array
    in the configuration file.

    Example:

        terraform-ingest config add-repo --url https://github.com/org/repo

        terraform-ingest config add-repo --url https://github.com/org/repo --name my-repo --branches main,develop

        terraform-ingest config add-repo --url https://github.com/org/repo --recursive --max-tags 5
    """
    try:
        config_path = Path(config)

        # Load existing configuration
        if not config_path.exists():
            click.echo(f"Error: Configuration file not found: {config}", err=True)
            raise click.Abort()

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        # Parse branches
        branches_list = [b.strip() for b in branches.split(",") if b.strip()]

        # Create new repository config
        new_repo = RepositoryConfig(
            url=url,
            name=name,
            branches=branches_list,
            include_tags=include_tags,
            max_tags=max_tags,
            path=path,
            recursive=recursive,
        )

        # Ensure repositories array exists
        if "repositories" not in config_data:
            config_data["repositories"] = []

        # Check if repository with same URL already exists
        existing_repos = config_data["repositories"]
        for repo in existing_repos:
            if repo.get("url") == url:
                click.echo(
                    f"Warning: Repository with URL '{url}' already exists in configuration",
                    err=True,
                )
                click.echo(
                    "Use 'config set' to update specific values or remove the repository first.",
                    err=True,
                )
                raise click.Abort()

        # Add new repository
        config_data["repositories"].append(new_repo.model_dump())

        # Write back to file
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        click.echo(f"✓ Added repository: {url}")
        if name:
            click.echo(f"  Name: {name}")
        click.echo(f"  Branches: {branches_list if branches_list else '(none)'}")
        click.echo(f"  Include tags: {include_tags}")
        click.echo(f"  Max tags: {max_tags}")
        click.echo(f"  Path: {path}")
        click.echo(f"  Recursive: {recursive}")

    except Exception as e:
        click.echo(f"Error adding repository: {e}", err=True)
        raise click.Abort()


@config.command(name="remove-repo")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="config.yaml",
    help="Configuration file to update (default: config.yaml)",
)
@click.option(
    "--url",
    help="Repository URL to remove",
)
@click.option(
    "--name",
    help="Repository name to remove",
)
def config_remove_repo(config, url, name):
    """Remove a repository from the configuration.

    Specify either --url or --name to identify the repository to remove.

    Example:

        terraform-ingest config remove-repo --url https://github.com/org/repo

        terraform-ingest config remove-repo --name my-repo
    """
    try:
        if not url and not name:
            click.echo("Error: Must specify either --url or --name", err=True)
            raise click.Abort()

        config_path = Path(config)

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        # Get repositories array
        if "repositories" not in config_data or not config_data["repositories"]:
            click.echo("No repositories found in configuration")
            return

        # Find and remove the repository
        repositories = config_data["repositories"]
        removed = False
        removed_repo = None

        for i, repo in enumerate(repositories):
            if (url and repo.get("url") == url) or (name and repo.get("name") == name):
                removed_repo = repositories.pop(i)
                removed = True
                break

        if not removed:
            identifier = f"URL '{url}'" if url else f"name '{name}'"
            click.echo(f"Error: Repository with {identifier} not found", err=True)
            raise click.Abort()

        # Write back to file
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        click.echo(
            f"✓ Removed repository: {removed_repo.get('url', removed_repo.get('name'))}"
        )

    except Exception as e:
        click.echo(f"Error removing repository: {e}", err=True)
        raise click.Abort()


def _convert_value(value: str):
    """Convert a string value to the appropriate type.

    Attempts to convert the value to boolean, integer, float, or returns
    as string if no conversion is possible.

    Args:
        value: String value to convert

    Returns:
        Converted value (bool, int, float, or str)

    Examples:
        >>> _convert_value("true")
        True
        >>> _convert_value("42")
        42
        >>> _convert_value("3.14")
        3.14
        >>> _convert_value("hello")
        'hello'

    Note:
        Boolean conversions:
        - True: "true", "yes", "on", "1"
        - False: "false", "no", "off", "0"
    """
    # Try boolean
    if value.lower() in ("true", "yes", "on", "1"):
        return True
    if value.lower() in ("false", "no", "off", "0"):
        return False

    # Try integer
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Return as string
    return value


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
