import tempfile
import unittest
from pathlib import Path

from utils.docs_builder import build_documentation, markdown_to_html, render_html


class DocsBuilderTest(unittest.TestCase):
    def test_markdown_to_html_basic_blocks(self):
        html = markdown_to_html(
            "# Title\n\n"
            "1. first\n"
            "2. second\n\n"
            "- item\n\n"
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n\n"
            "Use `code` and **bold**."
        )

        self.assertIn("<h1>Title</h1>", html)
        self.assertIn("<ol><li>first</li><li>second</li></ol>", html)
        self.assertIn("<li>item</li>", html)
        self.assertIn("<table>", html)
        self.assertIn("<code>code</code>", html)
        self.assertIn("<strong>bold</strong>", html)

    def test_render_html_has_navigation(self):
        page = render_html("# Title", "Doc")

        self.assertIn("architecture.html", page)
        self.assertIn("<main", page)

    def test_build_documentation_outputs_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "index.md").write_text("# Home", encoding="utf-8")
            (docs / "architecture.md").write_text("# Arch", encoding="utf-8")
            (docs / "user-guide.md").write_text("# Guide", encoding="utf-8")

            index = build_documentation(root)

            self.assertTrue(index.exists())
            self.assertTrue((docs / "html" / "architecture.html").exists())
            self.assertIn("Home", index.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
