# R05b MetadataService 与 NameResolver 字段归属

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M10` |
| 阶段 | `P0` |
| 前置依赖 | `M04`, `M06`, `M09` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

基于 ScopeModel 与 M04 MetadataRepository 完成 MetadataService 查询封装、字段归属、未知表、未知字段和歧义字段诊断。

## 3. 本模块做什么

- 实现 `backend/app/services/metadata_service.py`，只封装 M04 MetadataRepository，不重写 SQLite 访问。
- 解析物理表是否存在。
- 解析字段属于哪个 scope_relation。
- 生成 scope_column 到 physical column 的映射。
- 处理 UNKNOWN_TABLE、UNKNOWN_COLUMN、AMBIGUOUS_COLUMN。

## 4. 本模块不做什么

- 不展开 select *。
- 不处理复杂 CTE/子查询。
- 不生成图谱。

## 5. 交付物

- backend/app/domain/name_resolution_model.py。
- backend/app/services/metadata_service.py。
- backend/app/services/name_resolver.py。
- tests/unit/test_name_resolver.py。
- tests/golden_cases/p0/unknown_column/。
- tests/golden_cases/p0/ambiguous_column/。

## 6. 对外契约 / 输入输出

输入 ScopeModel + MetadataContext + MetadataRepository 查询结果，输出 NameResolutionResult：resolved_columns、unresolved_references、diagnostics。

## 7. 建议实现步骤

- 实现表解析。
- 实现 qualified column 解析。
- 实现 unqualified column 单表解析。
- 实现多表同名歧义诊断。
- 补 metadata_context missing/ambiguous 字段。

## 8. 单元测试与集成测试

- 单表字段解析测试。
- 未知表测试。
- 未知字段测试。
- 多表同名字段歧义测试。
- 默认 schema 测试。

## 9. 回归测试要求

- 每次改 MetadataService / NameResolver 必须跑 M04/M09 回归。
- 不得改写 M04 migration、Repository 基础 CRUD 或直接绕过 Repository 查 SQLite。
- 不得猜测多表歧义字段来源。

## 10. 验收标准

- 字段归属可复现。
- 诊断结构稳定。
- metadata_context 可反映 resolved/missing/ambiguous。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
