#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="$ROOT_DIR/artifacts"
TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
REVIEW_FILE="$ROOT_DIR/artifacts/review-report.md"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"

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
  review  Run scripts/run_reviewer.sh
  finish  Run scripts/finalize_change.sh
  status  Show task and review artifact paths plus next commands
EOF
}

ensure_artifacts_dir() {
  mkdir -p "$ARTIFACTS_DIR"
}

write_task_packet() {
  local summary="$1"

  ensure_artifacts_dir

  cat >"$TASK_FILE" <<EOF
# Current Task

Generated at: $TIMESTAMP

## Goal

$summary

## Required Workflow

1. Read \`AGENTS.md\`
2. Implement the change
3. Before completion, run:

\`\`\`bash
bash scripts/finalize_change.sh
\`\`\`

## Expected Deliverable

- Code changes aligned with the goal
- Updated \`artifacts/review-report.md\`
- Findings-first review result

## Notes

- If any \`P1\` or \`P2\` finding exists, completion is blocked.
- Do not declare completion before the finalize gate passes.
EOF

  echo "[dev-task] wrote task packet to $TASK_FILE"
  echo "[dev-task] next:"
  echo "  - implement the change"
  echo "  - run: bash scripts/dev_task.sh check"
  echo "  - run: bash scripts/dev_task.sh review"
  echo "  - run: bash scripts/dev_task.sh finish"
}

print_status() {
  echo "[dev-task] root: $ROOT_DIR"
  echo "[dev-task] task file: $TASK_FILE"
  echo "[dev-task] review file: $REVIEW_FILE"

  if [[ -f "$TASK_FILE" ]]; then
    echo "[dev-task] current task:"
    sed -n '1,120p' "$TASK_FILE"
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
