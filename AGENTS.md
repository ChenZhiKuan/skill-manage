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

3. 优先通过统一入口生成或更新：

```bash
bash scripts/dev_task.sh review
```

等价命令为：

```text
artifacts/review-report.md
```

其中 `artifacts/review-report.md` 必须先通过以下命令生成最新 reviewer 包：

```bash
bash scripts/run_reviewer.sh
```

4. 如果存在 `P1` 或 `P2` finding，则不得结束，必须继续修复

5. 最终对用户的完成说明，必须包含：
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
