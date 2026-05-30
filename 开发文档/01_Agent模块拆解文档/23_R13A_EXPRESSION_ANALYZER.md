# R13a 完整 ExpressionAnalyzer 基础能力

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M23` |
| 阶段 | `P2` |
| 前置依赖 | `M11`, `M19`, `M12` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

在 P0 MinimalExpressionExtractor 与 LineageIR P0 基础上扩展完整 ExpressionAnalyzer，抽取聚合、case when、窗口函数、复杂函数嵌套和表达式依赖。该后端领域能力不得依赖 M22 前端双向定位。

## 3. 本模块做什么

- 表达式分类。
- source column 抽取。
- aggregate/count distinct。
- case when 条件和值依赖。
- window partition/order/source 依赖。

## 4. 本模块不做什么

- 不直接生成自然语言口径。
- 不做图谱多视图。
- 不做 AI 解释。
- 不依赖 SQL 与图谱双向定位，也不依赖前端联动状态。

## 5. 交付物

- backend/app/domain/expression_model.py。
- backend/app/services/expression_analyzer.py。
- tests/golden_cases/p2/case_when_metric/、count_distinct_metric、window_function。

## 6. 对外契约 / 输入输出

输入 ParseResult + NameResolutionResult + LineageIR P0，输出 ExpressionModel。可消费 M18 SourceLocation，但不得把 M22 作为硬依赖。

## 7. 建议实现步骤

- 定义 ExpressionNode。
- 实现函数/聚合分类。
- 实现 case when 依赖抽取。
- 实现窗口函数结构抽取。
- 接入 LineageEngine 增强。

## 8. 单元测试与集成测试

- sum 表达式测试。
- count distinct 测试。
- case when 测试。
- window function 测试。
- 未知 UDF 降级测试。

## 9. 回归测试要求

- 必须跑 P0/P1 Golden Regression。
- 不得引入对 M22 前端双向定位的依赖。
- 不得改变 MinimalExpressionExtractor 的 P0 输出。

## 10. 验收标准

- 复杂表达式依赖可结构化输出。
- 未知语义有 low confidence/diagnostics。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
