# R11a select * / alias.* 元数据驱动展开

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M20` |
| 阶段 | `P1` |
| 前置依赖 | `M04`, `M10`, `M19` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

基于 MetadataService 和当前 scope 实现 select * 与 alias.* 展开，保证字段顺序、元数据版本和诊断可追踪。

## 3. 本模块做什么

- 展开单表 `*`。
- 展开 `alias.*`。
- 按 catalog_columns.ordinal 排序。
- 元数据缺失返回 STAR_EXPANSION_FAILED。

## 4. 本模块不做什么

- 不重写用户 SQL。
- 不做前端补全。
- 不支持复杂 struct.*。

## 5. 交付物

- backend/app/services/star_expander.py。
- tests/golden_cases/p1/select_star/。
- tests/unit/test_star_expander.py。

## 6. 对外契约 / 输入输出

输入 ScopeModel + MetadataContext + select item，输出 ExpandedProjectionItems。

## 7. 建议实现步骤

- 实现单表星号展开。
- 实现 alias.* 展开。
- 接入 ProjectionExtractor。
- 失败时追加诊断。

## 8. 单元测试与集成测试

- 单表 * 测试。
- alias.* 测试。
- 字段顺序测试。
- 缺失元数据诊断测试。

## 9. 回归测试要求

- 必须跑 P0/P1 CTE/join 回归。
- 展开结果必须绑定 metadata_version。

## 10. 验收标准

- select * 可以进入字段级 LineageIR。
- 失败不伪装为 success。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
