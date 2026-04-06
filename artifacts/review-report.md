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
