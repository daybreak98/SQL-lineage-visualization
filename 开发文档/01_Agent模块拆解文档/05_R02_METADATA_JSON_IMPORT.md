# R02 JSON 元数据导入与预览提交

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M05` |
| 阶段 | `P0` |
| 前置依赖 | `M04`, `M06` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

实现标准 JSON 元数据导入，支持 preview/commit、事务 upsert、导入诊断和回滚。本模块必须在 M06 Diagnostics primitives 之后开发。

## 3. 本模块做什么

- 校验 schema_version、tables、columns。
- 导入 catalog_tables/catalog_columns。
- 记录 import_jobs/import_errors。
- 返回导入摘要和结构化 diagnostics，不允许把错误仅写成字符串。

## 4. 本模块不做什么

- 不支持 DDL 转 JSON。
- 不支持 Hive Metastore。
- 不做复杂字段类型解析。

## 5. 交付物

- backend/app/api/metadata_controller.py。
- backend/app/services/metadata_import_service.py。
- tests/golden_cases/p0/metadata_json_import/。
- tests/integration/test_metadata_import.py。

## 6. 对外契约 / 输入输出

POST `/api/metadata/import/preview`；POST `/api/metadata/import/commit`。输入为标准 metadata JSON，输出 import_summary + diagnostics。

## 7. 建议实现步骤

- 实现 JSON Schema 轻校验。
- 实现 preview 计算新增/更新/未变化。
- 实现 commit 事务写入。
- 实现重复字段、空 columns、unsupported schema_version 诊断。

## 8. 单元测试与集成测试

- 合法 JSON 导入测试。
- 重复字段诊断测试。
- 写入失败事务回滚测试。
- unknown data_type warning 测试。

## 9. 回归测试要求

- 每次修改导入逻辑必须跑 M04 元数据仓库回归。
- 不得破坏标准 JSON 格式。

## 10. 验收标准

- 导入后 MetadataRepository 可查询表字段。
- 错误输入返回 diagnostics，不崩溃。
- import_errors 与 diagnostics_report 使用一致 DiagnosticCode / level / message / suggestion 结构。
- 事务回滚生效。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
