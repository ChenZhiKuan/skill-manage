# Current Task

Generated at: 2026-04-06 16:14:41 CST

## Goal

为首页新增第三方 skill 搜索与一键安装能力，统一搜索结果卡片布局，优化 hero 区密度与中文指标文案，并确认 Skills CLI 当前不支持真实分页后移除误导性的“查看更多”

## Required Workflow

1. Read `AGENTS.md`
2. Implement the change
3. Before completion, run:

```bash
bash scripts/finalize_change.sh
```

## Expected Deliverable

- 首页支持基于 `npx skills find` 搜索第三方 skill，并调用 `npx skills add` 一键安装
- 搜索结果卡片与本地 skill 卡片保持一致，桌面端一行三列展示
- hero 区去掉左侧大块空白，右侧指标文案改为中文
- 搜索结果区不再展示会让人误以为存在“下一页结果”的查看更多控件
- Updated `artifacts/review-report.md`
- Findings-first review result

## Notes

- If any `P1` or `P2` finding exists, completion is blocked.
- Do not declare completion before the finalize gate passes.
