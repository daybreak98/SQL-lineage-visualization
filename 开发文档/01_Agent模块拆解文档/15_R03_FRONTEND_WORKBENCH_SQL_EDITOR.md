# R03 前端 Workbench Shell 与 Monaco SQL Editor

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M15` |
| 阶段 | `P0` |
| 前置依赖 | `M01`, `M02`, `M14` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

实现前端 Workbench 页面、Monaco SQL 输入、格式化按钮、分析按钮和 AnalysisResultStore，打通前后端最小交互。

## 3. 本模块做什么

- 集成 Monaco Editor。
- 实现 SQL 文本状态。
- 调用 `/api/sql/analyze`。
- 展示 analysis_id/status/diagnostics 数量。
- 实现 API Client 类型约束。

## 4. 本模块不做什么

- 不做 completion/hover。
- 不做 SourceLocation marker/decorations。
- 不推导血缘。

## 5. 交付物

- frontend/src/components/SqlEditor/SqlEditor.tsx。
- frontend/src/pages/Workbench/index.tsx。
- frontend/src/services/analyzeApi.ts。
- frontend/src/stores/analysisResultStore.ts。
- tests/frontend/sql_editor.test.tsx。

## 6. 对外契约 / 输入输出

前端只消费 AnalysisResult，不消费 SQLGlot AST。Analyze API Client 使用手工 TS 类型。

## 7. 建议实现步骤

- 集成 Monaco 基础组件。
- 实现方言选择占位。
- 实现分析按钮。
- 实现 loading/error 状态。
- 将响应写入 store。

## 8. 单元测试与集成测试

- SqlEditor 可输入测试。
- Analyze API mock 测试。
- status 展示测试。
- API 错误展示测试。

## 9. 回归测试要求

- 前端类型编译必须通过。
- 不得在前端解析 SQL 或补边。

## 10. 验收标准

- 用户可输入 SQL 并提交分析。
- 前端能展示基础状态和诊断数量。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
