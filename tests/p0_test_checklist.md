# P0 测试门禁清单 - R00 + R01 + R02 + M07-M14

> 状态：R01 ✅ / R02 ✅ / M07-M14 P0 Analyze 闭环 ✅ 全部通过（95/95）
> 目标：确保每个功能点有测试，100% 通过方可进入下一轮迭代

---

## 后端测试 — M07-M14 P0 Analyze 闭环

> 测试文件：
> - `backend/tests/unit/test_text_coordinates.py`
> - `backend/tests/unit/test_scope_resolver.py`
> - `backend/tests/unit/test_name_resolver.py`
> - `backend/tests/unit/test_lineage_graph_p0.py`
> - `backend/tests/integration/test_analyze_api_p0.py`

| # | 测试范围 | 覆盖功能点 | 通过 |
|---|---------|-----------|------|
| M07 | SourceLocation / UTF-16 坐标 | 中文、emoji、CRLF、synthetic location | ✅ |
| M09 | ScopeResolver | FROM/JOIN、别名、schema.table、重复别名诊断 | ✅ |
| M10 | NameResolver | 字段归属、未知表、未知字段、歧义字段 | ✅ |
| M11-M13 | Projection / LineageIR / GraphViewModel | 直接字段、alias、literal、图节点边 | ✅ |
| M14 | Analyze API | success / partial / failed、stage_statuses、正式 AnalysisResult | ✅ |

联调验证：

| 范围 | 结果 |
|---|---|
| `POST /api/sql/analyze` | ✅ 返回 `schema_version=1.0`、6 nodes、2 edges、8 stage_statuses |
| `POST /api/sql/format` | ✅ 返回格式化 SQL |
| Vite `/api` 代理 | ✅ `5173/api/sql/analyze` 和 `5173/api/sql/format` 均可用 |

---

## 后端测试 — MetadataRepository (R01)

| # | 测试用例 | 覆盖功能点 | 通过 |
|---|---------|-----------|------|
| 1 | `test_create_metadata_version` | 创建并查询元数据版本 | ✅ |
| 2 | `test_get_latest_metadata_version` | latest 版本查询 | ✅ |
| 3 | `test_list_metadata_versions` | 列出所有元数据版本 | ✅ |
| 4 | `test_upsert_and_get_table` | upsert 表并查询 | ✅ |
| 5 | `test_unique_table_constraint` | 表 upsert 唯一约束 | ✅ |
| 6 | `test_get_table_by_name` | 按表名精确查询 | ✅ |
| 7 | `test_get_table_by_name_not_found` | 不存在表返回 None | ✅ |
| 8 | `test_get_tables_with_keyword` | 关键词查询表 | ✅ |
| 9 | `test_upsert_and_get_columns` | upsert 列并查询 | ✅ |
| 10 | `test_unique_column_constraint` | 列 upsert 唯一约束 | ✅ |
| 11 | `test_get_metadata_context` | 元数据上下文聚合查询 | ✅ |
| 12 | `test_get_metadata_context_no_version` | 无版本时返回空上下文 | ✅ |
| 13 | `test_case_sensitivity` | 大小写不敏感查找 | ✅ |
| 14 | `test_migration_idempotent` | migration 幂等执行 | ✅ |

## 后端测试 — JSON 元数据导入 (R02)

> 测试文件: `backend/tests/integration/test_metadata_import.py`
> 状态: ✅ 全部通过（16/16）

### 核心导入流程

| # | 测试用例 | 覆盖功能点 | TC-R02 | 通过 |
|---|---------|-----------|--------|------|
| I1 | `test_preview_valid_json` | 合法 JSON preview 返回 changes，无 error | 01 | ✅ |
| I2 | `test_commit_import` | commit 后可查询表字段 | 02 | ✅ |

### 异常与诊断

| # | 测试用例 | 覆盖功能点 | TC-R02 | 通过 |
|---|---------|-----------|--------|------|
| I3 | `test_duplicate_column_diagnostic` | 重复字段触发 DUPLICATE_COLUMN diagnostic | 03 | ✅ |
| I4 | `test_empty_columns_diagnostic` | 空 columns 触发 pydantic min_length 校验 | 04 | ✅ |
| I5 | `test_schema_version_unsupported` | unsupported schema_version → diagnostic | 06 | ✅ |
| I6 | `test_empty_tables_error` | tables=[] 触发 pydantic min_length 校验 | 08 | ✅ |
| I7 | `test_unknown_data_type_warning` | unknown data_type 不阻断导入 | 09 | ✅ |
| I8 | `test_invalid_json` | 非法 JSON/extra 字段 → ValidationError | 07 | ✅ |
| I9 | `test_empty_table_name_diagnostic` | 空表名/空白表名 → error diagnostic | — | ✅ |
| I10 | `test_complex_type_diagnostic` | 复杂类型（array<>, map<>, decimal()）→ info | — | ✅ |
| I11 | `test_missing_ordinal_diagnostic` | 缺失 ordinal → warning diagnostic | — | ✅ |

