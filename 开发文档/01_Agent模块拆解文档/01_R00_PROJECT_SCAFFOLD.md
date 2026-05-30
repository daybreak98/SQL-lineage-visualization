# R00 项目初始化与工程骨架

> 来源：`..\00_主需求文档\sql_lineage_workbench_requirement_breakdown_v0.9.1.md`。
> 适用对象：编码 Agent / Code Review Agent / 测试 Agent。
> 交付原则：本模块只能在前置契约上做**增量实现**，不得重写已通过回归的上游模块。

## 1. 模块定位

| 字段 | 内容 |
|---|---|
| 模块编号 | `M01` |
| 阶段 | `P0` |
| 前置依赖 | 无 |
| 交付粒度 | 适合 1 个 Agent 独立开发、测试、提交 PR |

## 2. 目标

搭建前后端可启动、可测试、可持续扩展的工程骨架，为后续所有模块提供稳定目录、命令和 CI 基础。

## 3. 本模块做什么

- 创建 backend FastAPI 工程骨架。
- 创建 frontend React + TypeScript + Vite 工程骨架。
- 建立统一配置、启动脚本、测试命令和基础 CI。
- 提供 health check 与前端空白 Workbench 页面。

## 4. 本模块不做什么

- 不实现 SQL 解析。
- 不实现元数据导入。
- 不接入 Monaco 和 React Flow 的业务能力。
- 不设计完整 UI。

## 5. 交付物

- backend/app/main.py。
- backend/app/api/health_controller.py。
- frontend/src/pages/Workbench/index.tsx。
- Makefile 或 scripts/dev 脚本。
- 基础 README。

## 6. 对外契约 / 输入输出

GET `/api/health` 返回 `{ "status": "ok" }`。前端 `/` 可打开 Workbench 占位页面。

## 7. 建议实现步骤

- 初始化目录结构。
- 配置 Python 依赖管理和前端依赖管理。
- 添加后端 pytest、前端 vitest。
- 添加 lint/format 命令。
- 实现 health check 和 Workbench shell。

## 8. 单元测试与集成测试

- 后端 health check 单测。
- 前端 Workbench 渲染 smoke test。
- 脚本命令测试：后端启动、前端启动、测试命令可执行。

## 9. 回归测试要求

- 每次后续模块提交均必须保证 health check 不失败。
- 前端 shell 页面不得被业务模块破坏。

## 10. 验收标准

- `pytest` 通过。
- `npm test` 或等价前端测试通过。
- 本地可同时启动前后端。

---

## 不可破坏的上游约束

- 不允许让 SQLGlot AST 直接暴露给前端。
- 不允许让前端自行推导或修正血缘。
- 不允许把 CTE、子查询、输出字段伪装成物理字段。
- 不允许把 unsupported 结构伪装成 success。
- 每次提交必须跑完本模块测试和所有前置模块回归。
