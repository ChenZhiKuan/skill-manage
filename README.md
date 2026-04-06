# Skill Manage

一个本地运行的 Skill 浏览器，同时也是一个用极小成本验证 `review harness` 工作流的实验项目。

它有两条主线：

- 产品面：扫描本地常见 skill 目录，用一个简单的 Web 界面浏览、分类和查看 `SKILL.md`
- 工程面：把“改完代码就算完成”收紧成“先检查、再生成 reviewer packet、再进入完成 gate”

如果你只是想运行它，把它当作一个本地 skill atlas 即可；如果你关心的是 agent / harness engineering，它也展示了一套非常轻量的本地 review 流程。

## 项目定位

这个项目不是完整的插件市场，也不是成熟的技能管理平台。当前目标更聚焦在两件事：

1. 提供一个足够轻量的本地 skill 浏览器
2. 在真实的小项目里试验一套低成本、可复用、可被 agent 遵守的 review harness

## 功能概览

- 扫描常见 skill 根目录
- 首页支持按路径分类和按功能分类切换
- 支持前端搜索过滤
- 支持全站主题切换（浅色 / 深色 / 跟随系统）
- 支持通过 `npx skills` 搜索第三方 skill，并在页面里一键安装
- 详情页展示对应 `SKILL.md`
- 内置 `GET /api/skills` 和 `GET /api/health`

## 启动

```bash
cd /Users/ryan/kingswarecode/something/skill-manage
python3 app.py
```

默认地址：

```text
http://127.0.0.1:8421
```

自定义端口：

```bash
python3 app.py --port 9000
```

如果你要使用“搜索并安装 skill”功能，当前机器还需要能运行：

```bash
npx -y skills find react
```

安装动作会调用：

```bash
npx -y skills add <owner/repo@skill> -g -y
```

## 扫描路径

- `~/.agents/skills`
- `~/.codex/skills`
- `~/.codex/plugins`
- 当前工作区下的 `.agents/skills`
- 当前工作区下的 `miscellany/agent/skills`

## 项目结构

```text
skill-manage/
├── app.py                  # Python HTTP server
├── static/
│   ├── app.js              # Frontend behavior and theme switching
│   └── style.css           # Page styles
├── scripts/
│   ├── dev_task.sh         # Unified development entry
│   ├── review_harness.sh   # Local checks and smoke tests
│   ├── run_reviewer.sh     # Reviewer packet generator
│   └── finalize_change.sh  # Completion gate
├── artifacts/
│   ├── current-task.md     # Current task packet
│   └── review-report.md    # Reviewer output template
├── AGENTS.md               # Project rules / Definition of Done
├── REVIEW_PROMPT.md        # Reviewer contract
└── REVIEW_CHECKLIST.md     # Review checklist
```

## Review Harness

这个项目最特别的部分不是页面本身，而是它把 review 流程也作为项目的一部分版本化了。

### 核心思路

不是让 agent “记得 review 一下”，而是把 review 变成一条显式工作流：

1. 记录任务
2. 修改代码
3. 跑本地确定性检查
4. 生成 reviewer packet
5. 进入完成 gate
6. 根据 findings 决定是继续修复还是允许结束

### 流程图

```text
[开始任务]
    |
    v
dev_task.sh start
    |
    v
生成 artifacts/current-task.md
    |
    v
[实现改动]
    |
    v
dev_task.sh check
    |
    v
review_harness.sh
(语法检查 + smoke test)
    |
    v
dev_task.sh review
    |
    v
run_reviewer.sh
(生成 artifacts/review-report.md)
    |
    v
dev_task.sh finish
    |
    v
finalize_change.sh
(再次跑检查 + 确认 review-report 存在)
    |
    v
[Reviewer 填写 findings / verdict]
    |
    +--------------------------+
    |                          |
    | 有 P1 / P2               | 无 P1 / P2
    v                          v
[继续修复代码]              [允许宣告完成]
```

### 什么是 gate

这里的 `gate` 指“门禁点”或“过关点”。

