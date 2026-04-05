# Review Report

Generated at: 2026-04-05 17:17:54 CST

## Review Mode

- Mode: `git-working-tree`
- Prompt: `REVIEW_PROMPT.md`
- Checklist: `REVIEW_CHECKLIST.md`

## Change Summary

- Goal: 增加全站一键换肤，支持深色、浅色、跟随系统
- Files changed / reviewed:
  - ` M README.md`
  - ` M scripts/dev_task.sh`
  - ` M scripts/run_reviewer.sh`
- Expected behavior:

## Harness Checks

- Command: `bash scripts/review_harness.sh`
- Result: PASS
- Optional bind smoke run: no

## Review Context

Git working tree detected. Review should prioritize these changes:

### Git Status

```text
 M README.md
 M scripts/dev_task.sh
 M scripts/run_reviewer.sh
```

### Unstaged Diff

```diff
diff --git a/README.md b/README.md
index b2e5b60..cbd65f6 100644
--- a/README.md
+++ b/README.md
@@ -1,6 +1,29 @@
 # Skill Manage
 
-一个本地运行的 Skill 浏览器首版。
+一个本地运行的 Skill 浏览器，同时也是一个用极小成本验证 `review harness` 工作流的实验项目。
+
+它有两条主线：
+
+- 产品面：扫描本地常见 skill 目录，用一个简单的 Web 界面浏览、分类和查看 `SKILL.md`
+- 工程面：把“改完代码就算完成”收紧成“先检查、再生成 reviewer packet、再进入完成 gate”
+
+如果你只是想运行它，把它当作一个本地 skill atlas 即可；如果你关心的是 agent / harness engineering，它也展示了一套非常轻量的本地 review 流程。
+
+## 项目定位
+
+这个项目不是完整的插件市场，也不是成熟的技能管理平台。当前目标更聚焦在两件事：
+
+1. 提供一个足够轻量的本地 skill 浏览器
+2. 在真实的小项目里试验一套低成本、可复用、可被 agent 遵守的 review harness
+
+## 功能概览
+
+- 扫描常见 skill 根目录
+- 首页支持按路径分类和按功能分类切换
+- 支持前端搜索过滤
+- 支持全站主题切换（浅色 / 深色 / 跟随系统）
+- 详情页展示对应 `SKILL.md`
+- 内置 `GET /api/skills` 和 `GET /api/health`
 
 ## 启动
 
@@ -21,20 +44,119 @@ http://127.0.0.1:8421
 python3 app.py --port 9000
 ```
 
-## 当前能力
+## 扫描路径
 
-- 扫描常见 skill 根目录
-- 首页支持按路径分类和按功能分类切换
-- 支持前端搜索过滤
-- 支持全站主题切换（浅色 / 深色 / 跟随系统）
-- 详情页展示对应 `SKILL.md`
-- 内置 `GET /api/skills` 和 `GET /api/health`
+- `~/.agents/skills`
+- `~/.codex/skills`
+- `~/.codex/plugins`
+- 当前工作区下的 `.agents/skills`
+- 当前工作区下的 `miscellany/agent/skills`
+
+## 项目结构
+
+```text
+skill-manage/
+├── app.py                  # Python HTTP server
+├── static/
+│   ├── app.js              # Frontend behavior and theme switching
+│   └── style.css           # Page styles
+├── scripts/
+│   ├── dev_task.sh         # Unified development entry
+│   ├── review_harness.sh   # Local checks and smoke tests
+│   ├── run_reviewer.sh     # Reviewer packet generator
+│   └── finalize_change.sh  # Completion gate
+├── artifacts/
+│   ├── current-task.md     # Current task packet
+│   └── review-report.md    # Reviewer output template
+├── AGENTS.md               # Project rules / Definition of Done
+├── REVIEW_PROMPT.md        # Reviewer contract
+└── REVIEW_CHECKLIST.md     # Review checklist
+```
+
+## Review Harness
+
+这个项目最特别的部分不是页面本身，而是它把 review 流程也作为项目的一部分版本化了。
+
+### 核心思路
+
+不是让 agent “记得 review 一下”，而是把 review 变成一条显式工作流：
+
+1. 记录任务
+2. 修改代码
+3. 跑本地确定性检查
+4. 生成 reviewer packet
+5. 进入完成 gate
+6. 根据 findings 决定是继续修复还是允许结束
+
+### 流程图
+
+```text
+[开始任务]
+    |
+    v
+dev_task.sh start
+    |
+    v
+生成 artifacts/current-task.md
+    |
+    v
+[实现改动]
+    |
+    v
+dev_task.sh check
+    |
+    v
+review_harness.sh
+(语法检查 + smoke test)
+    |
+    v
+dev_task.sh review
+    |
+    v
+run_reviewer.sh
+(生成 artifacts/review-report.md)
+    |
+    v
+dev_task.sh finish
+    |
+    v
+finalize_change.sh
+(再次跑检查 + 确认 review-report 存在)
+    |
+    v
+[Reviewer 填写 findings / verdict]
+    |
+    +--------------------------+
+    |                          |
+    | 有 P1 / P2               | 无 P1 / P2
+    v                          v
+[继续修复代码]              [允许宣告完成]
+```
+
+### 什么是 gate
+
+这里的 `gate` 指“门禁点”或“过关点”。
+
+在这个项目里，`scripts/finalize_change.sh` 就是一个轻量 completion gate。它的作用不是帮你自动判断代码质量，而是强制在“宣告完成”之前先满足最低要求：
 
