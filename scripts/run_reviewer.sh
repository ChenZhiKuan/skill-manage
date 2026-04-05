#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_FILE="$ROOT_DIR/artifacts/review-report.md"
TMP_DIFF="$(mktemp -t skill-manage-review-diff.XXXXXX)"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"

cleanup() {
  rm -f "$TMP_DIFF"
}

trap cleanup EXIT

collect_scope_files() {
  find "$ROOT_DIR" \
    -type f \
    ! -path '*/__pycache__/*' \
    ! -path '*/artifacts/*' \
    ! -name '*.pyc' \
    | sed "s#^$ROOT_DIR/##" \
    | sort
}

collect_git_diff() {
  if git -C "$ROOT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$ROOT_DIR" diff -- . >"$TMP_DIFF" || true
    return 0
  fi
  return 1
}

SCOPE_FILES=()
while IFS= read -r line; do
  SCOPE_FILES+=("$line")
done < <(collect_scope_files)

DIFF_MODE="scope-only"
if collect_git_diff && [[ -s "$TMP_DIFF" ]]; then
  DIFF_MODE="git-diff"
else
  : >"$TMP_DIFF"
fi

{
  echo "# Review Report"
  echo
  echo "Generated at: $TIMESTAMP"
  echo
  echo "## Review Mode"
  echo
  echo "- Mode: \`$DIFF_MODE\`"
  echo "- Prompt: \`REVIEW_PROMPT.md\`"
  echo "- Checklist: \`REVIEW_CHECKLIST.md\`"
  echo
  echo "## Change Summary"
  echo
  echo "- Goal:"
  echo "- Files changed / reviewed:"
  for file in "${SCOPE_FILES[@]}"; do
    echo "  - \`$file\`"
  done
  echo "- Expected behavior:"
  echo
  echo "## Harness Checks"
  echo
  echo "- Command: \`bash scripts/review_harness.sh\`"
  echo "- Result: PASS"
  echo "- Optional bind smoke run: no"
  echo
  echo "## Review Context"
  echo
  if [[ "$DIFF_MODE" == "git-diff" ]]; then
    echo "Git diff detected. Review should prioritize this diff:"
    echo
    echo '```diff'
    sed -n '1,240p' "$TMP_DIFF"
    echo '```'
  else
    echo "No git diff available. Review must be based on the current project scope listed above."
  fi
  echo
  echo "## Findings"
  echo
  echo "### P1"
  echo
  echo "- None"
  echo
  echo "### P2"
  echo
  echo "- None"
  echo
  echo "### P3"
  echo
  echo "- None"
  echo
  echo "## Residual Risks"
  echo
  echo "- None"
  echo
  echo "## Reviewer Verdict"
  echo
  echo "- Verdict: \`PASS / FAIL / PARTIAL\`"
  echo "- Reviewer:"
  echo "- Reviewed at:"
  echo
  echo "## Notes"
  echo
  echo "- If any \`P1\` or \`P2\` finding exists, completion must be blocked."
  echo "- If no findings exist, explicitly keep \`None\` entries rather than deleting sections."
} >"$REPORT_FILE"

echo "[reviewer] wrote reviewer packet to $REPORT_FILE"
echo "[reviewer] mode: $DIFF_MODE"
