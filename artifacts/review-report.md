# Review Report Log

Last updated: 2026-04-06 16:38:50 CST
Update mode: migrated
Git state before update: legacy

## Legacy Snapshot

```md
# Review Report

Generated at: 2026-04-06 16:29:27 CST

## Review Mode

- Mode: `git-working-tree`
- Prompt: `REVIEW_PROMPT.md`
- Checklist: `REVIEW_CHECKLIST.md`

## Change Summary

- Goal: 为首页新增第三方 skill 搜索与一键安装能力，统一搜索结果卡片布局，优化 hero 区密度与中文指标文案，并确认 Skills CLI 当前不支持真实分页后移除误导性的“查看更多”
- Files changed / reviewed:
  - `M  AGENTS.md`
  - `M  README.md`
  - `M  app.py`
  - `M  scripts/review_harness.sh`
  - `M  static/app.js`
  - `M  static/style.css`
- Expected behavior:

## Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: no

## Review Context

Git working tree detected. Review should prioritize these changes:

### Git Status

```text
M  AGENTS.md
M  README.md
M  app.py
M  scripts/review_harness.sh
M  static/app.js
M  static/style.css
```

### Unstaged Diff

```diff
No unstaged diff.
```

### Staged Diff

```diff
diff --git a/AGENTS.md b/AGENTS.md
index 05950f0..60f2949 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -30,7 +30,7 @@ bash scripts/review_harness.sh
 REVIEW_CHECKLIST.md
 ```
 
-3. 优先通过统一入口生成或更新：
+3. 优先通过统一入口生成或更新 reviewer packet：
 
 ```bash
 bash scripts/dev_task.sh review
@@ -38,19 +38,34 @@ bash scripts/dev_task.sh review
 
 等价命令为：
 
-```text
-artifacts/review-report.md
-```
-
-其中 `artifacts/review-report.md` 必须先通过以下命令生成最新 reviewer 包：
-
 ```bash
 bash scripts/run_reviewer.sh
 ```
 
-4. 如果存在 `P1` 或 `P2` finding，则不得结束，必须继续修复
+4. 在 reviewer packet 生成后，必须完成一次真正的 findings-first code review：
+
+- review 必须基于以下输入材料：
+  - `REVIEW_PROMPT.md`
+  - `REVIEW_CHECKLIST.md`
+  - `artifacts/current-task.md`
+  - `artifacts/review-report.md`
+  - 当前改动涉及的源码文件
+- reviewer 角色只读，不直接修改代码
+- review 输出必须包含：
+  - `Findings`
+  - `Residual Risks`
+  - `Verdict`
+- 每条 finding 必须包含：
+  - Severity
+  - File
+  - Why it matters
+- 如果没有问题，明确写 `No findings`
+- review 结果必须回填到：
+  - `artifacts/review-report.md`
+
+5. 如果存在 `P1` 或 `P2` finding，则不得结束，必须继续修复
 
-5. 最终对用户的完成说明，必须包含：
+6. 最终对用户的完成说明，必须包含：
    - 已运行的检查命令
    - 检查结果
    - 是否存在 findings
@@ -74,6 +89,9 @@ Reviewer 角色必须遵守：
 - 不允许在未执行 harness 的情况下宣告完成
 - 不允许跳过 `scripts/run_reviewer.sh`
 - 不允许跳过 `artifacts/review-report.md`
+- 不允许只生成 reviewer packet 而不执行真正的 code review
+- 不允许在存在 `P1` 或 `P2` finding 时宣告完成
+- 不允许让 reviewer 同时承担实现者角色并直接修改代码
 - 不允许用模糊表达替代结论，例如“应该没问题”“大概率可以”
 
 ## Goal
diff --git a/README.md b/README.md
index cbd65f6..b3138e3 100644
--- a/README.md
+++ b/README.md
@@ -22,6 +22,7 @@
 - 首页支持按路径分类和按功能分类切换
 - 支持前端搜索过滤
 - 支持全站主题切换（浅色 / 深色 / 跟随系统）
+- 支持通过 `npx skills` 搜索第三方 skill，并在页面里一键安装
 - 详情页展示对应 `SKILL.md`
 - 内置 `GET /api/skills` 和 `GET /api/health`
 
