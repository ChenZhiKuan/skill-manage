# 从 `skill-manage` 到 Harness Engineering：一组可复用的设计模式

## 1. 背景与判断口径

这份文档不是仓库说明，也不是对外文章，而是一份基于 `skill-manage` 现有实现整理出来的方法论笔记。目标有两个：

1. 先忠实总结 `skill-manage` 到底做了什么，为什么它已经有了 harness 的味道。
2. 再把这些做法向上抽象成一组可迁移的 Harness Engineering 设计模式。

这里先给出一个统一判断：

`skill-manage` 不是完整的 eval platform，不是纯单元测试集合，也不是只靠人工 review 的流程规范。它更接近一个轻量、agent-obeyable、带完成门禁的 review harness 雏形。

为了避免概念混淆，这里统一区分四层：

- `check`：确定性验证，例如语法检查、smoke test、契约检查。
- `review`：发现问题、形成 findings、给出 verdict。
- `gate`：决定“能不能宣称完成”的门禁点。
- `harness`：把 `check + review + gate` 串成一个可重复执行的闭环。

换句话说，测试并不自动等于 harness。只有当验证、评审和完成门禁被串成一条明确工作流时，才更接近 Harness Engineering。

## 2. `skill-manage` 的当前实践总结

如果只看页面功能，这个项目是一个本地 Skill 浏览器；但如果从工程实践看，它已经把“改完代码”重新定义成“先通过最小验证闭环，再允许结束”。

当前实践可以抽成六个事实层模式。

### 2.1 任务入口模式

项目通过 `start / check / review / finish / status` 这组统一入口，把开发流程从“记在脑子里”变成了显式步骤。

它解决的问题是：迭代过程容易散，执行者知道自己该做什么，但系统不知道这次开发到了哪一步。

在 `skill-manage` 里，它体现为：

- `scripts/dev_task.sh start`
- `scripts/dev_task.sh check`
- `scripts/dev_task.sh review`
- `scripts/dev_task.sh finish`
- `scripts/dev_task.sh status`

它已经超出“单纯自测”的原因是：这里记录的不是一个测试命令，而是一条从任务开始到完成门禁的工作流。

### 2.2 分层验证模式

项目没有一上来就押注重型测试，而是先建立低成本、稳定的分层验证。

它解决的问题是：如果验证层太重，大家会绕过；如果验证层太轻，又不足以构成最小可信度。

在 `skill-manage` 里，它体现为：

- Python / JS 语法检查
- in-process smoke checks
- 可选的 bind smoke checks

它已经超出“单纯自测”的原因是：这里不是“手动点一点页面”，而是把验证层做成了默认执行、可重复、可脚本化的 gate 前置步骤。

### 2.3 Reviewer Packet 模式

项目要求在进入完成 gate 之前先生成 reviewer packet 和 review report。

它解决的问题是：reviewer 很容易在缺乏上下文的情况下评审，只能做表层检查，难以形成 findings-first 输出。

在 `skill-manage` 里，它体现为：

- `scripts/run_reviewer.sh`
- `artifacts/current-task.md`
- `artifacts/review-report.md`

它已经超出“单纯自测”的原因是：系统不只要求“跑测试”，还要求给下一轮 review 提供结构化输入。

### 2.4 Completion Gate 模式

项目明确规定：如果 review 里存在 `P1 / P2` findings，就不能宣称完成。

它解决的问题是：很多项目虽然要求 review，但 review 的结论对完成状态没有约束力，最后还是“跑过测试就算 done”。

在 `skill-manage` 里，它体现为：

- `scripts/finalize_change.sh`
- `AGENTS.md` 里的 Definition of Done
- `REVIEW_CHECKLIST.md` 里的 findings-first 口径

它已经超出“单纯自测”的原因是：这里真正被 gate 的不是测试结果本身，而是“验证 + review 之后的完成资格”。

### 2.5 Artifact 留痕模式

项目不是只保留当前状态，而是保留 task 与 review 的增量日志。

它解决的问题是：很多轻量流程在单次对话里看起来清楚，但一旦连续迭代，就无法回看上一轮任务、review 结论和上下文差异。

在 `skill-manage` 里，它体现为：

- `artifacts/current-task.md`
- `artifacts/review-report.md`
- 基于 git working tree 的 append / reset 策略

