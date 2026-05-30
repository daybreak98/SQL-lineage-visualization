# Stable Entity ID 与 StageStatus 基础设施

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M03` |
| 阶段 | `P0` |
| 前置依赖 | `M02` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

实现稳定实体 ID 生成与阶段状态记录，为血缘、图谱、SourceLocation、diff 和诊断提供统一身份体系。

## 3. 本模块做什么

- 实现 table、column、scope、scope_relation、scope_column、output_column、expression、node、edge 的 ID 生成工具。
- 实现 StageStatusBuilder。
- 支持 normalized_name / hash_name。

## 4. 本模块不做什么

- 不实现 ScopeResolver。
- 不查询 SQLite。
- 不生成 LineageIR。

## 5. 交付物

- backend/app/domain/entity_id.py。
- backend/app/services/stage_status_builder.py。
- tests/unit/test_entity_id.py。
- tests/unit/test_stage_status.py。

## 6. 对外契约 / 输入输出

`EntityIdFactory` 输入 catalog/schema/table/column/scope/alias 等，输出稳定字符串 ID。`StageStatusBuilder` 输出 stage、status、elapsed_ms、diagnostic_codes。

## 7. 建议实现步骤

- 实现名称归一化策略。
- 实现包含特殊字符时的 hash_name。
- 实现 node_id/edge_id 生成逻辑。
- 实现 stage_status 创建、跳过、失败和部分成功记录。

## 8. 单元测试与集成测试

- 物理表/字段 ID 生成测试。
- scope_relation/scope_column/output_column ID 生成测试。
- 中文、点号、反引号、空格字段名测试。
- stage_status success/partial/failed/skipped 测试。

## 9. 回归测试要求

- 所有后续模块不得手写不规范 ID。
- 所有新增实体类型必须先扩展本模块测试。

## 10. 验收标准

- ID 稳定且可重复生成。
- 特殊字符不会破坏 ID 格式。
- stage_status 可被 AnalysisResult 引用。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
