"""CLI commands for agent skill management."""

from __future__ import annotations

from pathlib import Path
from typing import List

import click

from terraform_ingest.skills import (
    SUPPORTED_TARGETS,
    install_skills_for_targets,
    list_skills,
    resolve_skill_names,
    resolve_skills_root,
    resolve_targets,
    skill_markdown,
    validate_config,
    validate_skill,
)


@click.group(name="skills", invoke_without_command=True)
@click.pass_context
def skills(ctx: click.Context) -> None:
    """Manage and deploy terraform-ingest agent skills."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@skills.command("list")
def skills_list() -> None:
    """List available skills in the skills directory."""
    root = resolve_skills_root()
    names = list_skills(root)
    if not names:
        click.echo(f"No skills found in {root}")
        return
    click.echo(f"Skills ({root}):")
    for name in names:
        click.echo(f"- {name}")


@skills.command("path")
def skills_path() -> None:
    """Print the resolved skills directory path."""
    click.echo(str(resolve_skills_root()))


@skills.command("show")
@click.argument("skill_name", required=False)
def skills_show(skill_name: str | None) -> None:
    """Show SKILL.md content for one skill."""
    if not skill_name:
        names = list_skills()
        if not names:
            click.echo("No skills found.", err=True)
            raise click.Abort()
        click.echo("Available skills:")
        for name in names:
            click.echo(f"- {name}")
        click.echo(
            "Use `terraform-ingest skills show <name>` to print SKILL.md content."
        )
        return

    content = skill_markdown(skill_name)
    if content is None:
        click.echo(f"Skill '{skill_name}' not found.", err=True)
        raise click.Abort()
    click.echo(content)


@skills.command("validate")
@click.argument("skill_name", required=False)
def skills_validate(skill_name: str | None) -> None:
    """Validate skill format (Claude Code SKILL.md frontmatter)."""
    names = [skill_name] if skill_name else list_skills()
    if not names:
        click.echo("No skills found to validate.", err=True)
        raise click.Abort()

    failed = False
    for name in names:
        result = validate_skill(name)
        if result.valid:
            click.echo(f"OK: {name}")
        else:
            failed = True
            click.echo(f"ERROR: {name}", err=True)
            for error in result.errors:
                click.echo(f"  - {error}", err=True)

    if failed:
        raise click.Abort()


@skills.command("validate-config")
@click.argument("config_file", type=click.Path(exists=True), default="config.yaml")
def skills_validate_config(config_file: str) -> None:
    """Validate a terraform-ingest YAML configuration file."""
    exit_code = validate_config(Path(config_file))
    if exit_code != 0:
        raise click.Abort()


@skills.command("install")
@click.option(
    "--scope",
    type=click.Choice(["project", "user"]),
    default="project",
    show_default=True,
    help="Install to project-local or user-global agent directories.",
)
@click.option(
    "--target",
    "targets",
    multiple=True,
    type=click.Choice(SUPPORTED_TARGETS),
    help="Explicit agent target (repeatable). Auto-detect when omitted.",
)
@click.option(
    "--disable-target",
    "disable_targets",
    multiple=True,
    type=click.Choice(SUPPORTED_TARGETS),
    help="Disable one or more auto-detected targets.",
)
@click.option(
    "--skill",
    "skill_names",
    multiple=True,
    help="Install only this skill (repeatable). Omit to install all.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be installed without writing files.",
)
def skills_install(
    scope: str,
    targets: List[str],
    disable_targets: List[str],
    skill_names: List[str],
    dry_run: bool,
) -> None:
    """Deploy skills to supported AI agent directories."""
    selected_targets = resolve_targets(
        scope=scope,  # type: ignore[arg-type]
        enable_targets=list(targets),
        disable_targets=list(disable_targets),
    )
    if not selected_targets:
        click.echo(
            "No targets selected. Use --target to choose targets explicitly.",
            err=True,
        )
        raise click.Abort()

    try:
        selected_skills = resolve_skill_names(
            list(skill_names) if skill_names else None
        )
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise click.Abort()

    results = install_skills_for_targets(
        targets=selected_targets,
        scope=scope,  # type: ignore[arg-type]
        skill_names=selected_skills if skill_names else None,
        dry_run=dry_run,
    )

    for result in results:
        line = f"[{result.target}] {result.details} -> {result.path}"
        if result.dry_run:
            click.echo(f"(dry run) {line}")
        elif result.applied:
            click.secho(line, fg="green")
        else:
            click.secho(line, fg="yellow")
