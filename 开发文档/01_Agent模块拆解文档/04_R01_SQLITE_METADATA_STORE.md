# R01 SQLite MetadataRepository 与元数据仓库初始化

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M04` |
| 阶段 | `P0` |
| 前置依赖 | `M01`, `M02`, `M03` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

建立 SQLite 元数据仓库、migration 与 MetadataRepository / MetadataStore 基础 CRUD，支撑后续 MetadataService 与 NameResolver。

## 3. 本模块做什么

- 创建 metadata_versions、catalog_tables、catalog_columns、import_jobs、import_errors。
- 实现唯一约束和索引。
- 实现 MetadataRepository / MetadataStore 基础查询与事务访问。

## 4. 本模块不做什么

- 不做 JSON 导入 UI。
- 不做 Hive Metastore 同步。
- 不做字段血缘。
- 不实现面向 NameResolver 的 MetadataService 查询封装。
- 不在本模块实现字段归属或业务解析逻辑。

## 5. 交付物

- backend/app/repositories/metadata_repository.py。
- backend/app/db/migrations/001_metadata.sql。
- backend/app/domain/metadata_model.py。
- tests/integration/test_metadata_store.py。

## 6. 对外契约 / 输入输出

Repository / Store 提供：create_schema、get_table、list_columns、get_metadata_context、upsert_table、upsert_columns。M10 才允许在此基础上实现 `backend/app/services/metadata_service.py` 查询封装。

## 7. 建议实现步骤

- 设计 SQLite migration。
- 实现 metadata_version 创建。
- 实现表字段 upsert。
- 实现按 metadata_version + catalog/schema/table 查询。
- 实现 normalized_table_name 和 normalized_column_name。

## 8. 单元测试与集成测试

- migration 可重复执行测试。
- 唯一约束测试。
- 按 schema.table 查询字段测试。
- 大小写敏感/不敏感测试。

## 9. 回归测试要求

- 后续模块不得绕过 MetadataRepository / MetadataStore 直接查 SQLite。
- M04 不拥有 `backend/app/services/metadata_service.py`；该文件所有权属于 M10。
- 变更表结构必须补 migration 和回归测试。

## 10. 验收标准

- SQLite 初始化成功。
- 元数据版本可查询。
- catalog_tables/catalog_columns 约束生效。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
