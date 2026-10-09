"""Build the Root Cause Analysis teaching guide PDF.

A student-facing companion to the Complete Code Documentation. That document
walks every file; this one follows a single question - how does an anomaly score
become an explanation someone can act on - through the six stages that answer it.

    python tools/build_rca_teaching_guide.py

Prose lives in `rca_teaching_content.py`; every code fragment is quoted from the
live source tree at build time, so the guide cannot drift from the code.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from doc_blocks import CSS, ROOT  # noqa: E402
from rca_teaching_content import DOCUMENT  # noqa: E402

OUTPUT_PDF = ROOT / "documents" / "CARCI_Root_Cause_Analysis_Teaching_Guide.pdf"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CARCI - Root Cause Analysis Teaching Guide</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def find_chrome(explicit: str | None) -> str:
    if explicit:
        if not Path(explicit).is_file():
            sys.exit("No browser at {}".format(explicit))
        return explicit
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    sys.exit(
        "Could not find Chrome or Edge. Pass one with --chrome, for example:\n"
        '  python tools/build_code_documentation.py --chrome "C:\\Path\\To\\chrome.exe"'
    )


def build_html() -> str:
    return PAGE_TEMPLATE.format(css=CSS, body="\n".join(DOCUMENT))


def render_pdf(browser: str, html_path: Path, pdf_path: Path) -> None:
    # A fresh profile directory keeps the print from attaching to a running
    # Chrome instance, which would return before the PDF was written.
    with tempfile.TemporaryDirectory() as profile:
        command = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            "--user-data-dir={}".format(profile),
            "--print-to-pdf={}".format(pdf_path),
            html_path.as_uri(),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    if not pdf_path.is_file():
        sys.exit(
            "Chrome did not produce a PDF.\n"
            "exit code: {}\nstderr:\n{}".format(result.returncode, result.stderr[:2000])
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chrome", help="path to a Chrome or Edge binary")
    parser.add_argument("--output", default=str(OUTPUT_PDF), help="destination PDF")
    parser.add_argument("--html", help="also write the intermediate HTML here")
    args = parser.parse_args()

    browser = find_chrome(args.chrome)
    html_text = build_html()
    pdf_path = Path(args.output).resolve()

    if args.html:
        Path(args.html).write_text(html_text, encoding="utf-8")

    with tempfile.TemporaryDirectory() as workspace:
        html_path = Path(workspace) / "carci_documentation.html"
        html_path.write_text(html_text, encoding="utf-8")
        render_pdf(browser, html_path, pdf_path)

    size_kb = pdf_path.stat().st_size / 1024
    print("Wrote {} ({:.0f} KB)".format(pdf_path, size_kb))


if __name__ == "__main__":
    main()
