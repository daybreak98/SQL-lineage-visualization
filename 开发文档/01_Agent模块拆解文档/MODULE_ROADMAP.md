# SQL 血缘解析工作台｜模块拆解路线图 v1.1

## 1. 拆解原则

本拆解遵循四个原则：

1. **先契约，后能力**：先稳定 AnalysisResult、Entity ID、StageStatus、Diagnostics、SourceLocation，再进入血缘和前端渲染。
2. **先 P0 最小闭环，后复杂 SQL**：P0 只覆盖简单 SQL、元数据导入、字段归属、基础血缘、基础图谱、基础诊断。
3. **每个模块只增量增强，不反向重写**：下游模块只能消费上游稳定输出，不得绕过 Repository、Adapter 或 ContractAssembler。
4. **测试随模块交付**：每个模块都必须有单元测试、必要集成测试和前置模块回归。

## 2. 模块阶段

| 阶段 | 模块范围 | 目标 |
|---|---|---|
| P0 | M01-M17 | 完成最小可用闭环 |
| P1 | M18-M22 | 支持真实 SQL 结构、基础精准定位和编辑器增强 |
| P2 | M23-M26 | 支持表达式、口径分析和多视图图谱 |
| P3 | M27-M28 | 支持 diff、历史与快照 |

## 3. P0 关键闭环

```text
SQLite 元数据仓库初始化
→ Diagnostics primitives
→ SQLite 元数据导入
→ SQLGlot 解析
→ Scope / Name Resolution
→ MinimalExpressionExtractor
→ LineageIR
→ Diagnostics
→ GraphViewModel
→ React Flow 展示
→ Contract Test + Golden Case
```


## 3.1 推荐执行路径 v1.1

```text
P0: M01 → M02 → M03 → M04 → M06 → M05 → M07 → M08 → M09 → M10 → M11 → M12 → M13 → M14 → M15 → M16 → M17
P1: M18 → M19 → M20 → M21 → M22
P2: M23 → M24 → M25 → M26
P3: M27 → M28
```

核心修正：M06 Diagnostics primitives 必须早于 M05 Metadata JSON Import；M23 ExpressionAnalyzer 不依赖 M22 前端双向定位。

## 4. 不返工保障

| 风险 | 防护模块 | 说明 |
|---|---|---|
| 前后端字段漂移 | M02 / M14 / M17 | Contract Test 固化 AnalysisResult |
| ID 混乱影响 diff/定位 | M03 | Stable Entity ID 先行 |
| SourceLocation 坐标偏移 | M07 / M18 / M24 | UTF-16 / original_sql 规范先行 |
| 前端污染后端图模型 | M13 / M16 | GraphViewModel 与 GraphInteractionState 分离 |
| 复杂 SQL 拖慢 P0 | M11 / M12 / M14 | P0 只做 MinimalExpressionExtractor 和基础 LineageIR |
| 解析准确率静默回退 | M17 | Golden Case 与 Snapshot Test |
| MetadataService 职责重叠 | M04 / M10 | M04 只做 Repository/Store/migration，M10 才做 MetadataService 查询封装与 NameResolver |
| 后端能力依赖前端联动 | M23 / M22 | ExpressionAnalyzer 不依赖双向定位，表达式图谱和多视图才依赖 M22 |
