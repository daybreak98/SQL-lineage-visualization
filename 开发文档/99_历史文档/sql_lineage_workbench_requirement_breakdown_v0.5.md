# SQL 血缘解析工作台｜需求拆分与整体规划 v0.5

## 0. 文档说明

本文档基于《SQL 血缘解析工作台技术方案 v0.4》继续拆解，将原有架构设计拆成可推进、可分工、可验收的细粒度需求包。

本文档重点回答：

1. 项目应按什么顺序推进；
2. 每一阶段交付什么；
3. 每个需求的前端、后端、数据库分别要做什么；
4. 每个需求的依赖关系、验收标准和优先级；
5. 哪些内容属于 MVP，哪些内容应延后。

当前项目定位仍然保持为：

```text
SQL Analysis Workbench
= SQL 静态解析
+ 元数据补全
+ 字段级血缘
+ SQL 与图谱联动
+ 查询口径分析
+ 诊断提示
+ 前端交互式血缘画布
```

第一阶段不做真实 SQL 执行引擎，不连接 Hive / Spark / StarRocks 执行查询。

---

## 1. 总体推进原则

### 1.1 研发推进顺序

推荐按如下顺序推进：

```text
项目骨架
  ↓
SQLite 元数据仓库
  ↓
JSON 元数据导入
  ↓
SQL 编辑器基础能力
  ↓
/api/sql/analyze 最小分析接口
  ↓
ScopeResolver / MetadataService / NameResolver
  ↓
基础 LineageIR
  ↓
GraphViewModel
  ↓
React Flow 血缘画布
  ↓
Diagnostics 错误码与诊断面板
  ↓
SourceLocation 双向定位
  ↓
SemanticsReport 查询口径分析
  ↓
多视图图谱
  ↓
表达式级、子查询级、复杂 SQL 扩展
```

### 1.2 P0 范围控制

P0 只覆盖简单 SQL 和基础字段血缘，不追求复杂数仓 SQL 全覆盖。

P0 支持范围：

```text
select col1, col2
from schema.table
where dt = '2026-01-01'
```

P0 可以支持的轻量增强：

```text
1. 单表 select
2. 简单字段别名
3. 简单 where 条件
4. 基础字段注释展示
5. 基础表级 / 字段级血缘图
6. 未知表、未知字段、字段歧义诊断
```

P0 暂不覆盖：

```text
1. 多层 CTE
2. 深层子查询
3. union all
4. window function
5. insert overwrite
6. create table as select
7. 复杂表达式血缘
8. AI 自动改 SQL
9. 真实 SQL 执行
```

---

## 2. 版本路线图

| 阶段 | 目标 | 核心交付 | 重点原则 |
|---|---|---|---|
| P0 | 最小可用闭环 | 元数据导入、简单 SQL 解析、基础字段血缘、基础画布 | 先保证链路跑通和结果正确 |
| P1 | 数仓 SQL 基础增强 | join、CTE、子查询、select *、基础诊断增强 | 覆盖常见开发场景 |
| P2 | 语义分析增强 | SemanticsReport、表达式血缘、口径视图、SQL 与图谱联动 | 从血缘工具升级为 SQL 理解工具 |
| P3 | 高级交互工作台 | 多视图、路径高亮、折叠、Diff、历史快照 | 提升可用性和分析效率 |
| P4 | 平台化扩展 | 批量分析、外部元数据接入、OpenLineage / DataHub 对接 | 支撑团队化和长期扩展 |

---

## 3. 项目模块总览

```text
sql-lineage-workbench/
├── frontend/                         # 前端工作台
│   ├── src/
│   │   ├── app/
│   │   ├── pages/Workbench/
│   │   ├── components/
│   │   │   ├── SqlEditor/
│   │   │   ├── LineageCanvas/
│   │   │   ├── MetadataImport/
│   │   │   ├── MetadataPanel/
│   │   │   ├── SemanticsPanel/
│   │   │   ├── DiagnosticsPanel/
│   │   │   └── Toolbar/
│   │   ├── stores/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   └── package.json
│
├── backend/                          # Python 后端服务
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── domain/
│   │   │   ├── source_location.py
│   │   │   ├── scope_model.py
│   │   │   ├── lineage_ir.py
│   │   │   ├── semantics_model.py
│   │   │   ├── diagnostics_model.py
│   │   │   ├── graph_view_model.py
│   │   │   └── analysis_result.py
│   │   ├── services/
│   │   │   ├── analysis_orchestrator.py
│   │   │   ├── sql_parse_service.py
│   │   │   ├── scope_resolver.py
│   │   │   ├── metadata_service.py
│   │   │   ├── name_resolver.py
│   │   │   ├── lineage_engine.py
│   │   │   ├── semantics_analyzer.py
│   │   │   ├── diagnostics_engine.py
│   │   │   ├── graph_builder.py
│   │   │   └── metadata_import_service.py
│   │   ├── repositories/
│   │   ├── adapters/
│   │   ├── diagnostics/
│   │   └── config/
│   ├── tests/
│   └── pyproject.toml
│
├── metadata/                         # SQLite 元数据仓库与样例
│   ├── sqlite/
│   │   ├── schema/
│   │   ├── migrations/
│   │   └── seeds/
│   └── samples/
│
├── docs/                             # 设计文档
├── examples/                         # 示例 SQL、示例元数据、期望结果
├── scripts/                          # 初始化、导入、测试脚本
├── docker/                           # 后续容器化
├── README.md
└── Makefile
```

