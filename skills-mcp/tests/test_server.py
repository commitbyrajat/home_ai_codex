import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastmcp import Client
from skills_mcp.server import get_skill, list_skills, mcp


class SkillsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "skills"
        self.root.mkdir()
        self.environment = patch.dict(os.environ, SKILLS_DIR=str(self.root))
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def add_skill(self, name, content="# Example\nInstructions"):
        path = self.root / name / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text(content, encoding="utf-8")

    async def test_mcp_discovery_and_read(self):
        self.add_skill("nested/example")
        async with Client(mcp) as client:
            self.assertEqual(
                {tool.name for tool in await client.list_tools()},
                {"list_skills", "get_skill"},
            )
            listing = await client.call_tool("list_skills", {})
            self.assertFalse(listing.is_error)
            self.assertIn("nested/example", str(listing.content))
            result = await client.call_tool("get_skill", {"skill_id": "nested/example"})
            self.assertFalse(result.is_error)
            self.assertEqual(result.content[0].text, "# Example\nInstructions")

    async def test_boundaries_and_live_edits(self):
        self.assertEqual(list_skills(), [])
        self.add_skill("example")
        outside = self.root.parent / "outside.md"
        outside.write_text("private", encoding="utf-8")
        (self.root / "escape").mkdir()
        (self.root / "escape" / "SKILL.md").symlink_to(outside)
        self.assertEqual(list_skills(), [{"id": "example", "path": "example/SKILL.md"}])
        for invalid in ("../outside.md", "escape", "/etc/passwd", "missing"):
            with self.assertRaises(ValueError):
                get_skill(invalid)
        (self.root / "example" / "SKILL.md").write_text("updated", encoding="utf-8")
        self.assertEqual(get_skill("example"), "updated")

    async def test_missing_directory(self):
        self.root.rmdir()
        with self.assertRaisesRegex(ValueError, "does not exist"):
            list_skills()


if __name__ == "__main__":
    unittest.main()
