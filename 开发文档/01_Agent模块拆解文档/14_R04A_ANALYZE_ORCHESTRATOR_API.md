# R04a Analyze API、AnalysisOrchestrator 与 ContractAssembler

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M14` |
| 阶段 | `P0` |
| 前置依赖 | `M02`, `M06`, `M07`, `M08`, `M09`, `M10`, `M11`, `M12`, `M13` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

串联 P0 后端分析链路，提供 `/api/sql/analyze` 最小可用接口，统一组装 AnalysisResult、stage_statuses、diagnostics 和降级状态。

## 3. 本模块做什么

- 实现 AnalyzeController。
- 实现 AnalysisOrchestrator。
- 实现 ContractAssembler。
- 执行 parse→scope→metadata/name→projection→lineage→graph→diagnostics→contract。

## 4. 本模块不做什么

- 不实现 SemanticsAnalyzer。
- 不实现复杂 SQL 支持。
- 不做历史保存。

## 5. 交付物

- backend/app/api/analyze_controller.py。
- backend/app/services/analysis_orchestrator.py。
- backend/app/services/contract_assembler.py。
- tests/integration/test_analyze_api_p0.py。
- scripts/test_unit.sh 增量接入本模块测试。

## 6. 对外契约 / 输入输出

POST `/api/sql/analyze`。请求含 sql、dialect、default_catalog、default_schema、metadata_version、analysis_options。响应为 AnalysisResult。

## 7. 建议实现步骤

- 实现请求模型。
- 实现 stage_statuses 采集。
- 上游 failed 时下游 skipped。
- semantics P0 默认 skipped。
- 实现 unsupported_features 聚合。
- 实现 elapsed_ms。

## 8. 单元测试与集成测试

- 成功响应契约测试。
- partial 响应契约测试。
- failed parse 响应契约测试。
- stage_statuses 顺序测试。
- semantics skipped 测试。

## 9. 回归测试要求

- 必须跑 M02 Contract Test、M12 LineageIR Snapshot、M13 Graph Snapshot。
- 必须通过 `scripts/test_contract.sh` 与 `scripts/test_unit.sh`，M17 再统一纳入 `scripts/test_p0_regression.sh`。
- 不得绕过 ContractAssembler 返回 dict。

## 10. 验收标准

- Analyze API 可完成 P0 后端闭环。
- 任何失败均结构化进入 diagnostics_report/stage_statuses。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
