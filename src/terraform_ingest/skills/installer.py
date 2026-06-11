"""Install and manage terraform-ingest agent skills."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from terraform_ingest import SCRIPT_PATH

InstallScope = Literal["project", "user"]

SUPPORTED_TARGETS = [
    "opencode",
    "hermes",
    "openclaw",
    "claude_code",
    "cursor",
    "github_copilot",
    "windsurf",
    "codex",
]


class TargetPaths(BaseModel):
    """Paths for skill deployment in each scope."""

    project_skills_path: str = Field(
        ..., description="Project-local skills destination"
    )
    user_skills_path: str = Field(..., description="User-global skills destination")


class InstallResult(BaseModel):
    """Summary for a single target installation."""

    target: str
    scope: InstallScope
    applied: bool
    path: str
    details: str
    dry_run: bool = False


class SkillValidationResult(BaseModel):
    """Result of validating a single skill directory."""

    name: str
    valid: bool
    errors: List[str] = Field(default_factory=list)


TARGET_PATHS: Dict[str, TargetPaths] = {
    "opencode": TargetPaths(
        project_skills_path=".opencode/skills",
        user_skills_path="~/.config/opencode/skills",
    ),
    "hermes": TargetPaths(
        project_skills_path=".hermes/skills",
        user_skills_path="~/.config/hermes/skills",
    ),
    "openclaw": TargetPaths(
        project_skills_path=".openclaw/skills",
        user_skills_path="~/.config/openclaw/skills",
    ),
    "claude_code": TargetPaths(
        project_skills_path=".claude/skills",
        user_skills_path="~/.claude/skills",
    ),
    "cursor": TargetPaths(
        project_skills_path=".cursor/skills",
        user_skills_path="~/.cursor/skills",
    ),
    "github_copilot": TargetPaths(
        project_skills_path=".github/skills",
        user_skills_path="~/.copilot/skills",
    ),
    "windsurf": TargetPaths(
        project_skills_path=".windsurf/skills",
        user_skills_path="~/.codeium/windsurf/skills",
    ),
    "codex": TargetPaths(
        project_skills_path=".agents/skills",
        user_skills_path="~/.agents/skills",
    ),
}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def resolve_skills_root(start: Optional[Path] = None) -> Path:
    """Resolve the canonical skills directory for this repo or install."""
    env_path = os.getenv("TERRAFORM_INGEST_SKILLS")
    if env_path:
        return Path(os.path.expanduser(env_path)).resolve()

    candidate = (start or Path.cwd()) / "skills"
    if candidate.is_dir() and any(candidate.iterdir()):
        return candidate.resolve()

    bundled = SCRIPT_PATH / "data" / "skills"
    if bundled.is_dir() and any(bundled.iterdir()):
        return bundled.resolve()

    return candidate.resolve()


def list_skills(root: Optional[Path] = None) -> List[str]:
    """Return skill directory names that contain SKILL.md."""
    skills_root = root or resolve_skills_root()
    if not skills_root.exists():
        return []
    names: List[str] = []
    for item in sorted(skills_root.iterdir()):
        if item.is_dir() and (item / "SKILL.md").is_file():
            names.append(item.name)
    return names


def skill_markdown(skill_name: str, root: Optional[Path] = None) -> Optional[str]:
    """Load SKILL.md content for a skill."""
    skill_file = (root or resolve_skills_root()) / skill_name / "SKILL.md"
    if not skill_file.exists():
        return None
    return skill_file.read_text(encoding="utf-8")


def resolve_skill_names(
    skill_names: Optional[List[str]], root: Optional[Path] = None
) -> List[str]:
    """Validate and resolve skill names for install."""
    available = list_skills(root)
    if not skill_names:
        return available
    unknown = sorted({name for name in skill_names if name not in available})
    if unknown:
        available_text = ", ".join(available) if available else "(none)"
        raise ValueError(
            f"Unknown skill(s): {', '.join(unknown)}. Available: {available_text}"
        )
    return list(dict.fromkeys(skill_names))


def parse_skill_frontmatter(content: str) -> dict[str, str]:
    """Parse YAML-like frontmatter from SKILL.md."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def validate_skill(
    skill_name: str, root: Optional[Path] = None
) -> SkillValidationResult:
    """Validate a skill directory follows Claude Code skill format."""
    skills_root = root or resolve_skills_root()
    skill_dir = skills_root / skill_name
    errors: List[str] = []

    if not skill_dir.is_dir():
        return SkillValidationResult(
            name=skill_name,
            valid=False,
            errors=[f"Skill directory not found: {skill_dir}"],
        )

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        errors.append("Missing SKILL.md")
        return SkillValidationResult(name=skill_name, valid=False, errors=errors)

    content = skill_file.read_text(encoding="utf-8")
    if not _FRONTMATTER_RE.match(content):
        errors.append("SKILL.md must begin with YAML frontmatter (--- ... ---)")
    else:
        frontmatter = parse_skill_frontmatter(content)
        if not frontmatter.get("name"):
            errors.append("Frontmatter missing required field: name")
        elif frontmatter["name"] != skill_name:
            errors.append(
                f"Frontmatter name '{frontmatter['name']}' must match directory '{skill_name}'"
            )
        if not frontmatter.get("description"):
            errors.append("Frontmatter missing required field: description")

    return SkillValidationResult(name=skill_name, valid=not errors, errors=errors)


