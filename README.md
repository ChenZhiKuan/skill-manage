# Skill Manage

一个本地运行的 Skill 浏览器首版。

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

## 当前能力

- 扫描常见 skill 根目录
- 首页支持按路径分类和按功能分类切换
- 支持前端搜索过滤
- 支持全站主题切换（浅色 / 深色 / 跟随系统）
- 详情页展示对应 `SKILL.md`
- 内置 `GET /api/skills` 和 `GET /api/health`

## 最小 Review Harness

项目内现在包含一个最小版 review harness，用于把“写完代码”变成“先检查、再评审”。

### 文件

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
  - 收集当前 review scope
  - 如果项目处于 git 仓库中，则优先附带 git diff
- `REVIEW_PROMPT.md`
  - 定义 reviewer 的严格评审口径
  - 约束 findings-first 输出格式
- `REVIEW_CHECKLIST.md`
  - 严格 review 清单
  - 定义 findings-first 输出和严重级别
- `artifacts/review-report.md`
  - reviewer 输出模板
  - 由 `scripts/run_reviewer.sh` 自动覆盖生成

### 执行顺序

1. 任务开始时建议运行：

```bash
cd /Users/ryan/kingswarecode/something/skill-manage
bash scripts/dev_task.sh start "描述这次要做的改动"
```

2. 完成本次改动
3. 运行：

```bash
cd /Users/ryan/kingswarecode/something/skill-manage
bash scripts/review_harness.sh
```

如果当前环境允许本地绑定端口，可以额外开启端口级 smoke test：

```bash
RUN_BIND_SMOKE=1 bash scripts/review_harness.sh
```

4. 脚本通过后，再按 `REVIEW_CHECKLIST.md` 做一轮严格 review
5. 如果有 `P1` 或 `P2` finding，则阻断并修复
6. 修复后重新执行脚本，再做复审

### 统一入口

如果不想分别记开始和结束命令，用统一入口：

```bash
bash scripts/dev_task.sh start "描述这次要做的改动"
bash scripts/dev_task.sh check
bash scripts/dev_task.sh review
bash scripts/dev_task.sh finish
```

查看当前任务与 review 文件位置：

```bash
bash scripts/dev_task.sh status
```

如果只想通过统一入口跑本地检查：

```bash
bash scripts/dev_task.sh check
```

如果只想通过统一入口刷新 reviewer packet：

```bash
bash scripts/dev_task.sh review
```

如果你要把“完成前必须 review”做成统一出口，使用：

```bash
bash scripts/finalize_change.sh
```

这一步会先刷新 reviewer packet，但不会替你自动下 review 结论。

如果只想单独刷新 reviewer 输出模板，可以运行：

```bash
bash scripts/run_reviewer.sh
```

### 这套最小 harness 解决什么问题

- 避免“代码改完但服务起不来”
- 避免“页面或渲染主路径已坏但没注意到”
- 避免 review 只有泛泛评价，没有固定口径
- 为后续引入 reviewer subagent 保留稳定 contract

## 当前扫描路径

- `~/.agents/skills`
- `~/.codex/skills`
- `~/.codex/plugins`
- 当前工作区下的 `.agents/skills`
- 当前工作区下的 `miscellany/agent/skills`

## 备注

这是首版，功能分类目前以内置映射和简单规则为主。
