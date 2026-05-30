# R08a DiagnosticCode 与 DiagnosticsCollector

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M06` |
| 阶段 | `P0` |
| 前置依赖 | `M02`, `M03` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

提前建立统一诊断码、诊断模型和旁路收集器，让 parse、metadata、name resolve、lineage、graph build 都能产生结构化诊断。

## 3. 本模块做什么

- 定义 P0/P1+ 诊断码。
- 实现 Diagnostic 对象和 DiagnosticsCollector。
- 实现去重、排序、level 归一。

## 4. 本模块不做什么

- 不做具体业务诊断生成。
- 不修改 SQL。
- 不和前端 UI 绑定。

## 5. 交付物

- backend/app/diagnostics/codes.py。
- backend/app/diagnostics/collector.py。
- backend/app/services/diagnostics_engine.py。
- tests/unit/test_diagnostics.py。

## 6. 对外契约 / 输入输出

Diagnostic 包含 code、level、message、suggestion、source_location_id、related_entity_ids。Collector 支持 add_error/add_warning/add_info。

## 7. 建议实现步骤

- 定义枚举。
- 实现 collector append。
- 实现按 code+location+related_entities 去重。
- 实现 final report 排序：error > warning > info。

## 8. 单元测试与集成测试

- 诊断序列化测试。
- 重复诊断去重测试。
- level 排序测试。
- related_entity_ids 格式测试。

## 9. 回归测试要求

- 后续模块新增诊断码必须在本模块注册并补测试。
- 不得直接返回字符串错误替代 Diagnostic。

## 10. 验收标准

- DiagnosticsReport 可稳定进入 AnalysisResult。
- P0 基础诊断码可用。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
