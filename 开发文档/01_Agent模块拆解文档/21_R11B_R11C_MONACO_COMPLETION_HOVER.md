# R11b/R11c Monaco Completion 与 Hover

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M21` |
| 阶段 | `P1` |
| 前置依赖 | `M15`, `M10`, `M18`, `M20` |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

为 Monaco 提供表名、字段名、别名补全和字段 hover 信息，全部基于后端 scope/name resolve 与 metadata，不在前端推导血缘。模块内部按 M21a/M21b 递进，基础 completion 不强依赖 select * 展开。

## 3. 本模块做什么

- CompletionProvider。
- HoverProvider。
- 后端 completion/hover API。
- 字段注释、类型、来源表、诊断摘要展示。

## 4. 本模块不做什么

- 不做 SQL LSP 完整能力。
- 不在前端解析 SQL。
- 不做 AI 推荐。

## 5. 交付物

- backend/app/api/editor_controller.py。
- backend/app/services/completion_service.py。
- backend/app/services/hover_service.py。
- frontend/src/components/SqlEditor/providers.ts。
- tests/frontend/editor_providers.test.tsx。

## 6. 对外契约 / 输入输出

GET/POST completion/hover API 输入 sql、cursor、metadata_version，返回 candidates 或 hover card。

### 6.1 内部分阶段边界

```text
M21a：基础 completion，依赖 M10 + M15，覆盖表名/字段名候选，不强依赖 select * 展开。
M21b：scope-aware completion / hover，依赖 M18 + M20，增强别名、展开字段和 SourceLocation 关联。
```

基础 completion 不得为了等待 select * 展开而阻塞；scope-aware hover 可以在 M20 后增强。

## 7. 建议实现步骤

- 实现 M21a 表名前缀搜索。
- 实现 M21a 当前 scope 下字段补全。
- 实现 M21b hover 字段归属查询与 SourceLocation 关联。
- 前端注册 Monaco providers。

## 8. 单元测试与集成测试

- 表名补全测试。
- 字段补全测试。
- 未知字段 hover 测试。
- 同名字段需要 NameResolver 的测试。

## 9. 回归测试要求

- 必须跑 P0 前端回归。
- 前端不得直接查全库字段后自行过滤。
- 基础 completion 不得强依赖 select * 展开；scope-aware hover 可以消费 M20 增强结果。

## 10. 验收标准

- Monaco 能基于元数据和 scope 给出准确提示。
- 无匹配时不报错。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
