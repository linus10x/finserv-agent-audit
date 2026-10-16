# GATE_REQUEST

Relay for Grok Bot, then Chief of Staff, then Plato. Public metadata. Do not land on main until each APPROVE names this PR's exact head.

- Repo: linus10x/finserv-agent-audit
- Branch: seo-crawl-20261016
- Site: https://linus10x.github.io/finserv-agent-audit/ (GitHub Pages, source /docs)

## What this PR changes

- docs/robots.txt, docs/sitemap.xml (77 URLs, one per markdown page already published, no trailing slash), docs/llms.txt.
- docs/_includes/head-custom.html adds SoftwareSourceCode JSON-LD. The live theme already includes that file (the comment is in the current head).
- No markdown page was edited. The description matches the repo description already in the Jekyll SEO tag. The author name is the one in CITATION.cff.

## Stops

A reviewer APPROVE has to name this head before anyone lands it on main. GitHub Pages publishes /docs from main.
