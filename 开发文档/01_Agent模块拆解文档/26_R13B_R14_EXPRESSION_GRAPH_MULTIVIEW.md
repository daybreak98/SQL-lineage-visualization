# R13b/R14 表达式级血缘图谱与多视图

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M26` |
| 阶段 | `P2` |
| 前置依赖 | `M13`, `M23`, `M25`, `M22` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

将表达式、指标、过滤、join、诊断等语义结构映射到多视图 GraphViewModel，并在前端支持视图切换。

## 3. 本模块做什么

- 表达式节点和边。
- 表级/字段级/表达式级/口径级/诊断级视图。
- 前端 view_mode 切换。
- 诊断视图高亮。

## 4. 本模块不做什么

- 不做大图性能虚拟化。
- 不做历史快照。
- 不把前端折叠状态写回后端。

## 5. 交付物

- backend/app/services/graph_builder.py 增强。
- frontend/src/components/LineageCanvas/ViewModeSwitcher.tsx。
- tests/golden_cases/p2/multiview_graph/。

## 6. 对外契约 / 输入输出

GraphBuilder 根据 view_mode 输出不同节点边集合。前端基于 supported_view_modes 切换。

## 7. 建议实现步骤

- 扩展 GraphBuilder view_mode。
- 实现 expression nodes/edges。
- 实现 semantics view。
- 实现 diagnostics view。
- 前端添加视图切换控件。

## 8. 单元测试与集成测试

- expression graph snapshot。
- semantics view snapshot。
- diagnostics view snapshot。
- 前端切换测试。

## 9. 回归测试要求

- 必须跑 P0 GraphViewModel Snapshot。
- 不得破坏 column view。

## 10. 验收标准

- 多视图可切换。
- 每种视图节点边稳定可快照。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
