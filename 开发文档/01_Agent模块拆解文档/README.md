# SQL 血缘解析工作台｜Agent 模块文档包索引 v1.1

> 本文档包基于 `..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md` 拆解，并结合模块文档 v1.1 修订意见完成小修。目标是让 Agent 按模块递进开发，每一步都有稳定契约、回归测试和不可破坏约束。

## 模块清单

| 顺序 | 文件 | 模块 | 阶段 | 前置依赖 |
|---:|---|---|---|---|
| M00 | `00_AGENT_MODULE_INDEX.md` | Agent 模块拆解总览与执行协议 | ALL | 无 |
| M01 | `01_R00_PROJECT_SCAFFOLD.md` | R00 项目初始化与工程骨架 | P0 | 无 |
| M02 | `02_R04B_CONTRACT_BASELINE.md` | R04b 契约基线与领域模型外壳 | P0 | M01 |
| M03 | `03_ENTITY_ID_AND_STAGE_STATUS.md` | Stable Entity ID 与 StageStatus 基础设施 | P0 | M02 |
| M04 | `04_R01_SQLITE_METADATA_STORE.md` | R01 SQLite MetadataRepository 与元数据仓库初始化 | P0 | M01, M02, M03 |
| M06 | `06_R08A_DIAGNOSTICS_PRIMITIVES.md` | R08a DiagnosticCode 与 DiagnosticsCollector | P0 | M02, M03 |
| M05 | `05_R02_METADATA_JSON_IMPORT.md` | R02 JSON 元数据导入与预览提交 | P0 | M04, M06 |
| M07 | `07_R09A_SOURCE_LOCATION_MODEL.md` | R09a SourceLocation 数据模型与 UTF-16 坐标工具 | P0 | M02, M03 |
| M08 | `08_R03_SQL_PARSE_ADAPTER.md` | M08 SQLGlotAdapter 与 SQL Parse/Format 服务 | P0 | M01, M02, M06 |
| M09 | `09_R05_SCOPE_RESOLVER.md` | R05a ScopeResolver 与 scope_relation 建模 | P0 | M03, M08, M06 |
| M10 | `10_R05_METADATA_AND_NAME_RESOLVER.md` | R05b MetadataService 与 NameResolver 字段归属 | P0 | M04, M06, M09 |
| M11 | `11_MINIMAL_EXPRESSION_EXTRACTOR.md` | ProjectionExtractor / MinimalExpressionExtractor | P0 | M09, M10, M03 |
| M12 | `12_R06_LINEAGE_IR_P0.md` | R06 基础 LineageIR 生成 | P0 | M02, M03, M10, M11, M06 |
| M13 | `13_R07_GRAPH_VIEW_MODEL_BUILDER.md` | R07a GraphViewModel 后端生成 | P0 | M12, M07, M03 |
| M14 | `14_R04A_ANALYZE_ORCHESTRATOR_API.md` | R04a Analyze API、AnalysisOrchestrator 与 ContractAssembler | P0 | M02, M06, M07, M08, M09, M10, M11, M12, M13 |
| M15 | `15_R03_FRONTEND_WORKBENCH_SQL_EDITOR.md` | R03 前端 Workbench Shell 与 Monaco SQL Editor | P0 | M01, M02, M14 |
| M16 | `16_R07B_CANVAS_AND_DIAGNOSTICS_PANEL.md` | R07b/R08c React Flow 基础画布与 DiagnosticsPanel | P0 | M13, M14, M15, M06 |
| M17 | `17_R17_P0_GOLDEN_CASE_REGRESSION.md` | R17 P0 Golden Case 与回归测试基线 | P0 | M04, M05, M10, M12, M13, M14, M16 |
| M18 | `18_R09B1_SOURCE_LOCATION_PRECISE_BASIC.md` | R09b1 SourceLocation 基础精准提取 | P1 | M07, M08, M09, M10, M17 |
| M19 | `19_R10_CTE_SUBQUERY_JOIN_UNION.md` | R10 CTE / 子查询 / Join / Union 结构增强 | P1 | M09, M10, M12, M17 |
| M20 | `20_R11A_SELECT_STAR_EXPANSION.md` | R11a select * / alias.* 元数据驱动展开 | P1 | M04, M10, M19 |
| M21 | `21_R11B_R11C_MONACO_COMPLETION_HOVER.md` | R11b/R11c Monaco Completion 与 Hover | P1 | M15, M10, M18, M20 |
| M22 | `22_R09C_BIDIRECTIONAL_LINKING.md` | R09c SQL 与图谱双向定位 | P1 | M16, M18, M21, M13 |
| M23 | `23_R13A_EXPRESSION_ANALYZER.md` | R13a 完整 ExpressionAnalyzer 基础能力 | P2 | M11, M19, M12 |
| M24 | `24_R09B2_COMPLEX_SOURCE_LOCATION.md` | R09b2 复杂结构 SourceLocation 提取 | P2 | M18, M19, M23 |
| M25 | `25_R12_SEMANTICS_REPORT.md` | R12 SemanticsReport 查询口径分析 | P2 | M23, M24, M12 |
| M26 | `26_R13B_R14_EXPRESSION_GRAPH_MULTIVIEW.md` | R13b/R14 表达式级血缘图谱与多视图 | P2 | M13, M23, M25, M22 |
| M27 | `27_R15_CURRENT_SQL_DIFF.md` | R15 当前 SQL diff 与变更摘要 | P3 | M14, M25, M26, M03 |
| M28 | `28_R16_HISTORY_AND_SNAPSHOTS.md` | R16 分析历史与快照 | P3 | M14, M27, M04 |

## 推荐执行路径

```text
P0: M01 → M02 → M03 → M04 → M06 → M05 → M07 → M08 → M09 → M10 → M11 → M12 → M13 → M14 → M15 → M16 → M17
P1: M18 → M19 → M20 → M21 → M22
P2: M23 → M24 → M25 → M26
P3: M27 → M28
```

## 全局回归要求

- 每完成一个模块，必须运行本模块测试。
- 每完成一个模块，必须运行所有前置模块回归。
- P0 之后任意修改都必须运行 `scripts/test_p0_regression.sh`。
- Golden Case 的 expected JSON 只有在契约显式变更时才能更新，并必须在 PR 中说明原因。
- 后端不得让 SQLGlot AST 直接流向前端；前端不得推导血缘。

## Agent PR 输出模板

```md
## 本次模块
- 模块编号：
- 文档文件：

## 实现内容
- 

## 未实现内容 / 明确不做
- 

## 测试结果
- 单元测试：
- 集成测试：
- Golden Case：
- 前置模块回归：

## 契约变更
- 无 / 有，说明如下：

## 风险与回滚
- 
```