-## 最小 Review Harness
+- 本地 harness 已跑过
+- reviewer packet 已生成
+- `artifacts/review-report.md` 已存在
 
-项目内现在包含一个最小版 review harness，用于把“写完代码”变成“先检查、再评审”。
+### 什么是 “如果有 P1/P2，继续修”
 
-### 文件
+这句话的含义是：
+
+- 如果 review 发现高严重度或中高严重度问题，这次改动不能算完成
+- 必须继续修复，再重新走 `check -> review -> finish`
+
+`P1 / P2 / P3` 的解释以 `REVIEW_CHECKLIST.md` 为准，但可以粗略理解成：
+
+- `P1`：明显错误、主流程损坏、关键功能不可用
+- `P2`：明确的回归风险、关键边界问题、重要结构缺陷
+- `P3`：一般建议或低风险优化项
+
+### 脚本与文件职责
 
 - `AGENTS.md`
   - 项目级规则
@@ -56,8 +178,8 @@ python3 app.py --port 9000
   - `status` 用于查看当前任务与 review 文件位置
 - `scripts/run_reviewer.sh`
   - 自动覆盖生成 `artifacts/review-report.md`
-  - 收集当前 review scope
-  - 如果项目处于 git 仓库中，则优先附带 git diff
+  - 优先收集当前 `git status`、staged diff、unstaged diff
+  - 如果没有 git 变更，再退化到全项目 scope review
 - `REVIEW_PROMPT.md`
   - 定义 reviewer 的严格评审口径
   - 约束 findings-first 输出格式
@@ -68,39 +190,13 @@ python3 app.py --port 9000
   - reviewer 输出模板
   - 由 `scripts/run_reviewer.sh` 自动覆盖生成
 
-### 执行顺序
+### 推荐开发流程
 
-1. 任务开始时建议运行：
+现在推荐直接通过统一入口完成一次迭代：
 
 ```bash
 cd /Users/ryan/kingswarecode/something/skill-manage
 bash scripts/dev_task.sh start "描述这次要做的改动"
-```
-
-2. 完成本次改动
-3. 运行：
-
-```bash
-cd /Users/ryan/kingswarecode/something/skill-manage
-bash scripts/review_harness.sh
-```
-
-如果当前环境允许本地绑定端口，可以额外开启端口级 smoke test：
-
-```bash
-RUN_BIND_SMOKE=1 bash scripts/review_harness.sh
-```
-
-4. 脚本通过后，再按 `REVIEW_CHECKLIST.md` 做一轮严格 review
-5. 如果有 `P1` 或 `P2` finding，则阻断并修复
-6. 修复后重新执行脚本，再做复审
-
-### 统一入口
-
-如果不想分别记开始和结束命令，用统一入口：
-
-```bash
-bash scripts/dev_task.sh start "描述这次要做的改动"
 bash scripts/dev_task.sh check
 bash scripts/dev_task.sh review
 bash scripts/dev_task.sh finish
@@ -112,47 +208,47 @@ bash scripts/dev_task.sh finish
 bash scripts/dev_task.sh status
 ```
 
-如果只想通过统一入口跑本地检查：
+如果当前环境允许本地绑定端口，可以额外开启端口级 smoke test：
 
 ```bash
-bash scripts/dev_task.sh check
+RUN_BIND_SMOKE=1 bash scripts/review_harness.sh
 ```
 
-如果只想通过统一入口刷新 reviewer packet：
+如果只想单独运行某一步，也可以：
 
 ```bash
+bash scripts/dev_task.sh check
 bash scripts/dev_task.sh review
+bash scripts/finalize_change.sh
 ```
 
-如果你要把“完成前必须 review”做成统一出口，使用：
```

### Staged Diff

```diff
No staged diff.
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

- None

## Reviewer Verdict

- Verdict: `PASS / FAIL / PARTIAL`
- Reviewer:
- Reviewed at:

## Notes

- If any `P1` or `P2` finding exists, completion must be blocked.
- If no findings exist, explicitly keep `None` entries rather than deleting sections.
