#!/usr/bin/env python3
"""SEO checks for the finserv docs crawl files. Exits non-zero on failure."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_llms_full  # noqa: E402

BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"]
errors = []


def fail(msg):
    errors.append(msg)


def main():
    robots = (ROOT / "docs" / "robots.txt").read_text()
    for bot in BOTS:
        if f"User-agent: {bot}\nAllow: /\n" not in robots:
            fail(f"robots.txt does not allow {bot}")
    llms = (ROOT / "docs" / "llms.txt").read_text()
    full_path = ROOT / "docs" / "llms-full.txt"
    full = full_path.read_text()
    if full != build_llms_full.render():
        fail("docs/llms-full.txt is stale; run python3 tools/build_llms_full.py")
    if "llms-full.txt" not in llms:
        fail("llms.txt does not link llms-full.txt")
    locs = re.findall(r"<loc>(.*?)</loc>", (ROOT / "docs" / "sitemap.xml").read_text())
    if len(locs) < 70:
        fail(f"sitemap has {len(locs)} urls")
    for loc in locs:
        if loc not in full:
            fail(f"llms-full.txt missing {loc}")
    index = (ROOT / "docs" / "index.md").read_text()
    if "FAQPage" not in index or "What is finserv-agent-audit?" not in index:
        fail("docs home missing the FAQ")
    blob = llms + full + robots + index
    if re.search(r"inwood|75244", blob, re.I):
        fail("street address is present")
    if "(no matching markdown file)" in full:
        fail("a sitemap URL has no markdown source")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"all checks passed: {len(locs)} docs urls")
    return 0


if __name__ == "__main__":
    sys.exit(main())
