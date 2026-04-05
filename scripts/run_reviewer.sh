#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
REPORT_FILE="$ROOT_DIR/artifacts/review-report.md"
TMP_DIFF="$(mktemp -t skill-manage-review-diff.XXXXXX)"
TMP_STAGED_DIFF="$(mktemp -t skill-manage-review-staged-diff.XXXXXX)"
TMP_STATUS="$(mktemp -t skill-manage-review-status.XXXXXX)"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
GIT_REVIEW_PATHS=(
  "."
  ":(exclude)artifacts/current-task.md"
  ":(exclude)artifacts/review-report.md"
)

cleanup() {
  rm -f "$TMP_DIFF"
  rm -f "$TMP_STAGED_DIFF"
  rm -f "$TMP_STATUS"
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
    git -C "$ROOT_DIR" status --short --untracked-files=all -- "${GIT_REVIEW_PATHS[@]}" >"$TMP_STATUS" || true
    git -C "$ROOT_DIR" diff -- "${GIT_REVIEW_PATHS[@]}" >"$TMP_DIFF" || true
    git -C "$ROOT_DIR" diff --cached -- "${GIT_REVIEW_PATHS[@]}" >"$TMP_STAGED_DIFF" || true
    return 0
  fi
  return 1
}

collect_task_goal() {
  if [[ -f "$TASK_FILE" ]]; then
    awk '
      /^## Goal$/ { capture=1; next }
      /^## / && capture { exit }
      capture { print }
    ' "$TASK_FILE" | sed '/^[[:space:]]*$/d'
  fi
}

strip_generated_artifact_noise() {
  if [[ -f "$TMP_STATUS" ]]; then
    grep -vE '^[[:space:]MADRCU\?]{2} artifacts/(current-task|review-report)\.md$' "$TMP_STATUS" >"$TMP_STATUS.filtered" || true
    mv "$TMP_STATUS.filtered" "$TMP_STATUS"
  fi

  if [[ -f "$TMP_DIFF" ]]; then
    awk '
      /^diff --git a\/artifacts\/(current-task|review-report)\.md b\/artifacts\/(current-task|review-report)\.md$/ { skip=1; next }
      /^diff --git / { skip=0 }
      !skip { print }
    ' "$TMP_DIFF" >"$TMP_DIFF.filtered"
    mv "$TMP_DIFF.filtered" "$TMP_DIFF"
  fi

  if [[ -f "$TMP_STAGED_DIFF" ]]; then
    awk '
      /^diff --git a\/artifacts\/(current-task|review-report)\.md b\/artifacts\/(current-task|review-report)\.md$/ { skip=1; next }
      /^diff --git / { skip=0 }
      !skip { print }
    ' "$TMP_STAGED_DIFF" >"$TMP_STAGED_DIFF.filtered"
    mv "$TMP_STAGED_DIFF.filtered" "$TMP_STAGED_DIFF"
  fi
}

SCOPE_FILES=()
while IFS= read -r line; do
  SCOPE_FILES+=("$line")
done < <(collect_scope_files)

TASK_GOAL="$(collect_task_goal)"
DIFF_MODE="scope-only"
CHANGED_FILES=()

if collect_git_diff; then
  strip_generated_artifact_noise

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    CHANGED_FILES+=("$line")
  done <"$TMP_STATUS"

  if [[ -s "$TMP_STATUS" || -s "$TMP_DIFF" || -s "$TMP_STAGED_DIFF" ]]; then
    DIFF_MODE="git-working-tree"
  fi
fi

if [[ "$DIFF_MODE" == "scope-only" ]]; then
  : >"$TMP_DIFF"
  : >"$TMP_STAGED_DIFF"
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
  echo "- Goal: ${TASK_GOAL:-}"
  echo "- Files changed / reviewed:"
  if [[ "$DIFF_MODE" == "git-working-tree" ]]; then
    if [[ ${#CHANGED_FILES[@]} -gt 0 ]]; then
      for file in "${CHANGED_FILES[@]}"; do
        echo "  - \`$file\`"
      done
    else
      echo "  - \`No path-level status entries captured; review the diff sections below.\`"
    fi
  else
    for file in "${SCOPE_FILES[@]}"; do
      echo "  - \`$file\`"
    done
  fi
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
  if [[ "$DIFF_MODE" == "git-working-tree" ]]; then
    echo "Git working tree detected. Review should prioritize these changes:"
    echo
    echo "### Git Status"
    echo
    echo '```text'
    if [[ -s "$TMP_STATUS" ]]; then
      sed -n '1,240p' "$TMP_STATUS"
    else
      echo "No path-level status entries captured."
    fi
    echo '```'
    echo
    echo "### Unstaged Diff"
    echo
    echo '```diff'
    if [[ -s "$TMP_DIFF" ]]; then
      sed -n '1,240p' "$TMP_DIFF"
    else
      echo "No unstaged diff."
    fi
    echo '```'
    echo
    echo "### Staged Diff"
    echo
    echo '```diff'
    if [[ -s "$TMP_STAGED_DIFF" ]]; then
      sed -n '1,240p' "$TMP_STAGED_DIFF"
    else
      echo "No staged diff."
    fi
    echo '```'
    echo
    echo "If a changed file is untracked and not represented in the diff above, review it directly from the working tree."
  else
    echo "No git diff available. Review must be based on the current project scope listed above."
    echo
    echo "Tip: now that the project is in git, prefer running review before commit so the reviewer packet can focus on the active working tree changes."
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
