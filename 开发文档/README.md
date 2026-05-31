# 开发文档索引

## 当前推荐入口

| 目录 | 作用 | 是否当前主线 |
|---|---|---|
| `00_主需求文档/` | 冻结版主需求文档，定义产品边界、阶段、核心模型 | 是 |
| `01_Agent模块拆解文档/` | 面向 agent 的模块级开发文档，M01-M28 | 是，最高优先级 |
| `02_阶段开发规格/` | P0-P3/P4 阶段级开发规格和补充说明 | 是，辅助参考 |
| `03_前端页面文档/` | 前端页面与交互设计规格 | 是，前端参考 |
| `04_交接文档/` | 当前实现交接、后续开发注意事项、OpenCode 继续开发上下文 | 是，交接入口 |
| `99_历史文档/` | 旧方案、旧需求、评审与评价报告 | 否，仅追溯 |

## 当前前端入口

当前运行前端位于项目根目录的 `frontend/`，已切换为 `sql-lineage-workbench-v1.4/` 对应的 React + Vite 实现。

- 启动目录：`frontend/`
- 启动命令：`npm run dev`
- 浏览地址：`http://localhost:5173`
- React 入口：`frontend/src/main.tsx`
- 页面主组件：`frontend/src/App.tsx`
- Vite 配置：`frontend/vite.config.ts`
- 后端代理：`/api` → `http://localhost:8000`

`sql-lineage-workbench-v1.4/` 保留为来源参考目录；后续开发、联调和修复应以 `frontend/` 为准。

## Agent 开发阅读顺序

```text
00_主需求文档/sql_lineage_workbench_requirement_breakdown_v0.9.1.md
  ↓
01_Agent模块拆解文档/README.md
  ↓
01_Agent模块拆解文档/00_AGENT_MODULE_INDEX.md
  ↓
具体模块文档，例如 01_R00_PROJECT_SCAFFOLD.md
  ↓
必要时参考 02_阶段开发规格/
```

## 当前主线判断

`01_Agent模块拆解文档` 是当前最适合直接交给 agent 实现的文档包。

`02_阶段开发规格` 中的 P0/P1/P2/P3P4 文档提供阶段级合同、API、Golden Case 和前端状态说明，但粒度不如模块拆解文档细。实现时以模块文档为准，阶段规格作为补充。

## 历史文档使用规则

`99_历史文档` 中的文档不要直接作为开发入口。它们用于：

- 回看方案演进；
- 查找评审依据；
- 对比旧版本为何被替换；
- 追溯某个技术决策的来源。

