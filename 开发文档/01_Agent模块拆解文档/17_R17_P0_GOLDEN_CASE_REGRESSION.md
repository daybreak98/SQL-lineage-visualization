# R17 P0 Golden Case 与回归测试基线

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M17` |
| 阶段 | `P0` |
| 前置依赖 | `M04`, `M05`, `M10`, `M12`, `M13`, `M14`, `M16` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

建立 P0 Golden Case、Snapshot Test 和端到端回归命令，让后续每个模块都能避免静默回归。M17 是 P0 最终总回归，不替代各模块自己的单元测试和集成测试。

## 3. 本模块做什么

- 创建 tests/golden_cases/p0 目录。
- 实现 golden case runner。
- 覆盖 simple_select、alias、unknown_table、unknown_column、ambiguous_column、metadata_json_import、source_location_basic、graph_view_model_snapshot、contract_schema_basic。

## 4. 本模块不做什么

- 不覆盖复杂 CTE/join/window。
- 不做性能基准。

## 5. 交付物

- tests/golden_cases/p0/*。
- tests/golden_runner.py。
- docs/golden-cases.md。
- scripts/test_p0_regression.sh。
- 汇总调用 M02/M14 已建立的 `scripts/test_contract.sh`、`scripts/test_unit.sh`。

## 6. 对外契约 / 输入输出

每个 Golden Case 包含 input.sql、metadata.json、options.json、expected_analysis_result.json 或拆分 expected。

## 7. 建议实现步骤

- 实现 runner 读取 case。
- 调用 analyze API 或 Orchestrator。
- 比较 expected JSON。
- 支持忽略 elapsed_ms/analysis_id 等动态字段。
- 输出 diff 报告。

## 8. 单元测试与集成测试

- 每个 P0 case 通过测试。
- Snapshot 字段漂移测试。
- 动态字段忽略测试。

## 9. 回归测试要求

- 后续任意模块提交必须跑 `scripts/test_p0_regression.sh`。
- expected 更新必须说明原因。

## 10. 验收标准

- P0 回归一键运行。
- 失败时能定位到具体字段差异。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
