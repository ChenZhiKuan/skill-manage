#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_FILE="$ROOT_DIR/app.py"
JS_FILE="$ROOT_DIR/static/app.js"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8421}"
BASE_URL="http://${HOST}:${PORT}"
SERVER_LOG="$(mktemp -t skill-manage-review-log.XXXXXX)"
SERVER_PID=""
RUN_BIND_SMOKE="${RUN_BIND_SMOKE:-0}"

cleanup() {
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
  rm -f "${SERVER_LOG}"
}

trap cleanup EXIT

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[review] missing required command: $1" >&2
    exit 1
  fi
}

wait_for_server() {
  local attempts=30
  local delay=0.5

  for _ in $(seq 1 "${attempts}"); do
    if curl -fsS "${BASE_URL}/api/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay}"
  done

  echo "[review] server did not become ready in time" >&2
  if [[ -f "${SERVER_LOG}" ]]; then
    echo "[review] server log:" >&2
    cat "${SERVER_LOG}" >&2
  fi
  exit 1
}

assert_json_contains() {
  local url="$1"
  local expected_expr="$2"
  local response

  response="$(curl -fsS "${url}")"
  python3 - <<'PY' "${response}" "${expected_expr}"
import json
import sys

payload = json.loads(sys.argv[1])
expr = sys.argv[2]

if expr == "health_ok":
    assert payload.get("status") == "ok", payload
elif expr == "skills_nonempty":
    assert isinstance(payload, list) and len(payload) > 0, payload
elif expr == "discover_recommendations":
    assert payload.get("mode") == "recommend", payload
    assert isinstance(payload.get("suggestions"), list) and len(payload["suggestions"]) > 0, payload
else:
    raise AssertionError(f"unknown assertion: {expr}")
PY
}

echo "[review] step 1/5: syntax checks"
python3 -m py_compile "${APP_FILE}"
node --check "${JS_FILE}"

echo "[review] step 2/5: in-process smoke checks"
python3 - <<'PY' "${ROOT_DIR}"
import importlib.util
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
app_path = root / "app.py"

spec = importlib.util.spec_from_file_location("skill_manage_app", app_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)

skills = module.load_skills()
assert len(skills) > 0, "expected at least one scanned skill"

home_html = module.render_home("path").decode("utf-8")
assert "本机 Skill 地图" in home_html
assert "/api/skills" in home_html or "查看详情" in home_html

detail_html = module.render_detail(skills[0]).decode("utf-8")
assert skills[0].title in detail_html
assert skills[0].skill_path in detail_html

health_json = module.render_json({"status": "ok"}).decode("utf-8")
assert '"status": "ok"' in health_json

discover_payload = module.discover_skills("")
assert discover_payload["mode"] == "recommend"
assert len(discover_payload["suggestions"]) > 0

sample_output = """
vercel-labs/agent-skills@vercel-react-best-practices 261.1K installs
└ https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices
"""
parsed = module.parse_find_results(sample_output)
assert len(parsed) == 1
assert parsed[0].package == "vercel-labs/agent-skills@vercel-react-best-practices"
assert parsed[0].url == "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices"
PY

echo "[review] step 3/5: optional bind smoke mode"
if [[ "${RUN_BIND_SMOKE}" == "1" ]]; then
  require_cmd curl
  python3 "${APP_FILE}" --host "${HOST}" --port "${PORT}" >"${SERVER_LOG}" 2>&1 &
  SERVER_PID=$!
  wait_for_server

  echo "[review] step 4/5: endpoint checks"
  assert_json_contains "${BASE_URL}/api/health" "health_ok"
  assert_json_contains "${BASE_URL}/api/skills" "skills_nonempty"
  assert_json_contains "${BASE_URL}/api/discover-skills" "discover_recommendations"

  echo "[review] step 5/5: page smoke checks"
  curl -fsS "${BASE_URL}/" >/dev/null
  curl -fsS "${BASE_URL}/?view=category" >/dev/null
else
  echo "[review] bind smoke disabled (set RUN_BIND_SMOKE=1 to enable)"
  echo "[review] step 4/5: endpoint contract skipped"
  echo "[review] step 5/5: page request smoke skipped"
fi

echo "[review] PASS: local harness checks completed"
