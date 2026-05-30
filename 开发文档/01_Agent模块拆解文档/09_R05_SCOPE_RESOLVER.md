# R05a ScopeResolver 与 scope_relation 建模

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M09` |
| 阶段 | `P0` |
| 前置依赖 | `M03`, `M08`, `M06` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

基于 SQLGlot 解析结果建立最小作用域模型，识别主查询 FROM 表、别名和基础 select 输出关系，为 NameResolver 服务。

## 3. 本模块做什么

- 识别 main scope。
- 识别 from table 和 alias。
- 生成 scope_relation。
- 记录 unresolved relation 诊断。

## 4. 本模块不做什么

- 不处理复杂 CTE/子查询全量。
- 不做字段归属。
- 不生成 LineageIR。

## 5. 交付物

- backend/app/domain/scope_model.py。
- backend/app/services/scope_resolver.py。
- tests/unit/test_scope_resolver.py。

## 6. 对外契约 / 输入输出

输入 ParseResult，输出 ScopeModel：scopes、relations、select_items 的结构化表示。

## 7. 建议实现步骤

- 定义 ScopeModel。
- 实现单表 FROM。
- 实现表别名识别。
- 实现 schema.table 解析。
- 为后续 CTE/subquery 预留 scope 类型。

## 8. 单元测试与集成测试

- 单表无别名测试。
- 单表有别名测试。
- schema.table 测试。
- 重复别名或缺失 relation 诊断测试。

## 9. 回归测试要求

- 后续模块不得把表别名直接当物理表。
- 所有 FROM/JOIN 引用必须先建模为 scope_relation。

## 10. 验收标准

- ScopeResolver 能输出 main scope 和 scope_relation。
- 不会查询 SQLite。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