---

## 4. 需求拆分总表

| 编号 | 需求名称 | 阶段 | 前端 | 后端 | 数据库 | 说明 |
|---|---|---|---:|---:|---:|---|
| R00 | 项目初始化与工程骨架 | P0 | 是 | 是 | 否 | 建立前后端工程和基础规范 |
| R01 | SQLite 元数据仓库初始化 | P0 | 否 | 是 | 是 | 建立元数据存储基础 |
| R02 | JSON 元数据导入 | P0 | 是 | 是 | 是 | 支持页面导入表字段元数据 |
| R03 | SQL 编辑器基础能力 | P0 | 是 | 是 | 否 | Monaco 编辑器、格式化、基础错误提示 |
| R04 | SQL 分析 API 最小闭环 | P0 | 是 | 是 | 是 | `/api/sql/analyze` 最小请求响应 |
| R05 | ScopeResolver / MetadataService / NameResolver | P0 | 否 | 是 | 是 | 字段级血缘准确性的核心链路 |
| R06 | 基础 LineageIR 与字段级血缘 | P0 | 否 | 是 | 是 | 生成稳定血缘中间表示 |
| R07 | GraphViewModel 与基础血缘画布 | P0 | 是 | 是 | 否 | 后端图模型 + React Flow 展示 |
| R08 | Diagnostics 错误码与诊断面板 | P0 | 是 | 是 | 可选 | 结构化诊断和前端展示 |
| R09 | SourceLocation 与 SQL/图谱联动 | P1 | 是 | 是 | 否 | SQL 片段和图节点双向定位 |
| R10 | join / CTE / 子查询基础支持 | P1 | 是 | 是 | 是 | 扩展常见数仓 SQL |
| R11 | select * 展开与字段补全增强 | P1 | 是 | 是 | 是 | 强化元数据驱动分析 |
| R12 | SemanticsReport 查询口径分析 | P2 | 是 | 是 | 是 | 粒度、过滤、指标、join、去重分析 |
| R13 | 表达式级血缘 | P2 | 是 | 是 | 否 | 聚合、case when、函数、窗口函数 |
| R14 | 多视图图谱 | P2 | 是 | 是 | 否 | 表级、字段级、表达式级、口径级、诊断级 |
| R15 | SQL 重写辅助 | P3 | 是 | 是 | 可选 | 格式化、select * 展开、字段裁剪建议 |
| R16 | 分析历史与快照 | P3 | 是 | 是 | 是 | 保存 SQL 分析结果和图谱快照 |
| R17 | 测试体系与 Golden Case | P0-P3 | 可选 | 是 | 是 | 保证血缘结果稳定 |
| R18 | 平台化扩展预留 | P4 | 是 | 是 | 是 | 批量分析、外部元数据、权限、集成 |

---

# 5. 需求详细设计

---

## R00｜项目初始化与工程骨架

### 目标

搭建前后端基础工程，使后续需求可以并行推进。

### 范围

- 建立前端 React + TypeScript + Vite 项目；
- 建立后端 FastAPI 项目；
- 建立统一目录结构；
- 增加本地启动脚本；
- 增加基础开发规范。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 初始化 React 工程 | 使用 React + TypeScript + Vite |
| 建立页面路由 | 至少包含 Workbench 主页面 |
| 建立基础布局 | Header、左侧编辑区、右侧画布区、底部面板 |
| 建立 API 客户端 | 统一封装后端请求 |
| 建立状态管理 | 管理 SQL、分析结果、图谱状态 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| 初始化 FastAPI 工程 | 建立 main.py、api、services、domain、repositories |
| 增加健康检查接口 | 用于确认后端启动成功 |
| 增加配置管理 | 管理数据库路径、默认方言、默认 schema |
| 增加统一异常处理 | 为后续诊断和 API 错误结构打基础 |

### 数据库工作

无强制数据库变更。

### 验收标准

```text
1. 前端可以本地启动并访问 Workbench 页面。
2. 后端可以本地启动并返回健康检查结果。
3. 前端可以成功调用后端健康检查接口。
4. 项目目录与后续模块拆分一致。
```

---

## R01｜SQLite 元数据仓库初始化

### 目标

建立轻量级元数据仓库，为字段补全、字段注释、字段级血缘、字段消歧提供基础。

### 范围

- 表元数据；
- 字段元数据；
- 元数据版本上下文；
- 导入批次；
- 导入变更记录；
- 后续扩展的主键、粒度、指标定义预留。

### 前端工作

P0 阶段无强制前端工作。后续可在 MetadataPanel 展示元数据。

### 后端工作

| 工作项 | 说明 |
|---|---|
| MetadataRepository | 封装 SQLite 读写 |
| MetadataService | 对外提供表、字段、注释、版本上下文查询 |
| 元数据上下文模型 | 包含 metadata_version、case_sensitive、default_schema |
| 元数据查询能力 | 支持按库表查字段、按字段名搜索候选来源 |

### 数据库工作

建议建立以下逻辑表或等价结构：

| 对象 | 用途 |
|---|---|
| catalog_tables | 存储表基础信息 |
| catalog_columns | 存储字段名、类型、注释、字段顺序、分区标识 |
| metadata_versions | 存储元数据版本、大小写策略、默认 schema |
| import_batches | 存储每次导入批次 |
| import_changes | 存储每次导入的新增、更新、未变化、疑似过期字段 |
| table_keys | 后续支持主键、唯一键、业务 key |
| table_grains | 后续支持表粒度说明 |
| metrics | 后续支持指标口径 |

