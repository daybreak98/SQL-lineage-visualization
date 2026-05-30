# R04b 契约基线与领域模型外壳

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M02` |
| 阶段 | `P0` |
| 前置依赖 | `M01` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

先稳定 AnalysisResult、StageStatus、Diagnostics、LineageIR、GraphViewModel、SourceLocation 的 Pydantic/TS 最小模型，避免后续前后端字段漂移。

## 3. 本模块做什么

- 定义 Pydantic 响应模型。
- 定义前端手工 TS 类型。
- 保留 schema_version、stage_statuses、confidence_level 等稳定字段。
- 实现基础 Contract Test。

## 4. 本模块不做什么

- 不做自动 TS 类型生成。
- 不做完整 JSON Schema Snapshot。
- 不实现业务解析逻辑。
- 不实现 SourceLocation 坐标转换工具。

## 5. 交付物

- backend/app/domain/analysis_result.py。
- backend/app/domain/stage_status.py。
- backend/app/domain/diagnostics_model.py。
- backend/app/domain/lineage_ir.py。
- backend/app/domain/graph_view_model.py。
- backend/app/domain/source_location.py。
- frontend/src/types/analysis.ts。
- tests/contracts/test_analysis_result_contract.py。
- scripts/test_contract.sh。
- scripts/test_unit.sh。

## 6. 对外契约 / 输入输出

核心契约为 `AnalysisResult`。SourceLocation 在 M02 只定义 Pydantic/TS 契约壳，坐标转换工具、source_sql_id 工厂、synthetic/unavailable 工厂由 M07 实现。

核心契约为 `AnalysisResult`。P0 必填字段：schema_version、analysis_id、status、confidence_level、confidence_reasons、stage_statuses、metadata_context、unsupported_features、lineage_ir、semantics_report、diagnostics_report、graph_view_model、source_locations、elapsed_ms。

## 7. 建议实现步骤

- 建立 enum：status、stage status、diagnostic level、confidence_level。
- 实现空 AnalysisResult 工厂。
- 实现 success/partial/failed 三类契约样例。
- 前端定义对应 TS interface。
- 添加后端 Contract Test。
- 添加 `scripts/test_contract.sh` 与 `scripts/test_unit.sh` 的最小入口，M17 再补完整 P0 Golden Regression。

## 8. 单元测试与集成测试

- Pydantic 模型序列化测试。
- success/partial/failed 三类响应结构测试。
- 前端 TypeScript 类型编译测试。

## 9. 回归测试要求

- 后续任何 API 字段删除、改名、必填变更必须导致 Contract Test 失败。
- 下游模块只能扩展 optional 字段，不得破坏本模块字段。

## 10. 验收标准

- Contract Test 通过。
- OpenAPI 可展示 analyze 响应模型占位。
- 前端 TS 编译通过。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
