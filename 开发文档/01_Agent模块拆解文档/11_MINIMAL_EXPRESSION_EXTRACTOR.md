# ProjectionExtractor / MinimalExpressionExtractor

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M11` |
| 阶段 | `P0` |
| 前置依赖 | `M09`, `M10`, `M03` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

抽取 P0 所需的 select item、alias、literal、简单字段引用和 function wrapper，稳定 projection/alias/literal 血缘输入。

## 3. 本模块做什么

- 识别 select 输出项。
- 识别 alias。
- 识别 literal 常量。
- 识别简单字段引用。
- 识别 cast/nvl 等 function wrapper 的直接依赖字段。

## 4. 本模块不做什么

- 不做 aggregate/case/window 完整表达式树。
- 不做口径分析。
- 不做复杂 UDF 语义。

## 5. 交付物

- backend/app/domain/minimal_expression_model.py。
- backend/app/services/projection_extractor.py。
- tests/unit/test_projection_extractor.py。
- tests/golden_cases/p0/single_table_alias/。

## 6. 对外契约 / 输入输出

输入 ParseResult + NameResolutionResult，输出 ProjectionModel：output_columns、source_refs、alias_edges、literal_nodes、unsupported_expressions。

## 7. 建议实现步骤

- 定义 ProjectionItem。
- 实现 select col。
- 实现 select t.col as alias。
- 实现 select 1 as flag。
- 实现 cast/nvl wrapper 提取 source column。
- 复杂表达式写入 unsupported_features 或 unknown。

## 8. 单元测试与集成测试

- 直接字段测试。
- alias 测试。
- literal 测试。
- function wrapper 测试。
- 复杂表达式降级测试。

## 9. 回归测试要求

- 后续 LineageEngine 只能消费 ProjectionModel，不直接重新解析 select item。
- literal 不得降级为 unknown。

## 10. 验收标准

- projection/alias/literal 可稳定输出。
- 复杂表达式可解释降级。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
