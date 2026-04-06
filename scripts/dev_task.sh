#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="$ROOT_DIR/artifacts"
TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
REVIEW_FILE="$ROOT_DIR/artifacts/review-report.md"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
GIT_TASK_PATHS=(
  "."
  ":(exclude)artifacts/current-task.md"
  ":(exclude)artifacts/review-report.md"
)

usage() {
  cat <<EOF
Usage:
  bash scripts/dev_task.sh start "<task summary>"
  bash scripts/dev_task.sh check
  bash scripts/dev_task.sh review
  bash scripts/dev_task.sh finish
  bash scripts/dev_task.sh status

Commands:
  start   Create or refresh artifacts/current-task.md
  check   Run scripts/review_harness.sh
  review  Run scripts/run_reviewer.sh with git-aware review context
  finish  Run scripts/finalize_change.sh
  status  Show task and review artifact paths plus next commands
EOF
}

ensure_artifacts_dir() {
  mkdir -p "$ARTIFACTS_DIR"
}

git_has_pending_project_changes() {
  if ! git -C "$ROOT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
    return 1
  fi

  git -C "$ROOT_DIR" status --short --untracked-files=all -- "${GIT_TASK_PATHS[@]}" | grep -q '.'
}

task_entry_count() {
  if [[ ! -f "$TASK_FILE" ]]; then
    echo 0
    return
  fi

  awk '/^## Task Entry [0-9]+$/ { count++ } END { print count + 0 }' "$TASK_FILE"
}

write_log_header() {
  local mode="$1"
  local git_state="$2"

  cat <<EOF
# Current Task Log

Last updated: $TIMESTAMP
Update mode: $mode
Git state before update: $git_state

EOF
}

write_task_entry() {
  local entry_number="$1"
  local summary="$2"
  local mode="$3"
  local git_state="$4"

  cat <<EOF
## Task Entry $entry_number

Generated at: $TIMESTAMP
Entry mode: $mode
Git state before update: $git_state

### Goal

$summary

### Required Workflow

1. Read \`AGENTS.md\`
2. Implement the change
3. Before completion, run:

\`\`\`bash
bash scripts/finalize_change.sh
\`\`\`

### Expected Deliverable

- Code changes aligned with the goal
- Updated \`artifacts/review-report.md\`
- Findings-first review result

### Notes

- If any \`P1\` or \`P2\` finding exists, completion is blocked.
- Do not declare completion before the finalize gate passes.
EOF
}

write_task_packet() {
  local summary="$1"
  local mode="reset"
  local git_state="clean"
  local entry_number="1"
  local tmp_file
  tmp_file="$(mktemp -t skill-manage-current-task.XXXXXX)"

  ensure_artifacts_dir

  if git_has_pending_project_changes && [[ -f "$TASK_FILE" ]]; then
    mode="append"
    git_state="dirty"
    entry_number="$(( $(task_entry_count) + 1 ))"
  fi

  {
    if [[ "$mode" == "reset" ]]; then
      write_log_header "$mode" "$git_state"
    else
      if [[ -f "$TASK_FILE" ]] && grep -q '^## Task Entry [0-9]\+$' "$TASK_FILE"; then
        cat "$TASK_FILE"
        echo
      elif [[ -f "$TASK_FILE" ]]; then
        write_log_header "migrated" "legacy"
        echo "## Legacy Snapshot"
        echo
        echo '```md'
        cat "$TASK_FILE"
        echo
        echo '```'
        echo
      else
        write_log_header "$mode" "$git_state"
      fi
    fi

    write_task_entry "$entry_number" "$summary" "$mode" "$git_state"
  } >"$tmp_file"

  mv "$tmp_file" "$TASK_FILE"

  echo "[dev-task] wrote task packet to $TASK_FILE ($mode)"
  echo "[dev-task] next:"
  echo "  - implement the change"
  echo "  - run: bash scripts/dev_task.sh check"
  echo "  - run: bash scripts/dev_task.sh review"
  echo "  - run: bash scripts/dev_task.sh finish"
}

print_latest_task_entry() {
  if [[ ! -f "$TASK_FILE" ]]; then
    echo "[dev-task] no current task packet yet"
    return
  fi

  if grep -q '^## Task Entry [0-9]\+$' "$TASK_FILE"; then
    awk '
      /^## Task Entry [0-9]+$/ {
        current = $0 ORS
        capture = 1
        next
      }
      capture {
        current = current $0 ORS
      }
      END {
        printf "%s", current
      }
    ' "$TASK_FILE"
  else
    sed -n '1,120p' "$TASK_FILE"
  fi
}

print_status() {
  echo "[dev-task] root: $ROOT_DIR"
  echo "[dev-task] task file: $TASK_FILE"
  echo "[dev-task] review file: $REVIEW_FILE"

  if [[ -f "$TASK_FILE" ]]; then
    echo "[dev-task] latest task entry:"
    print_latest_task_entry
  else
    echo "[dev-task] no current task packet yet"
  fi

  if [[ -f "$REVIEW_FILE" ]]; then
    echo "[dev-task] review report exists"
  else
    echo "[dev-task] review report not generated yet"
  fi

  echo "[dev-task] suggested flow:"
  echo "  1. bash scripts/dev_task.sh start \"<task summary>\""
  echo "  2. implement the change"
  echo "  3. bash scripts/dev_task.sh check"
  echo "  4. bash scripts/dev_task.sh review"
  echo "  5. bash scripts/dev_task.sh finish"
  echo "[dev-task] note: review now prefers current git working tree changes over full-project scope"
}

main() {
  if [[ $# -lt 1 ]]; then
    usage
    exit 1
  fi

  case "$1" in
    start)
      shift
      if [[ $# -lt 1 ]]; then
        echo "[dev-task] missing task summary for start" >&2
        usage
        exit 1
      fi
      write_task_packet "$*"
      ;;
    check)
      bash "$ROOT_DIR/scripts/review_harness.sh"
      ;;
    review)
      bash "$ROOT_DIR/scripts/run_reviewer.sh"
      ;;
    finish)
      bash "$ROOT_DIR/scripts/finalize_change.sh"
      ;;
    status)
      print_status
      ;;
    *)
      echo "[dev-task] unknown command: $1" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
