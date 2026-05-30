# M08 SQLGlotAdapter 与 SQL Parse/Format 服务

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M08` |
| 阶段 | `P0` |
| 前置依赖 | `M01`, `M02`, `M06` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

封装 SQLGlot 解析与格式化能力，保证后续模块不直接暴露 SQLGlot AST 给前端或领域契约。本模块是 R03 的后端支撑模块，不包含前端编辑器。

## 3. 本模块做什么

- 实现 parse smoke check。
- 实现 format API。
- 将 SQLGlot 异常转为 PARSE_ERROR。
- 输出 ParseResult 内部对象。

## 4. 本模块不做什么

- 不生成 LineageIR。
- 不查询 SQLite。
- 不做字段归属。
- 不实现 Monaco Editor 或前端 Workbench。

## 5. 交付物

- backend/app/adapters/sqlglot_adapter.py。
- backend/app/services/sql_parse_service.py。
- backend/app/api/sql_controller.py。
- tests/unit/test_sql_parse_service.py。

## 6. 对外契约 / 输入输出

POST `/api/sql/format` 输入 sql/dialect，输出 normalized_sql 或 PARSE_ERROR。内部 ParseResult 只在后端使用。

## 7. 建议实现步骤

- 封装 sqlglot.parse_one。
- 实现 dialect 参数。
- 实现格式化。
- 捕获异常并写入 DiagnosticsCollector。

## 8. 单元测试与集成测试

- 合法 SQL parse 测试。
- 非法 SQL PARSE_ERROR 测试。
- format 不改变原 SQL SourceLocation 的测试说明。
- dialect 参数透传测试。

## 9. 回归测试要求

- 后续模块不能在 api/controller 中直接调用 sqlglot。
- parse 失败时后续 scope/name/lineage 阶段应 skipped。

## 10. 验收标准

- SQLGlotAdapter 单测通过。
- 非法 SQL 返回结构化诊断。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
