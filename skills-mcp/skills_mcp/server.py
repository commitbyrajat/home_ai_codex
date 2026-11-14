"""Expose SKILL.md files without allowing access outside the skills directory."""

import os
from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("Local Skills", instructions="List available skills, then read a skill's instructions using its id.")
READONLY = ToolAnnotations(readOnlyHint=True)


def skills_root() -> Path:
    return Path(os.environ.get("SKILLS_DIR", "~/.skills")).expanduser().resolve()


def skill_files() -> dict[str, Path]:
    root = skills_root()
    if not root.is_dir():
        raise ValueError(f"Skills directory does not exist: {root}")
    return {
        path.parent.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("SKILL.md"))
        if path.is_file() and path.resolve().is_relative_to(root)
    }


@mcp.tool(annotations=READONLY)
def list_skills() -> list[dict[str, str]]:
    """List skills recursively, returning an id and relative SKILL.md path for each."""
    return [
        {"id": skill_id, "path": path.relative_to(skills_root()).as_posix()}
        for skill_id, path in skill_files().items()
    ]


@mcp.tool(annotations=READONLY)
def get_skill(skill_id: str) -> str:
    """Return the full SKILL.md text for an exact id returned by list_skills."""
    path = skill_files().get(skill_id)
    if path is None:
        raise ValueError(f"Unknown skill: {skill_id}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    mcp.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")


if __name__ == "__main__":
    main()
