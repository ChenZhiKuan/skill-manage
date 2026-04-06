# Project Rules

本文件定义 `skill-manage` 项目的本地 agent 协作规则。

## Definition of Done

任何代码改动在声明完成前，必须完成以下步骤：

0. 建议先通过统一入口记录任务：

```bash
bash scripts/dev_task.sh start "<task summary>"
```

1. 优先通过统一入口运行本地检查：

```bash
bash scripts/dev_task.sh check
```

等价命令为：

```bash
bash scripts/review_harness.sh
```

2. 阅读并执行：

```text
REVIEW_CHECKLIST.md
```

3. 优先通过统一入口生成或更新 reviewer packet：

```bash
bash scripts/dev_task.sh review
```

等价命令为：

```bash
bash scripts/run_reviewer.sh
```

说明：

- `artifacts/current-task.md` 与 `artifacts/review-report.md` 现在是增量日志文件，不再默认单次覆盖
- 如果当前 git working tree 仍有未提交改动，则新任务和新 reviewer packet 应以 append 方式追加
- 如果当前 git working tree 干净，则允许把下一次 `start` / `review` 视为新一轮开发周期的初始化，并重置当前视图

4. 在 reviewer packet 生成后，必须完成一次真正的 findings-first code review：

- review 必须基于以下输入材料：
  - `REVIEW_PROMPT.md`
  - `REVIEW_CHECKLIST.md`
  - `artifacts/current-task.md`
  - `artifacts/review-report.md`
  - 当前改动涉及的源码文件
- reviewer 角色只读，不直接修改代码
- review 输出必须包含：
  - `Findings`
  - `Residual Risks`
  - `Verdict`
- 每条 finding 必须包含：
  - Severity
  - File
  - Why it matters
- 如果没有问题，明确写 `No findings`
- review 结果必须回填到：
  - `artifacts/review-report.md`

5. 如果存在 `P1` 或 `P2` finding，则不得结束，必须继续修复

6. 最终对用户的完成说明，必须包含：
   - 已运行的检查命令
   - 检查结果
   - 是否存在 findings
   - 是否存在 residual risks

## Reviewer Contract

Reviewer 角色必须遵守：

- 只读评审，不直接修改代码
- findings-first 输出
- 每条 finding 必须包含：
  - 严重级别
  - 文件位置
  - 风险说明
- 如果没有问题，明确写 `No findings`

## Engineering Constraints

- 不允许把 review 当成“最后顺手看一眼”
- 不允许在未执行 harness 的情况下宣告完成
- 不允许跳过 `scripts/run_reviewer.sh`
- 不允许跳过 `artifacts/review-report.md`
- 不允许只生成 reviewer packet 而不执行真正的 code review
- 不允许在存在 `P1` 或 `P2` finding 时宣告完成
- 不允许让 reviewer 同时承担实现者角色并直接修改代码
- 不允许在同一批未提交改动中无故覆盖掉已有 task/review 记录
- 不允许用模糊表达替代结论，例如“应该没问题”“大概率可以”

## Goal

本项目的目标不是“代码写完”，而是“代码经过最小可验证 review 流程后再结束”。

## Recommended Entry

优先使用统一入口：

```bash
bash scripts/dev_task.sh start "<task summary>"
bash scripts/dev_task.sh check
bash scripts/dev_task.sh review
bash scripts/dev_task.sh finish
```

这样可以把任务记录、本地检查、review packet 刷新、完成 gate 都收口到一个脚本上。

## Artifact Retention

- `artifacts/current-task.md`
  - 记录当前未提交开发周期中的任务条目
  - git working tree 脏时增量追加
  - git working tree 干净时允许开启新一轮并重置当前视图
- `artifacts/review-report.md`
  - 记录当前未提交开发周期中的 reviewer packet 与 review 结果
  - git working tree 脏时增量追加
  - git working tree 干净时允许开启新一轮并重置当前视图
- 如果历史文件还是旧格式，脚本首次运行时允许迁移为 log 结构，并保留 `Legacy Snapshot`
