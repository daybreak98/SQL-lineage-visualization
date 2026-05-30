# R16 分析历史与快照

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M28` |
| 阶段 | `P3` |
| 前置依赖 | `M14`, `M27`, `M04` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

保存 SQL、AnalysisResult 和 GraphViewModel 快照，用于历史查看和历史 diff。

## 3. 本模块做什么

- analysis_history 表。
- analysis_snapshots 表。
- 保存和读取 AnalysisResult。
- 历史列表和历史 diff。

## 4. 本模块不做什么

- 不做权限体系。
- 不做多项目空间。
- 不做跨版本 schema migration 的复杂兼容。

## 5. 交付物

- backend/app/repositories/analysis_repository.py。
- backend/app/api/history_controller.py。
- frontend/src/components/HistoryPanel/HistoryPanel.tsx。
- tests/golden_cases/p3/history_snapshot_diff/。

## 6. 对外契约 / 输入输出

POST 保存快照；GET 历史列表；GET 快照详情；POST 历史 diff。

## 7. 建议实现步骤

- 创建历史表 migration。
- 实现保存分析结果。
- 实现读取快照。
- 复用 DiffService。
- 前端历史列表。

## 8. 单元测试与集成测试

- 保存历史测试。
- 读取快照测试。
- 历史 diff 测试。
- schema_version 记录测试。

## 9. 回归测试要求

- 必须跑 M27 diff 回归。
- 不得把 GraphInteractionState 混入 AnalysisResult 快照，除非另建 workspace 状态。

## 10. 验收标准

- 历史分析可回溯。
- 历史 diff 基于 entity_id。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