在这个项目里，`scripts/finalize_change.sh` 就是一个轻量 completion gate。它的作用不是帮你自动判断代码质量，而是强制在“宣告完成”之前先满足最低要求：

- 本地 harness 已跑过
- reviewer packet 已生成
- `artifacts/review-report.md` 已存在

### 什么是 “如果有 P1/P2，继续修”

这句话的含义是：

- 如果 review 发现高严重度或中高严重度问题，这次改动不能算完成
- 必须继续修复，再重新走 `check -> review -> finish`

`P1 / P2 / P3` 的解释以 `REVIEW_CHECKLIST.md` 为准，但可以粗略理解成：

- `P1`：明显错误、主流程损坏、关键功能不可用
- `P2`：明确的回归风险、关键边界问题、重要结构缺陷
- `P3`：一般建议或低风险优化项

### 脚本与文件职责

- `AGENTS.md`
  - 项目级规则
  - 定义 completion gate 与 reviewer contract
- `scripts/review_harness.sh`
  - 本地检查脚本
  - 包含 Python / JS 语法检查
  - 默认包含进程内渲染 smoke test
  - 可选包含服务启动与 `/api/health`、`/api/skills` 检查
- `scripts/finalize_change.sh`
  - 统一完成出口
  - 先跑 harness，再生成 reviewer packet，并检查 review report 模板
- `scripts/dev_task.sh`
  - 统一开发入口
  - `start` 用于生成当前任务包
  - `check` 用于运行本地检查
  - `review` 用于刷新 reviewer packet
  - `finish` 用于进入完成 gate
  - `status` 用于查看当前任务与 review 文件位置
- `scripts/run_reviewer.sh`
  - 自动覆盖生成 `artifacts/review-report.md`
  - 优先收集当前 `git status`、staged diff、unstaged diff
  - 如果没有 git 变更，再退化到全项目 scope review
- `REVIEW_PROMPT.md`
  - 定义 reviewer 的严格评审口径
  - 约束 findings-first 输出格式
- `REVIEW_CHECKLIST.md`
  - 严格 review 清单
  - 定义 findings-first 输出和严重级别
- `artifacts/review-report.md`
  - reviewer 输出模板
  - 由 `scripts/run_reviewer.sh` 自动覆盖生成

### 推荐开发流程

现在推荐直接通过统一入口完成一次迭代：

```bash
cd /Users/ryan/kingswarecode/something/skill-manage
bash scripts/dev_task.sh start "描述这次要做的改动"
bash scripts/dev_task.sh check
bash scripts/dev_task.sh review
bash scripts/dev_task.sh finish
```

查看当前任务与 review 文件位置：

```bash
bash scripts/dev_task.sh status
```

如果当前环境允许本地绑定端口，可以额外开启端口级 smoke test：

```bash
RUN_BIND_SMOKE=1 bash scripts/review_harness.sh
```

如果只想单独运行某一步，也可以：

```bash
bash scripts/dev_task.sh check
bash scripts/dev_task.sh review
bash scripts/finalize_change.sh
```

### 为什么 git 仓库状态会改变 review 流程

现在项目已经进了 git，review 的重点也应该随之变化。

之前不是 git 仓库时，`run_reviewer.sh` 只能基于“当前项目全量 scope”生成 review packet，这会导致：

- reviewer 输入过大
- 改了一个小功能也要看全项目
- 很难判断这次变更真正影响了什么

现在变成 git 仓库后，review 更合理的默认输入是：

- `git status`
- unstaged diff
- staged diff
- untracked files

也就是：**优先评审当前工作树中的真实改动，而不是整个仓库。**

### 当前这套 harness 解决什么问题

- 避免“代码改完但服务起不来”
- 避免“页面或主路径已坏但没注意到”
- 避免 reviewer 输入过大、评审不聚焦
- 避免 review 只有泛泛评价，没有固定口径
- 为后续引入 reviewer subagent 或更强 gate 保留稳定 contract

## 备注

这是首版，功能分类目前以内置映射和简单规则为主；review harness 也还是轻量版，但已经足够支撑小项目里的真实迭代。
