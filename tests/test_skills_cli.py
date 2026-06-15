"""Tests for terraform-ingest skills CLI commands."""

from pathlib import Path

from click.testing import CliRunner

from terraform_ingest.cli import cli
from terraform_ingest.skills import list_skills, validate_skill

REPO_SKILLS = Path(__file__).resolve().parent.parent / "skills"


def test_list_skills_finds_bundled_workflow_skills() -> None:
    names = list_skills()
    assert "terraform-ingest" in names
    assert "terraform-ingest-setup" in names
    assert "terraform-ingest-configure" in names
    assert "terraform-ingest-ingest" in names


def test_validate_all_skills_pass() -> None:
    for name in list_skills():
        result = validate_skill(name)
        assert result.valid, f"{name}: {result.errors}"


def test_skills_list_cli() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["skills", "list"])
    assert result.exit_code == 0
    assert "terraform-ingest" in result.output


def test_skills_show_cli() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["skills", "show", "terraform-ingest"])
    assert result.exit_code == 0
    assert "name: terraform-ingest" in result.output


def test_skills_path_cli() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["skills", "path"])
    assert result.exit_code == 0
    assert Path(result.output.strip()).name == "skills"


def test_skills_install_project_target() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        for name in ["terraform-ingest"]:
            dest = Path("skills") / name
            dest.mkdir(parents=True)
            (dest / "SKILL.md").write_text(
                (REPO_SKILLS / name / "SKILL.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

        result = runner.invoke(
            cli,
            [
                "skills",
                "install",
                "--scope",
                "project",
                "--target",
                "cursor",
                "--skill",
                "terraform-ingest",
            ],
        )
        assert result.exit_code == 0
        assert Path(".cursor/skills/terraform-ingest/SKILL.md").exists()


def test_skills_install_dry_run() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        name = "terraform-ingest"
        dest = Path("skills") / name
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text(
            (REPO_SKILLS / name / "SKILL.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        result = runner.invoke(
            cli,
            [
                "skills",
                "install",
                "--scope",
                "project",
                "--target",
                "cursor",
                "--skill",
                name,
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "dry run" in result.output
        assert not Path(".cursor/skills").exists()


def test_skills_install_unknown_skill_fails() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["skills", "install", "--target", "cursor", "--skill", "not-a-skill"],
    )
    assert result.exit_code != 0
    assert "Unknown skill" in result.output