### 验收标准

```text
1. SQLite 可以初始化成功。
2. 后端可以查询指定表的字段列表。
3. 后端可以根据字段名搜索候选表字段。
4. 元数据上下文可以返回 metadata_version、case_sensitive、default_schema。
```

---

## R02｜JSON 元数据导入

### 目标

支持用户在前端页面上传或粘贴 JSON 元数据，并将表字段信息写入 SQLite。

### 标准 JSON 格式

```json
{
  "schema_version": "1.0",
  "metadata_context": {
    "metadata_version": "2026-05-28-001",
    "default_schema": "default",
    "case_sensitive": false
  },
  "tables": [
    {
      "catalog": "hive",
      "schema": "default",
      "table": "mdw_order_v3_international",
      "comment": "国际酒店订单主表",
      "columns": [
        {
          "name": "order_no",
          "type": "string",
          "comment": "订单号",
          "ordinal": 1,
          "is_partition": false
        },
        {
          "name": "dt",
          "type": "string",
          "comment": "分区日期",
          "ordinal": 2,
          "is_partition": true
        }
      ]
    }
  ]
}
```

### 前端工作

| 工作项 | 说明 |
|---|---|
| MetadataImport 入口 | 在工具栏或元数据面板增加导入入口 |
| JSON 文件上传 | 支持本地 JSON 文件上传 |
| JSON 文本粘贴 | 支持直接粘贴 JSON 文本 |
| 前端格式校验 | 判断是否为合法 JSON |
| 导入预览页面 | 展示新增表、新增字段、更新字段、未变化字段、疑似过期字段 |
| 冲突提示 | 展示字段类型变化、注释覆盖、字段大量减少等风险 |
| 导入结果展示 | 展示成功数量、失败原因、导入批次 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| JsonMetadataImporter | 解析 JSON 标准格式 |
| MetadataImportService | 负责校验、预览、确认导入 |
| 结构校验 | 校验 schema_version、tables、columns |
| 业务校验 | 校验重复字段、空字段、非法类型、表名缺失 |
| 差异计算 | 对比 SQLite 中已有表字段，生成导入预览 |
| 事务 upsert | 用户确认后事务化写入 SQLite |
| 导入历史 | 写入 import_batches 和 import_changes |

### 数据库工作

| 工作项 | 说明 |
|---|---|
| catalog_tables 更新 | 表不存在则新增，存在则更新注释和上下文 |
| catalog_columns 更新 | 字段不存在则新增，存在则更新类型、注释、分区标识 |
| import_batches 写入 | 记录导入批次和状态 |
| import_changes 写入 | 记录新增、更新、未变化、疑似过期字段 |

### 验收标准

```text
1. 用户可以上传或粘贴合法 JSON。
2. 系统可以生成导入预览，不直接写库。
3. 用户确认后才写入 SQLite。
4. 写入失败时整体回滚。
5. 导入成功后 SQL 编辑器字段补全和字段注释可以使用最新元数据。
```

---

## R03｜SQL 编辑器基础能力

### 目标

建立在线 SQL 编辑器体验，为后续 SQL 分析、错误定位、字段 hover 和图谱联动打基础。

### 前端工作

| 工作项 | 说明 |
|---|---|
| Monaco Editor 集成 | 在 Workbench 中嵌入 SQL 编辑器 |
| 方言选择 | 支持 hive、spark、starrocks 等选项，P0 可默认 hive 或 spark |
| SQL 格式化按钮 | 调用后端格式化接口 |
| 编辑器状态管理 | 保存当前 SQL、当前方言、默认 schema |
| 基础错误标注 | 接收 diagnostics 后在编辑器中标注错误 |
| 字段 hover 预留 | 后续接入字段注释和 SourceLocation |

### 后端工作

| 工作项 | 说明 |
|---|---|
| SQL 格式化服务 | 基于 SQLGlot 格式化 SQL |
| SQL 解析错误捕获 | 将 SQLGlot parse error 转成 Diagnostic |
| 编辑器辅助 API 预留 | 后续支持 completion、hover、definition |

### 数据库工作

无强制变更。字段补全阶段需要读取 catalog_tables 和 catalog_columns。

### 验收标准

```text
1. 页面可以输入和编辑 SQL。
2. 用户可以选择 SQL 方言。
3. 点击格式化后 SQL 可以被格式化。
4. SQL 解析失败时，页面能显示基础错误信息。
```

---

## R04｜SQL 分析 API 最小闭环

### 目标

建立统一的 SQL 分析入口，前端后续所有血缘、口径、诊断、图谱能力都从该接口获取结果。

### 最小 API

```text
POST /api/sql/analyze
```

### 最小请求结构

```json
{
  "sql": "select order_no from default.mdw_order_v3_international",
  "dialect": "spark",
  "default_catalog": "hive",
  "default_schema": "default",
  "metadata_version": "latest",
  "analysis_options": {
    "include_lineage": true,
    "include_semantics": false,
    "include_diagnostics": true,
    "include_graph": true
  }
}
```

### 最小响应结构

```json
{
  "analysis_id": "uuid",
  "status": "success",
  "normalized_sql": "select order_no from default.mdw_order_v3_international",
  "metadata_context": {
    "metadata_version": "2026-05-28-001",
    "case_sensitive": false,
    "default_schema": "default"
  },
  "lineage_ir": {
    "nodes": [],
    "edges": []
  },
  "semantics_report": null,
  "diagnostics_report": {
    "items": []
  },
  "graph_view_model": {
    "nodes": [],
    "edges": [],
    "view_modes": ["table", "column"]
  }
}
```