@@ -44,6 +45,18 @@ http://127.0.0.1:8421
 python3 app.py --port 9000
 ```
 
+如果你要使用“搜索并安装 skill”功能，当前机器还需要能运行：
+
+```bash
+npx -y skills find react
+```
+
+安装动作会调用：
+
+```bash
+npx -y skills add <owner/repo@skill> -g -y
+```
+
 ## 扫描路径
 
 - `~/.agents/skills`
diff --git a/app.py b/app.py
index 3070d1b..bdc5f73 100644
--- a/app.py
+++ b/app.py
@@ -4,7 +4,9 @@ from __future__ import annotations
 import argparse
 import html
 import json
+import os
 import re
+import subprocess
 import sys
 import textwrap
 import urllib.parse
@@ -19,6 +21,13 @@ from typing import Iterable
 APP_DIR = Path(__file__).resolve().parent
 WORKSPACE_ROOT = APP_DIR.parent
 HOME = Path.home()
+ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
+PACKAGE_LINE_RE = re.compile(
+    r"^(?P<package>[A-Za-z0-9._-]+/[A-Za-z0-9._-]+@[\w./:-]+)(?:\s+(?P<installs>[0-9][0-9.,KMB]*\s+installs))?$"
+)
+SKILLS_URL_RE = re.compile(r"^└\s+(?P<url>https://skills\.sh/\S+)$")
+PACKAGE_SPEC_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+@[\w./:-]+$")
+SKILLS_COMMAND_TIMEOUT = 45
 
 
 ROOT_SPECS: list[tuple[str, Path]] = [
@@ -80,6 +89,40 @@ EXPLICIT_CATEGORY_MAP = {
 }
 
 
+DISCOVER_SUGGESTIONS = [
+    {
+        "label": "React",
+        "query": "react",
+        "description": "组件实践、性能与前端工程",
+    },
+    {
+        "label": "Testing",
+        "query": "testing",
+        "description": "单测、E2E 与自动化校验",
+    },
+    {
+        "label": "PR Review",
+        "query": "pr review",
+        "description": "代码评审与改评审意见",
+    },
+    {
+        "label": "Docs",
+        "query": "docs",
+        "description": "README、文档与知识整理",
+    },
+    {
+        "label": "Automation",
+        "query": "automation",
+        "description": "工作流、脚本与 agent 自动化",
+    },
+    {
+        "label": "GitHub",
+        "query": "github",
+        "description": "PR、issue、CI 与仓库协作",
+    },
+]
+
+
 @dataclass(frozen=True)
 class SkillRecord:
     slug: str
@@ -97,6 +140,16 @@ class SkillRecord:
     detail_markdown: str
 
 
+@dataclass(frozen=True)
+class DiscoverResult:
+    package: str
+    name: str
+    url: str
+    installs: str
+    source_repo: str
+    description: str
+
+
 def parse_args() -> argparse.Namespace:
     parser = argparse.ArgumentParser(description="Local skill browser for Codex-style skills.")
     parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Default: 127.0.0.1")
@@ -221,6 +274,117 @@ def load_skills() -> list[SkillRecord]:
     return records
 
 
+def strip_ansi(text: str) -> str:
+    return ANSI_ESCAPE_RE.sub("", text)
+
+
+def skills_command_env() -> dict[str, str]:
+    env = dict(**os.environ)
+    env["NO_COLOR"] = "1"
+    env["FORCE_COLOR"] = "0"
+    env["CI"] = "1"
+    return env
+
+
+def run_skills_command(args: list[str]) -> subprocess.CompletedProcess[str]:
+    return subprocess.run(
+        args,
+        capture_output=True,
+        text=True,
+        timeout=SKILLS_COMMAND_TIMEOUT,
+        env=skills_command_env(),
+        cwd=str(APP_DIR),
+        check=False,
+    )
+
+
+def parse_find_results(raw_output: str) -> list[DiscoverResult]:
+    lines = [strip_ansi(line).strip() for line in raw_output.splitlines()]
+    results: list[DiscoverResult] = []
+
+    for line in lines:
+        if not line:
+            continue
+
+        package_match = PACKAGE_LINE_RE.match(line)
+        if package_match:
+            package = package_match.group("package")
+            skill_name = package.split("@", 1)[1]
+            source_repo = package.split("@", 1)[0]
+            results.append(
+                DiscoverResult(
+                    package=package,
+                    name=skill_name,
+                    url="",
+                    installs=package_match.group("installs") or "",
+                    source_repo=source_repo,
+                    description=f"来自 {source_repo} 的 {skill_name} skill。",
+                )
+            )
+            continue
+
+        url_match = SKILLS_URL_RE.match(line)
+        if url_match and results:
+            last = results[-1]
+            results[-1] = DiscoverResult(
```

If a changed file is untracked and not represented in the diff above, review it directly from the working tree.

## Findings

### P1

- None

### P2

- None

### P3

- None

## Residual Risks

- 第三方 skill 搜索与安装仍依赖当前机器上的 `npx skills` 版本、网络状态和本地权限；如果后续 CLI 行为或 `skills.sh` API contract 变化，当前关于“无真实分页”的结论需要重新核验。

## Reviewer Verdict

- Verdict: `PASS`
- Reviewer: `Codex`
- Reviewed at: `2026-04-06 16:29:12 CST`

## Notes

- If any `P1` or `P2` finding exists, completion must be blocked.
- If no findings exist, explicitly keep `None` entries rather than deleting sections.

```

## Review Entry 1

Generated at: 2026-04-06 16:38:50 CST
Entry mode: append
Git state before update: dirty

### Review Mode

- Mode: `git-working-tree`
- Prompt: `REVIEW_PROMPT.md`
- Checklist: `REVIEW_CHECKLIST.md`

### Change Summary

- Goal: 
- Files changed / reviewed:
  - ` M scripts/dev_task.sh`
  - ` M scripts/run_reviewer.sh`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: no

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M scripts/dev_task.sh
 M scripts/run_reviewer.sh
```

#### Unstaged Diff

