# R07a GraphViewModel 后端生成

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M13` |
| 阶段 | `P0` |
| 前置依赖 | `M12`, `M07`, `M03` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

将 LineageIR 转换为后端 GraphViewModel，保留 entity_id，不混入前端交互状态。

## 3. 本模块做什么

- 生成 nodes/edges。
- 保留 node_id 与 entity_id。
- 保留 source_entity_id/target_entity_id。
- 支持 column view 的基础图。

## 4. 本模块不做什么

- 不做 React Flow 交互。
- 不保存拖拽位置。
- 不做多视图切换实现。

## 5. 交付物

- backend/app/services/graph_builder.py。
- backend/app/domain/graph_view_model.py。
- tests/unit/test_graph_builder.py。
- tests/golden_cases/p0/graph_view_model_snapshot/。

## 6. 对外契约 / 输入输出

输入 LineageIR，输出 GraphViewModel：view_mode、supported_view_modes、nodes、edges。

## 7. 建议实现步骤

- 映射 LineageIR nodes 到 graph nodes。
- 映射 LineageIR edges 到 graph edges。
- 保留 SourceLocation 引用。
- 实现稳定 node_id/edge_id。

## 8. 单元测试与集成测试

- 简单血缘图快照测试。
- entity_id 保留测试。
- node_id 稳定性测试。
- GraphViewModel 不含 GraphInteractionState 测试。

## 9. 回归测试要求

- GraphBuilder 不允许查询 SQLite。
- GraphBuilder 不允许消费 SQLGlot AST。

## 10. 验收标准

- GraphViewModel 可被前端直接渲染。
- 后端响应不包含 selected/collapsed/viewport 状态。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
