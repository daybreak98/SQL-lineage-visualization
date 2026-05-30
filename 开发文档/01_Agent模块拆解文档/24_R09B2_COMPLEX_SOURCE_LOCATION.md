# R09b2 复杂结构 SourceLocation 提取

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M24` |
| 阶段 | `P2` |
| 前置依赖 | `M18`, `M19`, `M23` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

将 SourceLocation 从基础 select/from 扩展到 CTE、子查询、join condition、union、case when、window function 的 range 定位。

## 3. 本模块做什么

- 定位 CTE 名称和 CTE body。
- 定位子查询 alias 和内部输出字段。
- 定位 join condition。
- 定位 case/window 表达式 range。
- 定位 union 分支输出映射。

## 4. 本模块不做什么

- 不追求所有复杂 SQL 100% exact。
- 不在定位失败时阻断血缘。

## 5. 交付物

- backend/app/services/source_location_extractor.py 增强。
- tests/golden_cases/p2/source_location_complex/。

## 6. 对外契约 / 输入输出

输入 original_sql + ScopeModel + ExpressionModel，输出复杂 SourceLocation 列表。

## 7. 建议实现步骤

- 扩展 CTE 定位。
- 扩展 subquery 定位。
- 扩展 join condition 定位。
- 扩展 expression range 定位。
- 失败标记 approximate/unavailable。

## 8. 单元测试与集成测试

- CTE range 测试。
- join condition range 测试。
- case when range 测试。
- window range 测试。
- approximate 降级测试。

## 9. 回归测试要求

- 必须跑 M07 UTF-16 坐标测试和 M18 基础定位回归。
- 不得改变 SourceLocation 坐标协议。

## 10. 验收标准

- 复杂结构可定位或可解释降级。
- Monaco 跳转不发生明显偏移。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
