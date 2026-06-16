#!/usr/bin/env python3
"""Render the participant guide (docs/lab-guide/README.md) into ONE self-contained HTML file
for the per-workspace lab-guide app: markdown -> HTML, screenshots inlined as data URIs (no
binary files in the courseware zip — workspace import of arbitrary binaries is unproven), and a
clean Databricks-flavored reading shell. Called by build_zips.sh; output is a build artifact
(gitignored).

Usage: python3 render_guide.py <guide_md> <img_dir> <out_html>
"""
import base64
import pathlib
import re
import sys

import markdown

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #f6f7f9; color: #1b3139;
       font: 16px/1.65 -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }
.wrap { max-width: 880px; margin: 0 auto; padding: 48px 28px 96px; }
h1, h2, h3 { line-height: 1.25; color: #0b2026; }
h1 { font-size: 30px; border-bottom: 3px solid #ff3621; padding-bottom: 12px; }
h2 { font-size: 23px; margin-top: 44px; border-bottom: 1px solid #d8dde1; padding-bottom: 6px; }
h3 { font-size: 18px; margin-top: 28px; }
a { color: #2272b4; }
code { background: #eceef0; border-radius: 4px; padding: 2px 6px;
       font: 13.5px/1.5 'SF Mono', Menlo, Consolas, monospace; }
pre { background: #0b2026; color: #e8eaec; padding: 16px 18px; border-radius: 8px;
      overflow-x: auto; }
pre code { background: none; color: inherit; padding: 0; }
blockquote { border-left: 4px solid #ff3621; margin: 16px 0; padding: 8px 18px;
             background: #fff3f1; border-radius: 0 8px 8px 0; }
blockquote p { margin: 6px 0; }
table { border-collapse: collapse; width: 100%; margin: 18px 0; font-size: 14.5px; }
th, td { border: 1px solid #d8dde1; padding: 9px 12px; text-align: left; vertical-align: top; }
th { background: #eceef0; }
img { max-width: 100%; border: 1px solid #d8dde1; border-radius: 10px;
      box-shadow: 0 6px 24px rgba(11, 32, 38, 0.12); margin: 10px 0; }
hr { border: none; border-top: 1px solid #d8dde1; margin: 36px 0; }
.topnav { position: sticky; top: 0; background: #0b2026; color: #fff; padding: 10px 28px;
          display: flex; gap: 18px; align-items: center; font-size: 14px; z-index: 10; }
.topnav a { color: #9fd4ea; text-decoration: none; }
.topnav .brand { font-weight: 700; color: #fff; }
.topnav .spacer { flex: 1; }
"""


def main() -> int:
    guide_md, img_dir, out_html = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
    src = pathlib.Path(guide_md).read_text()

    html_body = markdown.markdown(src, extensions=["tables", "fenced_code", "sane_lists"])

    # Inline every referenced screenshot as a data URI.
    def inline(m: re.Match) -> str:
        rel = m.group(1)
        p = img_dir / pathlib.Path(rel).name
        if not p.is_file():
            print(f"  WARNING: missing image {rel}")
            return m.group(0)
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f'src="data:image/png;base64,{b64}"'

    html_body, n = re.subn(r'src="img/([^"]+)"', inline, html_body)

    out = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lab Guide — Build a Custom AI Agent on Databricks Apps</title>
<style>{CSS}</style></head>
<body>
<nav class="topnav"><span class="brand">🛠️ Agent Apps Lab</span>
<a href="/">Guide</a> <a href="/deck">Field-guide deck</a>
<span class="spacer"></span><span>DAIS 2026</span></nav>
<div class="wrap">
{html_body}
</div>
</body></html>"""
    pathlib.Path(out_html).write_text(out)
    print(f"  rendered guide.html ({len(out)//1024} KB, {n} images inlined)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
