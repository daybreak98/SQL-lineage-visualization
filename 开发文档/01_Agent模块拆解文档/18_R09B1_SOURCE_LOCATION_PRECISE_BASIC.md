# R09b1 SourceLocation 基础精准提取

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M18` |
| 阶段 | `P1` |
| 前置依赖 | `M07`, `M08`, `M09`, `M10`, `M17` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

在 P0 坐标模型基础上实现 select/from/where/group by/order by 的字段、表、别名基础精准定位，并绑定 M10 产出的 entity_id，为 SQL 与图谱联动打基础。

## 3. 本模块做什么

- 定位 select 字段、输出别名、from 表、表别名、where 字段、group/order 字段。
- 基于 NameResolutionResult 将位置绑定到 scope_relation、scope_column、output_column 或 physical column。
- 返回 exact/approximate/unavailable。
- 覆盖中文和跨行 SQL。

## 4. 本模块不做什么

- 不定位复杂 CTE 内部。
- 不定位 case/window 复杂表达式。
- 不做前端双向跳转。

## 5. 交付物

- backend/app/services/source_location_extractor.py。
- tests/unit/test_source_location_basic.py。
- tests/golden_cases/p1/source_location_basic_precise/。

## 6. 对外契约 / 输入输出

输入 original_sql + ParseResult + ScopeModel + NameResolutionResult，输出绑定 entity_id 的 SourceLocation 列表。

## 7. 建议实现步骤

- 实现 token/AST 混合定位。
- 实现 select item range。
- 实现 from relation range。
- 实现 alias range。
- 将定位结果绑定 NameResolutionResult 中的 entity_id；无法绑定时返回 approximate/unavailable 并追加诊断。
- 无法定位时返回 unavailable 并诊断。

## 8. 单元测试与集成测试

- select 字段定位测试。
- from 表定位测试。
- 别名定位测试。
- where/group/order 字段定位测试。
- 中文/跨行测试。

## 9. 回归测试要求

- 必须跑 P0 Golden Regression。
- 不得改变 SourceLocation 坐标协议。

## 10. 验收标准

- 基础 SQL 位置能被 Monaco revealRange 使用。
- 定位失败可解释降级。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