### 前端工作

| 工作项 | 说明 |
|---|---|
| Analyze 调用 | 点击解析按钮调用 `/api/sql/analyze` |
| 加载状态 | 分析过程中显示 loading |
| 结果状态管理 | 保存 AnalysisResult |
| 错误展示 | 分析失败时展示错误 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| AnalyzeController | 提供统一 API 入口 |
| AnalysisOrchestrator | 编排解析、元数据、血缘、诊断、图谱构建流程 |
| AnalysisResult | 聚合 LineageIR、SemanticsReport、DiagnosticsReport、GraphViewModel |
| 最小异常处理 | 返回标准失败结构 |

### 数据库工作

| 工作项 | 说明 |
|---|---|
| analysis_history 可选 | P0 可暂不保存，P3 再完整建设 |
| metadata_context 读取 | 从 metadata_versions 中获取当前元数据上下文 |

### 验收标准

```text
1. 前端提交 SQL 后能收到标准 AnalysisResult。
2. 成功结果包含 lineage_ir 和 graph_view_model。
3. 失败结果包含 diagnostics_report。
4. LineageIR 不包含 semantics 和 diagnostics。
5. AnalysisResult 是唯一聚合对象。
```

---

## R05｜ScopeResolver / MetadataService / NameResolver

### 目标

建立字段级血缘准确性的核心链路。

统一链路：

```text
SQLGlot AST
  → ScopeResolver
  → MetadataService
  → NameResolver
  → ResolvedScope
```

### 前端工作

无直接前端工作。前端只消费最终分析结果。

### 后端工作

| 模块 | 工作项 | 说明 |
|---|---|---|
| ScopeResolver | 查询块识别 | 识别主查询、CTE、子查询、派生表 |
| ScopeResolver | 表别名解析 | 建立 alias → table / subquery / cte 映射 |
| ScopeResolver | 可见字段上下文 | 确定每个 scope 中可见的字段候选范围 |
| MetadataService | 表字段加载 | 根据 scope 中的表引用加载字段元数据 |
| MetadataService | 元数据上下文 | 支持 metadata_version、case_sensitive、default_schema |
| NameResolver | 字段归属消歧 | 判断无表名前缀字段来源 |
| NameResolver | 字段歧义识别 | 多表同名字段时输出 AMBIGUOUS_COLUMN |
| NameResolver | 字段缺失识别 | 元数据中找不到字段时输出 UNKNOWN_COLUMN |
| NameResolver | select * 预留 | P1 做完整展开，P0 可先诊断提示 |

### 数据库工作

| 工作项 | 说明 |
|---|---|
| 表字段查询索引 | 支持按 schema.table 查询字段 |
| 字段名搜索索引 | 支持按字段名查候选表 |
| 大小写策略 | 根据 case_sensitive 决定字段匹配方式 |

### 验收标准

```text
1. 能识别 SQL 中的真实表和别名。
2. 能根据 SQLite 元数据找到字段来源。
3. 无前缀字段在唯一候选时可以正确归属。
4. 多表同名字段能输出 AMBIGUOUS_COLUMN。
5. 找不到字段时能输出 UNKNOWN_COLUMN。
```

---

## R06｜基础 LineageIR 与字段级血缘

### 目标

生成稳定的内部血缘中间表示，避免 SQLGlot AST、语义分析和前端图模型强耦合。

### LineageIR 职责边界

LineageIR 只表达血缘，不包含：

```text
1. SemanticsReport
2. DiagnosticsReport
3. React Flow 节点坐标
4. 前端折叠状态
```

### LineageIR 核心内容

| 对象 | 说明 |
|---|---|
| nodes | 表、字段、表达式、scope 等血缘节点 |
| edges | projection、alias、expression、aggregation 等血缘边 |
| scopes | 主查询、CTE、子查询等作用域引用 |
| source_locations | 节点和 SQL 片段的位置映射 |

### 前端工作

无直接前端工作。前端主要消费 GraphViewModel。

### 后端工作

| 工作项 | 说明 |
|---|---|
| lineage_ir.py | 定义 LineageNode、LineageEdge、LineageIR |
| LineageEngine | 根据 ResolvedScope 生成基础字段血缘 |
| 投影血缘 | `source_col → output_col` |
| 别名血缘 | `order_no as order_id` |
| 基础表达式占位 | P0 可把表达式作为 unknown / expression 节点 |
| SourceLocation 关联 | 为节点和边保留 SQL 位置 |

### 数据库工作

读取元数据即可，无新增数据库结构。

### 验收标准

```text
1. 单表 select 可以生成字段级血缘。
2. 字段别名可以生成 alias / projection 血缘。
3. LineageIR 不包含 semantics_report 和 diagnostics_report。
4. LineageIR 可以被 GraphBuilder 转成 GraphViewModel。
```

---

## R07｜GraphViewModel 与基础血缘画布

### 目标

将 LineageIR 转换为前端可展示、可扩展的图模型，并用 React Flow 展示基础血缘图。

### 前端工作

