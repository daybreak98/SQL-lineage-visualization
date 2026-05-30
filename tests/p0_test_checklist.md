# P0 测试门禁清单 - R00 + R01

> 状态：已准备
> 目标：确保每个功能点有测试，100% 通过方可进入下一轮迭代

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

| 条件 | 说明 |
|------|------|
| health check 返回非 200 | 后端服务不可用 |
| migration 执行失败 | 数据库初始化异常 |
| 唯一约束不生效 | 数据完整性风险 |
| `test_create_metadata_version` 不通过 | 元数据版本不可创建 |
| 任意 Golden Case (GC-P0-001 ~ GC-P0-008) 不通过 | P0 核心分析链路有 bug |

---

## 注意事项

1. **测试独立性**：每个测试用例使用独立的临时 SQLite 数据库（`temp_db` fixture），互不干扰。
2. **Fixtures 路径**：`conftest.py` 自动定位项目根，Golden fixture 位于 `tests/golden_cases/fixtures/p0_metadata_fixture.json`。
3. **前端测试环境**：需要 `vitest` + `@testing-library/react` + `jsdom`。首次运行前执行 `npm install`。
4. **后端测试环境**：需要 `pytest`。首次运行前执行 `pip install pytest`。
5. **Golden Case 断言工具**：后续需要实现 `nodes_contains`、`edges_contains`、`diagnostics_contains` 辅助断言函数（参见 P0 Golden Case 规格）。
