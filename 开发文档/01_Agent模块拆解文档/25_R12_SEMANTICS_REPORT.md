# R12 SemanticsReport 查询口径分析

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M25` |
| 阶段 | `P2` |
| 前置依赖 | `M23`, `M24`, `M12` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

基于 ExpressionModel、LineageIR、MetadataContext 和 SourceLocation 生成证据驱动的查询口径报告。M25 依赖 M24 的目标不是要求所有复杂 SourceLocation 都 exact，而是确保 evidence_refs 至少能引用 loc / expression / lineage 中的一类证据。

## 3. 本模块做什么

- 识别 result_grain。
- 识别 filters。
- 识别 metrics。
- 识别 joins。
- 识别 dedup_rules/window_functions。
- 输出 risks 和 evidence_refs。

## 4. 本模块不做什么

- 不生成无法验证的自然语言猜测。
- 不修改 SQL。
- 不替代指标平台。

## 5. 交付物

- backend/app/services/semantics_analyzer.py。
- backend/app/domain/semantics_model.py。
- tests/golden_cases/p2/group_by_metric/、join_expansion_risk。

## 6. 对外契约 / 输入输出

输入 ExpressionModel + LineageIR + MetadataContext + SourceLocations，输出 SemanticsReport。

## 7. 建议实现步骤

- 实现 group by 粒度。
- 实现 where/having filters。
- 实现 aggregate metrics。
- 实现 distinct/row_number 去重识别。
- 实现 join risk warning。
- 每个确定结论附 evidence_refs。
- 复杂定位失败时允许 `range_type=approximate` 或 `unavailable`，但必须保留 expression / lineage 证据引用。

## 8. 单元测试与集成测试

- group by 粒度测试。
- where filter 测试。
- aggregate metric 测试。
- dedup 测试。
- evidence_refs 缺失失败测试。

## 9. 回归测试要求

- 必须跑所有 P2 ExpressionAnalyzer 回归。
- 没有证据不得输出确定口径。
- 不要求 M24 对所有复杂结构都返回 exact location；可解释降级必须可回归。

## 10. 验收标准

- SemanticsReport 可解释“怎么算”。
- 每个确定结论可追溯。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
