# SQL 血缘解析工作台｜Agent 模块文档 v1.1 修订报告

> 基准包：`sql_lineage_agent_module_docs_v1.zip`  
> 审阅依据：模块文档 v1.1 修订意见  
> 输出包：`sql_lineage_agent_module_docs_v1.1.zip`  
> 修订原则：只修执行顺序、依赖关系、文件所有权和模块边界；不新增大模块，不重排 P0/P1/P2/P3 阶段。

---

## 1. 总体结论

已在原模块开发计划基础上采纳审阅报告中的合理意见，形成 `module_docs_v1.1`。

本轮没有改变 M01-M28 的编号，也没有拆出新大模块；主要修复的是：

```text
1. M06 Diagnostics primitives 前移到 M05 Metadata JSON Import 之前。
2. M04 / M10 的 MetadataRepository 与 MetadataService 文件所有权切开。
3. M02 / M07 的 SourceLocation 契约外壳与坐标工具职责切开。
4. M18 增加 M10 依赖，保证 SourceLocation 能绑定 entity_id。
5. M23 移除 M22 前端双向定位依赖，避免后端 ExpressionAnalyzer 依赖 UI。
6. M16 显式依赖 M14 Analyze API。
7. M21 增加 M21a / M21b 内部分阶段说明。
8. M25 补充 evidence_refs 与复杂 SourceLocation 的降级关系。
9. M08 标题调整，避免与 M15 前端 R03 混淆。
10. M02 / M14 / M17 补充最小测试入口与 P0 总回归边界。
```

---

## 2. 必须修正项采纳情况

| 审阅项 | 处理结果 | 修改文件 | 状态 |
|---|---|---|---|
| M05 与 M06 顺序倒置 | M06 前移到 M05 前，README / Roadmap / Index 同步更新 | README.md, MODULE_ROADMAP.md, 00_AGENT_MODULE_INDEX.md, 05_R02_METADATA_JSON_IMPORT.md | 已采纳 |
| M04 与 M10 MetadataService 职责重叠 | M04 只保留 Repository / Store / migration；M10 拥有 MetadataService | 04_R01_SQLITE_METADATA_STORE.md, 10_R05_METADATA_AND_NAME_RESOLVER.md | 已采纳 |
| M02 与 M07 SourceLocation 文件所有权不清 | M02 定义契约壳；M07 只增强坐标工具与工厂，不破坏契约字段 | 02_R04B_CONTRACT_BASELINE.md, 07_R09A_SOURCE_LOCATION_MODEL.md | 已采纳 |
| M18 缺少 M10 依赖 | M18 依赖增加 M10，输入改为 ParseResult + ScopeModel + NameResolutionResult | README.md, 18_R09B1_SOURCE_LOCATION_PRECISE_BASIC.md | 已采纳 |
| M23 不应依赖 M22 | M23 依赖改为 M11, M19, M12，并明确不得依赖前端联动 | README.md, 23_R13A_EXPRESSION_ANALYZER.md | 已采纳 |

---

## 3. 建议修正项采纳情况

| 审阅项 | 处理结果 | 修改文件 | 状态 |
|---|---|---|---|
| M17 Golden Case 太靠后 | M02/M14 增加 `scripts/test_contract.sh`、`scripts/test_unit.sh` 最小测试入口，M17 汇总 P0 总回归 | 02_R04B_CONTRACT_BASELINE.md, 14_R04A_ANALYZE_ORCHESTRATOR_API.md, 17_R17_P0_GOLDEN_CASE_REGRESSION.md | 已采纳 |
| M08 标题与 M15 混淆 | M08 标题改为 `M08 SQLGlotAdapter 与 SQL Parse/Format 服务`，并注明不包含前端编辑器 | README.md, 08_R03_SQL_PARSE_ADAPTER.md | 已采纳 |
| M16 显式依赖 M14 | M16 前置依赖增加 M14 | README.md, 16_R07B_CANVAS_AND_DIAGNOSTICS_PANEL.md | 已采纳 |
| M21 Completion/Hover 内部边界 | 增加 M21a / M21b 内部分阶段说明，基础 completion 不强依赖 select * 展开 | README.md, 21_R11B_R11C_MONACO_COMPLETION_HOVER.md | 已采纳 |
| M25 与 M24 依赖说明 | 保留依赖，但说明不要求复杂 SourceLocation 全部 exact，可用 loc/expression/lineage 证据降级 | 25_R12_SEMANTICS_REPORT.md | 已采纳 |

---

## 4. v1.1 推荐执行路径

```text
P0: M01 → M02 → M03 → M04 → M06 → M05 → M07 → M08 → M09 → M10 → M11 → M12 → M13 → M14 → M15 → M16 → M17
P1: M18 → M19 → M20 → M21 → M22
P2: M23 → M24 → M25 → M26
P3: M27 → M28
```

---

## 5. 不采纳或未扩大处理的内容

| 内容 | 处理 | 理由 |
|---|---|---|
| 强制重命名 M05/M06 文件编号 | 未采纳 | 保留原文件编号，避免额外扰动；只修推荐执行顺序 |
| 拆出独立 M21a / M21b 文件 | 未拆文件，只在 M21 内部分阶段 | 审阅报告建议“不扩大模块数量” |
| 让 M23 硬依赖 M18 | 未设为硬依赖，只允许可选消费 | M23 是后端表达式建模，不应被定位能力强绑定 |
| 新增大模块 | 未采纳 | 当前修订目标是 v1.1 小修，不扩大主计划 |

---

## 6. 交付判断

`module_docs_v1.1` 可以作为 Agent 分阶段开发入口。

建议下一步：

```text
1. 先按 v1.1 执行 M01-M04-M06-M05 的 P0 前段模块。
2. 每个模块必须跑本模块测试和所有前置模块回归。
3. M14 完成后跑 Contract Test + Analyze API 集成测试。
4. M17 完成后固定 P0 Golden Regression。
```