| 工作项 | 说明 |
|---|---|
| LineageCanvas | 集成 React Flow |
| 基础节点类型 | table、column、expression |
| 基础边类型 | projection、alias、unknown |
| 图谱缩放拖拽 | 支持画布拖动、缩放、节点拖拽 |
| 节点详情 | 点击节点展示表名、字段名、字段注释 |
| 空状态 | 未分析时展示引导 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| graph_view_model.py | 定义前端图模型 |
| GraphBuilder | LineageIR → GraphViewModel |
| view_modes | P0 支持 table、column 两类 |
| 节点分层 | 输入表、源字段、输出字段基础布局信息 |

### 数据库工作

无需新增结构。字段注释从 catalog_columns 读取。

### 验收标准

```text
1. P0 单表 SQL 可以展示表级和字段级血缘。
2. 节点可以拖拽，画布可以缩放。
3. 点击字段节点能看到字段类型和注释。
4. 后端返回的是 GraphViewModel，不是 React Flow 强绑定内部对象。
```

---

## R08｜Diagnostics 错误码与诊断面板

### 目标

建立结构化诊断体系，让系统能解释解析失败、字段歧义、元数据缺失和 SQL 风险。

### DiagnosticCode 枚举

```text
PARSE_ERROR
UNKNOWN_TABLE
UNKNOWN_COLUMN
AMBIGUOUS_COLUMN
STAR_EXPANSION_FAILED
UNSUPPORTED_DIALECT_FEATURE
JOIN_CARDINALITY_UNKNOWN
JOIN_EXPANSION_RISK
MISSING_PARTITION_FILTER
UNKNOWN_GRAIN
UNSUPPORTED_EXPRESSION
METADATA_VERSION_NOT_FOUND
JSON_SCHEMA_INVALID
JSON_DUPLICATE_COLUMN
JSON_IMPORT_CONFLICT
```

### 前端工作

| 工作项 | 说明 |
|---|---|
| DiagnosticsPanel | 展示诊断列表 |
| 诊断级别 | error、warning、info |
| 点击诊断 | P1 联动 SourceLocation 定位 SQL |
| 诊断过滤 | 按错误、警告、提示过滤 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| diagnostics_model.py | 定义 DiagnosticItem、DiagnosticCode、DiagnosticLevel |
| DiagnosticsEngine | 聚合 SQL 解析、元数据、字段消歧、血缘推导中的诊断 |
| 诊断建议 | 每个诊断尽量给出 suggestion |
| 诊断位置 | 支持 SourceLocation |

### 数据库工作

P0 可不落库。P3 可增加 diagnostic_events 保存历史诊断。

### 验收标准

```text
1. SQL 解析失败能返回 PARSE_ERROR。
2. 未知表能返回 UNKNOWN_TABLE。
3. 未知字段能返回 UNKNOWN_COLUMN。
4. 字段歧义能返回 AMBIGUOUS_COLUMN。
5. 前端能按级别展示诊断。
```

---

## R09｜SourceLocation 与 SQL / 图谱联动

### 目标

建立 SQL 文本与图谱节点之间的位置映射，支撑点击 SQL 高亮图节点、点击图节点定位 SQL、诊断跳转。

### SourceLocation 模型

```json
{
  "start_line": 1,
  "start_col": 8,
  "end_line": 1,
  "end_col": 16,
  "text": "order_no"
}
```

### 前端工作

| 工作项 | 说明 |
|---|---|
| SQL 选中监听 | 捕获当前光标或选区 |
| 节点高亮 | 根据 SourceLocation 匹配图节点 |
| 图节点点击 | 点击节点后定位 SQL 片段 |
| 诊断跳转 | 点击诊断项跳到对应 SQL 位置 |
| 高亮样式 | SQL 编辑器和画布均有高亮态 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| SourceLocation 提取 | 从 SQLGlot AST 或自定义扫描中获取位置 |
| 节点位置绑定 | LineageNode、DiagnosticItem 绑定 SourceLocation |
| GraphViewModel 透传 | 图节点携带 source_location |

### 数据库工作

无需新增结构。分析历史阶段可保存 SourceLocation 快照。

### 验收标准

```text
1. 点击图节点可以定位到 SQL 中对应字段。
2. 点击诊断项可以定位到 SQL 中对应问题位置。
3. SQL 中选中字段可以高亮相关图节点。
```

---

## R10｜join / CTE / 子查询基础支持

### 目标

从简单 SQL 扩展到真实数仓 SQL 中最常见的结构。

### 前端工作

| 工作项 | 说明 |
|---|---|
| CTE 节点展示 | 图谱中展示 CTE / subquery 节点 |
| join 边展示 | 展示 join condition 影响边 |
| 子查询折叠预留 | P2 做完整折叠，P1 可先展示节点 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| ScopeResolver 增强 | 支持 CTE、from 子查询、join scope |
| NameResolver 增强 | 支持 CTE 输出字段和派生表字段归属 |
| LineageEngine 增强 | 支持跨 scope 字段传递 |
| Diagnostics 增强 | join key 缺失、字段歧义、未知 CTE |

### 数据库工作

| 工作项 | 说明 |
|---|---|
| table_keys 可选 | 用于后续 join 风险识别 |
| table_grains 可选 | 用于后续粒度判断 |

### 验收标准

```text
1. 简单 join SQL 可以解析来源字段。
2. 简单 CTE SQL 可以追踪 CTE 输出字段到源表字段。
3. from 子查询可以被识别为独立 scope。
4. 字段歧义能够被诊断。
```

---

## R11｜select * 展开与字段补全增强

### 目标