def resolve_targets(
    scope: InstallScope,
    enable_targets: List[str],
    disable_targets: List[str],
) -> List[str]:
    """Resolve install targets by explicit include/exclude or auto-detection."""
    disabled = set(disable_targets)
    if enable_targets:
        return [target for target in enable_targets if target not in disabled]
    detected = autodetect_targets(scope=scope)
    return [target for target in detected if target not in disabled]


def autodetect_targets(scope: InstallScope) -> List[str]:
    """Detect target applications by existing config/directories."""
    resolved: List[str] = []
    for target in SUPPORTED_TARGETS:
        target_paths = TARGET_PATHS[target]
        candidate = _expand_target_path(
            target_paths.project_skills_path
            if scope == "project"
            else target_paths.user_skills_path
        )
        if candidate.exists() or candidate.parent.exists():
            resolved.append(target)
    return resolved


def install_skills_for_targets(
    targets: List[str],
    scope: InstallScope,
    skill_names: Optional[List[str]] = None,
    *,
    root: Optional[Path] = None,
    dry_run: bool = False,
) -> List[InstallResult]:
    """Install skills for selected agent targets."""
    source_root = root or resolve_skills_root()
    results: List[InstallResult] = []
    if not source_root.exists():
        return [
            InstallResult(
                target="all",
                scope=scope,
                applied=False,
                path=str(source_root),
                details="Skills directory not found",
            )
        ]

    selected_skills = resolve_skill_names(skill_names, source_root)
    if not selected_skills:
        return [
            InstallResult(
                target="all",
                scope=scope,
                applied=False,
                path=str(source_root),
                details="No skills available to install",
            )
        ]

    for target in targets:
        target_paths = TARGET_PATHS[target]
        destination = _expand_target_path(
            target_paths.project_skills_path
            if scope == "project"
            else target_paths.user_skills_path
        )
        if not dry_run:
            destination.mkdir(parents=True, exist_ok=True)

        installed_names: List[str] = []
        for skill_name in selected_skills:
            source_skill = source_root / skill_name
            if not source_skill.is_dir():
                continue
            dest_skill = destination / skill_name
            if dry_run:
                installed_names.append(skill_name)
                continue
            if dest_skill.exists():
                shutil.rmtree(dest_skill)
            shutil.copytree(source_skill, dest_skill)
            installed_names.append(skill_name)

        verb = "Would install" if dry_run else "Installed"
        if len(installed_names) == 1:
            details = f"{verb} skill '{installed_names[0]}'"
        elif installed_names:
            details = (
                f"{verb} {len(installed_names)} skills: {', '.join(installed_names)}"
            )
        else:
            details = "No skills installed"

        results.append(
            InstallResult(
                target=target,
                scope=scope,
                applied=bool(installed_names),
                path=str(destination),
                details=details,
                dry_run=dry_run,
            )
        )
    return results


def _expand_target_path(path_value: str) -> Path:
    expanded = Path(os.path.expanduser(path_value))
    return expanded if expanded.is_absolute() else Path.cwd() / expanded
