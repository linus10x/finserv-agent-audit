#!/usr/bin/env bash
# heal_check.core.sh — GENERIC control-center doctor (global scaffold, distilled from the
# kunjar-resume-control-center reference doctor). Drop into any repo as
# 00_Control/heal_check.sh to give that project baseline self-healing. A project that needs
# more (a brand gate, a council gate, drift tripwire) keeps its OWN richer heal_check.sh —
# the installer never clobbers an existing one — or layers checks via 00_Control/heal_check.ext.sh.
#
# Universal invariants (true for ANY of Kunjar's repos): hooks armed, exec bits, no tracked PII,
# cost discipline (no ANTHROPIC_API_KEY). Default-deny .gitignore is RECOMMENDED (warn, not fail).
#
# Exit 0 = invariants hold (possibly after auto-repair). Exit 1 = unrepairable finding.
set -u
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
HOOKS="$REPO_ROOT/00_Control/githooks"; LINTS="$REPO_ROOT/00_Control/lints"
problems=0; repairs=0
ok()    { printf '  ✓ %s\n' "$1"; }
fixed() { printf '  ~ repaired %s\n' "$1"; repairs=$((repairs+1)); }
bad()   { printf '  ✗ %s\n' "$1"; problems=$((problems+1)); }
warn()  { printf '  ! %s\n' "$1"; }
echo "=== heal_check.core $(date -u +%FT%TZ) — $(basename "$REPO_ROOT") ==="

# 1. Hooks armed (self-repair) — only if this repo uses the 00_Control/githooks convention.
if [ -d "$HOOKS" ]; then
  want="00_Control/githooks"; have="$(git config --get core.hooksPath || true)"
  if [ "$have" = "$want" ]; then ok "core.hooksPath = $want"
  else git config core.hooksPath "$want" && fixed "core.hooksPath '$have' → $want"; fi
fi

# 2. Executable bits (self-repair) on any hooks + lint scripts present.
for f in "$HOOKS"/* "$LINTS"/*.sh "$LINTS"/*.py; do
  [ -f "$f" ] || continue
  [ -x "$f" ] || { chmod +x "$f" && fixed "+x ${f#$REPO_ROOT/}"; }
done
ok "executable bits checked"

# 3. Default-deny .gitignore (RECOMMENDED, warn-only — not every repo opts into allowlisting).
if [ -f .gitignore ] && grep -qxF '/*' .gitignore; then ok ".gitignore default-deny '/*' present"
else warn ".gitignore has no default-deny '/*' — consider allowlisting (recommended for repos with private material)"; fi

# 4. No PII tracked (HARD — universal). Portable ERE; filename + SSN-pattern content scan.
FRE='(passport|driver.?licen|green.?card|h-?1b|eta\.?750|gratuity|separation.?agreement|background.?check|social.?security|(^|[^a-z0-9])(w-?2|w-?9|i-?9|ssn)($|[^a-z0-9]))'
pii="$(git ls-files | grep -iE "$FRE" || true)"
[ -z "$pii" ] && ok "no PII-looking tracked filenames" || { bad "PII-looking tracked filename(s):"; printf '      %s\n' $pii; }
# Boundary guards exclude matches embedded in longer digit-hyphen runs (ISBNs in
# citation URLs like 978-88-6969-443-1 are not SSNs).
ssn="$(git grep -I -nE '(^|[^0-9-])[0-9]{3}-[0-9]{2}-[0-9]{4}([^0-9-]|$)' -- '*.md' '*.txt' '*.csv' '*.json' '*.yaml' '*.yml' '*.html' 2>/dev/null || true)"
[ -z "$ssn" ] && ok "no SSN-pattern content in tracked text" || { bad "SSN-pattern content tracked:"; printf '%s\n' "$ssn" | head -3; }

# 5. Cost discipline (HARD — global rule): no ANTHROPIC_API_KEY in env or committed config.
[ -z "${ANTHROPIC_API_KEY:-}" ] && ok "ANTHROPIC_API_KEY not set in env" || bad "ANTHROPIC_API_KEY set — subscription auth only (unset it)"
# A real ASSIGNMENT only — redacted/placeholder values, Secrets-Manager references
# (valueFrom ARNs), and shell self-expansions are fine.
keyhits="$(git grep -InE '(ANTHROPIC_API_KEY=|"ANTHROPIC_API_KEY"[[:space:]]*:)' -- '*.json' '*.sh' ':!*heal_check*' 2>/dev/null \
  | grep -ivE 'REDACTED|your[_-]?[a-z_-]*key|placeholder|example|changeme|dummy|<[^>]*>|valueFrom|secretsmanager|\$\{?ANTHROPIC_API_KEY' || true)"
[ -z "$keyhits" ] && ok "no ANTHROPIC_API_KEY assignment in tracked config" \
  || { bad "ANTHROPIC_API_KEY assigned in tracked config — remove it"; printf '%s\n' "$keyhits" | head -3; }
# Key MATERIAL anywhere in tracked text is a leak regardless of file type (the old
# *.json/*.sh-only scan missed a key pasted into a tracked .md) — rotate + purge.
realkey="$(git grep -InE 'sk-ant-[A-Za-z0-9_-]{16,}' 2>/dev/null | grep -vi 'redacted' | grep -v 'heal_check' || true)"
[ -z "$realkey" ] && ok "no Anthropic key material tracked" \
  || { bad "Anthropic key material (sk-ant-...) tracked — rotate the key + purge:"; printf '%s\n' "$realkey" | head -3; }

# 6. Project extension hook — a repo can layer its own checks without forking this core.
EXT="$REPO_ROOT/00_Control/heal_check.ext.sh"
if [ -f "$EXT" ]; then
  # shellcheck disable=SC1090
  if . "$EXT"; then ok "ran project extension (heal_check.ext.sh)"; else bad "project extension reported a failure"; fi
fi

echo "=== heal_check.core: $repairs repair(s), $problems unrepairable problem(s) ==="
[ "$problems" -eq 0 ]
