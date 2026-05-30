# R15 当前 SQL diff 与变更摘要

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M27` |
| 阶段 | `P3` |
| 前置依赖 | `M14`, `M25`, `M26`, `M03` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

比较当前页面内两段 SQL 的 AnalysisResult，输出字段、血缘、口径和诊断变化摘要。

## 3. 本模块做什么

- 基于 entity_id 比较节点边。
- 比较 output columns。
- 比较 lineage edges。
- 比较 semantics_report。
- 展示新增/删除/变化。

## 4. 本模块不做什么

- 不依赖历史快照。
- 不保存数据库。
- 不按 node label 或坐标比较。

## 5. 交付物

- backend/app/services/diff_service.py。
- frontend/src/components/DiffPanel/DiffPanel.tsx。
- tests/golden_cases/p3/current_sql_diff/。

## 6. 对外契约 / 输入输出

POST `/api/sql/diff` 输入 left_sql/right_sql 或 left_analysis/right_analysis，输出 DiffResult。

## 7. 建议实现步骤

- 定义 DiffResult。
- 实现 entity_id based compare。
- 实现字段差异。
- 实现边差异。
- 实现口径差异摘要。
- 前端展示 diff 面板。

## 8. 单元测试与集成测试

- 字段新增删除测试。
- 血缘边变化测试。
- 口径变化测试。
- 同 label 不同 entity_id 测试。

## 9. 回归测试要求

- 必须跑 P0/P1/P2 Golden Regression。
- 不得按 graph node 坐标比较。

## 10. 验收标准

- 当前 SQL diff 可用。
- diff 结果稳定可解释。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