```diff
diff --git a/scripts/dev_task.sh b/scripts/dev_task.sh
index 8ed9e97..ea5870d 100644
--- a/scripts/dev_task.sh
+++ b/scripts/dev_task.sh
@@ -7,6 +7,11 @@ ARTIFACTS_DIR="$ROOT_DIR/artifacts"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REVIEW_FILE="$ROOT_DIR/artifacts/review-report.md"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
+GIT_TASK_PATHS=(
+  "."
+  ":(exclude)artifacts/current-task.md"
+  ":(exclude)artifacts/review-report.md"
+)
 
 usage() {
   cat <<EOF
@@ -30,21 +35,55 @@ ensure_artifacts_dir() {
   mkdir -p "$ARTIFACTS_DIR"
 }
 
-write_task_packet() {
-  local summary="$1"
+git_has_pending_project_changes() {
+  if ! git -C "$ROOT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
+    return 1
+  fi
 
-  ensure_artifacts_dir
+  git -C "$ROOT_DIR" status --short --untracked-files=all -- "${GIT_TASK_PATHS[@]}" | grep -q '.'
+}
+
+task_entry_count() {
+  if [[ ! -f "$TASK_FILE" ]]; then
+    echo 0
+    return
+  fi
+
+  awk '/^## Task Entry [0-9]+$/ { count++ } END { print count + 0 }' "$TASK_FILE"
+}
+
+write_log_header() {
+  local mode="$1"
+  local git_state="$2"
 
-  cat >"$TASK_FILE" <<EOF
-# Current Task
+  cat <<EOF
+# Current Task Log
+
+Last updated: $TIMESTAMP
+Update mode: $mode
+Git state before update: $git_state
+
+EOF
+}
+
+write_task_entry() {
+  local entry_number="$1"
+  local summary="$2"
+  local mode="$3"
+  local git_state="$4"
+
+  cat <<EOF
+## Task Entry $entry_number
 
 Generated at: $TIMESTAMP
+Entry mode: $mode
+Git state before update: $git_state
 
-## Goal
+### Goal
 
 $summary
 
-## Required Workflow
+### Required Workflow
 
 1. Read \`AGENTS.md\`
 2. Implement the change
@@ -54,19 +93,62 @@ $summary
 bash scripts/finalize_change.sh
 \`\`\`
 
-## Expected Deliverable
+### Expected Deliverable
 
 - Code changes aligned with the goal
 - Updated \`artifacts/review-report.md\`
 - Findings-first review result
 
-## Notes
+### Notes
 
 - If any \`P1\` or \`P2\` finding exists, completion is blocked.
 - Do not declare completion before the finalize gate passes.
 EOF
+}
 
-  echo "[dev-task] wrote task packet to $TASK_FILE"
+write_task_packet() {
+  local summary="$1"
+  local mode="reset"
+  local git_state="clean"
+  local entry_number="1"
+  local tmp_file
+  tmp_file="$(mktemp -t skill-manage-current-task.XXXXXX)"
+
+  ensure_artifacts_dir
+
+  if git_has_pending_project_changes && [[ -f "$TASK_FILE" ]]; then
+    mode="append"
+    git_state="dirty"
+    entry_number="$(( $(task_entry_count) + 1 ))"
+  fi
+
+  {
+    if [[ "$mode" == "reset" ]]; then
+      write_log_header "$mode" "$git_state"
+    else
+      if [[ -f "$TASK_FILE" ]] && grep -q '^## Task Entry [0-9]\+$' "$TASK_FILE"; then
+        cat "$TASK_FILE"
+        echo
+      elif [[ -f "$TASK_FILE" ]]; then
+        write_log_header "migrated" "legacy"
+        echo "## Legacy Snapshot"
+        echo
+        echo '```md'
+        cat "$TASK_FILE"
+        echo
+        echo '```'
+        echo
+      else
+        write_log_header "$mode" "$git_state"
+      fi
+    fi
+
+    write_task_entry "$entry_number" "$summary" "$mode" "$git_state"
+  } >"$tmp_file"
+
+  mv "$tmp_file" "$TASK_FILE"
+
+  echo "[dev-task] wrote task packet to $TASK_FILE ($mode)"
   echo "[dev-task] next:"
   echo "  - implement the change"
   echo "  - run: bash scripts/dev_task.sh check"
@@ -74,14 +156,39 @@ EOF
   echo "  - run: bash scripts/dev_task.sh finish"
 }
 
+print_latest_task_entry() {
+  if [[ ! -f "$TASK_FILE" ]]; then
+    echo "[dev-task] no current task packet yet"
+    return
+  fi
+
+  if grep -q '^## Task Entry [0-9]\+$' "$TASK_FILE"; then
+    awk '
+      /^## Task Entry [0-9]+$/ {
+        current = $0 ORS
+        capture = 1
+        next
+      }
+      capture {
+        current = current $0 ORS
+      }
+      END {
+        printf "%s", current
+      }
+    ' "$TASK_FILE"
+  else
+    sed -n '1,120p' "$TASK_FILE"
+  fi
+}
+
 print_status() {
   echo "[dev-task] root: $ROOT_DIR"
   echo "[dev-task] task file: $TASK_FILE"
   echo "[dev-task] review file: $REVIEW_FILE"
 
   if [[ -f "$TASK_FILE" ]]; then
-    echo "[dev-task] current task:"
-    sed -n '1,120p' "$TASK_FILE"
+    echo "[dev-task] latest task entry:"
+    print_latest_task_entry
   else
     echo "[dev-task] no current task packet yet"
   fi
diff --git a/scripts/run_reviewer.sh b/scripts/run_reviewer.sh
index 681d697..42404bc 100644
--- a/scripts/run_reviewer.sh
+++ b/scripts/run_reviewer.sh
@@ -46,9 +46,24 @@ collect_git_diff() {
 collect_task_goal() {
   if [[ -f "$TASK_FILE" ]]; then
     awk '
-      /^## Goal$/ { capture=1; next }
-      /^## / && capture { exit }
-      capture { print }
+      /^### Goal$/ {
+        capture=1
+        current=""
+        next
+      }
+      /^### / && capture {
+        last=current
+        capture=0
+      }
+      capture {
+        current = current $0 ORS
+      }
+      END {
+        if (capture) {
+          last=current
+        }
+        printf "%s", last
+      }
     ' "$TASK_FILE" | sed '/^[[:space:]]*$/d'
   fi
 }
@@ -105,23 +120,61 @@ if [[ "$DIFF_MODE" == "scope-only" ]]; then
   : >"$TMP_STAGED_DIFF"
 fi
 
