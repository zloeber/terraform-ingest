"""Command-line interface for terraform-ingest."""

import click
import json
from pathlib import Path
from .ingest import TerraformIngest
from .models import IngestConfig


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Terraform Ingest - A terraform multi-repo module AI RAG ingestion engine.
    
    This tool accepts a YAML file of terraform git repository sources,
    downloads them locally, and creates JSON summaries for RAG ingestion.
    """
    pass


@cli.command()
@click.argument("config_file", type=click.Path(exists=True), default="config.yaml")
@click.option(
    "--output-dir",
    "-o",
    default="./output",
    help="Directory to save JSON summaries",
)
@click.option(
    "--clone-dir",
    "-c",
    default="./repos",
    help="Directory to clone repositories",
)
@click.option(
    "--cleanup/--no-cleanup",
    default=False,
    help="Clean up cloned repositories after ingestion",
)
def ingest(config_file, output_dir, clone_dir, cleanup):
    """Ingest terraform repositories from a YAML configuration file.
    
    CONFIG_FILE: Path to the YAML configuration file containing repository sources.
    
    Example:
    
        terraform-ingest ingest config.yaml
    
        terraform-ingest ingest config.yaml -o ./my-output -c ./my-repos
    """
    click.echo(f"Loading configuration from {config_file}")

    try:
        ingester = TerraformIngest.from_yaml(config_file)
        
        # Override config if command-line options are provided
        if output_dir != "./output":
            ingester.config.output_dir = output_dir
            ingester.output_dir = Path(output_dir)
            ingester.output_dir.mkdir(parents=True, exist_ok=True)
            
        if clone_dir != "./repos":
            ingester.config.clone_dir = clone_dir
            ingester.repo_manager.clone_dir = Path(clone_dir)
            ingester.repo_manager.clone_dir.mkdir(parents=True, exist_ok=True)

        click.echo("Starting ingestion...")
        summaries = ingester.ingest()

        click.echo(f"\nIngestion complete!")
        click.echo(f"Processed {len(summaries)} module(s)")
        click.echo(f"Summaries saved to {ingester.output_dir}")

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
def analyze(repository_url, branch, output, include_tags, max_tags):
    """Analyze a single terraform repository.
    
    REPOSITORY_URL: Git URL of the repository to analyze.
    
    Example:
    
        terraform-ingest analyze https://github.com/user/terraform-module
    
        terraform-ingest analyze https://github.com/user/terraform-module -b develop --include-tags
    """
    from .models import RepositoryConfig
    
    click.echo(f"Analyzing repository: {repository_url}")

    try:
        # Create a temporary config
        repo_config = RepositoryConfig(
            url=repository_url,
            branches=[branch],
            include_tags=include_tags,
            max_tags=max_tags,
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
    import yaml
    
    config_path = Path(config_file)
    
    if config_path.exists():
        click.echo(f"Error: {config_file} already exists", err=True)
        raise click.Abort()

    sample_config = {
        "repositories": [
            {
                "url": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
                "name": "terraform-aws-vpc",
                "branches": ["main"],
                "include_tags": True,
                "max_tags": 5,
                "path": ".",
            }
        ],
        "output_dir": "./output",
        "clone_dir": "./repos",
    }

    with open(config_path, "w") as f:
        yaml.dump(sample_config, f, default_flow_style=False, sort_keys=False)

    click.echo(f"Created sample configuration at {config_file}")
    click.echo("\nEdit this file to add your terraform repositories, then run:")
    click.echo(f"  terraform-ingest ingest {config_file}")


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


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