基于 SQLite 元数据增强 SQL 分析体验和字段级血缘准确性。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 字段补全 | 根据当前表别名提供字段补全 |
| 表名补全 | 根据 catalog_tables 提供表名补全 |
| hover 注释 | 展示字段类型、注释、所属表 |
| select * 展开入口 | 提供手动展开按钮 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| CompletionService | 提供表名、字段名补全候选 |
| MetadataService 增强 | 按表别名和 scope 返回可见字段 |
| RewriteService | 基于元数据展开 select * |
| Diagnostics | 无法展开时返回 STAR_EXPANSION_FAILED |

### 数据库工作

依赖 catalog_tables、catalog_columns。

### 验收标准

```text
1. 输入表名或别名时可提示字段。
2. hover 字段可展示字段注释。
3. select * 可以基于元数据展开。
4. 元数据缺失时给出明确诊断。
```

---

## R12｜SemanticsReport 查询口径分析

### 目标

将 SQL 血缘工具升级为 SQL 理解工具，回答“最终结果按什么口径计算”。

### SemanticsReport 内容

| 结构 | 说明 |
|---|---|
| query_type | select / insert / ctas / view |
| result_grain | group by、distinct、window partition 推导结果粒度 |
| filters | where、having、分区过滤、时间过滤 |
| metrics | 指标名、公式、来源字段、聚合方式 |
| joins | join 类型、join key、主从表、风险 |
| windows | 窗口函数、partition by、order by |
| dedup_logic | distinct、row_number、group by 去重 |
| risks | 粒度混杂、join 放大、无分区过滤等风险 |

### 前端工作

| 工作项 | 说明 |
|---|---|
| SemanticsPanel | 展示粒度、过滤、指标、join、去重 |
| 口径卡片 | 每类语义独立卡片 |
| 风险提示 | 展示 join 放大、无分区过滤、未知粒度 |
| 与图谱联动 | 点击口径项高亮相关字段或边 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| semantics_model.py | 定义结构化 SemanticsReport |
| SemanticsAnalyzer | 从 AST、ResolvedScope、LineageIR 中提取口径 |
| 指标识别 | sum、count、avg、count distinct、case when |
| 粒度识别 | group by、distinct、window partition |
| 过滤识别 | where、having、partition filter |
| join 风险初判 | 结合 table_keys / table_grains 判断 |

### 数据库工作

| 工作项 | 说明 |
|---|---|
| table_keys | 用于 join 唯一性判断 |
| table_grains | 用于结果粒度解释 |
| metrics | 后续用于指标口径对齐 |

### 验收标准

```text
1. group by SQL 可以输出 result_grain。
2. where 条件可以输出 filters。
3. sum/count 指标可以输出 metrics。
4. join 可以输出 join type 和 join keys。
5. 无法判断粒度时输出 UNKNOWN_GRAIN。
```

---

## R13｜表达式级血缘

### 目标

支持从输出字段追溯到表达式内部依赖字段，解释字段是如何计算出来的。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 表达式节点 | 展示 sum、case、function、window 节点 |
| 表达式详情 | 点击表达式节点展示原始 SQL 片段 |
| 表达式折叠 | 支持隐藏复杂表达式细节 |
| 表达式视图 | 多视图之一，专门分析加工逻辑 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| ExpressionLineageEngine | 提取表达式依赖字段 |
| 聚合表达式 | sum、count、avg、count distinct |
| 条件表达式 | case when 的条件字段和结果字段 |
| 函数表达式 | 普通函数依赖字段，UDF 标记为黑盒 |
| 窗口表达式 | partition by、order by、函数主体依赖 |

### 数据库工作

无强制新增结构。

### 验收标准

```text
1. sum(order_amt) as gmv 可以追踪 order_amt → gmv。
2. case when status = 1 then amount end 可以区分条件依赖和产出依赖。
3. UDF 表达式可以标记为黑盒表达式。
4. 表达式节点可以在图谱中折叠和展开。
```

---

## R14｜多视图图谱

### 目标

避免复杂 SQL 所有信息堆在一张图中，提升前端分析体验。

### 视图类型

| 视图 | 用途 |
|---|---|
| table | 表级视图，查看输入表、输出表、CTE、子查询关系 |
| column | 字段级视图，查看输出字段来源 |
| expression | 表达式视图，查看函数、聚合、case、window 加工过程 |
| semantics | 口径视图，查看过滤、join、group by、去重、窗口影响 |
| diagnostics | 诊断视图，高亮未知字段、歧义字段、join 风险等 |

### 前端工作

| 工作项 | 说明 |
|---|---|
| 视图切换器 | 支持 table / column / expression / semantics / diagnostics |
| 边类型过滤 | projection、aggregation、filter、join、group_by |
| 路径高亮 | 点击节点高亮上游 / 下游路径 |
| 节点折叠 | CTE、表达式、子查询可折叠 |
| 自动布局 | 不同视图使用不同布局策略 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| GraphBuilder 增强 | 根据 view_mode 生成不同图模型 |
| GraphViewModel 增强 | 支持 view_modes、groups、filters、highlight hints |
| 大图裁剪 | 支持只返回当前视图必要节点和边 |

### 数据库工作

无强制新增结构。

### 验收标准

```text
1. 用户可以在不同视图之间切换。
2. 表级视图比字段级视图更简洁。
3. 表达式视图能看到表达式加工过程。
4. 诊断视图能突出异常节点和边。
5. 大 SQL 不应默认展示所有节点。
```

---

## R15｜SQL 重写辅助

### 目标

基于解析结果和元数据，提供安全、可解释的 SQL 重写建议。

