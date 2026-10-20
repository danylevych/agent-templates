#!/usr/bin/env python3
"""Validate every template in this repository.

Checks what a schema cannot: the id matches the directory, the category exists, and the
instruction files are present. A template only picks skills obot already has, so it must
not ship a skills/ directory of its own.

With --mcp-catalog DIR it also checks each app key and tool name against an obot MCP
catalog directory (one *.yml per server, with entryKey and toolPreview), for example
the obot repository's catalogs/mcp. With --skill-source DIR (repeatable) it checks each
skill name against the SKILL.md files of a checked-out skill source.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = ("AGENTS.md", "SOUL.md", "IDENTITY.md")
# TOOLS.md is written by the agent host from the agent's real tools; a copy here would
# disagree with it. Skills come from obot's skill sources, never from a template.
FORBIDDEN_FILES = ("TOOLS.md", "skills")
ID_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
ALLOWED_KEYS = set(json.loads((ROOT / "schema" / "template.schema.json").read_text())["properties"])


def load_mcp_catalog(directory: Path) -> dict[str, set[str]]:
    catalog: dict[str, set[str]] = {}
    for path in sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml")):
        entry = yaml.safe_load(path.read_text()) or {}
        key = entry.get("entryKey")
        if key:
            catalog[key] = {tool["name"] for tool in entry.get("toolPreview") or [] if "name" in tool}
    return catalog


def load_skill_names(directories: list[Path]) -> set[str]:
    names: set[str] = set()
    for directory in directories:
        for skill_md in directory.rglob("SKILL.md"):
            text = skill_md.read_text()
            if text.startswith("---"):
                name = (yaml.safe_load(text.split("---", 2)[1]) or {}).get("name")
                if name:
                    names.add(name)
    return names


def validate(template_dir: Path, categories: set[str], mcp: dict[str, set[str]] | None,
             skills: set[str] | None) -> list[str]:
    errors: list[str] = []
    manifest = yaml.safe_load((template_dir / "template.yaml").read_text()) or {}

    unknown = set(manifest) - ALLOWED_KEYS
    if unknown:
        errors.append(f"unknown fields: {', '.join(sorted(unknown))}")
    for field in ("id", "name", "category", "description", "status"):
        if not manifest.get(field):
            errors.append(f"{field} is required")

    template_id = manifest.get("id", "")
    if template_id and not ID_PATTERN.match(template_id):
        errors.append(f"id {template_id!r} is not a lowercase DNS label")
    if template_id and template_id != template_dir.name:
        errors.append(f"id {template_id!r} must equal the directory name {template_dir.name!r}")
    if manifest.get("category") and manifest["category"] not in categories:
        errors.append(f"category {manifest['category']!r} is not in categories.yaml")
    if manifest.get("status") not in (None, "draft", "published"):
        errors.append(f"status must be draft or published, not {manifest['status']!r}")

    for name in REQUIRED_FILES:
        if not (template_dir / name).is_file():
            errors.append(f"{name} is missing")
    for name in FORBIDDEN_FILES:
        if (template_dir / name).exists():
            errors.append(f"{name} must not be shipped in a template")

    listed = manifest.get("skills") or []
    if len(listed) != len(set(listed)):
        errors.append("a skill is listed twice")
    if skills is not None:
        for skill in listed:
            if skill not in skills:
                errors.append(f"skill {skill!r} is in none of the given skill sources")

    seen_apps: set[str] = set()
    for app in manifest.get("apps") or []:
        key = app.get("key")
        tools = app.get("tools")
        if not key:
            errors.append("an app has no key")
            continue
        if key in seen_apps:
            errors.append(f"app {key!r} is listed twice")
        seen_apps.add(key)
        if not isinstance(tools, list):
            errors.append(f"app {key!r}: tools must be a list")
            continue
        if len(tools) != len(set(tools)):
            errors.append(f"app {key!r}: a tool is listed twice")
        if mcp is not None:
            if key not in mcp:
                errors.append(f"app {key!r}: no MCP catalog entry has this entryKey")
            else:
                missing = sorted(set(tools) - mcp[key])
                if missing:
                    errors.append(f"app {key!r}: unknown tools {', '.join(missing)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mcp-catalog", type=Path, help="obot MCP catalog directory to check app keys and tools against")
    parser.add_argument("--skill-source", type=Path, action="append", default=[],
                        help="checked-out skill source to check skill names against; repeatable")
    args = parser.parse_args()

    categories = {c["id"] for c in yaml.safe_load((ROOT / "categories.yaml").read_text())}
    mcp = load_mcp_catalog(args.mcp_catalog) if args.mcp_catalog else None
    skills = load_skill_names(args.skill_source) if args.skill_source else None

    failed = 0
    template_dirs = sorted(p.parent for p in (ROOT / "templates").glob("*/template.yaml"))
    for template_dir in template_dirs:
        errors = validate(template_dir, categories, mcp, skills)
        if errors:
            failed += 1
            print(f"✗ {template_dir.name}")
            for error in errors:
                print(f"    {error}")
        else:
            print(f"✓ {template_dir.name}")
    print(f"{len(template_dirs) - failed}/{len(template_dirs)} templates valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
