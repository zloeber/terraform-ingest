#!/usr/bin/env python3
"""Validate every bundled SKILL.md under skills/."""

from __future__ import annotations

import sys
from pathlib import Path

from terraform_ingest.skills import list_skills, validate_skill


def main() -> int:
    skills_root = Path("skills")
    if not skills_root.is_dir():
        print("ERROR: skills/ directory not found", file=sys.stderr)
        return 2

    names = list_skills(skills_root)
    if not names:
        print("ERROR: no skills found under skills/", file=sys.stderr)
        return 2

    failed = False
    for name in names:
        result = validate_skill(name, skills_root)
        if result.valid:
            print(f"PASS: {name}")
            continue
        failed = True
        print(f"FAIL: {name}", file=sys.stderr)
        for error in result.errors:
            print(f"  - {error}", file=sys.stderr)

    if failed:
        return 1

    print(f"PASS: skills_validate — {len(names)}/{len(names)} skills passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