### 前端工作

| 工作项 | 说明 |
|---|---|
| RewritePanel | 展示可用重写建议 |
| select * 展开 | 展示展开前后 SQL |
| 字段裁剪建议 | 展示疑似未使用字段 |
| SQL diff | 展示重写前后差异 |
| 用户确认 | 重写不自动覆盖原 SQL，必须用户确认 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| RewriteService | SQL 格式化、select * 展开、字段裁剪建议 |
| 安全策略 | 不做不确定语义的自动改写 |
| DiffService | 生成重写前后差异摘要 |

### 数据库工作

可选保存 rewrite_history。

### 验收标准

```text
1. select * 可以展开为明确字段列表。
2. SQL 格式化不会改变语义。
3. 重写建议必须说明原因。
4. 用户确认后才应用重写结果。
```

---

## R16｜分析历史与快照

### 目标

保存 SQL 分析结果，方便复现问题、对比版本和做回归测试。

### 前端工作

| 工作项 | 说明 |
|---|---|
| AnalysisHistoryPanel | 展示历史分析记录 |
| 打开历史记录 | 恢复 SQL 和分析结果 |
| 快照对比入口 | 后续支持 Diff |

### 后端工作

| 工作项 | 说明 |
|---|---|
| AnalysisRepository | 保存分析记录 |
| SnapshotService | 保存 AnalysisResult 快照 |
| 历史查询 API | 查询、打开、删除历史记录 |

### 数据库工作

| 对象 | 用途 |
|---|---|
| analysis_history | 保存 SQL、方言、元数据版本、创建时间 |
| analysis_snapshots | 保存 LineageIR、SemanticsReport、DiagnosticsReport、GraphViewModel |

### 验收标准

```text
1. 用户可以保存一次分析结果。
2. 用户可以重新打开历史分析。
3. 历史结果包含当时使用的 metadata_version。
4. 旧结果不会被新元数据静默覆盖。
```

---

## R17｜测试体系与 Golden Case

### 目标

保证字段级血缘、元数据导入、图模型和口径分析结果可回归、可验证。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 组件测试 | SQL 编辑器、导入面板、图谱画布基础测试 |
| E2E 测试 | 从导入元数据到分析 SQL 再到展示图谱 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| parser_tests | SQLGlot 解析适配测试 |
| metadata_import_tests | JSON 导入、预览、冲突、回滚测试 |
| scope_tests | 作用域解析和字段消歧测试 |
| lineage_tests | 字段级血缘测试 |
| semantics_tests | 查询口径分析测试 |
| graph_tests | GraphViewModel 快照测试 |

### 数据库工作

| 工作项 | 说明 |
|---|---|
| test fixtures | 示例元数据初始化 |
| isolated sqlite | 每个测试使用隔离 SQLite 数据库 |

### Golden Case 集合

```text
simple_select
alias_projection
unknown_table
unknown_column
ambiguous_column
select_star
simple_join
cte_basic
subquery_basic
group_by_metric
case_when
window_function
union_all
insert_overwrite
metadata_json_import
```

### 验收标准

```text
1. P0 核心链路有自动化测试覆盖。
2. 每次修改血缘逻辑后可以运行回归测试。
3. GraphViewModel 有 snapshot test。
4. JSON 元数据导入有事务回滚测试。
```

---

## R18｜平台化扩展预留

### 目标

为后续团队化、平台化、批量化能力预留架构边界，但不进入 P0。

### 前端工作

| 扩展方向 | 说明 |
|---|---|
| 项目空间 | 按项目管理 SQL 和元数据 |
| 批量分析页面 | 批量上传 SQL 文件或任务脚本 |
| 对接平台入口 | DataHub / OpenMetadata / OpenLineage 配置页 |

### 后端工作

| 扩展方向 | 说明 |
|---|---|
| Hive Metastore 同步 | 自动拉取表字段元数据 |
| 调度任务解析 | 批量解析脚本中的 SQL |
| OpenLineage 输出 | 输出标准 lineage event |
| DataHub / OpenMetadata 对接 | 向企业元数据平台发布血缘 |
| 权限系统 | 多用户、多项目、元数据隔离 |

### 数据库工作

| 扩展方向 | 说明 |
|---|---|
| workspace | 项目空间 |
| users / roles | 用户权限 |
| external_integrations | 外部平台连接配置 |
| lineage_exports | 血缘导出记录 |

### 验收标准

P4 再定义。P0-P3 只保留架构扩展点，不实际开发。

---

# 6. 阶段交付计划

## 6.1 P0：最小可用闭环

### 目标

跑通：

```text
JSON 元数据导入
  → SQLite 元数据维护
  → 简单 SQL 输入
  → SQLGlot 解析
  → ScopeResolver / MetadataService / NameResolver
  → 基础 LineageIR
  → GraphViewModel
  → React Flow 展示
  → 基础诊断
```

### P0 需求范围

```text
R00 项目初始化与工程骨架
R01 SQLite 元数据仓库初始化
R02 JSON 元数据导入
R03 SQL 编辑器基础能力
R04 SQL 分析 API 最小闭环
R05 ScopeResolver / MetadataService / NameResolver
R06 基础 LineageIR 与字段级血缘
R07 GraphViewModel 与基础血缘画布
R08 Diagnostics 错误码与诊断面板
R17 测试体系与 Golden Case 的 P0 子集
```

### P0 验收口径