### 幂等性与事务

| # | 测试用例 | 覆盖功能点 | TC-R02 | 通过 |
|---|---------|-----------|--------|------|
| I12 | `test_rollback_on_error` | 事务回滚生效，无部分数据残留 | 05 | ✅ |
| I13 | `test_upsert_semantics` | 重复导入产生 updated/unchanged | 10 | ✅ |

### import_jobs 与统计

| # | 测试用例 | 覆盖功能点 | TC-R02 | 通过 |
|---|---------|-----------|--------|------|
| I14 | `test_import_jobs_lifecycle` | import_jobs 状态流转（preview 不创建，commit running→completed） | 11 | ✅ |
| I15 | `test_table_count_updated` | commit 后 metadata_versions.table_count 正确 | 12 | ✅ |

### 边界与冒烟

| # | 测试用例 | 覆盖功能点 | TC-R02 | 通过 |
|---|---------|-----------|--------|------|
| I16 | `test_large_payload_smoke` | 大面积导入（3 表 15 字段）冒烟测试 | — | ✅ |

## 前端测试 — Workbench Smoke (R00)

| # | 测试用例 | 覆盖功能点 | 通过 |
|---|---------|-----------|------|
| F1 | `renders without crashing` | Workbench 页面渲染不崩溃 | ⬜ (需 vitest 环境) |
| F2 | `contains header brand text` | Header 品牌文字 | ⬜ (需 vitest 环境) |
| F3 | `contains main-split layout` | 分栏布局渲染 | ⬜ (需 vitest 环境) |
| F4 | `does not show Analyze button when SQL is empty` | empty 模式隐藏按钮 | ⬜ (需 vitest 环境) |
| F5 | `contains dialect selector` | 方言选择器存在 | ⬜ (需 vitest 环境) |

## 回归测试 (R00 准入)

| # | 测试用例 | 覆盖功能点 | 通过 |
|---|---------|-----------|------|
| R1 | `GET /api/health` 返回 200 `{"status":"ok"}` | health check 持续可用 | ✅ |
| R2 | 后续模块不绕过 MetadataRepository 直接查 SQLite | 模块边界 | ⚠ 需 code review 确认 |

---

## 阻断标准

以下任一条件不满足 → **阻断**，不得进入下一轮：

| 条件 | 说明 | 状态 |
|------|------|------|
| health check 返回非 200 | 后端服务不可用 | ✅ |
| migration 执行失败 | 数据库初始化异常 | ✅ |
| 唯一约束不生效 | 数据完整性风险 | ✅ |
| `test_create_metadata_version` 不通过 | 元数据版本不可创建 | ✅ |
| `test_preview_valid_json` (I1) 不通过 | 预览流程不可用 | ✅ |
| `test_commit_import` (I2) 不通过 | 导入流程不可用 | ✅ |
| 任意 Golden Case (GC-P0-001 ~ GC-P0-008) 不通过 | P0 核心分析链路有 bug | ⬜ 待实现 |

---

## 注意事项

1. **测试独立性**：每个测试用例使用独立的 SQLite 数据库（`:memory:` 或临时文件），互不干扰。
2. **Fixtures 路径**：`conftest.py` 自动定位项目根，Golden fixture 位于 `tests/golden_cases/fixtures/p0_metadata_fixture.json`。
3. **R02 测试全部通过**：16 个集成测试覆盖了 preview、commit、异常诊断、事务回滚、upsert 语义、import_jobs 生命周期、边界条件。
4. **前端测试环境**：需要 `vitest` + `@testing-library/react` + `jsdom`。首次运行前执行 `npm install`。
5. **后端测试环境**：需要 `pytest`。首次运行前执行 `pip install pytest`。
6. **Golden Case 断言工具**：后续需要实现 `nodes_contains`、`edges_contains`、`diagnostics_contains` 辅助断言函数（参见 P0 Golden Case 规格）。
7. **R02 HTTP 422 测试**：完整的 HTTP 层测试需要在 API endpoint 实现后补充（当前 `test_invalid_json` 覆盖了 Pydantic 模型校验层）。
