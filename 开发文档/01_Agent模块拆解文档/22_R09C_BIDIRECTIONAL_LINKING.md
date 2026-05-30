# R09c SQL 与图谱双向定位

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M22` |
| 阶段 | `P1` |
| 前置依赖 | `M16`, `M18`, `M21`, `M13` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

基于 SourceLocation、entity_id 和 GraphViewModel 实现 SQL 编辑器与 React Flow 图谱的双向定位。

## 3. 本模块做什么

- 点击 SQL 高亮图节点。
- 点击图节点定位 SQL range。
- 点击诊断跳转到 SQL。
- 基础上游/下游路径高亮。

## 4. 本模块不做什么

- 不做复杂多视图定位。
- 不做历史快照恢复。
- 不做复杂表达式 range 全覆盖。

## 5. 交付物

- frontend/src/components/SqlEditor/decorations.ts。
- frontend/src/components/LineageCanvas/highlight.ts。
- frontend/src/stores/linkingStore.ts。
- tests/frontend/bidirectional_linking.test.tsx。

## 6. 对外契约 / 输入输出

前端通过 entity_id/source_location_id 建立 editor range 与 graph node 的映射。

## 7. 建议实现步骤

- 建立 SourceLocation lookup。
- 实现 editor selection 到 entity_id。
- 实现 graph node click 到 editor revealRange。
- 实现 diagnostics click。
- 实现无 location 降级提示。

## 8. 单元测试与集成测试

- SQL→图节点高亮测试。
- 图节点→SQL 定位测试。
- 诊断跳转测试。
- 无 SourceLocation 不崩溃测试。

## 9. 回归测试要求

- 必须跑前端画布和编辑器回归。
- 不得根据 label 模糊匹配节点，必须用 entity_id/source_location_id。

## 10. 验收标准

- 双向定位在基础 SQL 中可用。
- 定位失败有提示且不影响分析结果。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
