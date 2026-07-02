#!/usr/bin/env bash
# Zero-friction demo — runs from a COLD CLONE with NO install and NO network.
#
#   git clone https://github.com/linus10x/finserv-agent-audit && cd finserv-agent-audit
#   ./demo.sh
#
# It sets PYTHONPATH to the in-tree src/ (the package uses a src layout, so a
# bare `python examples/...` would fail with ModuleNotFoundError without an
# editable install). No pip, no venv, no credentials, no network calls.
#
# The demo builds a grant -> examine -> revoke authority lifecycle, anchors it to
# an external witness, then runs four attacks a hash-chain alone would miss and
# proves each is caught. It exits non-zero if any expected catch fails to fire.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"

export PYTHONPATH="${HERE}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PY}" "${HERE}/examples/demotion_gate_demo.py"
