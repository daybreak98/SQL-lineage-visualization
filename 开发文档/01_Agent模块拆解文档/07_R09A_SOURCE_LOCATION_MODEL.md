# R09a SourceLocation 数据模型与 UTF-16 坐标工具

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M07` |
| 阶段 | `P0` |
| 前置依赖 | `M02`, `M03` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

定义 SourceLocation 模型和 Monaco 兼容坐标工具。P0 允许 coarse/synthetic/unavailable，但坐标规范必须固定。

## 3. 本模块做什么

- 实现 SourceLocation Pydantic/TS 类型。
- 实现 original_sql hash。
- 实现 line/column 与 UTF-16 offset 转换工具。
- 实现 synthetic/unavailable location 工厂。

## 4. 本模块不做什么

- 不做复杂精准定位。
- 不做 Monaco decoration。
- 不做格式化后坐标复用。

### 4.1 文件所有权约束

M07 只能在 M02 已定义的 SourceLocation 契约基础上增加坐标工具、`source_sql_id` 工厂、`synthetic` / `unavailable` 工厂；不得重命名、删除或改变 M02 中已经进入 AnalysisResult 的 SourceLocation 字段。

## 5. 交付物

- backend/app/domain/source_location.py（仅做兼容增强，不破坏 M02 契约字段）。
- backend/app/utils/text_coordinates.py。
- frontend/src/types/sourceLocation.ts。
- tests/unit/test_text_coordinates.py。

## 6. 对外契约 / 输入输出

SourceLocation 固定 original_sql、one_based line/col、utf16_code_unit、start_offset_utf16/end_offset_utf16。

## 7. 建议实现步骤

- 实现 UTF-16 code unit 长度计算。
- 实现 offset→line/col 与 line/col→offset。
- 处理中文、emoji、换行、CRLF。
- 实现 source_sql_id 计算。

## 8. 单元测试与集成测试

- 中文字段定位测试。
- emoji 注释定位测试。
- 跨行 SQL 定位测试。
- synthetic/unavailable 序列化测试。

## 9. 回归测试要求

- 任何后续 SourceLocation 精准提取必须复用本工具。
- 不得重写或删除 M02 已通过 Contract Test 的 SourceLocation 字段。
- 格式化 SQL 后不得复用旧 SourceLocation。

## 10. 验收标准

- 坐标工具与 Monaco 1-based/UTF-16 约定一致。
- SourceLocation 可进入 AnalysisResult。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
