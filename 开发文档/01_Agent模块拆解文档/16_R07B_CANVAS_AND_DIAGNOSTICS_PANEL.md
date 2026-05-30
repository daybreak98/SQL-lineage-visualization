# R07b/R08c React Flow 基础画布与 DiagnosticsPanel

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M16` |
| 阶段 | `P0` |
| 前置依赖 | `M13`, `M14`, `M15`, `M06` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

在前端展示 Analyze API 返回的 GraphViewModel 基础节点边，并展示 diagnostics_report；交互状态完全由前端维护。

## 3. 本模块做什么

- 集成 React Flow。
- 渲染 table/column/output/literal/unknown 节点。
- 渲染 projection/alias/unknown 边。
- 实现拖拽、缩放、fit view。
- 实现 DiagnosticsPanel。

## 4. 本模块不做什么

- 不做路径高亮。
- 不做双向定位。
- 不把交互状态传回后端。

## 5. 交付物

- frontend/src/components/LineageCanvas/LineageCanvas.tsx。
- frontend/src/components/DiagnosticsPanel/DiagnosticsPanel.tsx。
- frontend/src/stores/graphInteractionStore.ts。
- tests/frontend/lineage_canvas.test.tsx。

## 6. 对外契约 / 输入输出

输入 GraphViewModel + DiagnosticsReport。输出 UI 展示和 GraphInteractionState。

## 7. 建议实现步骤

- 实现 GraphViewModel 到 React Flow nodes/edges 适配。
- 实现 selected_node_ids/viewport 本地状态。
- 实现空图状态。
- 实现 error/warning/info 展示。

## 8. 单元测试与集成测试

- 基础节点渲染测试。
- 基础边渲染测试。
- 空 graph_view_model 测试。
- diagnostics 展示测试。
- 拖拽不修改后端数据测试。

## 9. 回归测试要求

- 必须继续通过 M14 Analyze API 契约测试与 M15 前端 API 测试。
- 不得把 GraphInteractionState 混入 AnalysisResult。

## 10. 验收标准

- P0 端到端页面可展示 SQL 输入、分析状态、图谱和诊断。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