它已经超出“单纯自测”的原因是：这里已经开始处理“证据保留”和“开发周期上下文”，而不仅是“当前是否通过”。

### 2.6 Agent 服从模式

项目通过 `AGENTS.md` 把流程从“写给人看的建议”变成了“写给 agent 的制度”。

它解决的问题是：如果流程只是 README 里的建议，agent 很容易绕过；只有当流程变成 Definition of Done，它才可能被持续执行。

在 `skill-manage` 里，它体现为：

- 必须跑 harness
- 必须生成 reviewer packet
- 必须更新 review report
- 存在 `P1 / P2` 时不得宣称完成

它已经超出“单纯自测”的原因是：这里已经在尝试把 Harness Engineering 写成一个 agent 能遵守的规则系统。

## 3. 六个 Harness Engineering 设计模式

基于上面的实践，可以进一步抽象成六个通用模式。

---

### 3.1 Completion Gate Pattern

**一句话定义**

“完成”必须经过门禁，而不能由提交者主观宣告。

**它解决的问题**

很多团队其实有测试、有 review，但缺少真正决定“能不能结束”的统一出口。结果是验证和评审存在，却不形成约束。

**在 `skill-manage` 中的映射**

- `scripts/finalize_change.sh`
- `AGENTS.md` 的 Definition of Done
- `P1 / P2` findings 阻断完成

**适用边界**

适用于任何希望把“自我声明完成”收紧成“通过最小验证闭环”的项目。尤其适合 agent 参与开发的场景。

**成本与收益**

- 成本：开发流会更显式，结束动作不再是随口一句“done”。
- 收益：把质量约束从道德层面变成流程层面。

**下一阶段怎么增强**

把 gate 从“脚本 + 人工判断”推进到“脚本 + 结构化 verdict + 自动阻断”。

---

### 3.2 Deterministic First Pattern

**一句话定义**

先跑稳定、便宜、可重复的 checks，再进入更昂贵的 review 环节。

**它解决的问题**

如果一开始就依赖昂贵的 review 或复杂的端到端验证，团队会自然绕过流程；如果完全没有确定性验证，又很难建立最低可信度。

**在 `skill-manage` 中的映射**

- 语法检查
- in-process smoke
- 可选 bind smoke

**适用边界**

适用于小团队、小项目、以及所有想先立住最低成本质量底座的场景。

**成本与收益**

- 成本：需要维护一组稳定的 smoke checks。
- 收益：把最常见的低级错误挡在 review 之前，降低 reviewer 负担。

**下一阶段怎么增强**

从 smoke checks 扩展到 task-level evals，例如固定场景、golden cases、契约回归集。

---

### 3.3 Reviewer Packet Pattern

**一句话定义**

reviewer 不应从零猜任务背景，而应拿到结构化上下文包。

**它解决的问题**

很多 review 低效，不是 reviewer 不认真，而是缺少任务目标、改动上下文、影响范围和预期输出。

**在 `skill-manage` 中的映射**

- `artifacts/current-task.md`
- `artifacts/review-report.md`
- `scripts/run_reviewer.sh`

**适用边界**

适用于人类 reviewer，也适用于 agent reviewer，尤其适合需要 findings-first 输出的流程。

**成本与收益**

- 成本：需要维护 packet 模板和生成逻辑。
- 收益：review 从“自由发挥”转向“基于上下文的定向审阅”。

**下一阶段怎么增强**

把 reviewer packet 进一步结构化，例如明确任务目标、变更范围、验证结果、已知风险、待确认点。

---

### 3.4 Findings-Driven Iteration Pattern

**一句话定义**

迭代是否继续，由 findings 的严重级别驱动，而不是由“测试跑过”驱动。

**它解决的问题**

“测试通过就合并”很容易掩盖重要的结构性问题、边界问题和回归风险。

**在 `skill-manage` 中的映射**

- `P1 / P2 / P3` findings 口径
- findings-first review contract
- `P1 / P2` 阻断完成

**适用边界**

适用于不希望把质量判断完全交给测试结果的项目，尤其适合 agent 参与实现但仍需要显式风险判断的场景。

**成本与收益**

- 成本：需要定义 findings 严重级别，并坚持执行。
- 收益：把 review 从“可选建议”变成驱动下一轮迭代的输入。

**下一阶段怎么增强**

