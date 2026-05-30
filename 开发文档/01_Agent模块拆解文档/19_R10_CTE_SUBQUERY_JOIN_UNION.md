# R10 CTE / 子查询 / Join / Union 结构增强

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M19` |
| 阶段 | `P1` |
| 前置依赖 | `M09`, `M10`, `M12`, `M17` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

扩展 ScopeResolver、NameResolver 和 LineageEngine，使系统支持常见数仓 SQL 结构，同时保持明确降级边界。

## 3. 本模块做什么

- 支持非递归 CTE。
- 支持 from 子查询。
- 支持 inner/left/right/full join 字段归属和 join key 抽取。
- 支持 union all 同名字段多来源合并。

## 4. 本模块不做什么

- 不精确判断真实 join 基数。
- 不支持 recursive CTE。
- 复杂 correlated subquery 可 partial。
- lateral/explode 只识别诊断。

## 5. 交付物

- backend/app/services/scope_resolver.py 增强。
- backend/app/services/name_resolver.py 增强。
- backend/app/services/lineage_engine.py 增强。
- tests/golden_cases/p1/cte_basic/、subquery_basic、join_basic、union_all。

## 6. 对外契约 / 输入输出

输入复杂 SQL，输出包含 scope、scope_relation、scope_column、union_mapping 的 LineageIR。

## 7. 建议实现步骤

- 扩展 scope 类型。
- 实现 CTE scope 依赖。
- 实现 subquery scope。
- 实现 join relation 和 join key 记录。
- 实现 union all 字段映射。
- 添加 unsupported diagnostics。

## 8. 单元测试与集成测试

- CTE 字段回溯测试。
- 子查询字段回溯测试。
- join 字段消歧测试。
- union all 多来源测试。
- unsupported recursive_cte 测试。

## 9. 回归测试要求

- 必须跑 P0 Golden Regression。
- 不得破坏 P0 simple_select 输出结构。

## 10. 验收标准

- P1 常见 SQL 可 partial/success 分级返回。
- 不支持结构进入 unsupported_features 和 diagnostics。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
