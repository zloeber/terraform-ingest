"""Validate a terraform-ingest YAML configuration file."""

import sys
from pathlib import Path

import yaml

from terraform_ingest.models import IngestConfig


def _check_dir_writable(path_str: str, label: str) -> str | None:
    """Create directory if needed and verify write access."""
    path = Path(path_str)
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".terraform_ingest_write_probe"
        probe.touch()
        probe.unlink()
    except OSError as exc:
        return f"{label} not writable ({path_str}): {exc}"
    return None


def _check_parent_writable(path_str: str, label: str) -> str | None:
    """Verify parent directory is writable without creating the target path."""
    path = Path(path_str)
    parent = path.parent if path.name else path
    try:
        parent.mkdir(parents=True, exist_ok=True)
        probe = parent / ".terraform_ingest_write_probe"
        probe.touch()
        probe.unlink()
    except OSError as exc:
        return f"{label} parent not writable ({parent}): {exc}"
    return None


def validate_config(config_path: Path) -> int:
    """Validate config file. Returns 0 on success, 1 on failure."""
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        with open(config_path) as file:
            data = yaml.safe_load(file) or {}
        config = IngestConfig.model_validate(data)
    except Exception as exc:
        print(f"ERROR: Invalid configuration: {exc}", file=sys.stderr)
        return 1

    warnings: list[str] = []
    errors: list[str] = []

    if not config.repositories:
        warnings.append("repositories is empty — ingestion will produce no modules")

    for label, path_str in [
        ("output_dir", config.output_dir),
        ("clone_dir", config.clone_dir),
    ]:
        error = _check_dir_writable(path_str, label)
        if error:
            errors.append(error)

    if config.embedding and config.embedding.enabled:
        error = _check_parent_writable(
            config.embedding.chromadb_path, "embedding.chromadb_path"
        )
        if error:
            errors.append(error)

    for warning in warnings:
        print(f"WARN: {warning}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    repo_count = len(config.repositories)
    embedding = config.embedding.enabled if config.embedding else False
    print(f"OK: config valid — {repo_count} repositories, embedding={embedding}")
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <config.yaml>", file=sys.stderr)
        sys.exit(2)
    sys.exit(validate_config(Path(sys.argv[1])))