把 findings 结构化存储，让 gate 能自动识别是否存在阻断级问题。

---

### 3.5 Artifact Trail Pattern

**一句话定义**

每一轮 task 和 review 都保留证据与上下文，而不是只保留最新状态。

**它解决的问题**

没有留痕的流程很难回看：为什么这轮通过、上一轮改了什么、哪次 review 提出了关键问题，都容易丢失。

**在 `skill-manage` 中的映射**

- `artifacts/current-task.md`
- `artifacts/review-report.md`
- append 风格日志与 legacy snapshot 迁移

**适用边界**

适用于连续迭代、多人协作、agent 协作，或任何需要回看上下文与决策链的项目。

**成本与收益**

- 成本：要处理日志增长和当前视图管理。
- 收益：获得最小可回看性，为归因、复盘和流程改进提供基础。

**下一阶段怎么增强**

把文本日志进一步演进为结构化 artifact，例如任务 ID、轮次、review verdict、验证结果索引。

---

### 3.6 Agent-Obeyable Workflow Pattern

**一句话定义**

把流程要求写成 agent 能执行的制度，而不是只写给人看的建议。

**它解决的问题**

如果流程只存在于 README 或团队默契里，agent 几乎一定会绕过；只有把流程写进规则，agent 才能把它当成任务的一部分。

**在 `skill-manage` 中的映射**

- `AGENTS.md`
- 明确禁止跳过 harness / review / review report / gate
- 完成说明必须包含 checks、results、findings、residual risks

**适用边界**

适用于任何引入 AI coding agent 的项目，尤其适合希望用规则收敛 agent 行为的团队。

**成本与收益**

- 成本：需要持续维护规则，并确保规则与脚本、工件、流程一致。
- 收益：把流程从“人类记忆”迁移到“系统约束”，提高稳定性。

**下一阶段怎么增强**

让 agent 规则和 gate 脚本共享同一套结构化协议，减少“规则写了一套、执行是一套”的偏差。

## 4. 演进路径与成熟度判断

如果把 Harness Engineering 当作一个连续谱，而不是非黑即白的标签，那么 `skill-manage` 更适合被放在下面这条路径里看。

### 阶段 1：Review Harness

特征：

- 有确定性 checks
- 有 review packet
- 有 findings-first review
- 有 completion gate
- 有 artifact 留痕

这一阶段的核心目标不是“自动评估一切”，而是建立最低可验证闭环。

`skill-manage` 当前大体就在这一阶段，而且完成度已经不低。它最重要的价值，不是测试覆盖率，而是把“完成”重新定义成“通过检查、review 和 gate”。

### 阶段 2：Task-Level Eval Harness

特征：

- 开始引入任务级回归样例
- 有 golden cases 或标准输入输出
- verdict 不再只靠自由文本 review
- 通过标准更结构化

这一阶段的核心目标，是把“review harness”推进成“带任务级评测能力的 harness”。

对 `skill-manage` 来说，下一步最值得补的不是盲目增加测试数量，而是补：

- 任务级回归 case
- golden output
- 结构化 verdict
- findings 与具体 case 的关联

### 阶段 3：Harness-Governed Runtime

特征：

- 验证结果、review findings、runtime evidence 开始统一收敛
- harness 不再只是完成前的动作，而成为运行时系统的一部分
- review、eval、execution evidence 开始形成闭环

这一阶段的核心目标，是把 Harness Engineering 从“开发流程工具”推进成“agent engineering 的控制面组成部分”。

对大多数小项目来说，这一阶段不需要一步到位；但它提供了一个清晰方向：未来 harness 不只是测试脚本，而是 runtime、evidence、gate 共同构成的治理层。

## 5. 结论：为什么它是一个小而真的起点

`skill-manage` 的价值，不在于它已经是一个成熟的 Harness Engineering 平台，而在于它已经跨过了一条关键分界线：

它不再把“自测”理解成“跑一下脚本”，而是把“完成”理解成“先过验证闭环，再允许结束”。

这正是 Harness Engineering 最值得保留的部分。

如果再压缩成一句话：

`skill-manage` 已经不是“带测试的小项目”，而是一个轻量、真实、可迁移的 review harness 雏形。

它的下一步，也不是变成更重的流程系统，而是继续把现有闭环结构化：从 smoke + review gate，走向 task-level eval 与更明确的 verdict 收敛。
