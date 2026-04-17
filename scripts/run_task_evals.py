#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
APP_PATH = ROOT_DIR / "app.py"
DEFAULT_CASE_FILE = ROOT_DIR / "evals" / "task_cases.json"
ALLOWED_TARGETS = {
    "load_skills",
    "render_home",
    "render_detail",
    "render_json",
    "discover_skills",
    "parse_find_results",
}


@dataclass
class CaseResult:
    case_id: str
    ok: bool
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run task-level evals for skill-manage.")
    parser.add_argument("--summary-only", action="store_true", help="Emit concise summary only.")
    return parser.parse_args()


def load_app_module():
    spec = importlib.util.spec_from_file_location("skill_manage_app", APP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load app module from {APP_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_cases() -> list[dict[str, Any]]:
    case_file = Path(os.environ.get("TASK_EVAL_CASE_FILE", str(DEFAULT_CASE_FILE)))
    payload = json.loads(case_file.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RuntimeError("No task eval cases found.")
    return cases


def to_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        if dataclasses.is_dataclass(value):
            return json.dumps(dataclasses.asdict(value), ensure_ascii=False)
        if isinstance(value, list):
            normalized: list[Any] = []
            for item in value:
                if dataclasses.is_dataclass(item):
                    normalized.append(dataclasses.asdict(item))
                else:
                    normalized.append(item)
            return json.dumps(normalized, ensure_ascii=False)
        return repr(value)


def nested_get(payload: Any, dotted_key: str) -> Any:
    current = payload
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(dotted_key)
    return current


def ensure_contains(text: str, needle: str) -> None:
    if needle not in text:
        raise AssertionError(f"expected output to contain {needle!r}")


def assert_expectations(expect: dict[str, Any], raw_result: Any, text_result: str, first_skill: Any | None) -> None:
    contains = expect.get("contains", [])
    for needle in contains:
        ensure_contains(text_result, str(needle))

    equals = expect.get("equals")
    if equals is not None and raw_result != equals:
        raise AssertionError(f"expected exact result {equals!r}, got {raw_result!r}")

    field_equals = expect.get("json_field_equals", {})
    if field_equals:
        if not isinstance(raw_result, dict):
            raise AssertionError("json_field_equals requires dict result")
        for key, expected_value in field_equals.items():
            actual = nested_get(raw_result, key)
            if actual != expected_value:
                raise AssertionError(f"expected field {key!r} == {expected_value!r}, got {actual!r}")

    nonempty = expect.get("json_list_nonempty")
    if nonempty:
        if isinstance(nonempty, bool):
            target = raw_result
        else:
            if not isinstance(raw_result, dict):
                raise AssertionError("json_list_nonempty path requires dict result")
            target = nested_get(raw_result, str(nonempty))
        if not isinstance(target, list) or len(target) == 0:
            raise AssertionError("expected non-empty list")

    field_contains = expect.get("contains_fields_from_first_skill", [])
    if field_contains:
        if first_skill is None:
            raise AssertionError("contains_fields_from_first_skill requires first skill context")
        for field_name in field_contains:
            value = getattr(first_skill, field_name, None)
            if not value:
                raise AssertionError(f"first skill missing field {field_name!r}")
            ensure_contains(text_result, str(value))


def execute_module_case(module, case: dict[str, Any], first_skill: Any | None) -> tuple[Any, str]:
    input_payload = case["input"]
    target_name = input_payload["target"]
    if target_name not in ALLOWED_TARGETS:
        raise AssertionError(f"target {target_name!r} is not allowed")

    target = getattr(module, target_name)
    if input_payload.get("from_first_skill"):
        if first_skill is None:
            raise AssertionError("no skills available for first skill case")
        raw_result = target(first_skill)
    else:
        args = input_payload.get("args", [])
        raw_result = target(*args)
    return raw_result, to_text(raw_result)


def execute_http_case(case: dict[str, Any]) -> tuple[Any, str]:
    if os.environ.get("TASK_EVAL_HTTP") != "1":
        raise RuntimeError("http_contract cases require TASK_EVAL_HTTP=1")
    base_url = os.environ.get("TASK_EVAL_BASE_URL")
    if not base_url:
        raise RuntimeError("http_contract cases require TASK_EVAL_BASE_URL")

    path = case["input"].get("path", "/")
    url = f"{base_url.rstrip('/')}{path}"
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return json.loads(body), body
    return body, body


def run_case(module, case: dict[str, Any], first_skill: Any | None) -> CaseResult:
    case_id = case["id"]
    try:
        kind = case["kind"]
        if kind == "module_call":
            raw_result, text_result = execute_module_case(module, case, first_skill)
        elif kind == "http_contract":
            raw_result, text_result = execute_http_case(case)
        else:
            raise AssertionError(f"unsupported case kind: {kind}")

        assert_expectations(case.get("expect", {}), raw_result, text_result, first_skill)
        return CaseResult(case_id=case_id, ok=True, detail="passed")
    except Exception as exc:  # noqa: BLE001
        return CaseResult(case_id=case_id, ok=False, detail=str(exc))


def emit_summary(results: list[CaseResult], summary_only: bool) -> None:
    total = len(results)
    passed = sum(1 for item in results if item.ok)
    failed = total - passed

    print(f"[task-eval] SUMMARY total={total} passed={passed} failed={failed}")
    for result in results:
        if result.ok:
            print(f"[task-eval] PASS {result.case_id}")
        else:
            print(f"[task-eval] FAIL {result.case_id}: {result.detail}")
    print(f"[task-eval] RESULT {'PASS' if failed == 0 else 'FAIL'}")
    if not summary_only and failed == 0:
        print("[task-eval] PASS: task-level evals completed")


def main() -> int:
    args = parse_args()
    module = load_app_module()
    cases = load_cases()
    first_skill = None
    if hasattr(module, "load_skills"):
        skills = module.load_skills()
        if skills:
            first_skill = skills[0]

    results = [run_case(module, case, first_skill) for case in cases]
    emit_summary(results, args.summary_only)
    return 0 if all(item.ok for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
