"""Agent skill discovery, validation, and deployment."""

from terraform_ingest.skills.installer import (
    SUPPORTED_TARGETS,
    InstallResult,
    autodetect_targets,
    install_skills_for_targets,
    list_skills,
    resolve_skill_names,
    resolve_skills_root,
    resolve_targets,
    skill_markdown,
    validate_skill,
)
from terraform_ingest.skills.validate_config import validate_config

__all__ = [
    "SUPPORTED_TARGETS",
    "InstallResult",
    "autodetect_targets",
    "install_skills_for_targets",
    "list_skills",
    "resolve_skill_names",
    "resolve_skills_root",
    "resolve_targets",
    "skill_markdown",
    "validate_config",
    "validate_skill",
]
