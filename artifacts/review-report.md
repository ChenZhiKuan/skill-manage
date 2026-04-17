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

## Review Entry 5

Generated at: 2026-04-17 12:01:24 CST
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
  - ` M scripts/review_harness.sh`
  - ` M scripts/run_reviewer.sh`
  - `?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md`
  - `?? evals/task_cases.json`
  - `?? scripts/run_task_evals.py`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: no

### Task-Level Eval Summary

- Ran task-level evals: yes
- Result: `PASS`
- Cases:
  - PASS `home_path_view_renders`
  - PASS `skills_api_nonempty`
  - PASS `detail_page_renders_first_skill`
  - PASS `discover_empty_query_returns_recommendations`

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M AGENTS.md
 M README.md
 M scripts/review_harness.sh
 M scripts/run_reviewer.sh
?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md
?? evals/task_cases.json
?? scripts/run_task_evals.py
```

#### Unstaged Diff

```diff
diff --git a/AGENTS.md b/AGENTS.md
index f0402b1..43f9db8 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -24,6 +24,13 @@ bash scripts/dev_task.sh check
 bash scripts/review_harness.sh
 ```
 
+这里的本地 harness 默认包含：
+
+- 语法检查
+- in-process smoke checks
+- task-level evals
+- 可选 bind smoke
+
 2. 阅读并执行：
 
 ```text
diff --git a/README.md b/README.md
index 0489a07..ef3b90a 100644
--- a/README.md
+++ b/README.md
@@ -97,9 +97,10 @@ skill-manage/
 1. 记录任务
 2. 修改代码
 3. 跑本地确定性检查
-4. 生成 reviewer packet
-5. 进入完成 gate
-6. 根据 findings 决定是继续修复还是允许结束
+4. 跑任务级验收 case
+5. 生成 reviewer packet
+6. 进入完成 gate
+7. 根据 findings 决定是继续修复还是允许结束
 
 ### 流程图
 
@@ -120,7 +121,7 @@ dev_task.sh check
     |
     v
 review_harness.sh
-(语法检查 + smoke test)
+(语法检查 + smoke test + task-level eval)
     |
     v
 dev_task.sh review
@@ -178,6 +179,7 @@ finalize_change.sh
   - 本地检查脚本
   - 包含 Python / JS 语法检查
   - 默认包含进程内渲染 smoke test
+  - 默认包含 task-level eval
   - 可选包含服务启动与 `/api/health`、`/api/skills` 检查
 - `scripts/finalize_change.sh`
   - 统一完成出口
@@ -217,6 +219,18 @@ finalize_change.sh
 
 这样做的目的，是避免同一批未提交改动里连续迭代 A、B 两个需求时，后一个条目把前一个条目直接覆盖掉。
 
+### 什么是 task-level eval
+
+除了“系统能启动、接口能返回、页面能渲染”这些 smoke checks 之外，项目现在还补了一层 task-level eval。
+
+这一层的目标不是把 `skill-manage` 变成重型测试框架，而是补几组最核心的 golden cases，验证：
+
+- 首页主路径是否仍然成立
+- 详情页关键元数据是否还能正确展示
+- Discover 推荐模式是否仍然成立
+
+这样 harness 不再只验证“系统还活着”，也开始验证“这次核心任务是否真的做对了”。
+
 ### 推荐开发流程
 
 现在推荐直接通过统一入口完成一次迭代：
diff --git a/scripts/review_harness.sh b/scripts/review_harness.sh
index 6595c0a..1ca99c0 100644
--- a/scripts/review_harness.sh
+++ b/scripts/review_harness.sh
@@ -5,6 +5,7 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 APP_FILE="$ROOT_DIR/app.py"
 JS_FILE="$ROOT_DIR/static/app.js"
+TASK_EVAL_RUNNER="$ROOT_DIR/scripts/run_task_evals.py"
 HOST="${HOST:-127.0.0.1}"
 PORT="${PORT:-8421}"
 BASE_URL="http://${HOST}:${PORT}"
@@ -120,24 +121,27 @@ assert parsed[0].package == "vercel-labs/agent-skills@vercel-react-best-practice
 assert parsed[0].url == "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices"
 PY
 
-echo "[review] step 3/5: optional bind smoke mode"
+echo "[review] step 3/5: task-level evals"
+python3 "${TASK_EVAL_RUNNER}"
+
+echo "[review] step 4/5: optional bind smoke mode"
 if [[ "${RUN_BIND_SMOKE}" == "1" ]]; then
   require_cmd curl
   python3 "${APP_FILE}" --host "${HOST}" --port "${PORT}" >"${SERVER_LOG}" 2>&1 &
   SERVER_PID=$!
   wait_for_server
 
-  echo "[review] step 4/5: endpoint checks"
+  echo "[review] step 5/5: endpoint checks"
   assert_json_contains "${BASE_URL}/api/health" "health_ok"
   assert_json_contains "${BASE_URL}/api/skills" "skills_nonempty"
   assert_json_contains "${BASE_URL}/api/discover-skills" "discover_recommendations"
 
-  echo "[review] step 5/5: page smoke checks"
+  echo "[review] step 5/5: page request smoke checks"
   curl -fsS "${BASE_URL}/" >/dev/null
   curl -fsS "${BASE_URL}/?view=category" >/dev/null
 else
   echo "[review] bind smoke disabled (set RUN_BIND_SMOKE=1 to enable)"
-  echo "[review] step 4/5: endpoint contract skipped"
+  echo "[review] step 5/5: endpoint contract skipped"
   echo "[review] step 5/5: page request smoke skipped"
 fi
 
diff --git a/scripts/run_reviewer.sh b/scripts/run_reviewer.sh
index 42404bc..8fabfa4 100644
--- a/scripts/run_reviewer.sh
+++ b/scripts/run_reviewer.sh
@@ -5,9 +5,11 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REPORT_FILE="$ROOT_DIR/artifacts/review-report.md"
+TASK_EVAL_RUNNER="$ROOT_DIR/scripts/run_task_evals.py"
 TMP_DIFF="$(mktemp -t skill-manage-review-diff.XXXXXX)"
 TMP_STAGED_DIFF="$(mktemp -t skill-manage-review-staged-diff.XXXXXX)"
 TMP_STATUS="$(mktemp -t skill-manage-review-status.XXXXXX)"