-{
-  echo "# Review Report"
+review_entry_count() {
+  if [[ ! -f "$REPORT_FILE" ]]; then
+    echo 0
+    return
+  fi
+
+  awk '/^## Review Entry [0-9]+$/ { count++ } END { print count + 0 }' "$REPORT_FILE"
+}
+
+git_state_label() {
+  if [[ "$DIFF_MODE" == "git-working-tree" ]]; then
+    echo "dirty"
+  else
+    echo "clean"
+  fi
```

#### Staged Diff

```diff
No staged diff.
```

If a changed file is untracked and not represented in the diff above, review it directly from the working tree.

### Findings

#### P1

- None

#### P2

- None

#### P3

- None

### Residual Risks

- 同一批未提交改动里如果频繁重复执行 `review` / `finish`，`artifacts/review-report.md` 会继续线性追加条目；当前实现没有自动裁剪或折叠旧 entry，长开发周期下日志体积会持续增长。

### Reviewer Verdict

- Verdict: `PASS`
- Reviewer: `Codex`
- Reviewed at: `2026-04-06 16:39:52 CST`

### Notes

- If any `P1` or `P2` finding exists, completion must be blocked.
- If no findings exist, explicitly keep `None` entries rather than deleting sections.

## Review Entry 2

Generated at: 2026-04-06 16:38:51 CST
Entry mode: append
Git state before update: dirty

### Review Mode

- Mode: `git-working-tree`
- Prompt: `REVIEW_PROMPT.md`
- Checklist: `REVIEW_CHECKLIST.md`

### Change Summary

- Goal: 补 current-task 和 review-report 的增量更新逻辑
- Files changed / reviewed:
  - ` M scripts/dev_task.sh`
  - ` M scripts/run_reviewer.sh`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: no

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M scripts/dev_task.sh
 M scripts/run_reviewer.sh
```

#### Unstaged Diff

```diff
diff --git a/scripts/dev_task.sh b/scripts/dev_task.sh
index 8ed9e97..ea5870d 100644
--- a/scripts/dev_task.sh
+++ b/scripts/dev_task.sh
@@ -7,6 +7,11 @@ ARTIFACTS_DIR="$ROOT_DIR/artifacts"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REVIEW_FILE="$ROOT_DIR/artifacts/review-report.md"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
+GIT_TASK_PATHS=(
+  "."
+  ":(exclude)artifacts/current-task.md"
+  ":(exclude)artifacts/review-report.md"
+)
 
 usage() {
   cat <<EOF
@@ -30,21 +35,55 @@ ensure_artifacts_dir() {
   mkdir -p "$ARTIFACTS_DIR"
 }
 
-write_task_packet() {
-  local summary="$1"
+git_has_pending_project_changes() {
+  if ! git -C "$ROOT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
+    return 1
+  fi
 
-  ensure_artifacts_dir
+  git -C "$ROOT_DIR" status --short --untracked-files=all -- "${GIT_TASK_PATHS[@]}" | grep -q '.'
+}
+
+task_entry_count() {
+  if [[ ! -f "$TASK_FILE" ]]; then
+    echo 0
+    return
+  fi
+
+  awk '/^## Task Entry [0-9]+$/ { count++ } END { print count + 0 }' "$TASK_FILE"
+}
+
+write_log_header() {
+  local mode="$1"
+  local git_state="$2"
 
-  cat >"$TASK_FILE" <<EOF
-# Current Task
+  cat <<EOF
+# Current Task Log
+
+Last updated: $TIMESTAMP
+Update mode: $mode
+Git state before update: $git_state
+
+EOF
+}
+
+write_task_entry() {
+  local entry_number="$1"
+  local summary="$2"
+  local mode="$3"
+  local git_state="$4"
+
+  cat <<EOF
+## Task Entry $entry_number
 
 Generated at: $TIMESTAMP
+Entry mode: $mode
+Git state before update: $git_state
 
-## Goal
+### Goal
 
 $summary
 
-## Required Workflow
+### Required Workflow
 
 1. Read \`AGENTS.md\`
 2. Implement the change
@@ -54,19 +93,62 @@ $summary
 bash scripts/finalize_change.sh
 \`\`\`
 
-## Expected Deliverable
+### Expected Deliverable
 
 - Code changes aligned with the goal
 - Updated \`artifacts/review-report.md\`
 - Findings-first review result
 
-## Notes
+### Notes
 
 - If any \`P1\` or \`P2\` finding exists, completion is blocked.
 - Do not declare completion before the finalize gate passes.
 EOF
+}
 
-  echo "[dev-task] wrote task packet to $TASK_FILE"
+write_task_packet() {
+  local summary="$1"
+  local mode="reset"
+  local git_state="clean"
+  local entry_number="1"
+  local tmp_file
+  tmp_file="$(mktemp -t skill-manage-current-task.XXXXXX)"
+
+  ensure_artifacts_dir
+
+  if git_has_pending_project_changes && [[ -f "$TASK_FILE" ]]; then
+    mode="append"
+    git_state="dirty"
+    entry_number="$(( $(task_entry_count) + 1 ))"
+  fi
+
+  {
+    if [[ "$mode" == "reset" ]]; then
+      write_log_header "$mode" "$git_state"
+    else
+      if [[ -f "$TASK_FILE" ]] && grep -q '^## Task Entry [0-9]\+$' "$TASK_FILE"; then
+        cat "$TASK_FILE"
+        echo
+      elif [[ -f "$TASK_FILE" ]]; then
+        write_log_header "migrated" "legacy"
+        echo "## Legacy Snapshot"
+        echo
+        echo '```md'
+        cat "$TASK_FILE"
+        echo
+        echo '```'
+        echo
+      else
+        write_log_header "$mode" "$git_state"
+      fi
+    fi
+
+    write_task_entry "$entry_number" "$summary" "$mode" "$git_state"
+  } >"$tmp_file"
+
+  mv "$tmp_file" "$TASK_FILE"
+
+  echo "[dev-task] wrote task packet to $TASK_FILE ($mode)"
   echo "[dev-task] next:"
   echo "  - implement the change"
   echo "  - run: bash scripts/dev_task.sh check"
@@ -74,14 +156,39 @@ EOF
   echo "  - run: bash scripts/dev_task.sh finish"
 }
 
