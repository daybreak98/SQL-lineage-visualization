# R06 基础 LineageIR 生成

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M12` |
| 阶段 | `P0` |
| 前置依赖 | `M02`, `M03`, `M10`, `M11`, `M06` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

基于 NameResolutionResult 和 ProjectionModel 生成 P0 字段级 LineageIR，只强制 projection、alias、literal、unknown。

## 3. 本模块做什么

- 生成 table/column/scope_column/output_column/literal/unknown 节点。
- 生成 projection、alias、unknown 边。
- 填充 partial、confidence_level、confidence_reasons。

## 4. 本模块不做什么

- 不生成 join/filter/group/window 边。
- 不做表达式级图谱。
- 不做前端布局。

## 5. 交付物

- backend/app/services/lineage_engine.py。
- backend/app/domain/lineage_ir.py。
- tests/unit/test_lineage_engine_p0.py。
- tests/golden_cases/p0/simple_select/。

## 6. 对外契约 / 输入输出

输入 NameResolutionResult + ProjectionModel，输出 LineageIR。

## 7. 建议实现步骤

- 实现节点构建。
- 实现 source column → output column projection。
- 实现 source column → output alias。
- 实现 literal → output。
- 实现 unknown 降级边。

## 8. 单元测试与集成测试

- simple_select Golden Case。
- single_table_alias Golden Case。
- literal output 测试。
- unknown 降级测试。
- LineageIR Snapshot Test。

## 9. 回归测试要求

- 每次改 LineageIR 字段必须跑 Contract Test 和 Snapshot Test。
- 不得把 scope_column/output_column 伪装为 physical column。

## 10. 验收标准

- P0 LineageIR 能表达基础字段血缘。
- 不可解析部分进入 unknown/partial/diagnostics。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
