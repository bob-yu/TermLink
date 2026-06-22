import html
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


DOCS = (
    ("index.md", "index.html", "TermLink Documentation"),
    ("user-guide.md", "user-guide.html", "User Guide"),
    ("architecture.md", "architecture.html", "Architecture"),
    ("remote-access.md", "remote-access.html", "Remote Access"),
    ("automation.md", "automation.html", "Automation Interfaces"),
    ("logging.md", "logging.html", "Logging"),
    ("troubleshooting.md", "troubleshooting.html", "Troubleshooting"),
)


STYLE = """
body {
    color: #202124;
    font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
    line-height: 1.65;
    margin: 0;
    background: #f6f7f9;
}
.page {
    box-sizing: border-box;
    max-width: 1040px;
    margin: 0 auto;
    padding: 32px 28px 56px;
    background: #ffffff;
    min-height: 100vh;
}
nav {
    border-bottom: 1px solid #dfe3e8;
    margin-bottom: 24px;
    padding-bottom: 12px;
}
nav a {
    color: #1557b0;
    margin-right: 18px;
    text-decoration: none;
    font-weight: 600;
}
h1, h2, h3 {
    color: #1f2937;
    line-height: 1.25;
}
h1 { font-size: 30px; margin-top: 0; }
h2 { border-top: 1px solid #edf0f2; margin-top: 34px; padding-top: 20px; }
code {
    background: #f1f3f5;
    border-radius: 4px;
    padding: 1px 5px;
}
pre {
    background: #111827;
    border-radius: 6px;
    color: #f9fafb;
    overflow-x: auto;
    padding: 14px 16px;
}
pre code {
    background: transparent;
    padding: 0;
}
table {
    border-collapse: collapse;
    margin: 14px 0 22px;
    width: 100%;
}
th, td {
    border: 1px solid #d7dce2;
    padding: 8px 10px;
    text-align: left;
}
th { background: #f3f5f7; }
blockquote {
    border-left: 4px solid #9fb7d9;
    color: #4b5563;
    margin-left: 0;
    padding-left: 14px;
}
"""


def docs_root(project_root: Path = None) -> Path:
    if project_root:
        return project_root / "docs"

    for root in _candidate_roots():
        docs = root / "docs"
        if docs.exists():
            return docs

    return Path(__file__).resolve().parents[1] / "docs"


def html_root(project_root: Path = None) -> Path:
    return docs_root(project_root) / "html"


def _candidate_roots() -> List[Path]:
    roots = [
        Path.cwd(),
        Path(__file__).resolve().parents[1],
    ]
    if getattr(sys, "frozen", False):
        roots.insert(0, Path(sys.executable).resolve().parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
    return roots


def build_documentation(project_root: Path = None) -> Path:
    root = docs_root(project_root)
    output_root = html_root(project_root)
    output_root.mkdir(parents=True, exist_ok=True)

    for source_name, output_name, title in DOCS:
        source = root / source_name
        if not source.exists():
            continue
        output = output_root / output_name
        output.write_text(
            render_html(source.read_text(encoding="utf-8"), title),
            encoding="utf-8",
        )

    return output_root / "index.html"


def render_html(markdown_text: str, title: str) -> str:
    body = markdown_to_html(markdown_text)
    nav = (
        '<nav>'
        '<a href="index.html">Home</a>'
        '<a href="user-guide.html">User Guide</a>'
        '<a href="architecture.html">Architecture</a>'
        '<a href="remote-access.html">Remote Access</a>'
        '<a href="automation.html">Automation</a>'
        '<a href="logging.html">Logging</a>'
        '<a href="troubleshooting.html">Troubleshooting</a>'
        '</nav>'
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{STYLE}</style>\n"
        "</head>\n"
        f"<body><main class=\"page\">{nav}{body}</main></body>\n"
        "</html>\n"
    )


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    blocks: List[str] = []
    paragraph: List[str] = []
    list_items: List[str] = []
    ordered_items: List[str] = []
    in_code = False
    code_lang = ""
    code_lines: List[str] = []
    table_rows: List[str] = []

    def flush_paragraph():
        if paragraph:
            blocks.append(f"<p>{inline_markup(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list():
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    def flush_ordered_list():
        if ordered_items:
            blocks.append("<ol>" + "".join(f"<li>{item}</li>" for item in ordered_items) + "</ol>")
            ordered_items.clear()

    def flush_table():
        if table_rows:
            blocks.append(_render_table(table_rows))
            table_rows.clear()

    for raw_line in lines:
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                blocks.append(
                    f'<pre><code class="language-{html.escape(code_lang)}">'
                    f"{html.escape(chr(10).join(code_lines))}</code></pre>"
                )
                in_code = False
                code_lang = ""
                code_lines.clear()
            else:
                flush_paragraph()
                flush_list()
                flush_ordered_list()
                flush_table()
                in_code = True
                code_lang = line[3:].strip()
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            flush_table()
            continue

        if _is_table_line(line):
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            table_rows.append(line)
            continue

        flush_table()

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{inline_markup(heading.group(2))}</h{level}>")
            continue

        if line.startswith("> "):
            flush_paragraph()
            flush_list()
            flush_ordered_list()
            blocks.append(f"<blockquote>{inline_markup(line[2:])}</blockquote>")
            continue

        list_match = re.match(r"^[-*]\s+(.+)$", line)
        if list_match:
            flush_paragraph()
            flush_ordered_list()
            list_items.append(inline_markup(list_match.group(1)))
            continue

        ordered_match = re.match(r"^\d+\.\s+(.+)$", line)
        if ordered_match:
            flush_paragraph()
            flush_list()
            ordered_items.append(inline_markup(ordered_match.group(1)))
            continue

        flush_ordered_list()
        paragraph.append(line.strip())

    if in_code:
        blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    flush_list()
    flush_ordered_list()
    flush_table()
    return "\n".join(blocks)


def inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _render_table(rows: Iterable[str]) -> str:
    parsed = [_split_table_row(row) for row in rows]
    if len(parsed) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in parsed[1]):
        header = parsed[0]
        body = parsed[2:]
    else:
        header = []
        body = parsed

    parts = ["<table>"]
    if header:
        parts.append("<thead><tr>" + "".join(f"<th>{inline_markup(cell.strip())}</th>" for cell in header) + "</tr></thead>")
    if body:
        parts.append("<tbody>")
        for row in body:
            parts.append("<tr>" + "".join(f"<td>{inline_markup(cell.strip())}</td>" for cell in row) + "</tr>")
        parts.append("</tbody>")
    parts.append("</table>")
    return "".join(parts)


def _split_table_row(row: str) -> List[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


if __name__ == "__main__":
    print(build_documentation())