+print_latest_task_entry() {
+  if [[ ! -f "$TASK_FILE" ]]; then
+    echo "[dev-task] no current task packet yet"
+    return
+  fi
+
+  if grep -q '^## Task Entry [0-9]\+$' "$TASK_FILE"; then
+    awk '
+      /^## Task Entry [0-9]+$/ {
+        current = $0 ORS
+        capture = 1
+        next
+      }
+      capture {
+        current = current $0 ORS
+      }
+      END {
+        printf "%s", current
+      }
+    ' "$TASK_FILE"
+  else
+    sed -n '1,120p' "$TASK_FILE"
+  fi
+}
+
 print_status() {
   echo "[dev-task] root: $ROOT_DIR"
   echo "[dev-task] task file: $TASK_FILE"
   echo "[dev-task] review file: $REVIEW_FILE"
 
   if [[ -f "$TASK_FILE" ]]; then
-    echo "[dev-task] current task:"
-    sed -n '1,120p' "$TASK_FILE"
+    echo "[dev-task] latest task entry:"
+    print_latest_task_entry
   else
     echo "[dev-task] no current task packet yet"
   fi
diff --git a/scripts/run_reviewer.sh b/scripts/run_reviewer.sh
index 681d697..42404bc 100644
--- a/scripts/run_reviewer.sh
+++ b/scripts/run_reviewer.sh
@@ -46,9 +46,24 @@ collect_git_diff() {
 collect_task_goal() {
   if [[ -f "$TASK_FILE" ]]; then
     awk '
-      /^## Goal$/ { capture=1; next }
-      /^## / && capture { exit }
-      capture { print }
+      /^### Goal$/ {
+        capture=1
+        current=""
+        next
+      }
+      /^### / && capture {
+        last=current
+        capture=0
+      }
+      capture {
+        current = current $0 ORS
+      }
+      END {
+        if (capture) {
+          last=current
+        }
+        printf "%s", last
+      }
     ' "$TASK_FILE" | sed '/^[[:space:]]*$/d'
   fi
 }
@@ -105,23 +120,61 @@ if [[ "$DIFF_MODE" == "scope-only" ]]; then
   : >"$TMP_STAGED_DIFF"
 fi
 
