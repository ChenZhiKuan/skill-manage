#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_FILE="$ROOT_DIR/artifacts/review-report.md"

echo "[finalize] step 1/3: run local review harness"
bash "$ROOT_DIR/scripts/review_harness.sh"

echo "[finalize] step 2/3: review checklist reminder"
echo "[finalize] generate reviewer packet"
bash "$ROOT_DIR/scripts/run_reviewer.sh"

echo "[finalize] step 3/3: verify review report template exists"
if [[ ! -f "$REPORT_FILE" ]]; then
  echo "[finalize] missing review report template: $REPORT_FILE" >&2
  exit 1
fi

echo "[finalize] next action: open $ROOT_DIR/REVIEW_PROMPT.md and fill findings into artifacts/review-report.md"
echo "[finalize] block completion on any P1 or P2 finding"
echo "[finalize] PASS: finalize gate passed, manual/agent review output still required"
