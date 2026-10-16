#!/usr/bin/env python3
"""Write docs/llms-full.txt from each sitemap URL's opening lines. No new claims."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ORIGIN = "https://linus10x.github.io/finserv-agent-audit"


def opening(text: str) -> tuple[str, str]:
    title = ""
    paras = []
    buf = []
    for ln in text.splitlines():
        if ln.startswith("# ") and not title:
            title = ln[2:].strip()
            continue
        if ln.startswith("## "):
            break
        if ln.strip() in ("---", ""):
            if buf:
                paras.append(" ".join(buf))
                buf = []
            if len(paras) >= 2:
                break
            continue
        buf.append(ln.strip())
    if buf and len(paras) < 2:
        paras.append(" ".join(buf))
    body = " ".join(paras)
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"[*_`>#]", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    return title, body[:480]


def render() -> str:
    locs = re.findall(r"<loc>(.*?)</loc>", (DOCS / "sitemap.xml").read_text())
    parts = [
        "# finserv-agent-audit",
        "",
        "> Opening lines of each docs page, copied from the markdown. "
        "This file does not add prices, customers, reviews, or a street address.",
        "",
    ]
    for loc in locs:
        rel = loc[len(ORIGIN) :].strip("/")
        path = DOCS / "index.md" if not rel else DOCS / f"{rel}.md"
        if not path.is_file():
            parts += [f"## {loc}", "", "(no matching markdown file)", ""]
            continue
        title, body = opening(path.read_text(encoding="utf-8"))
        parts += [f"## {loc}", "", title, "", body, ""]
    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    out = DOCS / "llms-full.txt"
    out.write_text(render(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
