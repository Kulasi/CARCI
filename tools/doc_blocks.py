"""Layout primitives and styling for the CARCI code documentation PDF.

Values here match the first edition of the document so that the regenerated PDF
is visually the same publication: Segoe UI for prose, Consolas for code, the
#047857 / #0f766e teal used by the app header.
"""

from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }

* { box-sizing: border-box; }

body {
    font-family: "Segoe UI", "Segoe UI Web", Tahoma, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #12181f;
    margin: 0;
}

/* ---------- cover ---------- */
.cover { height: 247mm; display: flex; flex-direction: column;
         align-items: center; justify-content: center; text-align: center; }
.cover h1 { font-size: 36pt; font-weight: 700; color: #047857;
            margin: 0; letter-spacing: 0.01em; }
.cover .sub { font-size: 15pt; color: #12181f; margin: 0.5rem 0 0; }
.cover .rule { width: 60px; height: 3px; background: #0f766e;
               margin: 1.9rem auto 1.7rem; }
.cover .doc { font-size: 14pt; color: #12181f; font-weight: 600; margin: 0; }
.cover .tag { font-size: 11pt; color: #5b6672; margin: 0.45rem 0 0; }
.cover .meta { margin-top: 3rem; font-size: 9.5pt; color: #5b6672; line-height: 1.75; }

/* ---------- contents ---------- */
h2.contents-title { font-size: 16pt; color: #047857; font-weight: 700;
                    margin: 0 0 0.35rem; border-bottom: 1.5px solid #0f766e;
                    padding-bottom: 0.45rem; }
.toc-1 { margin: 0.75rem 0 0; font-size: 10pt; font-weight: 600; }
.toc-1 .n { color: #0f766e; }
.toc-2 { margin: 0.18rem 0 0 1.45rem; font-size: 9.2pt; color: #5b6672; }
.toc-2 .n { color: #9aa5b1; }

/* ---------- chapters ---------- */
.chapter { page-break-before: always; }
h2.chapter-title { font-size: 16pt; font-weight: 700; color: #047857;
                   margin: 0 0 0.4rem; border-bottom: 1.5px solid #0f766e;
                   padding-bottom: 0.5rem; }
h2.chapter-title .num { color: #0f766e; margin-right: 0.85rem; }
h2.chapter-title code { font-family: Consolas, "Courier New", monospace;
                        font-size: 14.7pt; color: #047857; font-weight: 700; }

h3 { font-size: 12.6pt; color: #0f766e; font-weight: 700;
     margin: 1.5rem 0 0.5rem; page-break-after: avoid; }
h4 { font-size: 10.5pt; font-weight: 700; color: #12181f;
     margin: 1.15rem 0 0.35rem; page-break-after: avoid; }
p { margin: 0 0 0.6rem; }

/* file identity card at the head of each source chapter */
.filecard { background: #f0fdfa; border: 1px solid #cfe9e4; border-radius: 6px;
            padding: 0.7rem 0.9rem; margin: 0.9rem 0 1.1rem; }
.filecard .name { font-family: Consolas, "Courier New", monospace;
                  font-size: 11pt; font-weight: 700; color: #047857; }
.filecard .facts { font-size: 9.3pt; color: #5b6672; margin-top: 0.2rem; }

/* callouts */
.note { background: #f0fdfa; border-left: 3px solid #0f766e; border-radius: 3px;
        padding: 0.75rem 0.95rem; margin: 0.9rem 0; page-break-inside: avoid; }
.note .head { font-weight: 700; font-size: 9.9pt; margin-bottom: 0.3rem; }
.warn { background: #fffbeb; border-left: 3px solid #d97706; }
.warn .head { color: #92400e; }
.new { background: #eef6ff; border-left: 3px solid #2f54eb; }
.new .head { color: #1d39c4; }

code { font-family: Consolas, "Courier New", monospace;
       font-size: 9.3pt; color: #9333ea; }

/* source listings: gray line numbers, undecorated dark code, as in edition 1 */
.code { border: 1px solid #e2e8f0; border-radius: 5px; background: #fcfdfe;
        margin: 0.7rem 0 0.9rem; padding: 0.5rem 0.2rem 0.5rem 0; overflow: hidden; }
.code table { border-collapse: collapse; width: 100%; }
.code td { font-family: Consolas, "Courier New", monospace; font-size: 7.9pt;
           line-height: 1.42; vertical-align: top; padding: 0; }
.code td.ln { width: 2.9rem; text-align: right; padding-right: 0.7rem;
              color: #9aa5b1; }
.code td.src { color: #1e2530; white-space: pre-wrap; word-break: break-word;
               padding-right: 0.7rem; }

/* ascii diagrams and snippets without line numbers */
pre.diagram { border: 1px solid #e2e8f0; border-radius: 5px; background: #fcfdfe;
              font-family: Consolas, "Courier New", monospace; font-size: 8.1pt;
              line-height: 1.45; color: #1e2530; padding: 0.75rem 0.9rem;
              margin: 0.7rem 0 0.9rem; white-space: pre; overflow: hidden;
              page-break-inside: avoid; }

table.data { border-collapse: collapse; width: 100%; font-size: 9.3pt;
             margin: 0.6rem 0 1rem; page-break-inside: avoid; }
table.data th { text-align: left; font-weight: 600; color: #047857;
                border-bottom: 1.5px solid #0f766e; padding: 0.35rem 0.5rem; }
table.data td { border-bottom: 1px solid #e8edf2; padding: 0.35rem 0.5rem;
                vertical-align: top; }
table.data td code, table.data th code { font-size: 8.6pt; }

/* a quoted fragment of a real file, captioned with where it came from */
.excerpt { margin: 0.8rem 0 1rem; page-break-inside: avoid; }
.excerpt-cap { font-family: Consolas, "Courier New", monospace; font-size: 8pt;
               color: #5b6672; background: #f1f5f9; border: 1px solid #e2e8f0;
               border-bottom: none; border-radius: 5px 5px 0 0;
               padding: 0.3rem 0.7rem; }
.excerpt .code { margin: 0; border-radius: 0 0 5px 5px; }

/* step banner used to number the stages of the pipeline */
.stage { background: #0f766e; color: #ffffff; border-radius: 5px;
         padding: 0.4rem 0.8rem; margin: 1.4rem 0 0.7rem;
         font-size: 9.6pt; font-weight: 700; letter-spacing: 0.02em;
         page-break-after: avoid; }

ol, ul { margin: 0.3rem 0 0.7rem; padding-left: 1.35rem; }
li { margin-bottom: 0.28rem; }
em { font-style: italic; }
strong { font-weight: 700; }
.small { font-size: 9.3pt; color: #5b6672; }
"""


def read_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def line_count(relative_path: str) -> int:
    return len(read_source(relative_path).splitlines())


def source_listing(relative_path: str) -> str:
    """Render a file from disk as a numbered listing.

    Reading at build time is the whole point of this script: the listing cannot
    drift away from the code the way a pasted copy did.
    """
    rows = []
    for number, line in enumerate(read_source(relative_path).splitlines(), start=1):
        rows.append(
            '<tr><td class="ln">{}</td><td class="src">{}</td></tr>'.format(
                number, html.escape(line) or "&nbsp;"
            )
        )
    return '<div class="code"><table>' + "".join(rows) + "</table></div>"


def filecard(relative_path: str, role: str) -> str:
    return (
        '<div class="filecard">'
        '<div class="name">{}</div>'
        '<div class="facts">{} lines &nbsp;&middot;&nbsp; {}</div>'
        "</div>"
    ).format(html.escape(relative_path), line_count(relative_path), role)


def diagram(text: str) -> str:
    return '<pre class="diagram">' + html.escape(text.strip("\n")) + "</pre>"


def snippet(text: str) -> str:
    """A short illustrative code sample with line numbers, not read from disk."""
    rows = []
    for number, line in enumerate(text.strip("\n").splitlines(), start=1):
        rows.append(
            '<tr><td class="ln">{}</td><td class="src">{}</td></tr>'.format(
                number, html.escape(line) or "&nbsp;"
            )
        )
    return '<div class="code"><table>' + "".join(rows) + "</table></div>"


def table(headers, rows) -> str:
    head = "".join("<th>{}</th>".format(h) for h in headers)
    body = "".join(
        "<tr>" + "".join("<td>{}</td>".format(cell) for cell in row) + "</tr>"
        for row in rows
    )
    return (
        '<table class="data"><thead><tr>{}</tr></thead><tbody>{}</tbody></table>'
    ).format(head, body)


def note(head: str, body: str, kind: str = "") -> str:
    css_class = "note " + kind if kind else "note"
    return '<div class="{}"><div class="head">{}</div>{}</div>'.format(css_class, head, body)


def chapter(number: int, title_html: str, body: str) -> str:
    return (
        '<div class="chapter"><h2 class="chapter-title">'
        '<span class="num">{}</span>{}</h2>{}</div>'
    ).format(number, title_html, body)


def source_chapter(number: int, relative_path: str, subtitle: str, role: str, prose: str) -> str:
    """A chapter documenting one file: prose first, then the complete listing."""
    title = "<code>{}</code> &nbsp;&mdash; {}".format(html.escape(relative_path), subtitle)
    body = (
        filecard(relative_path, role)
        + prose
        + "<h3>{}.2 &nbsp; Complete source code</h3>".format(number)
        + source_listing(relative_path)
    )
    return chapter(number, title, body)


def excerpt(relative_path: str, start: int, end: int, caption: str = "") -> str:
    """Render lines `start`..`end` of a file, keeping the real line numbers.

    Teaching material quotes fragments rather than whole files, and a fragment
    renumbered from 1 cannot be found in the editor. Reading from disk keeps the
    quote honest; keeping the original numbers keeps it locatable.
    """
    lines = read_source(relative_path).splitlines()
    rows = []
    for number in range(start, min(end, len(lines)) + 1):
        rows.append(
            '<tr><td class="ln">{}</td><td class="src">{}</td></tr>'.format(
                number, html.escape(lines[number - 1]) or "&nbsp;"
            )
        )
    label = caption or "{} lines {}-{}".format(relative_path, start, end)
    return (
        '<div class="excerpt"><div class="excerpt-cap">{}</div>'
        '<div class="code"><table>{}</table></div></div>'
    ).format(html.escape(label), "".join(rows))