-{
-  echo "# Review Report"
+review_entry_count() {
+  if [[ ! -f "$REPORT_FILE" ]]; then
+    echo 0
+    return
+  fi
+
+  awk '/^## Review Entry [0-9]+$/ { count++ } END { print count + 0 }' "$REPORT_FILE"
+}
+
+git_state_label() {
+  if [[ "$DIFF_MODE" == "git-working-tree" ]]; then
+    echo "dirty"
+  else
+    echo "clean"
+  fi
```

#### Staged Diff

```diff
No staged diff.
```

If a changed file is untracked and not represented in the diff above, review it directly from the working tree.

### Findings

#### P1

- None

#### P2

- None

#### P3

- None

### Residual Risks

- None

### Reviewer Verdict

- Verdict: `PASS / FAIL / PARTIAL`
- Reviewer:
- Reviewed at:

### Notes

- If any `P1` or `P2` finding exists, completion must be blocked.
- If no findings exist, explicitly keep `None` entries rather than deleting sections.

## Review Entry 3

Generated at: 2026-04-06 16:42:34 CST
Entry mode: append
Git state before update: dirty

### Review Mode

- Mode: `git-working-tree`
- Prompt: `REVIEW_PROMPT.md`
- Checklist: `REVIEW_CHECKLIST.md`

### Change Summary

- Goal: 补 current-task 和 review-report 的增量更新逻辑
- Files changed / reviewed:
  - ` M AGENTS.md`
  - ` M README.md`
  - ` M scripts/dev_task.sh`
  - ` M scripts/run_reviewer.sh`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: no

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M AGENTS.md
 M README.md
 M scripts/dev_task.sh
 M scripts/run_reviewer.sh
```

#### Unstaged Diff

```diff
diff --git a/AGENTS.md b/AGENTS.md
index 60f2949..f0402b1 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -42,6 +42,12 @@ bash scripts/dev_task.sh review
 bash scripts/run_reviewer.sh
 ```
 
+说明：
+
+- `artifacts/current-task.md` 与 `artifacts/review-report.md` 现在是增量日志文件，不再默认单次覆盖
+- 如果当前 git working tree 仍有未提交改动，则新任务和新 reviewer packet 应以 append 方式追加
+- 如果当前 git working tree 干净，则允许把下一次 `start` / `review` 视为新一轮开发周期的初始化，并重置当前视图
+
 4. 在 reviewer packet 生成后，必须完成一次真正的 findings-first code review：
 
 - review 必须基于以下输入材料：
@@ -92,6 +98,7 @@ Reviewer 角色必须遵守：
 - 不允许只生成 reviewer packet 而不执行真正的 code review
 - 不允许在存在 `P1` 或 `P2` finding 时宣告完成
 - 不允许让 reviewer 同时承担实现者角色并直接修改代码
+- 不允许在同一批未提交改动中无故覆盖掉已有 task/review 记录
 - 不允许用模糊表达替代结论，例如“应该没问题”“大概率可以”
 
 ## Goal
@@ -110,3 +117,15 @@ bash scripts/dev_task.sh finish
 ```
 
 这样可以把任务记录、本地检查、review packet 刷新、完成 gate 都收口到一个脚本上。
+
+## Artifact Retention
+
+- `artifacts/current-task.md`
+  - 记录当前未提交开发周期中的任务条目
+  - git working tree 脏时增量追加
+  - git working tree 干净时允许开启新一轮并重置当前视图
+- `artifacts/review-report.md`
+  - 记录当前未提交开发周期中的 reviewer packet 与 review 结果
+  - git working tree 脏时增量追加
+  - git working tree 干净时允许开启新一轮并重置当前视图
+- 如果历史文件还是旧格式，脚本首次运行时允许迁移为 log 结构，并保留 `Legacy Snapshot`
diff --git a/README.md b/README.md
index b3138e3..0489a07 100644
--- a/README.md
+++ b/README.md
@@ -190,7 +190,7 @@ finalize_change.sh
   - `finish` 用于进入完成 gate
   - `status` 用于查看当前任务与 review 文件位置
 - `scripts/run_reviewer.sh`
-  - 自动覆盖生成 `artifacts/review-report.md`
+  - 自动刷新 `artifacts/review-report.md`
   - 优先收集当前 `git status`、staged diff、unstaged diff
   - 如果没有 git 变更，再退化到全项目 scope review
 - `REVIEW_PROMPT.md`
@@ -200,8 +200,22 @@ finalize_change.sh
   - 严格 review 清单
   - 定义 findings-first 输出和严重级别
 - `artifacts/review-report.md`
-  - reviewer 输出模板
-  - 由 `scripts/run_reviewer.sh` 自动覆盖生成
+  - reviewer 输出日志
+  - 由 `scripts/run_reviewer.sh` 自动刷新
+
+### Artifact 保留策略
+
+这套 harness 不再把 `current-task.md` 和 `review-report.md` 当作“单次覆盖文件”，而是按 git 状态维护一组轻量日志：
+
+- git working tree 有未提交改动时：
+  - 新任务条目增量追加到 `artifacts/current-task.md`
+  - 新 reviewer packet / review 结果增量追加到 `artifacts/review-report.md`
+- git working tree 干净时：
+  - 下一次 `start` / `review` 会被视为新一轮开发周期，可以重置当前视图
+- 如果旧文件还是单次覆盖格式：
+  - 脚本会在首次运行时自动迁移成 log 结构，并保留 `Legacy Snapshot`
+
+这样做的目的，是避免同一批未提交改动里连续迭代 A、B 两个需求时，后一个条目把前一个条目直接覆盖掉。
 
 ### 推荐开发流程
 
@@ -254,6 +268,20 @@ bash scripts/finalize_change.sh
 
 也就是：**优先评审当前工作树中的真实改动，而不是整个仓库。**
 
+### 为什么 task / review 文件要做成增量日志
+
+如果同一批未提交改动里连续做了 A、B 两个需求，而 `current-task.md` 与 `review-report.md` 每次都直接覆盖，就会丢失：
+
+- A 需求最初的任务目标
+- A 需求对应的 reviewer packet
+- A 与 B 在同一批提交里是如何叠加出来的
+
+现在改成增量日志后：
+
+- 同一批未提交改动中的多次迭代可以并列保留
+- 提交后的下一轮开发又可以自然重置为新的起点
+- review 结论和任务目标能和 git working tree 的生命周期更一致
+
 ### 当前这套 harness 解决什么问题
 
 - 避免“代码改完但服务起不来”
diff --git a/scripts/dev_task.sh b/scripts/dev_task.sh
index 8ed9e97..ea5870d 100644
--- a/scripts/dev_task.sh
+++ b/scripts/dev_task.sh
@@ -7,6 +7,11 @@ ARTIFACTS_DIR="$ROOT_DIR/artifacts"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REVIEW_FILE="$ROOT_DIR/artifacts/review-report.md"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
+GIT_TASK_PATHS=(
+  "."
+  ":(exclude)artifacts/current-task.md"
+  ":(exclude)artifacts/review-report.md"
+)
 
 usage() {
   cat <<EOF
@@ -30,21 +35,55 @@ ensure_artifacts_dir() {
   mkdir -p "$ARTIFACTS_DIR"
 }
 
-write_task_packet() {
-  local summary="$1"
+git_has_pending_project_changes() {
+  if ! git -C "$ROOT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
+    return 1
+  fi
 
-  ensure_artifacts_dir
+  git -C "$ROOT_DIR" status --short --untracked-files=all -- "${GIT_TASK_PATHS[@]}" | grep -q '.'
+}
+
+task_entry_count() {
+  if [[ ! -f "$TASK_FILE" ]]; then
+    echo 0
+    return
+  fi
+
+  awk '/^## Task Entry [0-9]+$/ { count++ } END { print count + 0 }' "$TASK_FILE"
+}
+
+write_log_header() {
+  local mode="$1"
+  local git_state="$2"
 
-  cat >"$TASK_FILE" <<EOF
-# Current Task
+  cat <<EOF
+# Current Task Log
+
+Last updated: $TIMESTAMP
+Update mode: $mode
+Git state before update: $git_state
+
+EOF
+}
+
+write_task_entry() {
+  local entry_number="$1"
+  local summary="$2"
+  local mode="$3"
+  local git_state="$4"
+
+  cat <<EOF
+## Task Entry $entry_number
 
 Generated at: $TIMESTAMP
+Entry mode: $mode
+Git state before update: $git_state
 
-## Goal
+### Goal
 
 $summary
 
-## Required Workflow
+### Required Workflow
 
 1. Read \`AGENTS.md\`
 2. Implement the change
@@ -54,19 +93,62 @@ $summary
 bash scripts/finalize_change.sh
 \`\`\`
 
-## Expected Deliverable
+### Expected Deliverable
 
 - Code changes aligned with the goal
 - Updated \`artifacts/review-report.md\`
 - Findings-first review result
 
-## Notes
+### Notes
 
 - If any \`P1\` or \`P2\` finding exists, completion is blocked.
 - Do not declare completion before the finalize gate passes.
 EOF
+}
 
-  echo "[dev-task] wrote task packet to $TASK_FILE"
+write_task_packet() {
+  local summary="$1"
+  local mode="reset"
+  local git_state="clean"
+  local entry_number="1"
+  local tmp_file
+  tmp_file="$(mktemp -t skill-manage-current-task.XXXXXX)"
+
+  ensure_artifacts_dir
+
+  if git_has_pending_project_changes && [[ -f "$TASK_FILE" ]]; then
+    mode="append"
+    git_state="dirty"
+    entry_number="$(( $(task_entry_count) + 1 ))"
+  fi
+
+  {
+    if [[ "$mode" == "reset" ]]; then
+      write_log_header "$mode" "$git_state"
+    else
+      if [[ -f "$TASK_FILE" ]] && grep -q '^## Task Entry [0-9]\+$' "$TASK_FILE"; then
+        cat "$TASK_FILE"
+        echo
+      elif [[ -f "$TASK_FILE" ]]; then
+        write_log_header "migrated" "legacy"
+        echo "## Legacy Snapshot"
+        echo
+        echo '```md'
+        cat "$TASK_FILE"
+        echo
+        echo '```'
+        echo
+      else
+        write_log_header "$mode" "$git_state"
+      fi
+    fi
+
+    write_task_entry "$entry_number" "$summary" "$mode" "$git_state"
+  } >"$tmp_file"
+
+  mv "$tmp_file" "$TASK_FILE"
```

#### Staged Diff

```diff
No staged diff.
```

If a changed file is untracked and not represented in the diff above, review it directly from the working tree.

### Findings

#### P1

- None

#### P2

- None

#### P3

- None

### Residual Risks

- None

### Reviewer Verdict

- Verdict: `PASS / FAIL / PARTIAL`
- Reviewer:
- Reviewed at:

### Notes

- If any `P1` or `P2` finding exists, completion must be blocked.
- If no findings exist, explicitly keep `None` entries rather than deleting sections.

## Review Entry 4

Generated at: 2026-04-06 16:42:43 CST
Entry mode: append
Git state before update: dirty

### Review Mode

- Mode: `git-working-tree`
- Prompt: `REVIEW_PROMPT.md`
- Checklist: `REVIEW_CHECKLIST.md`

### Change Summary

- Goal: 补 current-task 和 review-report 的增量更新逻辑
- Files changed / reviewed:
  - ` M AGENTS.md`
  - ` M README.md`
  - ` M scripts/dev_task.sh`
  - ` M scripts/run_reviewer.sh`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: no

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M AGENTS.md
 M README.md
 M scripts/dev_task.sh
 M scripts/run_reviewer.sh
```

#### Unstaged Diff

```diff
diff --git a/AGENTS.md b/AGENTS.md
index 60f2949..f0402b1 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -42,6 +42,12 @@ bash scripts/dev_task.sh review
 bash scripts/run_reviewer.sh
 ```
 
+说明：
+
+- `artifacts/current-task.md` 与 `artifacts/review-report.md` 现在是增量日志文件，不再默认单次覆盖
+- 如果当前 git working tree 仍有未提交改动，则新任务和新 reviewer packet 应以 append 方式追加
+- 如果当前 git working tree 干净，则允许把下一次 `start` / `review` 视为新一轮开发周期的初始化，并重置当前视图
+
 4. 在 reviewer packet 生成后，必须完成一次真正的 findings-first code review：
 
 - review 必须基于以下输入材料：
@@ -92,6 +98,7 @@ Reviewer 角色必须遵守：
 - 不允许只生成 reviewer packet 而不执行真正的 code review
 - 不允许在存在 `P1` 或 `P2` finding 时宣告完成
 - 不允许让 reviewer 同时承担实现者角色并直接修改代码
+- 不允许在同一批未提交改动中无故覆盖掉已有 task/review 记录
 - 不允许用模糊表达替代结论，例如“应该没问题”“大概率可以”
 
 ## Goal
@@ -110,3 +117,15 @@ bash scripts/dev_task.sh finish
 ```
 
 这样可以把任务记录、本地检查、review packet 刷新、完成 gate 都收口到一个脚本上。
+
+## Artifact Retention
+
+- `artifacts/current-task.md`
+  - 记录当前未提交开发周期中的任务条目
+  - git working tree 脏时增量追加
+  - git working tree 干净时允许开启新一轮并重置当前视图
+- `artifacts/review-report.md`
+  - 记录当前未提交开发周期中的 reviewer packet 与 review 结果
+  - git working tree 脏时增量追加
+  - git working tree 干净时允许开启新一轮并重置当前视图
+- 如果历史文件还是旧格式，脚本首次运行时允许迁移为 log 结构，并保留 `Legacy Snapshot`
diff --git a/README.md b/README.md
index b3138e3..0489a07 100644
--- a/README.md
+++ b/README.md
@@ -190,7 +190,7 @@ finalize_change.sh
   - `finish` 用于进入完成 gate
   - `status` 用于查看当前任务与 review 文件位置
 - `scripts/run_reviewer.sh`
-  - 自动覆盖生成 `artifacts/review-report.md`
+  - 自动刷新 `artifacts/review-report.md`
   - 优先收集当前 `git status`、staged diff、unstaged diff
   - 如果没有 git 变更，再退化到全项目 scope review
 - `REVIEW_PROMPT.md`
@@ -200,8 +200,22 @@ finalize_change.sh
   - 严格 review 清单
   - 定义 findings-first 输出和严重级别
 - `artifacts/review-report.md`
-  - reviewer 输出模板
-  - 由 `scripts/run_reviewer.sh` 自动覆盖生成
+  - reviewer 输出日志
+  - 由 `scripts/run_reviewer.sh` 自动刷新
+
+### Artifact 保留策略
+
+这套 harness 不再把 `current-task.md` 和 `review-report.md` 当作“单次覆盖文件”，而是按 git 状态维护一组轻量日志：
+
+- git working tree 有未提交改动时：
+  - 新任务条目增量追加到 `artifacts/current-task.md`
+  - 新 reviewer packet / review 结果增量追加到 `artifacts/review-report.md`
+- git working tree 干净时：
+  - 下一次 `start` / `review` 会被视为新一轮开发周期，可以重置当前视图
+- 如果旧文件还是单次覆盖格式：
+  - 脚本会在首次运行时自动迁移成 log 结构，并保留 `Legacy Snapshot`
+
+这样做的目的，是避免同一批未提交改动里连续迭代 A、B 两个需求时，后一个条目把前一个条目直接覆盖掉。
 
 ### 推荐开发流程
 
@@ -254,6 +268,20 @@ bash scripts/finalize_change.sh
 
 也就是：**优先评审当前工作树中的真实改动，而不是整个仓库。**
 
+### 为什么 task / review 文件要做成增量日志
+
+如果同一批未提交改动里连续做了 A、B 两个需求，而 `current-task.md` 与 `review-report.md` 每次都直接覆盖，就会丢失：
+
+- A 需求最初的任务目标
+- A 需求对应的 reviewer packet
+- A 与 B 在同一批提交里是如何叠加出来的
+
+现在改成增量日志后：
+
+- 同一批未提交改动中的多次迭代可以并列保留
+- 提交后的下一轮开发又可以自然重置为新的起点
+- review 结论和任务目标能和 git working tree 的生命周期更一致
+
 ### 当前这套 harness 解决什么问题
 
 - 避免“代码改完但服务起不来”
diff --git a/scripts/dev_task.sh b/scripts/dev_task.sh
index 8ed9e97..ea5870d 100644
--- a/scripts/dev_task.sh
+++ b/scripts/dev_task.sh
@@ -7,6 +7,11 @@ ARTIFACTS_DIR="$ROOT_DIR/artifacts"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REVIEW_FILE="$ROOT_DIR/artifacts/review-report.md"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
+GIT_TASK_PATHS=(
+  "."
+  ":(exclude)artifacts/current-task.md"
+  ":(exclude)artifacts/review-report.md"
+)
 
 usage() {
   cat <<EOF
@@ -30,21 +35,55 @@ ensure_artifacts_dir() {
   mkdir -p "$ARTIFACTS_DIR"
 }
 
-write_task_packet() {
-  local summary="$1"
+git_has_pending_project_changes() {
+  if ! git -C "$ROOT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
+    return 1
+  fi
 
-  ensure_artifacts_dir
+  git -C "$ROOT_DIR" status --short --untracked-files=all -- "${GIT_TASK_PATHS[@]}" | grep -q '.'
+}
+
+task_entry_count() {
+  if [[ ! -f "$TASK_FILE" ]]; then
+    echo 0
+    return
+  fi
+
+  awk '/^## Task Entry [0-9]+$/ { count++ } END { print count + 0 }' "$TASK_FILE"
+}
+
+write_log_header() {
+  local mode="$1"
+  local git_state="$2"
 
-  cat >"$TASK_FILE" <<EOF
-# Current Task
+  cat <<EOF
+# Current Task Log
+
+Last updated: $TIMESTAMP
+Update mode: $mode
+Git state before update: $git_state
+
+EOF
+}
+
+write_task_entry() {
+  local entry_number="$1"
+  local summary="$2"
+  local mode="$3"
+  local git_state="$4"
+
+  cat <<EOF
+## Task Entry $entry_number
 
 Generated at: $TIMESTAMP
+Entry mode: $mode
+Git state before update: $git_state
 
-## Goal
+### Goal
 
 $summary
 
-## Required Workflow
+### Required Workflow
 
 1. Read \`AGENTS.md\`
 2. Implement the change
@@ -54,19 +93,62 @@ $summary
 bash scripts/finalize_change.sh
 \`\`\`
 
-## Expected Deliverable
+### Expected Deliverable
 
 - Code changes aligned with the goal
 - Updated \`artifacts/review-report.md\`
 - Findings-first review result
 
-## Notes
+### Notes
 
 - If any \`P1\` or \`P2\` finding exists, completion is blocked.
 - Do not declare completion before the finalize gate passes.
 EOF
+}
 
-  echo "[dev-task] wrote task packet to $TASK_FILE"
+write_task_packet() {
+  local summary="$1"
+  local mode="reset"
+  local git_state="clean"
+  local entry_number="1"
+  local tmp_file
+  tmp_file="$(mktemp -t skill-manage-current-task.XXXXXX)"
+
+  ensure_artifacts_dir
+
+  if git_has_pending_project_changes && [[ -f "$TASK_FILE" ]]; then
+    mode="append"
+    git_state="dirty"
+    entry_number="$(( $(task_entry_count) + 1 ))"
+  fi
+
+  {
+    if [[ "$mode" == "reset" ]]; then
+      write_log_header "$mode" "$git_state"
+    else
+      if [[ -f "$TASK_FILE" ]] && grep -q '^## Task Entry [0-9]\+$' "$TASK_FILE"; then
+        cat "$TASK_FILE"
+        echo
+      elif [[ -f "$TASK_FILE" ]]; then
+        write_log_header "migrated" "legacy"
+        echo "## Legacy Snapshot"
+        echo
+        echo '```md'
+        cat "$TASK_FILE"
+        echo
+        echo '```'
+        echo
+      else
+        write_log_header "$mode" "$git_state"
+      fi
+    fi
+
+    write_task_entry "$entry_number" "$summary" "$mode" "$git_state"
+  } >"$tmp_file"
+
+  mv "$tmp_file" "$TASK_FILE"
```

#### Staged Diff

```diff
No staged diff.
```

If a changed file is untracked and not represented in the diff above, review it directly from the working tree.

### Findings

#### P1

- None

#### P2

- None

#### P3

- None

### Residual Risks

- None

### Reviewer Verdict

- Verdict: `PASS / FAIL / PARTIAL`
- Reviewer:
- Reviewed at:

### Notes

- If any `P1` or `P2` finding exists, completion must be blocked.
- If no findings exist, explicitly keep `None` entries rather than deleting sections.