+TMP_TASK_EVAL="$(mktemp -t skill-manage-task-eval.XXXXXX)"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
 GIT_REVIEW_PATHS=(
   "."
@@ -19,6 +21,7 @@ cleanup() {
   rm -f "$TMP_DIFF"
   rm -f "$TMP_STAGED_DIFF"
   rm -f "$TMP_STATUS"
+  rm -f "$TMP_TASK_EVAL"
 }
 
 trap cleanup EXIT
@@ -68,6 +71,60 @@ collect_task_goal() {
   fi
 }
 
+run_task_eval_summary() {
+  if python3 "$TASK_EVAL_RUNNER" --summary-only >"$TMP_TASK_EVAL" 2>&1; then
+    TASK_EVAL_EXIT=0
+  else
+    TASK_EVAL_EXIT=$?
+  fi
+}
+
+task_eval_result_label() {
+  if [[ "${TASK_EVAL_EXIT:-1}" -eq 0 ]]; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+emit_task_eval_case_lines() {
+  if [[ ! -f "$TMP_TASK_EVAL" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] PASS / {
+      id = $0
+      sub(/^\[task-eval\] PASS /, "", id)
+      print "  - PASS `" id "`"
+    }
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      split(line, parts, ": ")
+      id = parts[1]
+      message = line
+      sub(/^[^:]+: /, "", message)
+      print "  - FAIL `" id "` — " message
+    }
+  ' "$TMP_TASK_EVAL"
+}
+
+emit_task_eval_failed_case_ids() {
+  if [[ ! -f "$TMP_TASK_EVAL" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      sub(/:.*$/, "", line)
+      print line
+    }
+  ' "$TMP_TASK_EVAL"
+}
+
 strip_generated_artifact_noise() {
   if [[ -f "$TMP_STATUS" ]]; then
     grep -vE '^[[:space:]MADRCU\?]{2} artifacts/(current-task|review-report)\.md$' "$TMP_STATUS" >"$TMP_STATUS.filtered" || true
@@ -120,6 +177,8 @@ if [[ "$DIFF_MODE" == "scope-only" ]]; then
   : >"$TMP_STAGED_DIFF"
 fi
 
+run_task_eval_summary
+
 review_entry_count() {
   if [[ ! -f "$REPORT_FILE" ]]; then
     echo 0
@@ -192,9 +251,23 @@ write_review_entry() {
   echo "### Harness Checks"
   echo
   echo "- Command: \`bash scripts/review_harness.sh\`"
-  echo "- Result: PASS"
+  echo "- Result: $(task_eval_result_label)"
   echo "- Optional bind smoke run: no"
   echo
+  echo "### Task-Level Eval Summary"
+  echo
+  echo "- Ran task-level evals: yes"
+  echo "- Result: \`$(task_eval_result_label)\`"
+  echo "- Cases:"
+  emit_task_eval_case_lines
+  if [[ "${TASK_EVAL_EXIT:-1}" -ne 0 ]]; then
+    echo "- Failed case ids:"
+    while IFS= read -r case_id; do
+      [[ -z "$case_id" ]] && continue
+      echo "  - \`$case_id\`"
+    done < <(emit_task_eval_failed_case_ids)
+  fi
+  echo
   echo "### Review Context"
   echo
   if [[ "$DIFF_MODE" == "git-working-tree" ]]; then
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

## Review Entry 6

Generated at: 2026-04-17 14:28:39 CST
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
  - `A  evals/task_cases.json`
  - ` M scripts/review_harness.sh`
  - ` M scripts/run_reviewer.sh`
  - `A  scripts/run_task_evals.py`
  - `?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: FAIL
- Optional bind smoke run: no

### Task-Level Eval Summary

- Ran task-level evals: yes
- Result: `FAIL`
- Cases:
  - FAIL `home_path_view_renders` — expected output to contain '绝不可能存在的首页文案'
  - PASS `skills_api_nonempty`
  - PASS `detail_page_renders_first_skill`
  - PASS `discover_empty_query_returns_recommendations`
- Failed case ids:
  - `home_path_view_renders`

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M AGENTS.md
 M README.md
A  evals/task_cases.json
 M scripts/review_harness.sh
 M scripts/run_reviewer.sh
A  scripts/run_task_evals.py
?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md
```

#### Unstaged Diff

```diff
diff --git a/AGENTS.md b/AGENTS.md
index f0402b1..43f9db8 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -24,6 +24,13 @@ bash scripts/dev_task.sh check
 bash scripts/review_harness.sh
 ```
 
+这里的本地 harness 默认包含：
+
+- 语法检查
+- in-process smoke checks
+- task-level evals
+- 可选 bind smoke
+
 2. 阅读并执行：
 
 ```text
diff --git a/README.md b/README.md
index 0489a07..ef3b90a 100644
--- a/README.md
+++ b/README.md
@@ -97,9 +97,10 @@ skill-manage/
 1. 记录任务
 2. 修改代码
 3. 跑本地确定性检查
-4. 生成 reviewer packet
-5. 进入完成 gate
-6. 根据 findings 决定是继续修复还是允许结束
+4. 跑任务级验收 case
+5. 生成 reviewer packet
+6. 进入完成 gate
+7. 根据 findings 决定是继续修复还是允许结束
 
 ### 流程图
 
@@ -120,7 +121,7 @@ dev_task.sh check
     |
     v
 review_harness.sh
-(语法检查 + smoke test)
+(语法检查 + smoke test + task-level eval)
     |
     v
 dev_task.sh review
@@ -178,6 +179,7 @@ finalize_change.sh
   - 本地检查脚本
   - 包含 Python / JS 语法检查
   - 默认包含进程内渲染 smoke test
+  - 默认包含 task-level eval
   - 可选包含服务启动与 `/api/health`、`/api/skills` 检查
 - `scripts/finalize_change.sh`
   - 统一完成出口
@@ -217,6 +219,18 @@ finalize_change.sh
 
 这样做的目的，是避免同一批未提交改动里连续迭代 A、B 两个需求时，后一个条目把前一个条目直接覆盖掉。
 
+### 什么是 task-level eval
+
+除了“系统能启动、接口能返回、页面能渲染”这些 smoke checks 之外，项目现在还补了一层 task-level eval。
+
+这一层的目标不是把 `skill-manage` 变成重型测试框架，而是补几组最核心的 golden cases，验证：
+
+- 首页主路径是否仍然成立
+- 详情页关键元数据是否还能正确展示
+- Discover 推荐模式是否仍然成立
+
+这样 harness 不再只验证“系统还活着”，也开始验证“这次核心任务是否真的做对了”。
+
 ### 推荐开发流程
 
 现在推荐直接通过统一入口完成一次迭代：
diff --git a/scripts/review_harness.sh b/scripts/review_harness.sh
index 6595c0a..1ca99c0 100644
--- a/scripts/review_harness.sh
+++ b/scripts/review_harness.sh
@@ -5,6 +5,7 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 APP_FILE="$ROOT_DIR/app.py"
 JS_FILE="$ROOT_DIR/static/app.js"
+TASK_EVAL_RUNNER="$ROOT_DIR/scripts/run_task_evals.py"
 HOST="${HOST:-127.0.0.1}"
 PORT="${PORT:-8421}"
 BASE_URL="http://${HOST}:${PORT}"
@@ -120,24 +121,27 @@ assert parsed[0].package == "vercel-labs/agent-skills@vercel-react-best-practice
 assert parsed[0].url == "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices"
 PY
 
-echo "[review] step 3/5: optional bind smoke mode"
+echo "[review] step 3/5: task-level evals"
+python3 "${TASK_EVAL_RUNNER}"
+
+echo "[review] step 4/5: optional bind smoke mode"
 if [[ "${RUN_BIND_SMOKE}" == "1" ]]; then
   require_cmd curl
   python3 "${APP_FILE}" --host "${HOST}" --port "${PORT}" >"${SERVER_LOG}" 2>&1 &
   SERVER_PID=$!
   wait_for_server
 
-  echo "[review] step 4/5: endpoint checks"
+  echo "[review] step 5/5: endpoint checks"
   assert_json_contains "${BASE_URL}/api/health" "health_ok"
   assert_json_contains "${BASE_URL}/api/skills" "skills_nonempty"
   assert_json_contains "${BASE_URL}/api/discover-skills" "discover_recommendations"
 
-  echo "[review] step 5/5: page smoke checks"
+  echo "[review] step 5/5: page request smoke checks"
   curl -fsS "${BASE_URL}/" >/dev/null
   curl -fsS "${BASE_URL}/?view=category" >/dev/null
 else
   echo "[review] bind smoke disabled (set RUN_BIND_SMOKE=1 to enable)"
-  echo "[review] step 4/5: endpoint contract skipped"
+  echo "[review] step 5/5: endpoint contract skipped"
   echo "[review] step 5/5: page request smoke skipped"
 fi
 
diff --git a/scripts/run_reviewer.sh b/scripts/run_reviewer.sh
index 42404bc..03fc671 100644
--- a/scripts/run_reviewer.sh
+++ b/scripts/run_reviewer.sh
@@ -5,9 +5,11 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REPORT_FILE="$ROOT_DIR/artifacts/review-report.md"
+HARNESS_SCRIPT="$ROOT_DIR/scripts/review_harness.sh"
 TMP_DIFF="$(mktemp -t skill-manage-review-diff.XXXXXX)"
 TMP_STAGED_DIFF="$(mktemp -t skill-manage-review-staged-diff.XXXXXX)"
 TMP_STATUS="$(mktemp -t skill-manage-review-status.XXXXXX)"
+TMP_HARNESS="$(mktemp -t skill-manage-harness.XXXXXX)"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
 GIT_REVIEW_PATHS=(
   "."
@@ -19,6 +21,7 @@ cleanup() {
   rm -f "$TMP_DIFF"
   rm -f "$TMP_STAGED_DIFF"
   rm -f "$TMP_STATUS"
+  rm -f "$TMP_HARNESS"
 }
 
 trap cleanup EXIT
@@ -68,6 +71,74 @@ collect_task_goal() {
   fi
 }
 
+run_harness_snapshot() {
+  if bash "$HARNESS_SCRIPT" >"$TMP_HARNESS" 2>&1; then
+    HARNESS_EXIT=0
+  else
+    HARNESS_EXIT=$?
+  fi
+}
+
+harness_result_label() {
+  if [[ "${HARNESS_EXIT:-1}" -eq 0 ]]; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+task_eval_ran() {
+  [[ -f "$TMP_HARNESS" ]] && grep -q '^\[task-eval\] SUMMARY ' "$TMP_HARNESS"
+}
+
+task_eval_result_label() {
+  if ! task_eval_ran; then
+    echo "NOT_RUN"
+  elif grep -q '^\[task-eval\] RESULT PASS$' "$TMP_HARNESS"; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+emit_task_eval_case_lines() {
+  if [[ ! -f "$TMP_HARNESS" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] PASS / {
+      id = $0
+      sub(/^\[task-eval\] PASS /, "", id)
+      print "  - PASS `" id "`"
+    }
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      split(line, parts, ": ")
+      id = parts[1]
+      message = line
+      sub(/^[^:]+: /, "", message)
+      print "  - FAIL `" id "` — " message
+    }
+  ' "$TMP_HARNESS"
+}
+
+emit_task_eval_failed_case_ids() {
+  if [[ ! -f "$TMP_HARNESS" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      sub(/:.*$/, "", line)
+      print line
+    }
+  ' "$TMP_HARNESS"
+}
+
 strip_generated_artifact_noise() {
   if [[ -f "$TMP_STATUS" ]]; then
     grep -vE '^[[:space:]MADRCU\?]{2} artifacts/(current-task|review-report)\.md$' "$TMP_STATUS" >"$TMP_STATUS.filtered" || true
@@ -120,6 +191,8 @@ if [[ "$DIFF_MODE" == "scope-only" ]]; then
   : >"$TMP_STAGED_DIFF"
 fi
 
+run_harness_snapshot
+
 review_entry_count() {
   if [[ ! -f "$REPORT_FILE" ]]; then
     echo 0
@@ -192,9 +265,27 @@ write_review_entry() {
   echo "### Harness Checks"
   echo
   echo "- Command: \`bash scripts/review_harness.sh\`"
-  echo "- Result: PASS"
+  echo "- Result: $(harness_result_label)"
   echo "- Optional bind smoke run: no"
   echo
+  echo "### Task-Level Eval Summary"
+  echo
+  if task_eval_ran; then
+    echo "- Ran task-level evals: yes"
+  else
+    echo "- Ran task-level evals: no"
+  fi
+  echo "- Result: \`$(task_eval_result_label)\`"
```

#### Staged Diff

```diff
diff --git a/evals/task_cases.json b/evals/task_cases.json
new file mode 100644
index 0000000..a873eca
--- /dev/null
+++ b/evals/task_cases.json
@@ -0,0 +1,66 @@
+{
+  "cases": [
+    {
+      "id": "home_path_view_renders",
+      "title": "首页按路径视图可渲染",
+      "kind": "module_call",
+      "goal": "验证用户能看到基础 skill 浏览页和路径视图入口。",
+      "input": {
+        "target": "render_home",
+        "args": ["path"]
+      },
+      "expect": {
+        "contains": [
+          "本机 Skill 地图",
+          "按路径分类",
+          "Skill Atlas"
+        ]
+      }
+    },
+    {
+      "id": "skills_api_nonempty",
+      "title": "技能列表非空",
+      "kind": "module_call",
+      "goal": "验证本地 skill 扫描结果非空。",
+      "input": {
+        "target": "load_skills",
+        "args": []
+      },
+      "expect": {
+        "json_list_nonempty": true
+      }
+    },
+    {
+      "id": "detail_page_renders_first_skill",
+      "title": "详情页可渲染首个技能",
+      "kind": "module_call",
+      "goal": "验证用户能进入一个 skill 详情页并看到关键元数据。",
+      "input": {
+        "target": "render_detail",
+        "from_first_skill": true
+      },
+      "expect": {
+        "contains_fields_from_first_skill": [
+          "title",
+          "skill_path"
+        ]
+      }
+    },
+    {
+      "id": "discover_empty_query_returns_recommendations",
+      "title": "空查询返回推荐",
+      "kind": "module_call",
+      "goal": "验证发现面板在空查询时仍然返回推荐模式。",
+      "input": {
+        "target": "discover_skills",
+        "args": [""]
+      },
+      "expect": {
+        "json_field_equals": {
+          "mode": "recommend"
+        },
+        "json_list_nonempty": "suggestions"
+      }
+    }
+  ]
+}
diff --git a/scripts/run_task_evals.py b/scripts/run_task_evals.py
new file mode 100644
index 0000000..00ae229
--- /dev/null
+++ b/scripts/run_task_evals.py
@@ -0,0 +1,221 @@
+#!/usr/bin/env python3
+from __future__ import annotations
+
+import argparse
+import dataclasses
+import importlib.util
+import json
+import os
+import sys
+import urllib.request
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any
+
+
+ROOT_DIR = Path(__file__).resolve().parent.parent
+APP_PATH = ROOT_DIR / "app.py"
+DEFAULT_CASE_FILE = ROOT_DIR / "evals" / "task_cases.json"
+ALLOWED_TARGETS = {
+    "load_skills",
+    "render_home",
+    "render_detail",
+    "render_json",
+    "discover_skills",
+    "parse_find_results",
+}
+
+
+@dataclass
+class CaseResult:
+    case_id: str
+    ok: bool
+    detail: str
+
+
+def parse_args() -> argparse.Namespace:
+    parser = argparse.ArgumentParser(description="Run task-level evals for skill-manage.")
+    parser.add_argument("--summary-only", action="store_true", help="Emit concise summary only.")
+    return parser.parse_args()
+
+
+def load_app_module():
+    spec = importlib.util.spec_from_file_location("skill_manage_app", APP_PATH)
+    if spec is None or spec.loader is None:
+        raise RuntimeError(f"Failed to load app module from {APP_PATH}")
+    module = importlib.util.module_from_spec(spec)
+    sys.modules[spec.name] = module
+    spec.loader.exec_module(module)
+    return module
+
+
+def load_cases() -> list[dict[str, Any]]:
+    case_file = Path(os.environ.get("TASK_EVAL_CASE_FILE", str(DEFAULT_CASE_FILE)))
+    payload = json.loads(case_file.read_text(encoding="utf-8"))
+    cases = payload.get("cases")
+    if not isinstance(cases, list) or not cases:
+        raise RuntimeError("No task eval cases found.")
+    return cases
+
+
+def to_text(value: Any) -> str:
+    if isinstance(value, bytes):
+        return value.decode("utf-8")
+    if isinstance(value, str):
+        return value
+    try:
+        return json.dumps(value, ensure_ascii=False)
+    except TypeError:
+        if dataclasses.is_dataclass(value):
+            return json.dumps(dataclasses.asdict(value), ensure_ascii=False)
+        if isinstance(value, list):
+            normalized: list[Any] = []
+            for item in value:
+                if dataclasses.is_dataclass(item):
+                    normalized.append(dataclasses.asdict(item))
+                else:
+                    normalized.append(item)
+            return json.dumps(normalized, ensure_ascii=False)
+        return repr(value)
+
+
+def nested_get(payload: Any, dotted_key: str) -> Any:
+    current = payload
+    for part in dotted_key.split("."):
+        if isinstance(current, dict) and part in current:
+            current = current[part]
+        else:
+            raise KeyError(dotted_key)
+    return current
+
+
+def ensure_contains(text: str, needle: str) -> None:
+    if needle not in text:
+        raise AssertionError(f"expected output to contain {needle!r}")
+
+
+def assert_expectations(expect: dict[str, Any], raw_result: Any, text_result: str, first_skill: Any | None) -> None:
+    contains = expect.get("contains", [])
+    for needle in contains:
+        ensure_contains(text_result, str(needle))
+
+    equals = expect.get("equals")
+    if equals is not None and raw_result != equals:
+        raise AssertionError(f"expected exact result {equals!r}, got {raw_result!r}")
+
+    field_equals = expect.get("json_field_equals", {})
+    if field_equals:
+        if not isinstance(raw_result, dict):
+            raise AssertionError("json_field_equals requires dict result")
+        for key, expected_value in field_equals.items():
+            actual = nested_get(raw_result, key)
+            if actual != expected_value:
+                raise AssertionError(f"expected field {key!r} == {expected_value!r}, got {actual!r}")
+
+    nonempty = expect.get("json_list_nonempty")
+    if nonempty:
+        if isinstance(nonempty, bool):
+            target = raw_result
+        else:
+            if not isinstance(raw_result, dict):
+                raise AssertionError("json_list_nonempty path requires dict result")
+            target = nested_get(raw_result, str(nonempty))
+        if not isinstance(target, list) or len(target) == 0:
+            raise AssertionError("expected non-empty list")
+
+    field_contains = expect.get("contains_fields_from_first_skill", [])
+    if field_contains:
+        if first_skill is None:
+            raise AssertionError("contains_fields_from_first_skill requires first skill context")
+        for field_name in field_contains:
+            value = getattr(first_skill, field_name, None)
+            if not value:
+                raise AssertionError(f"first skill missing field {field_name!r}")
+            ensure_contains(text_result, str(value))
+
+
+def execute_module_case(module, case: dict[str, Any], first_skill: Any | None) -> tuple[Any, str]:
+    input_payload = case["input"]
+    target_name = input_payload["target"]
+    if target_name not in ALLOWED_TARGETS:
+        raise AssertionError(f"target {target_name!r} is not allowed")
+
+    target = getattr(module, target_name)
+    if input_payload.get("from_first_skill"):
+        if first_skill is None:
+            raise AssertionError("no skills available for first skill case")
+        raw_result = target(first_skill)
+    else:
+        args = input_payload.get("args", [])
+        raw_result = target(*args)
+    return raw_result, to_text(raw_result)
+
+
+def execute_http_case(case: dict[str, Any]) -> tuple[Any, str]:
+    if os.environ.get("TASK_EVAL_HTTP") != "1":
+        raise RuntimeError("http_contract cases require TASK_EVAL_HTTP=1")
+    base_url = os.environ.get("TASK_EVAL_BASE_URL")
+    if not base_url:
+        raise RuntimeError("http_contract cases require TASK_EVAL_BASE_URL")
+
+    path = case["input"].get("path", "/")
+    url = f"{base_url.rstrip('/')}{path}"
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

## Review Entry 7

Generated at: 2026-04-17 14:36:45 CST
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
  - `A  evals/task_cases.json`
  - ` M scripts/review_harness.sh`
  - ` M scripts/run_reviewer.sh`
  - `A  scripts/run_task_evals.py`
  - `?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: no

### Task-Level Eval Summary

- Ran task-level evals: yes
- Result: `PASS`
- Cases:
  - PASS `home_path_view_renders`
  - PASS `skills_api_nonempty`
  - PASS `detail_page_renders_first_skill`
  - PASS `discover_empty_query_returns_recommendations`

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M AGENTS.md
 M README.md
A  evals/task_cases.json
 M scripts/review_harness.sh
 M scripts/run_reviewer.sh
A  scripts/run_task_evals.py
?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md
```

#### Unstaged Diff

```diff
diff --git a/AGENTS.md b/AGENTS.md
index f0402b1..43f9db8 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -24,6 +24,13 @@ bash scripts/dev_task.sh check
 bash scripts/review_harness.sh
 ```
 
+这里的本地 harness 默认包含：
+
+- 语法检查
+- in-process smoke checks
+- task-level evals
+- 可选 bind smoke
+
 2. 阅读并执行：
 
 ```text
diff --git a/README.md b/README.md
index 0489a07..ef3b90a 100644
--- a/README.md
+++ b/README.md
@@ -97,9 +97,10 @@ skill-manage/
 1. 记录任务
 2. 修改代码
 3. 跑本地确定性检查
-4. 生成 reviewer packet
-5. 进入完成 gate
-6. 根据 findings 决定是继续修复还是允许结束
+4. 跑任务级验收 case
+5. 生成 reviewer packet
+6. 进入完成 gate
+7. 根据 findings 决定是继续修复还是允许结束
 
 ### 流程图
 
@@ -120,7 +121,7 @@ dev_task.sh check
     |
     v
 review_harness.sh
-(语法检查 + smoke test)
+(语法检查 + smoke test + task-level eval)
     |
     v
 dev_task.sh review
@@ -178,6 +179,7 @@ finalize_change.sh
   - 本地检查脚本
   - 包含 Python / JS 语法检查
   - 默认包含进程内渲染 smoke test
+  - 默认包含 task-level eval
   - 可选包含服务启动与 `/api/health`、`/api/skills` 检查
 - `scripts/finalize_change.sh`
   - 统一完成出口
@@ -217,6 +219,18 @@ finalize_change.sh
 
 这样做的目的，是避免同一批未提交改动里连续迭代 A、B 两个需求时，后一个条目把前一个条目直接覆盖掉。
 
+### 什么是 task-level eval
+
+除了“系统能启动、接口能返回、页面能渲染”这些 smoke checks 之外，项目现在还补了一层 task-level eval。
+
+这一层的目标不是把 `skill-manage` 变成重型测试框架，而是补几组最核心的 golden cases，验证：
+
+- 首页主路径是否仍然成立
+- 详情页关键元数据是否还能正确展示
+- Discover 推荐模式是否仍然成立
+
+这样 harness 不再只验证“系统还活着”，也开始验证“这次核心任务是否真的做对了”。
+
 ### 推荐开发流程
 
 现在推荐直接通过统一入口完成一次迭代：
diff --git a/scripts/review_harness.sh b/scripts/review_harness.sh
index 6595c0a..1ca99c0 100644
--- a/scripts/review_harness.sh
+++ b/scripts/review_harness.sh
@@ -5,6 +5,7 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 APP_FILE="$ROOT_DIR/app.py"
 JS_FILE="$ROOT_DIR/static/app.js"
+TASK_EVAL_RUNNER="$ROOT_DIR/scripts/run_task_evals.py"
 HOST="${HOST:-127.0.0.1}"
 PORT="${PORT:-8421}"
 BASE_URL="http://${HOST}:${PORT}"
@@ -120,24 +121,27 @@ assert parsed[0].package == "vercel-labs/agent-skills@vercel-react-best-practice
 assert parsed[0].url == "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices"
 PY
 
-echo "[review] step 3/5: optional bind smoke mode"
+echo "[review] step 3/5: task-level evals"
+python3 "${TASK_EVAL_RUNNER}"
+
+echo "[review] step 4/5: optional bind smoke mode"
 if [[ "${RUN_BIND_SMOKE}" == "1" ]]; then
   require_cmd curl
   python3 "${APP_FILE}" --host "${HOST}" --port "${PORT}" >"${SERVER_LOG}" 2>&1 &
   SERVER_PID=$!
   wait_for_server
 
-  echo "[review] step 4/5: endpoint checks"
+  echo "[review] step 5/5: endpoint checks"
   assert_json_contains "${BASE_URL}/api/health" "health_ok"
   assert_json_contains "${BASE_URL}/api/skills" "skills_nonempty"
   assert_json_contains "${BASE_URL}/api/discover-skills" "discover_recommendations"
 
-  echo "[review] step 5/5: page smoke checks"
+  echo "[review] step 5/5: page request smoke checks"
   curl -fsS "${BASE_URL}/" >/dev/null
   curl -fsS "${BASE_URL}/?view=category" >/dev/null
 else
   echo "[review] bind smoke disabled (set RUN_BIND_SMOKE=1 to enable)"
-  echo "[review] step 4/5: endpoint contract skipped"
+  echo "[review] step 5/5: endpoint contract skipped"
   echo "[review] step 5/5: page request smoke skipped"
 fi
 
diff --git a/scripts/run_reviewer.sh b/scripts/run_reviewer.sh
index 42404bc..03fc671 100644
--- a/scripts/run_reviewer.sh
+++ b/scripts/run_reviewer.sh
@@ -5,9 +5,11 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REPORT_FILE="$ROOT_DIR/artifacts/review-report.md"
+HARNESS_SCRIPT="$ROOT_DIR/scripts/review_harness.sh"
 TMP_DIFF="$(mktemp -t skill-manage-review-diff.XXXXXX)"
 TMP_STAGED_DIFF="$(mktemp -t skill-manage-review-staged-diff.XXXXXX)"
 TMP_STATUS="$(mktemp -t skill-manage-review-status.XXXXXX)"
+TMP_HARNESS="$(mktemp -t skill-manage-harness.XXXXXX)"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
 GIT_REVIEW_PATHS=(
   "."
@@ -19,6 +21,7 @@ cleanup() {
   rm -f "$TMP_DIFF"
   rm -f "$TMP_STAGED_DIFF"
   rm -f "$TMP_STATUS"
+  rm -f "$TMP_HARNESS"
 }
 
 trap cleanup EXIT
@@ -68,6 +71,74 @@ collect_task_goal() {
   fi
 }
 
+run_harness_snapshot() {
+  if bash "$HARNESS_SCRIPT" >"$TMP_HARNESS" 2>&1; then
+    HARNESS_EXIT=0
+  else
+    HARNESS_EXIT=$?
+  fi
+}
+
+harness_result_label() {
+  if [[ "${HARNESS_EXIT:-1}" -eq 0 ]]; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+task_eval_ran() {
+  [[ -f "$TMP_HARNESS" ]] && grep -q '^\[task-eval\] SUMMARY ' "$TMP_HARNESS"
+}
+
+task_eval_result_label() {
+  if ! task_eval_ran; then
+    echo "NOT_RUN"
+  elif grep -q '^\[task-eval\] RESULT PASS$' "$TMP_HARNESS"; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+emit_task_eval_case_lines() {
+  if [[ ! -f "$TMP_HARNESS" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] PASS / {
+      id = $0
+      sub(/^\[task-eval\] PASS /, "", id)
+      print "  - PASS `" id "`"
+    }
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      split(line, parts, ": ")
+      id = parts[1]
+      message = line
+      sub(/^[^:]+: /, "", message)
+      print "  - FAIL `" id "` — " message
+    }
+  ' "$TMP_HARNESS"
+}
+
+emit_task_eval_failed_case_ids() {
+  if [[ ! -f "$TMP_HARNESS" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      sub(/:.*$/, "", line)
+      print line
+    }
+  ' "$TMP_HARNESS"
+}
+
 strip_generated_artifact_noise() {
   if [[ -f "$TMP_STATUS" ]]; then
     grep -vE '^[[:space:]MADRCU\?]{2} artifacts/(current-task|review-report)\.md$' "$TMP_STATUS" >"$TMP_STATUS.filtered" || true
@@ -120,6 +191,8 @@ if [[ "$DIFF_MODE" == "scope-only" ]]; then
   : >"$TMP_STAGED_DIFF"
 fi
 
+run_harness_snapshot
+
 review_entry_count() {
   if [[ ! -f "$REPORT_FILE" ]]; then
     echo 0
@@ -192,9 +265,27 @@ write_review_entry() {
   echo "### Harness Checks"
   echo
   echo "- Command: \`bash scripts/review_harness.sh\`"
-  echo "- Result: PASS"
+  echo "- Result: $(harness_result_label)"
   echo "- Optional bind smoke run: no"
   echo
+  echo "### Task-Level Eval Summary"
+  echo
+  if task_eval_ran; then
+    echo "- Ran task-level evals: yes"
+  else
+    echo "- Ran task-level evals: no"
+  fi
+  echo "- Result: \`$(task_eval_result_label)\`"
```

#### Staged Diff

```diff
diff --git a/evals/task_cases.json b/evals/task_cases.json
new file mode 100644
index 0000000..a873eca
--- /dev/null
+++ b/evals/task_cases.json
@@ -0,0 +1,66 @@
+{
+  "cases": [
+    {
+      "id": "home_path_view_renders",
+      "title": "首页按路径视图可渲染",
+      "kind": "module_call",
+      "goal": "验证用户能看到基础 skill 浏览页和路径视图入口。",
+      "input": {
+        "target": "render_home",
+        "args": ["path"]
+      },
+      "expect": {
+        "contains": [
+          "本机 Skill 地图",
+          "按路径分类",
+          "Skill Atlas"
+        ]
+      }
+    },
+    {
+      "id": "skills_api_nonempty",
+      "title": "技能列表非空",
+      "kind": "module_call",
+      "goal": "验证本地 skill 扫描结果非空。",
+      "input": {
+        "target": "load_skills",
+        "args": []
+      },
+      "expect": {
+        "json_list_nonempty": true
+      }
+    },
+    {
+      "id": "detail_page_renders_first_skill",
+      "title": "详情页可渲染首个技能",
+      "kind": "module_call",
+      "goal": "验证用户能进入一个 skill 详情页并看到关键元数据。",
+      "input": {
+        "target": "render_detail",
+        "from_first_skill": true
+      },
+      "expect": {
+        "contains_fields_from_first_skill": [
+          "title",
+          "skill_path"
+        ]
+      }
+    },
+    {
+      "id": "discover_empty_query_returns_recommendations",
+      "title": "空查询返回推荐",
+      "kind": "module_call",
+      "goal": "验证发现面板在空查询时仍然返回推荐模式。",
+      "input": {
+        "target": "discover_skills",
+        "args": [""]
+      },
+      "expect": {
+        "json_field_equals": {
+          "mode": "recommend"
+        },
+        "json_list_nonempty": "suggestions"
+      }
+    }
+  ]
+}
diff --git a/scripts/run_task_evals.py b/scripts/run_task_evals.py
new file mode 100644
index 0000000..00ae229
--- /dev/null
+++ b/scripts/run_task_evals.py
@@ -0,0 +1,221 @@
+#!/usr/bin/env python3
+from __future__ import annotations
+
+import argparse
+import dataclasses
+import importlib.util
+import json
+import os
+import sys
+import urllib.request
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any
+
+
+ROOT_DIR = Path(__file__).resolve().parent.parent
+APP_PATH = ROOT_DIR / "app.py"
+DEFAULT_CASE_FILE = ROOT_DIR / "evals" / "task_cases.json"
+ALLOWED_TARGETS = {
+    "load_skills",
+    "render_home",
+    "render_detail",
+    "render_json",
+    "discover_skills",
+    "parse_find_results",
+}
+
+
+@dataclass
+class CaseResult:
+    case_id: str
+    ok: bool
+    detail: str
+
+
+def parse_args() -> argparse.Namespace:
+    parser = argparse.ArgumentParser(description="Run task-level evals for skill-manage.")
+    parser.add_argument("--summary-only", action="store_true", help="Emit concise summary only.")
+    return parser.parse_args()
+
+
+def load_app_module():
+    spec = importlib.util.spec_from_file_location("skill_manage_app", APP_PATH)
+    if spec is None or spec.loader is None:
+        raise RuntimeError(f"Failed to load app module from {APP_PATH}")
+    module = importlib.util.module_from_spec(spec)
+    sys.modules[spec.name] = module
+    spec.loader.exec_module(module)
+    return module
+
+
+def load_cases() -> list[dict[str, Any]]:
+    case_file = Path(os.environ.get("TASK_EVAL_CASE_FILE", str(DEFAULT_CASE_FILE)))
+    payload = json.loads(case_file.read_text(encoding="utf-8"))
+    cases = payload.get("cases")
+    if not isinstance(cases, list) or not cases:
+        raise RuntimeError("No task eval cases found.")
+    return cases
+
+
+def to_text(value: Any) -> str:
+    if isinstance(value, bytes):
+        return value.decode("utf-8")
+    if isinstance(value, str):
+        return value
+    try:
+        return json.dumps(value, ensure_ascii=False)
+    except TypeError:
+        if dataclasses.is_dataclass(value):
+            return json.dumps(dataclasses.asdict(value), ensure_ascii=False)
+        if isinstance(value, list):
+            normalized: list[Any] = []
+            for item in value:
+                if dataclasses.is_dataclass(item):
+                    normalized.append(dataclasses.asdict(item))
+                else:
+                    normalized.append(item)
+            return json.dumps(normalized, ensure_ascii=False)
+        return repr(value)
+
+
+def nested_get(payload: Any, dotted_key: str) -> Any:
+    current = payload
+    for part in dotted_key.split("."):
+        if isinstance(current, dict) and part in current:
+            current = current[part]
+        else:
+            raise KeyError(dotted_key)
+    return current
+
+
+def ensure_contains(text: str, needle: str) -> None:
+    if needle not in text:
+        raise AssertionError(f"expected output to contain {needle!r}")
+
+
+def assert_expectations(expect: dict[str, Any], raw_result: Any, text_result: str, first_skill: Any | None) -> None:
+    contains = expect.get("contains", [])
+    for needle in contains:
+        ensure_contains(text_result, str(needle))
+
+    equals = expect.get("equals")
+    if equals is not None and raw_result != equals:
+        raise AssertionError(f"expected exact result {equals!r}, got {raw_result!r}")
+
+    field_equals = expect.get("json_field_equals", {})
+    if field_equals:
+        if not isinstance(raw_result, dict):
+            raise AssertionError("json_field_equals requires dict result")
+        for key, expected_value in field_equals.items():
+            actual = nested_get(raw_result, key)
+            if actual != expected_value:
+                raise AssertionError(f"expected field {key!r} == {expected_value!r}, got {actual!r}")
+
+    nonempty = expect.get("json_list_nonempty")
+    if nonempty:
+        if isinstance(nonempty, bool):
+            target = raw_result
+        else:
+            if not isinstance(raw_result, dict):
+                raise AssertionError("json_list_nonempty path requires dict result")
+            target = nested_get(raw_result, str(nonempty))
+        if not isinstance(target, list) or len(target) == 0:
+            raise AssertionError("expected non-empty list")
+
+    field_contains = expect.get("contains_fields_from_first_skill", [])
+    if field_contains:
+        if first_skill is None:
+            raise AssertionError("contains_fields_from_first_skill requires first skill context")
+        for field_name in field_contains:
+            value = getattr(first_skill, field_name, None)
+            if not value:
+                raise AssertionError(f"first skill missing field {field_name!r}")
+            ensure_contains(text_result, str(value))
+
+
+def execute_module_case(module, case: dict[str, Any], first_skill: Any | None) -> tuple[Any, str]:
+    input_payload = case["input"]
+    target_name = input_payload["target"]
+    if target_name not in ALLOWED_TARGETS:
+        raise AssertionError(f"target {target_name!r} is not allowed")
+
+    target = getattr(module, target_name)
+    if input_payload.get("from_first_skill"):
+        if first_skill is None:
+            raise AssertionError("no skills available for first skill case")
+        raw_result = target(first_skill)
+    else:
+        args = input_payload.get("args", [])
+        raw_result = target(*args)
+    return raw_result, to_text(raw_result)
+
+
+def execute_http_case(case: dict[str, Any]) -> tuple[Any, str]:
+    if os.environ.get("TASK_EVAL_HTTP") != "1":
+        raise RuntimeError("http_contract cases require TASK_EVAL_HTTP=1")
+    base_url = os.environ.get("TASK_EVAL_BASE_URL")
+    if not base_url:
+        raise RuntimeError("http_contract cases require TASK_EVAL_BASE_URL")
+
+    path = case["input"].get("path", "/")
+    url = f"{base_url.rstrip('/')}{path}"
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

## Review Entry 8

Generated at: 2026-04-17 14:37:51 CST
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
  - `A  evals/task_cases.json`
  - ` M scripts/review_harness.sh`
  - ` M scripts/run_reviewer.sh`
  - `A  scripts/run_task_evals.py`
  - `?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: FAIL
- Optional bind smoke run: no

### Task-Level Eval Summary

- Ran task-level evals: yes
- Result: `PASS`
- Cases:
  - PASS `home_path_view_renders`
  - PASS `skills_api_nonempty`
  - PASS `detail_page_renders_first_skill`
  - PASS `discover_empty_query_returns_recommendations`

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M AGENTS.md
 M README.md
A  evals/task_cases.json
 M scripts/review_harness.sh
 M scripts/run_reviewer.sh
A  scripts/run_task_evals.py
?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md
```

#### Unstaged Diff

```diff
diff --git a/AGENTS.md b/AGENTS.md
index f0402b1..43f9db8 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -24,6 +24,13 @@ bash scripts/dev_task.sh check
 bash scripts/review_harness.sh
 ```
 
+这里的本地 harness 默认包含：
+
+- 语法检查
+- in-process smoke checks
+- task-level evals
+- 可选 bind smoke
+
 2. 阅读并执行：
 
 ```text
diff --git a/README.md b/README.md
index 0489a07..ef3b90a 100644
--- a/README.md
+++ b/README.md
@@ -97,9 +97,10 @@ skill-manage/
 1. 记录任务
 2. 修改代码
 3. 跑本地确定性检查
-4. 生成 reviewer packet
-5. 进入完成 gate
-6. 根据 findings 决定是继续修复还是允许结束
+4. 跑任务级验收 case
+5. 生成 reviewer packet
+6. 进入完成 gate
+7. 根据 findings 决定是继续修复还是允许结束
 
 ### 流程图
 
@@ -120,7 +121,7 @@ dev_task.sh check
     |
     v
 review_harness.sh
-(语法检查 + smoke test)
+(语法检查 + smoke test + task-level eval)
     |
     v
 dev_task.sh review
@@ -178,6 +179,7 @@ finalize_change.sh
   - 本地检查脚本
   - 包含 Python / JS 语法检查
   - 默认包含进程内渲染 smoke test
+  - 默认包含 task-level eval
   - 可选包含服务启动与 `/api/health`、`/api/skills` 检查
 - `scripts/finalize_change.sh`
   - 统一完成出口
@@ -217,6 +219,18 @@ finalize_change.sh
 
 这样做的目的，是避免同一批未提交改动里连续迭代 A、B 两个需求时，后一个条目把前一个条目直接覆盖掉。
 
+### 什么是 task-level eval
+
+除了“系统能启动、接口能返回、页面能渲染”这些 smoke checks 之外，项目现在还补了一层 task-level eval。
+
+这一层的目标不是把 `skill-manage` 变成重型测试框架，而是补几组最核心的 golden cases，验证：
+
+- 首页主路径是否仍然成立
+- 详情页关键元数据是否还能正确展示
+- Discover 推荐模式是否仍然成立
+
+这样 harness 不再只验证“系统还活着”，也开始验证“这次核心任务是否真的做对了”。
+
 ### 推荐开发流程
 
 现在推荐直接通过统一入口完成一次迭代：
diff --git a/scripts/review_harness.sh b/scripts/review_harness.sh
index 6595c0a..1ca99c0 100644
--- a/scripts/review_harness.sh
+++ b/scripts/review_harness.sh
@@ -5,6 +5,7 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 APP_FILE="$ROOT_DIR/app.py"
 JS_FILE="$ROOT_DIR/static/app.js"
+TASK_EVAL_RUNNER="$ROOT_DIR/scripts/run_task_evals.py"
 HOST="${HOST:-127.0.0.1}"
 PORT="${PORT:-8421}"
 BASE_URL="http://${HOST}:${PORT}"
@@ -120,24 +121,27 @@ assert parsed[0].package == "vercel-labs/agent-skills@vercel-react-best-practice
 assert parsed[0].url == "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices"
 PY
 
-echo "[review] step 3/5: optional bind smoke mode"
+echo "[review] step 3/5: task-level evals"
+python3 "${TASK_EVAL_RUNNER}"
+
+echo "[review] step 4/5: optional bind smoke mode"
 if [[ "${RUN_BIND_SMOKE}" == "1" ]]; then
   require_cmd curl
   python3 "${APP_FILE}" --host "${HOST}" --port "${PORT}" >"${SERVER_LOG}" 2>&1 &
   SERVER_PID=$!
   wait_for_server
 
-  echo "[review] step 4/5: endpoint checks"
+  echo "[review] step 5/5: endpoint checks"
   assert_json_contains "${BASE_URL}/api/health" "health_ok"
   assert_json_contains "${BASE_URL}/api/skills" "skills_nonempty"
   assert_json_contains "${BASE_URL}/api/discover-skills" "discover_recommendations"
 
-  echo "[review] step 5/5: page smoke checks"
+  echo "[review] step 5/5: page request smoke checks"
   curl -fsS "${BASE_URL}/" >/dev/null
   curl -fsS "${BASE_URL}/?view=category" >/dev/null
 else
   echo "[review] bind smoke disabled (set RUN_BIND_SMOKE=1 to enable)"
-  echo "[review] step 4/5: endpoint contract skipped"
+  echo "[review] step 5/5: endpoint contract skipped"
   echo "[review] step 5/5: page request smoke skipped"
 fi
 
diff --git a/scripts/run_reviewer.sh b/scripts/run_reviewer.sh
index 42404bc..7dc7b7f 100644
--- a/scripts/run_reviewer.sh
+++ b/scripts/run_reviewer.sh
@@ -5,9 +5,11 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REPORT_FILE="$ROOT_DIR/artifacts/review-report.md"
+HARNESS_SCRIPT="$ROOT_DIR/scripts/review_harness.sh"
 TMP_DIFF="$(mktemp -t skill-manage-review-diff.XXXXXX)"
 TMP_STAGED_DIFF="$(mktemp -t skill-manage-review-staged-diff.XXXXXX)"
 TMP_STATUS="$(mktemp -t skill-manage-review-status.XXXXXX)"
+TMP_HARNESS="$(mktemp -t skill-manage-harness.XXXXXX)"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
 GIT_REVIEW_PATHS=(
   "."
@@ -19,6 +21,7 @@ cleanup() {
   rm -f "$TMP_DIFF"
   rm -f "$TMP_STAGED_DIFF"
   rm -f "$TMP_STATUS"
+  rm -f "$TMP_HARNESS"
 }
 
 trap cleanup EXIT
@@ -68,6 +71,86 @@ collect_task_goal() {
   fi
 }
 
+run_harness_snapshot() {
+  if bash "$HARNESS_SCRIPT" >"$TMP_HARNESS" 2>&1; then
+    HARNESS_EXIT=0
+  else
+    HARNESS_EXIT=$?
+  fi
+}
+
+harness_result_label() {
+  if [[ "${HARNESS_EXIT:-1}" -eq 0 ]]; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+task_eval_ran() {
+  [[ -f "$TMP_HARNESS" ]] && grep -q '^\[task-eval\] SUMMARY ' "$TMP_HARNESS"
+}
+
+task_eval_result_label() {
+  if ! task_eval_ran; then
+    echo "NOT_RUN"
+  elif grep -q '^\[task-eval\] RESULT PASS$' "$TMP_HARNESS"; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+bind_smoke_ran() {
+  [[ -f "$TMP_HARNESS" ]] && grep -q '^\[review\] step 5/5: endpoint checks$' "$TMP_HARNESS"
+}
+
+bind_smoke_label() {
+  if bind_smoke_ran; then
+    echo "yes"
+  else
+    echo "no"
+  fi
+}
+
+emit_task_eval_case_lines() {
+  if [[ ! -f "$TMP_HARNESS" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] PASS / {
+      id = $0
+      sub(/^\[task-eval\] PASS /, "", id)
+      print "  - PASS `" id "`"
+    }
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      split(line, parts, ": ")
+      id = parts[1]
+      message = line
+      sub(/^[^:]+: /, "", message)
+      print "  - FAIL `" id "` — " message
+    }
+  ' "$TMP_HARNESS"
+}
+
+emit_task_eval_failed_case_ids() {
+  if [[ ! -f "$TMP_HARNESS" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      sub(/:.*$/, "", line)
+      print line
+    }
+  ' "$TMP_HARNESS"
+}
+
 strip_generated_artifact_noise() {
   if [[ -f "$TMP_STATUS" ]]; then
     grep -vE '^[[:space:]MADRCU\?]{2} artifacts/(current-task|review-report)\.md$' "$TMP_STATUS" >"$TMP_STATUS.filtered" || true
@@ -120,6 +203,8 @@ if [[ "$DIFF_MODE" == "scope-only" ]]; then
   : >"$TMP_STAGED_DIFF"
 fi
 
+run_harness_snapshot
+
 review_entry_count() {
   if [[ ! -f "$REPORT_FILE" ]]; then
     echo 0
@@ -192,8 +277,26 @@ write_review_entry() {
   echo "### Harness Checks"
   echo
   echo "- Command: \`bash scripts/review_harness.sh\`"
```

#### Staged Diff

```diff
diff --git a/evals/task_cases.json b/evals/task_cases.json
new file mode 100644
index 0000000..a873eca
--- /dev/null
+++ b/evals/task_cases.json
@@ -0,0 +1,66 @@
+{
+  "cases": [
+    {
+      "id": "home_path_view_renders",
+      "title": "首页按路径视图可渲染",
+      "kind": "module_call",
+      "goal": "验证用户能看到基础 skill 浏览页和路径视图入口。",
+      "input": {
+        "target": "render_home",
+        "args": ["path"]
+      },
+      "expect": {
+        "contains": [
+          "本机 Skill 地图",
+          "按路径分类",
+          "Skill Atlas"
+        ]
+      }
+    },
+    {
+      "id": "skills_api_nonempty",
+      "title": "技能列表非空",
+      "kind": "module_call",
+      "goal": "验证本地 skill 扫描结果非空。",
+      "input": {
+        "target": "load_skills",
+        "args": []
+      },
+      "expect": {
+        "json_list_nonempty": true
+      }
+    },
+    {
+      "id": "detail_page_renders_first_skill",
+      "title": "详情页可渲染首个技能",
+      "kind": "module_call",
+      "goal": "验证用户能进入一个 skill 详情页并看到关键元数据。",
+      "input": {
+        "target": "render_detail",
+        "from_first_skill": true
+      },
+      "expect": {
+        "contains_fields_from_first_skill": [
+          "title",
+          "skill_path"
+        ]
+      }
+    },
+    {
+      "id": "discover_empty_query_returns_recommendations",
+      "title": "空查询返回推荐",
+      "kind": "module_call",
+      "goal": "验证发现面板在空查询时仍然返回推荐模式。",
+      "input": {
+        "target": "discover_skills",
+        "args": [""]
+      },
+      "expect": {
+        "json_field_equals": {
+          "mode": "recommend"
+        },
+        "json_list_nonempty": "suggestions"
+      }
+    }
+  ]
+}
diff --git a/scripts/run_task_evals.py b/scripts/run_task_evals.py
new file mode 100644
index 0000000..00ae229
--- /dev/null
+++ b/scripts/run_task_evals.py
@@ -0,0 +1,221 @@
+#!/usr/bin/env python3
+from __future__ import annotations
+
+import argparse
+import dataclasses
+import importlib.util
+import json
+import os
+import sys
+import urllib.request
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any
+
+
+ROOT_DIR = Path(__file__).resolve().parent.parent
+APP_PATH = ROOT_DIR / "app.py"
+DEFAULT_CASE_FILE = ROOT_DIR / "evals" / "task_cases.json"
+ALLOWED_TARGETS = {
+    "load_skills",
+    "render_home",
+    "render_detail",
+    "render_json",
+    "discover_skills",
+    "parse_find_results",
+}
+
+
+@dataclass
+class CaseResult:
+    case_id: str
+    ok: bool
+    detail: str
+
+
+def parse_args() -> argparse.Namespace:
+    parser = argparse.ArgumentParser(description="Run task-level evals for skill-manage.")
+    parser.add_argument("--summary-only", action="store_true", help="Emit concise summary only.")
+    return parser.parse_args()
+
+
+def load_app_module():
+    spec = importlib.util.spec_from_file_location("skill_manage_app", APP_PATH)
+    if spec is None or spec.loader is None:
+        raise RuntimeError(f"Failed to load app module from {APP_PATH}")
+    module = importlib.util.module_from_spec(spec)
+    sys.modules[spec.name] = module
+    spec.loader.exec_module(module)
+    return module
+
+
+def load_cases() -> list[dict[str, Any]]:
+    case_file = Path(os.environ.get("TASK_EVAL_CASE_FILE", str(DEFAULT_CASE_FILE)))
+    payload = json.loads(case_file.read_text(encoding="utf-8"))
+    cases = payload.get("cases")
+    if not isinstance(cases, list) or not cases:
+        raise RuntimeError("No task eval cases found.")
+    return cases
+
+
+def to_text(value: Any) -> str:
+    if isinstance(value, bytes):
+        return value.decode("utf-8")
+    if isinstance(value, str):
+        return value
+    try:
+        return json.dumps(value, ensure_ascii=False)
+    except TypeError:
+        if dataclasses.is_dataclass(value):
+            return json.dumps(dataclasses.asdict(value), ensure_ascii=False)
+        if isinstance(value, list):
+            normalized: list[Any] = []
+            for item in value:
+                if dataclasses.is_dataclass(item):
+                    normalized.append(dataclasses.asdict(item))
+                else:
+                    normalized.append(item)
+            return json.dumps(normalized, ensure_ascii=False)
+        return repr(value)
+
+
+def nested_get(payload: Any, dotted_key: str) -> Any:
+    current = payload
+    for part in dotted_key.split("."):
+        if isinstance(current, dict) and part in current:
+            current = current[part]
+        else:
+            raise KeyError(dotted_key)
+    return current
+
+
+def ensure_contains(text: str, needle: str) -> None:
+    if needle not in text:
+        raise AssertionError(f"expected output to contain {needle!r}")
+
+
+def assert_expectations(expect: dict[str, Any], raw_result: Any, text_result: str, first_skill: Any | None) -> None:
+    contains = expect.get("contains", [])
+    for needle in contains:
+        ensure_contains(text_result, str(needle))
+
+    equals = expect.get("equals")
+    if equals is not None and raw_result != equals:
+        raise AssertionError(f"expected exact result {equals!r}, got {raw_result!r}")
+
+    field_equals = expect.get("json_field_equals", {})
+    if field_equals:
+        if not isinstance(raw_result, dict):
+            raise AssertionError("json_field_equals requires dict result")
+        for key, expected_value in field_equals.items():
+            actual = nested_get(raw_result, key)
+            if actual != expected_value:
+                raise AssertionError(f"expected field {key!r} == {expected_value!r}, got {actual!r}")
+
+    nonempty = expect.get("json_list_nonempty")
+    if nonempty:
+        if isinstance(nonempty, bool):
+            target = raw_result
+        else:
+            if not isinstance(raw_result, dict):
+                raise AssertionError("json_list_nonempty path requires dict result")
+            target = nested_get(raw_result, str(nonempty))
+        if not isinstance(target, list) or len(target) == 0:
+            raise AssertionError("expected non-empty list")
+
+    field_contains = expect.get("contains_fields_from_first_skill", [])
+    if field_contains:
+        if first_skill is None:
+            raise AssertionError("contains_fields_from_first_skill requires first skill context")
+        for field_name in field_contains:
+            value = getattr(first_skill, field_name, None)
+            if not value:
+                raise AssertionError(f"first skill missing field {field_name!r}")
+            ensure_contains(text_result, str(value))
+
+
+def execute_module_case(module, case: dict[str, Any], first_skill: Any | None) -> tuple[Any, str]:
+    input_payload = case["input"]
+    target_name = input_payload["target"]
+    if target_name not in ALLOWED_TARGETS:
+        raise AssertionError(f"target {target_name!r} is not allowed")
+
+    target = getattr(module, target_name)
+    if input_payload.get("from_first_skill"):
+        if first_skill is None:
+            raise AssertionError("no skills available for first skill case")
+        raw_result = target(first_skill)
+    else:
+        args = input_payload.get("args", [])
+        raw_result = target(*args)
+    return raw_result, to_text(raw_result)
+
+
+def execute_http_case(case: dict[str, Any]) -> tuple[Any, str]:
+    if os.environ.get("TASK_EVAL_HTTP") != "1":
+        raise RuntimeError("http_contract cases require TASK_EVAL_HTTP=1")
+    base_url = os.environ.get("TASK_EVAL_BASE_URL")
+    if not base_url:
+        raise RuntimeError("http_contract cases require TASK_EVAL_BASE_URL")
+
+    path = case["input"].get("path", "/")
+    url = f"{base_url.rstrip('/')}{path}"
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

## Review Entry 9

Generated at: 2026-04-17 14:38:42 CST
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
  - `A  evals/task_cases.json`
  - ` M scripts/review_harness.sh`
  - ` M scripts/run_reviewer.sh`
  - `A  scripts/run_task_evals.py`
  - `?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md`
- Expected behavior:

### Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: yes

### Task-Level Eval Summary

- Ran task-level evals: yes
- Result: `PASS`
- Cases:
  - PASS `home_path_view_renders`
  - PASS `skills_api_nonempty`
  - PASS `detail_page_renders_first_skill`
  - PASS `discover_empty_query_returns_recommendations`

### Review Context

Git working tree detected. Review should prioritize these changes:

#### Git Status

```text
 M AGENTS.md
 M README.md
A  evals/task_cases.json
 M scripts/review_harness.sh
 M scripts/run_reviewer.sh
A  scripts/run_task_evals.py
?? HARNESS_ENGINEERING_PATTERNS.zh-CN.md
```

#### Unstaged Diff

```diff
diff --git a/AGENTS.md b/AGENTS.md
index f0402b1..43f9db8 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -24,6 +24,13 @@ bash scripts/dev_task.sh check
 bash scripts/review_harness.sh
 ```
 
+这里的本地 harness 默认包含：
+
+- 语法检查
+- in-process smoke checks
+- task-level evals
+- 可选 bind smoke
+
 2. 阅读并执行：
 
 ```text
diff --git a/README.md b/README.md
index 0489a07..ef3b90a 100644
--- a/README.md
+++ b/README.md
@@ -97,9 +97,10 @@ skill-manage/
 1. 记录任务
 2. 修改代码
 3. 跑本地确定性检查
-4. 生成 reviewer packet
-5. 进入完成 gate
-6. 根据 findings 决定是继续修复还是允许结束
+4. 跑任务级验收 case
+5. 生成 reviewer packet
+6. 进入完成 gate
+7. 根据 findings 决定是继续修复还是允许结束
 
 ### 流程图
 
@@ -120,7 +121,7 @@ dev_task.sh check
     |
     v
 review_harness.sh
-(语法检查 + smoke test)
+(语法检查 + smoke test + task-level eval)
     |
     v
 dev_task.sh review
@@ -178,6 +179,7 @@ finalize_change.sh
   - 本地检查脚本
   - 包含 Python / JS 语法检查
   - 默认包含进程内渲染 smoke test
+  - 默认包含 task-level eval
   - 可选包含服务启动与 `/api/health`、`/api/skills` 检查
 - `scripts/finalize_change.sh`
   - 统一完成出口
@@ -217,6 +219,18 @@ finalize_change.sh
 
 这样做的目的，是避免同一批未提交改动里连续迭代 A、B 两个需求时，后一个条目把前一个条目直接覆盖掉。
 
+### 什么是 task-level eval
+
+除了“系统能启动、接口能返回、页面能渲染”这些 smoke checks 之外，项目现在还补了一层 task-level eval。
+
+这一层的目标不是把 `skill-manage` 变成重型测试框架，而是补几组最核心的 golden cases，验证：
+
+- 首页主路径是否仍然成立
+- 详情页关键元数据是否还能正确展示
+- Discover 推荐模式是否仍然成立
+
+这样 harness 不再只验证“系统还活着”，也开始验证“这次核心任务是否真的做对了”。
+
 ### 推荐开发流程
 
 现在推荐直接通过统一入口完成一次迭代：
diff --git a/scripts/review_harness.sh b/scripts/review_harness.sh
index 6595c0a..1ca99c0 100644
--- a/scripts/review_harness.sh
+++ b/scripts/review_harness.sh
@@ -5,6 +5,7 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 APP_FILE="$ROOT_DIR/app.py"
 JS_FILE="$ROOT_DIR/static/app.js"
+TASK_EVAL_RUNNER="$ROOT_DIR/scripts/run_task_evals.py"
 HOST="${HOST:-127.0.0.1}"
 PORT="${PORT:-8421}"
 BASE_URL="http://${HOST}:${PORT}"
@@ -120,24 +121,27 @@ assert parsed[0].package == "vercel-labs/agent-skills@vercel-react-best-practice
 assert parsed[0].url == "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices"
 PY
 
-echo "[review] step 3/5: optional bind smoke mode"
+echo "[review] step 3/5: task-level evals"
+python3 "${TASK_EVAL_RUNNER}"
+
+echo "[review] step 4/5: optional bind smoke mode"
 if [[ "${RUN_BIND_SMOKE}" == "1" ]]; then
   require_cmd curl
   python3 "${APP_FILE}" --host "${HOST}" --port "${PORT}" >"${SERVER_LOG}" 2>&1 &
   SERVER_PID=$!
   wait_for_server
 
-  echo "[review] step 4/5: endpoint checks"
+  echo "[review] step 5/5: endpoint checks"
   assert_json_contains "${BASE_URL}/api/health" "health_ok"
   assert_json_contains "${BASE_URL}/api/skills" "skills_nonempty"
   assert_json_contains "${BASE_URL}/api/discover-skills" "discover_recommendations"
 
-  echo "[review] step 5/5: page smoke checks"
+  echo "[review] step 5/5: page request smoke checks"
   curl -fsS "${BASE_URL}/" >/dev/null
   curl -fsS "${BASE_URL}/?view=category" >/dev/null
 else
   echo "[review] bind smoke disabled (set RUN_BIND_SMOKE=1 to enable)"
-  echo "[review] step 4/5: endpoint contract skipped"
+  echo "[review] step 5/5: endpoint contract skipped"
   echo "[review] step 5/5: page request smoke skipped"
 fi
 
diff --git a/scripts/run_reviewer.sh b/scripts/run_reviewer.sh
index 42404bc..7dc7b7f 100644
--- a/scripts/run_reviewer.sh
+++ b/scripts/run_reviewer.sh
@@ -5,9 +5,11 @@ set -euo pipefail
 ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 TASK_FILE="$ROOT_DIR/artifacts/current-task.md"
 REPORT_FILE="$ROOT_DIR/artifacts/review-report.md"
+HARNESS_SCRIPT="$ROOT_DIR/scripts/review_harness.sh"
 TMP_DIFF="$(mktemp -t skill-manage-review-diff.XXXXXX)"
 TMP_STAGED_DIFF="$(mktemp -t skill-manage-review-staged-diff.XXXXXX)"
 TMP_STATUS="$(mktemp -t skill-manage-review-status.XXXXXX)"
+TMP_HARNESS="$(mktemp -t skill-manage-harness.XXXXXX)"
 TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
 GIT_REVIEW_PATHS=(
   "."
@@ -19,6 +21,7 @@ cleanup() {
   rm -f "$TMP_DIFF"
   rm -f "$TMP_STAGED_DIFF"
   rm -f "$TMP_STATUS"
+  rm -f "$TMP_HARNESS"
 }
 
 trap cleanup EXIT
@@ -68,6 +71,86 @@ collect_task_goal() {
   fi
 }
 
+run_harness_snapshot() {
+  if bash "$HARNESS_SCRIPT" >"$TMP_HARNESS" 2>&1; then
+    HARNESS_EXIT=0
+  else
+    HARNESS_EXIT=$?
+  fi
+}
+
+harness_result_label() {
+  if [[ "${HARNESS_EXIT:-1}" -eq 0 ]]; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+task_eval_ran() {
+  [[ -f "$TMP_HARNESS" ]] && grep -q '^\[task-eval\] SUMMARY ' "$TMP_HARNESS"
+}
+
+task_eval_result_label() {
+  if ! task_eval_ran; then
+    echo "NOT_RUN"
+  elif grep -q '^\[task-eval\] RESULT PASS$' "$TMP_HARNESS"; then
+    echo "PASS"
+  else
+    echo "FAIL"
+  fi
+}
+
+bind_smoke_ran() {
+  [[ -f "$TMP_HARNESS" ]] && grep -q '^\[review\] step 5/5: endpoint checks$' "$TMP_HARNESS"
+}
+
+bind_smoke_label() {
+  if bind_smoke_ran; then
+    echo "yes"
+  else
+    echo "no"
+  fi
+}
+
+emit_task_eval_case_lines() {
+  if [[ ! -f "$TMP_HARNESS" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] PASS / {
+      id = $0
+      sub(/^\[task-eval\] PASS /, "", id)
+      print "  - PASS `" id "`"
+    }
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      split(line, parts, ": ")
+      id = parts[1]
+      message = line
+      sub(/^[^:]+: /, "", message)
+      print "  - FAIL `" id "` — " message
+    }
+  ' "$TMP_HARNESS"
+}
+
+emit_task_eval_failed_case_ids() {
+  if [[ ! -f "$TMP_HARNESS" ]]; then
+    return
+  fi
+
+  awk '
+    /^\[task-eval\] FAIL / {
+      line = $0
+      sub(/^\[task-eval\] FAIL /, "", line)
+      sub(/:.*$/, "", line)
+      print line
+    }
+  ' "$TMP_HARNESS"
+}
+
 strip_generated_artifact_noise() {
   if [[ -f "$TMP_STATUS" ]]; then
     grep -vE '^[[:space:]MADRCU\?]{2} artifacts/(current-task|review-report)\.md$' "$TMP_STATUS" >"$TMP_STATUS.filtered" || true
@@ -120,6 +203,8 @@ if [[ "$DIFF_MODE" == "scope-only" ]]; then
   : >"$TMP_STAGED_DIFF"
 fi
 
+run_harness_snapshot
+
 review_entry_count() {
   if [[ ! -f "$REPORT_FILE" ]]; then
     echo 0
@@ -192,8 +277,26 @@ write_review_entry() {
   echo "### Harness Checks"
   echo
   echo "- Command: \`bash scripts/review_harness.sh\`"
```

#### Staged Diff

```diff
diff --git a/evals/task_cases.json b/evals/task_cases.json
new file mode 100644
index 0000000..a873eca
--- /dev/null
+++ b/evals/task_cases.json
@@ -0,0 +1,66 @@
+{
+  "cases": [
+    {
+      "id": "home_path_view_renders",
+      "title": "首页按路径视图可渲染",
+      "kind": "module_call",
+      "goal": "验证用户能看到基础 skill 浏览页和路径视图入口。",
+      "input": {
+        "target": "render_home",
+        "args": ["path"]
+      },
+      "expect": {
+        "contains": [
+          "本机 Skill 地图",
+          "按路径分类",
+          "Skill Atlas"
+        ]
+      }
+    },
+    {
+      "id": "skills_api_nonempty",
+      "title": "技能列表非空",
+      "kind": "module_call",
+      "goal": "验证本地 skill 扫描结果非空。",
+      "input": {
+        "target": "load_skills",
+        "args": []
+      },
+      "expect": {
+        "json_list_nonempty": true
+      }
+    },
+    {
+      "id": "detail_page_renders_first_skill",
+      "title": "详情页可渲染首个技能",
+      "kind": "module_call",
+      "goal": "验证用户能进入一个 skill 详情页并看到关键元数据。",
+      "input": {
+        "target": "render_detail",
+        "from_first_skill": true
+      },
+      "expect": {
+        "contains_fields_from_first_skill": [
+          "title",
+          "skill_path"
+        ]
+      }
+    },
+    {
+      "id": "discover_empty_query_returns_recommendations",
+      "title": "空查询返回推荐",
+      "kind": "module_call",
+      "goal": "验证发现面板在空查询时仍然返回推荐模式。",
+      "input": {
+        "target": "discover_skills",
+        "args": [""]
+      },
+      "expect": {
+        "json_field_equals": {
+          "mode": "recommend"
+        },
+        "json_list_nonempty": "suggestions"
+      }
+    }
+  ]
+}
diff --git a/scripts/run_task_evals.py b/scripts/run_task_evals.py
new file mode 100644
index 0000000..00ae229
--- /dev/null
+++ b/scripts/run_task_evals.py
@@ -0,0 +1,221 @@
+#!/usr/bin/env python3
+from __future__ import annotations
+
+import argparse
+import dataclasses
+import importlib.util
+import json
+import os
+import sys
+import urllib.request
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any
+
+
+ROOT_DIR = Path(__file__).resolve().parent.parent
+APP_PATH = ROOT_DIR / "app.py"
+DEFAULT_CASE_FILE = ROOT_DIR / "evals" / "task_cases.json"
+ALLOWED_TARGETS = {
+    "load_skills",
+    "render_home",
+    "render_detail",
+    "render_json",
+    "discover_skills",
+    "parse_find_results",
+}
+
+
+@dataclass
+class CaseResult:
+    case_id: str
+    ok: bool
+    detail: str
+
+
+def parse_args() -> argparse.Namespace:
+    parser = argparse.ArgumentParser(description="Run task-level evals for skill-manage.")
+    parser.add_argument("--summary-only", action="store_true", help="Emit concise summary only.")
+    return parser.parse_args()
+
+
+def load_app_module():
+    spec = importlib.util.spec_from_file_location("skill_manage_app", APP_PATH)
+    if spec is None or spec.loader is None:
+        raise RuntimeError(f"Failed to load app module from {APP_PATH}")
+    module = importlib.util.module_from_spec(spec)
+    sys.modules[spec.name] = module
+    spec.loader.exec_module(module)
+    return module
+
+
+def load_cases() -> list[dict[str, Any]]:
+    case_file = Path(os.environ.get("TASK_EVAL_CASE_FILE", str(DEFAULT_CASE_FILE)))
+    payload = json.loads(case_file.read_text(encoding="utf-8"))
+    cases = payload.get("cases")
+    if not isinstance(cases, list) or not cases:
+        raise RuntimeError("No task eval cases found.")
+    return cases
+
+
+def to_text(value: Any) -> str:
+    if isinstance(value, bytes):
+        return value.decode("utf-8")
+    if isinstance(value, str):
+        return value
+    try:
+        return json.dumps(value, ensure_ascii=False)
+    except TypeError:
+        if dataclasses.is_dataclass(value):
+            return json.dumps(dataclasses.asdict(value), ensure_ascii=False)
+        if isinstance(value, list):
+            normalized: list[Any] = []
+            for item in value:
+                if dataclasses.is_dataclass(item):
+                    normalized.append(dataclasses.asdict(item))
+                else:
+                    normalized.append(item)
+            return json.dumps(normalized, ensure_ascii=False)
+        return repr(value)
+
+
+def nested_get(payload: Any, dotted_key: str) -> Any:
+    current = payload
+    for part in dotted_key.split("."):
+        if isinstance(current, dict) and part in current:
+            current = current[part]
+        else:
+            raise KeyError(dotted_key)
+    return current
+
+
+def ensure_contains(text: str, needle: str) -> None:
+    if needle not in text:
+        raise AssertionError(f"expected output to contain {needle!r}")
+
+
+def assert_expectations(expect: dict[str, Any], raw_result: Any, text_result: str, first_skill: Any | None) -> None:
+    contains = expect.get("contains", [])
+    for needle in contains:
+        ensure_contains(text_result, str(needle))
+
+    equals = expect.get("equals")
+    if equals is not None and raw_result != equals:
+        raise AssertionError(f"expected exact result {equals!r}, got {raw_result!r}")
+
+    field_equals = expect.get("json_field_equals", {})
+    if field_equals:
+        if not isinstance(raw_result, dict):
+            raise AssertionError("json_field_equals requires dict result")
+        for key, expected_value in field_equals.items():
+            actual = nested_get(raw_result, key)
+            if actual != expected_value:
+                raise AssertionError(f"expected field {key!r} == {expected_value!r}, got {actual!r}")
+
+    nonempty = expect.get("json_list_nonempty")
+    if nonempty:
+        if isinstance(nonempty, bool):
+            target = raw_result
+        else:
+            if not isinstance(raw_result, dict):
+                raise AssertionError("json_list_nonempty path requires dict result")
+            target = nested_get(raw_result, str(nonempty))
+        if not isinstance(target, list) or len(target) == 0:
+            raise AssertionError("expected non-empty list")
+
+    field_contains = expect.get("contains_fields_from_first_skill", [])
+    if field_contains:
+        if first_skill is None:
+            raise AssertionError("contains_fields_from_first_skill requires first skill context")
+        for field_name in field_contains:
+            value = getattr(first_skill, field_name, None)
+            if not value:
+                raise AssertionError(f"first skill missing field {field_name!r}")
+            ensure_contains(text_result, str(value))
+
+
+def execute_module_case(module, case: dict[str, Any], first_skill: Any | None) -> tuple[Any, str]:
+    input_payload = case["input"]
+    target_name = input_payload["target"]
+    if target_name not in ALLOWED_TARGETS:
+        raise AssertionError(f"target {target_name!r} is not allowed")
+
+    target = getattr(module, target_name)
+    if input_payload.get("from_first_skill"):
+        if first_skill is None:
+            raise AssertionError("no skills available for first skill case")
+        raw_result = target(first_skill)
+    else:
+        args = input_payload.get("args", [])
+        raw_result = target(*args)
+    return raw_result, to_text(raw_result)
+
+
+def execute_http_case(case: dict[str, Any]) -> tuple[Any, str]:
+    if os.environ.get("TASK_EVAL_HTTP") != "1":
+        raise RuntimeError("http_contract cases require TASK_EVAL_HTTP=1")
+    base_url = os.environ.get("TASK_EVAL_BASE_URL")
+    if not base_url:
+        raise RuntimeError("http_contract cases require TASK_EVAL_BASE_URL")
+
+    path = case["input"].get("path", "/")
+    url = f"{base_url.rstrip('/')}{path}"
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