```text
1. 用户可以导入一张表的 JSON 元数据。
2. 用户可以输入简单 select SQL。
3. 系统可以识别表、字段、字段注释。
4. 系统可以生成基础字段级血缘。
5. 前端可以展示表级和字段级点线图。
6. 未知表、未知字段、字段歧义可以诊断。
7. P0 Golden Case 全部通过。
```

---

## 6.2 P1：真实数仓 SQL 基础覆盖

### 目标

覆盖常见 SQL 结构：join、CTE、子查询、select *。

### P1 需求范围

```text
R09 SourceLocation 与 SQL / 图谱联动
R10 join / CTE / 子查询基础支持
R11 select * 展开与字段补全增强
R17 测试体系与 Golden Case 的 P1 子集
```

### P1 验收口径

```text
1. 简单 join 可生成字段级血缘。
2. 简单 CTE 可追踪字段来源。
3. 简单 from 子查询可追踪字段来源。
4. select * 可以基于元数据展开。
5. 点击图节点可以定位 SQL。
6. 点击诊断可以定位 SQL 问题位置。
```

---

## 6.3 P2：SQL 语义理解增强

### 目标

从“字段血缘工具”升级为“SQL 理解工作台”。

### P2 需求范围

```text
R12 SemanticsReport 查询口径分析
R13 表达式级血缘
R14 多视图图谱
R17 测试体系与 Golden Case 的 P2 子集
```

### P2 验收口径

```text
1. group by 可输出结果粒度。
2. where / having 可输出过滤范围。
3. sum / count / case when 可输出指标公式和来源字段。
4. 图谱支持表级、字段级、表达式级、口径级、诊断级视图。
5. 用户可以按边类型过滤图谱。
```

---

## 6.4 P3：高级交互与工程化增强

### 目标

提升可用性、可复现性和协作效率。

### P3 需求范围

```text
R15 SQL 重写辅助
R16 分析历史与快照
R17 测试体系与 Golden Case 的 P3 子集
```

### P3 验收口径

```text
1. 支持 select * 展开重写。
2. 支持 SQL 格式化和重写前后 diff。
3. 支持保存和打开历史分析。
4. 历史分析保留 metadata_version。
5. GraphViewModel 有快照测试。
```

---

## 6.5 P4：平台化扩展

### 目标

面向团队和企业级平台扩展。

### P4 需求范围

```text
R18 平台化扩展预留
```

P4 可继续拆成独立项目：

```text
1. Hive Metastore 自动同步
2. SQL 文件批量分析
3. 调度任务血缘分析
4. DataHub / OpenMetadata / OpenLineage 对接
5. 多用户与权限管理
6. 项目空间管理
```

---

# 7. 关键依赖关系

```text
R00 项目骨架
  ↓
R01 SQLite 元数据仓库
  ↓
R02 JSON 元数据导入
  ↓
R04 SQL 分析 API
  ↓
R05 ScopeResolver / MetadataService / NameResolver
  ↓
R06 LineageIR
  ↓
R07 GraphViewModel 与画布
  ↓
R08 Diagnostics
  ↓
R09 SourceLocation 联动
  ↓
R12 SemanticsReport
  ↓
R14 多视图图谱
```

不建议跳过 R05 直接做图谱。否则会退化成：

```text
SQLGlot → React Flow
```

这会导致字段级血缘准确性、复杂 SQL 扩展和前端交互全部受限。

---

# 8. 需求优先级判断

## 8.1 必须先做

```text
1. 元数据仓库
2. JSON 元数据导入
3. SQL 分析 API
4. ScopeResolver
5. MetadataService
6. NameResolver
7. LineageIR
8. GraphViewModel
9. 基础 React Flow 画布
10. Diagnostics 错误码
```

## 8.2 可以第二阶段做

```text
1. SourceLocation 双向定位
2. CTE / 子查询 / join
3. select * 展开
4. 字段补全和 hover 增强
5. SemanticsReport
6. 多视图图谱
```

## 8.3 可以暂缓

```text
1. SQL 真实执行
2. Hive Metastore 自动同步
3. AI 自动改 SQL
4. 多用户权限系统
5. OpenLineage / DataHub 对接
6. 批量任务血缘
```

---

# 9. 最终交付形态

项目最终应形成以下交付闭环：

```text
用户导入元数据
  ↓
用户输入 SQL
  ↓
系统解析 SQL AST
  ↓
系统构建作用域
  ↓
系统读取元数据并消歧字段来源
  ↓
系统生成 LineageIR
  ↓
系统生成 SemanticsReport 和 DiagnosticsReport
  ↓
系统生成 GraphViewModel
  ↓
前端展示多视图血缘图
  ↓
用户通过图谱、口径面板和诊断面板理解并重写 SQL
```

最终产品不是单纯的 SQL Parser，而是：

> 面向数仓工程师的 SQL 静态编译分析工作台。

它的核心价值是：

```text
看清字段从哪来
看清指标怎么算
看清 SQL 有什么风险
看清修改 SQL 会影响什么
```

---

# 10. 参考技术依据

- SQLGlot：用于 SQL AST、方言处理、基础 lineage 和 SQL 格式化。
- FastAPI：用于 Python API 服务和请求 / 响应模型管理。
- Monaco Editor：用于在线 SQL 编辑器、hover、completion、diagnostics 等体验。
- React Flow：用于节点式交互图、血缘画布、节点拖拽、边展示和多视图图谱。
- SQLite：用于轻量级本地元数据仓库、导入历史、分析历史和快照保存。

