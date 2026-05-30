# SQL 血缘解析工作台｜需求拆分与整体规划 v0.6

## 0. 文档说明

本文档基于《SQL 血缘解析工作台需求拆分与整体规划 v0.5》继续调整，重点吸收本轮评审中确定合理的工程化建议。

本版核心变化：

| 调整项 | 处理结果 | 原因 |
|---|---|---|
| R09 SourceLocation 原整体放在 P1 | 拆为 R09a / R09b / R09c | 位置映射是 SQL 与图谱联动的底层模型，必须提前预留 |
| R12 / R13 顺序 | 调整为先 ExpressionAnalyzer，再 SemanticsReport | 口径分析依赖表达式抽取结果 |
| R11 内容混杂 | 拆为 R11a select * 展开、R11b completion、R11c hover | 三者依赖不同，交付和测试边界不同 |
| R08 诊断出现偏晚 | 拆为 R08a 诊断模型、R08b 诊断生成、R08c 诊断面板 | 错误码模型应先于 API 和图谱消费 |
| R04 API 契约过完整 | 保留完整契约，但 P0 允许 partial / 空数组 | 既稳定前后端契约，又控制 MVP 范围 |
| R14 多视图偏晚 | P0 GraphViewModel 先预留 view_mode / node_type / edge_type | 避免后续重构图模型 |
| R17 测试体系横向化 | 每个需求绑定最小测试 | 避免测试只在阶段末尾补，导致回归困难 |
| R15 / R16 依赖关系 | 当前 SQL diff 可先做；历史版本 diff 依赖 R16 | 降低 P3 交付耦合度 |

---

## 1. 项目定位

项目定位保持不变：

```text
SQL Analysis Workbench
= SQL 静态解析
+ SQLite 元数据补全
+ 字段级血缘
+ 表达式抽取
+ 查询口径解释
+ 诊断提示
+ SQL 与图谱联动
+ 前端交互式血缘画布
```

第一阶段不做真实 SQL 执行引擎，不连接 Hive / Spark / StarRocks 执行查询。

第一阶段重点是：

```text
简单 SQL
  → 元数据解析
  → 字段归属判断
  → 基础字段血缘
  → 基础图谱展示
  → 基础诊断提示
```

---

## 2. 调整后的总体推进顺序

### 2.1 最终推荐顺序

```text
P0：
R00 → R01 → R02 → R03 → R04a → R08a → R09a → R05 → R06 → R07 → R08b/R08c → R17

P1：
R09b → R10 → R11a → R11b/R11c → R09c → R17

P2：
R13a → R12 → R13b → R14 → R17

P3：
R15 → R16 → R17

P4：
R18
```

### 2.2 顺序调整的核心原因

| 调整 | 原因 |
|---|---|
| SourceLocation 数据模型提前 | 不提前会导致 GraphViewModel、Diagnostics、SQL Editor 后续反向修改 |
| DiagnosticCode 提前 | API、后端分析、前端诊断面板都依赖统一错误码 |
| ExpressionAnalyzer 早于 SemanticsReport | 指标、过滤、聚合、case when、窗口函数口径都依赖表达式抽取 |
| GraphViewModel 提前预留多视图字段 | 多视图不一定 P0 实现，但图模型必须 P0 预留 |
| select * / completion / hover 拆开 | select * 属于后端血缘能力，completion / hover 属于编辑器增强能力 |
| 每个需求绑定测试 | 字段级血缘系统最怕“看起来对，实际错”的静默回归 |

---

## 3. 总体分层架构

### 3.1 后端分析链路

后端核心链路统一为：

```text
AnalyzeController
  ↓
AnalysisOrchestrator
  ↓
SqlParseService
  ↓
ScopeResolver
  ↓
MetadataService
  ↓
NameResolver
  ↓
LineageEngine
  ↓
ExpressionAnalyzer
  ↓
SemanticsAnalyzer
  ↓
DiagnosticsEngine
  ↓
GraphBuilder
  ↓
AnalysisResult
```

### 3.2 关键设计边界

| 层 | 职责 | 不做什么 |
|---|---|---|
| SqlParseService | SQLGlot AST、格式化、方言解析 | 不查 SQLite、不做字段归属最终判断 |
| ScopeResolver | 构建查询作用域、CTE、子查询、表别名 | 不做元数据持久化 |
| MetadataService | 查询表字段、注释、主键、粒度、元数据上下文 | 不解析 SQL |
| NameResolver | 基于 Scope + Metadata 做字段归属、字段消歧 | 不生成前端图 |
| LineageEngine | 生成 LineageIR | 不包含 semantics / diagnostics |
| ExpressionAnalyzer | 抽取表达式依赖、聚合、case when、窗口函数结构 | 不做完整口径解释 |
| SemanticsAnalyzer | 生成 SemanticsReport | 不直接依赖前端组件 |
| DiagnosticsEngine | 生成 DiagnosticsReport | 不修改 SQL |
| GraphBuilder | 生成 GraphViewModel | 不直接依赖 SQLGlot AST |
| AnalysisResult | 聚合 lineage、semantics、diagnostics、graph 等结果 | 不承担具体分析逻辑 |

---

## 4. 核心数据模型约定

### 4.1 AnalysisResult 聚合模型

`LineageIR` 不再包含 `semantics` 和 `diagnostics`。统一由 `AnalysisResult` 聚合所有报告。

```json
{
  "analysis_id": "uuid",
  "status": "success | partial | failed",
  "dialect": "spark",
  "metadata_context": {},
  "lineage_ir": {},
  "semantics_report": {},
  "diagnostics_report": [],
  "graph_view_model": {},
  "source_locations": []
}
```

设计原则：

| 模型 | 职责 |
|---|---|
| LineageIR | 只表达血缘节点、血缘边、作用域、字段依赖 |
| SemanticsReport | 只表达粒度、过滤、指标、join、窗口、去重等口径信息 |
| DiagnosticsReport | 只表达错误、警告、风险、修复建议 |
| GraphViewModel | 只表达前端图谱视图模型 |
| AnalysisResult | 聚合以上结果，作为 API 返回主体 |

---

### 4.2 SourceLocation 模型

`SourceLocation` 从 P0 开始建立数据模型，P1 再做精准提取与交互联动。

```json
{
  "location_id": "loc_001",
  "entity_id": "column:order_no",
  "entity_type": "column | table | expression | filter | join | cte | subquery",
  "start_line": 3,
  "start_col": 8,
  "end_line": 3,
  "end_col": 16,
  "raw_text": "order_no",
  "confidence": 0.8
}
```

分阶段策略：

| 阶段 | 能力 |
|---|---|
| R09a / P0 | 定义模型，LineageIR / GraphViewModel / Diagnostics 可引用 location_id |
| R09b / P1 | 精准提取 SQL 片段位置 |
| R09c / P1 | 实现 SQL 编辑器和图谱双向定位 |

---

### 4.3 GraphViewModel 预留字段

P0 即使只做基础字段血缘，也必须预留多视图扩展字段。

```json
{
  "view_mode": "column",
  "supported_view_modes": ["table", "column", "expression", "semantics", "diagnostics"],
  "nodes": [
    {
      "id": "node_001",
      "node_type": "table | column | expression | filter | join | cte | subquery | diagnostic",
      "label": "order_no",
      "source_location_id": "loc_001"
    }
  ],
  "edges": [
    {
      "id": "edge_001",
      "edge_type": "projection | alias | expression | aggregation | filter_condition | join_condition | group_by | unknown",
      "source": "node_src",
      "target": "node_dst"
    }
  ]
}
```

---

### 4.4 DiagnosticCode 枚举

诊断错误码从 P0 提前定义。

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
DUPLICATE_ALIAS
METADATA_VERSION_MISMATCH
METADATA_IMPORT_INVALID_JSON
METADATA_IMPORT_DUPLICATE_COLUMN
METADATA_IMPORT_SCHEMA_UNSUPPORTED
SOURCE_LOCATION_UNAVAILABLE
```

诊断结构：

```json
{
  "code": "AMBIGUOUS_COLUMN",
  "level": "error | warning | info",
  "message": "字段 user_id 在多个输入表中同时存在",
  "suggestion": "请显式写成 a.user_id 或 b.user_id",
  "source_location_id": "loc_002",
  "related_entity_ids": ["table:a", "table:b"]
}
```

---

### 4.5 MetadataContext 模型

所有分析结果必须带元数据上下文，避免同一 SQL 在不同元数据版本下结果不一致却无法追踪。

```json
{
  "metadata_version": "2026-05-28T10:00:00Z",
  "case_sensitive": false,
  "default_catalog": "default",
  "default_schema": "ihotel_default",
  "resolved_tables": [],
  "missing_tables": [],
  "missing_columns": [],
  "ambiguous_columns": []
}
```

---

### 4.6 JSON 元数据导入标准格式

前端 JSON 导入必须有稳定标准格式。

```json
{
  "schema_version": "1.0",
  "metadata_version": "2026-05-28T10:00:00Z",
  "case_sensitive": false,
  "default_catalog": "default",
  "default_schema": "ihotel_default",
  "tables": [
    {
      "catalog": "default",
      "schema": "ihotel_default",
      "name": "mdw_order_v3_international",
      "comment": "国际酒店订单主表",
      "columns": [
        {
          "name": "order_no",
          "data_type": "string",
          "comment": "订单号",
          "ordinal": 1,
          "is_partition": false
        }
      ]
    }
  ]
}
```

校验规则：

| 字段 | 要求 |
|---|---|
| schema_version | 必填，用于兼容后续导入格式升级 |
| tables | 必填，数组，不允许为空 |
| table.catalog / table.schema / table.name | 表定位信息，至少 schema + name 必填 |
| columns | 必填，数组，不允许为空 |
| column.name | 必填 |
| column.data_type | 建议必填，允许 unknown 但必须诊断提示 |
| column.comment | 可选 |
| case_sensitive | 控制字段匹配是否大小写敏感 |

---

## 5. API 最小契约

### 5.1 `/api/sql/analyze` 请求结构

P0 必须定义稳定请求结构，但分析能力可以 partial。

```json
{
  "sql": "select order_no from default.mdw_order_v3_international where dt = '2026-05-01'",
  "dialect": "spark",
  "default_catalog": "default",
  "default_schema": "ihotel_default",
  "metadata_version": "latest",
  "analysis_options": {
    "include_graph": true,
    "include_semantics": false,
    "include_diagnostics": true,
    "include_source_location": true
  }
}
```

### 5.2 `/api/sql/analyze` 响应结构

P0 允许 `status = partial`，也允许部分数组为空。

```json
{
  "analysis_id": "uuid",
  "status": "success | partial | failed",
  "dialect": "spark",
  "normalized_sql": "select order_no from default.mdw_order_v3_international where dt = '2026-05-01'",
  "metadata_context": {
    "metadata_version": "2026-05-28T10:00:00Z",
    "case_sensitive": false,
    "default_catalog": "default",
    "default_schema": "ihotel_default"
  },
  "lineage_ir": {
    "nodes": [],
    "edges": [],
    "scopes": []
  },
  "semantics_report": {
    "status": "not_supported_in_p0",
    "result_grain": null,
    "filters": [],
    "metrics": [],
    "joins": []
  },
  "diagnostics_report": [],
  "graph_view_model": {
    "view_mode": "column",
    "supported_view_modes": ["table", "column", "expression", "semantics", "diagnostics"],
    "nodes": [],
    "edges": []
  },
  "source_locations": []
}
```

P0 约束：

| 字段 | P0 要求 |
|---|---|
| analysis_id | 必须返回 |
| status | 必须返回，允许 partial |
| metadata_context | 必须返回 |
| diagnostics_report | 必须返回，允许空数组 |
| lineage_ir | 必须返回，允许部分字段为空 |
| graph_view_model | 必须返回，允许 nodes / edges 为空 |
| semantics_report | 可返回 not_supported_in_p0 |
| source_locations | 可返回粗粒度或空数组 |

---

## 6. 需求拆分总表 v0.6

| ID | 需求 | 阶段 | 前端 | 后端 | 数据库 | 核心说明 |
|---|---|---|---:|---:|---:|---|
| R00 | 项目初始化与工程骨架 | P0 | 是 | 是 | 否 | 建立前后端工程、规范、启动脚本 |
| R01 | SQLite 元数据仓库初始化 | P0 | 否 | 是 | 是 | 建立元数据存储与版本上下文 |
| R02 | JSON 元数据导入 | P0 | 是 | 是 | 是 | 支持标准 JSON 导入并更新元数据 |
| R03 | SQL 编辑器基础能力 | P0 | 是 | 是 | 否 | Monaco 编辑器、基础格式化、基础提交分析 |
| R04a | SQL 分析 API 最小契约 | P0 | 是 | 是 | 可选 | 定义 `/api/sql/analyze` 请求响应契约 |
| R08a | DiagnosticCode 与诊断数据模型 | P0 | 可选 | 是 | 可选 | 提前定义错误码和诊断结构 |
| R09a | SourceLocation 数据模型 | P0 | 可选 | 是 | 可选 | 提前定义位置映射基础模型 |
| R05 | ScopeResolver / MetadataService / NameResolver | P0 | 否 | 是 | 是 | 字段归属和字段消歧核心链路 |
| R06 | 基础 LineageIR 与字段级血缘 | P0 | 否 | 是 | 是 | 生成基础字段血缘 IR |
| R07 | GraphViewModel 与基础血缘画布 | P0 | 是 | 是 | 否 | 图模型预留多视图字段，前端展示基础图 |
| R08b | 后端 Diagnostics 生成 | P0 | 否 | 是 | 可选 | 生成未知表、未知字段、歧义等诊断 |
| R08c | 诊断面板 | P0 | 是 | 是 | 否 | 前端展示诊断列表和基础提示 |
| R09b | SourceLocation 精准提取 | P1 | 可选 | 是 | 否 | 精确提取字段、表、表达式 SQL 位置 |
| R10 | join / CTE / 子查询基础支持 | P1 | 是 | 是 | 是 | 扩展真实数仓 SQL 结构 |
| R11a | select * 展开 | P1 | 是 | 是 | 是 | 元数据驱动字段展开 |
| R11b | SQL completion | P1 | 是 | 是 | 是 | 表名、字段名、函数补全 |
| R11c | SQL hover | P1 | 是 | 是 | 是 | 字段类型、字段注释、来源表 hover |
| R09c | SQL 与图谱双向联动 | P1 | 是 | 是 | 否 | 点击 SQL 定位图，点击图定位 SQL |
| R13a | ExpressionAnalyzer 基础抽取 | P2 | 可选 | 是 | 否 | 先抽取表达式结构，为口径分析服务 |
| R12 | SemanticsReport 查询口径分析 | P2 | 是 | 是 | 是 | 粒度、过滤、指标、join、去重分析 |
| R13b | 表达式级血缘增强 | P2 | 是 | 是 | 否 | 聚合、case when、函数、窗口函数血缘 |
| R14 | 多视图图谱 | P2 | 是 | 是 | 否 | 表级、字段级、表达式级、口径级、诊断级 |
| R15 | SQL 当前版本 diff 与重写辅助 | P3 | 是 | 是 | 可选 | 当前 SQL 修改前后血缘 diff |
| R16 | 分析历史与快照 | P3 | 是 | 是 | 是 | 保存分析结果，支撑历史版本 diff |
| R17 | 测试体系与 Golden Case | P0-P3 | 可选 | 是 | 是 | 每个需求绑定最小测试 |
| R18 | 平台化扩展预留 | P4 | 是 | 是 | 是 | 外部元数据、批量分析、权限、集成 |

---

# 7. P0 需求明细

## R00｜项目初始化与工程骨架

### 目标

建立可开发、可启动、可测试的前后端工程骨架。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 初始化 React + TypeScript + Vite | 前端基础工程 |
| 引入基础 UI 组件库 | 用于页面布局、表单、面板 |
| 建立 Workbench 页面骨架 | SQL 编辑器区、图谱区、诊断区预留 |
| 建立 API service 封装 | 统一调用后端接口 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| 初始化 FastAPI 工程 | 建立 API 服务入口 |
| 建立 app 分层目录 | api / domain / services / repositories / adapters / diagnostics |
| 建立配置管理 | sqlite 路径、默认方言、默认 schema |
| 建立基础健康检查接口 | 验证服务启动 |

### 数据库工作

无。

### 最小测试

| 测试 | 验收 |
|---|---|
| 前端启动测试 | 页面可正常打开 |
| 后端启动测试 | health check 返回成功 |
| API 连通测试 | 前端能访问后端 |

---

## R01｜SQLite 元数据仓库初始化

### 目标

建立 SQLite 元数据仓库，支持表字段、字段注释、元数据版本上下文。

### 前端工作

无强依赖，预留元数据状态展示入口。

### 后端工作

| 工作项 | 说明 |
|---|---|
| MetadataRepository | 封装表、字段、版本查询 |
| MetadataService | 向分析链路提供元数据上下文 |
| MetadataContext | 返回 metadata_version、case_sensitive、default_schema |

### 数据库工作

| 对象 | 说明 |
|---|---|
| catalog_tables | 表基础信息 |
| catalog_columns | 字段名、类型、注释、分区标识 |
| metadata_versions | 元数据版本信息 |
| import_batches | 导入批次 |
| import_changes | 导入变化明细 |

### 最小测试

| 测试 | 验收 |
|---|---|
| 初始化脚本测试 | SQLite 表可创建 |
| 元数据查询测试 | 能按 schema.table 查询字段 |
| 版本上下文测试 | 能返回 metadata_version / case_sensitive / default_schema |

---

## R02｜JSON 元数据导入

### 目标

支持用户通过前端上传或粘贴标准 JSON 元数据，并更新 SQLite。

### 前端工作

| 工作项 | 说明 |
|---|---|
| JSON 上传面板 | 支持上传 JSON 文件 |
| JSON 粘贴面板 | 支持直接粘贴 JSON 文本 |
| 导入预览表 | 展示新增表、新增字段、更新字段、未变化字段 |
| 导入结果摘要 | 展示成功、失败、回滚、诊断信息 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| JSON schema 校验 | 校验 schema_version / tables / columns |
| MetadataImportService | 负责 preview / commit |
| 事务化 upsert | 避免部分写入 |
| 导入诊断 | 返回重复字段、格式错误、版本不支持等 |

### 数据库工作

| 对象 | 说明 |
|---|---|
| import_batches | 记录导入批次 |
| import_changes | 记录每个字段新增、更新、未变化 |
| catalog_tables / catalog_columns | 执行 upsert 更新 |

### 最小测试

| 测试 | 验收 |
|---|---|
| 合法 JSON 导入 | 表字段成功写入 |
| 重复字段导入 | 返回 METADATA_IMPORT_DUPLICATE_COLUMN |
| schema_version 不支持 | 返回 METADATA_IMPORT_SCHEMA_UNSUPPORTED |
| 写入失败回滚 | 不产生半更新状态 |

---

## R03｜SQL 编辑器基础能力

### 目标

建立 Monaco SQL 编辑器基础能力，支持输入 SQL、格式化、提交分析。

### 前端工作

| 工作项 | 说明 |
|---|---|
| Monaco Editor 集成 | 基础 SQL 编辑器 |
| 方言选择 | spark / hive 预留 |
| 格式化按钮 | 调用后端格式化或 SQLGlot format |
| 分析按钮 | 调用 `/api/sql/analyze` |
| 基础结果展示 | 展示 analysis_id / status / diagnostics 数量 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| SQL 格式化服务 | 基于 SQLGlot 格式化 |
| SQL parse smoke check | 基础 parse 成功 / 失败返回 |

### 数据库工作

无强依赖。

### 最小测试

| 测试 | 验收 |
|---|---|
| 编辑器输入测试 | SQL 文本可编辑 |
| 格式化测试 | 简单 SQL 可格式化 |
| 提交分析测试 | 前端能收到 analysis response |

---

## R04a｜SQL 分析 API 最小契约

### 目标

定义 `/api/sql/analyze` 最小请求响应契约，P0 可返回 partial。

### 前端工作

| 工作项 | 说明 |
|---|---|
| Analyze API client | 封装请求结构 |
| AnalysisResult 类型 | 前端定义匹配后端响应结构 |
| partial 状态处理 | 部分结果也能正常展示 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| AnalyzeController | 接收 SQL 分析请求 |
| AnalysisOrchestrator | 串联 parse / metadata / lineage / diagnostics / graph |
| AnalysisResult 模型 | 聚合结果结构 |
| partial status | 部分能力未完成时返回 partial |

### 数据库工作

可选：P0 可不落库，后续 R16 再做历史保存。

### 最小测试

| 测试 | 验收 |
|---|---|
| 最小请求测试 | 合法 SQL 返回 analysis_id |
| partial 响应测试 | 未支持 semantics 时不报错 |
| 失败响应测试 | 语法错误返回 failed + PARSE_ERROR |

---

## R08a｜DiagnosticCode 与诊断数据模型

### 目标

提前定义诊断错误码和诊断数据结构，供 API、后端、前端、测试统一使用。

### 前端工作

可选：前端先定义枚举映射和基础展示文案。

### 后端工作

| 工作项 | 说明 |
|---|---|
| DiagnosticCode 枚举 | 定义统一错误码 |
| Diagnostic 模型 | code / level / message / suggestion / source_location_id |
| DiagnosticsReport | 作为 AnalysisResult 的独立组成部分 |

### 数据库工作

可选：暂不落库，R16 再保存历史诊断。

### 最小测试

| 测试 | 验收 |
|---|---|
| 枚举完整性测试 | 所有基础错误码可序列化 |
| 诊断结构测试 | API 返回诊断结构稳定 |

---

## R09a｜SourceLocation 数据模型

### 目标

提前建立 SQL 位置映射数据模型，先不要求精准提取。

### 前端工作

可选：前端类型定义 `SourceLocation`。

### 后端工作

| 工作项 | 说明 |
|---|---|
| SourceLocation 模型 | 定义 line / col / raw_text / confidence |
| AnalysisResult 集成 | source_locations 字段先可为空 |
| GraphViewModel 引用 | node / edge 允许绑定 source_location_id |
| Diagnostics 引用 | diagnostic 允许绑定 source_location_id |

### 数据库工作

无强依赖。

### 最小测试

| 测试 | 验收 |
|---|---|
| 模型序列化测试 | SourceLocation 可正常返回 |
| 空数组兼容测试 | P0 无位置时前端不报错 |

---

## R05｜ScopeResolver / MetadataService / NameResolver

### 目标

统一核心链路为：

```text
ScopeResolver → MetadataService → NameResolver
```

完成基础字段归属判断。

### 前端工作

无直接工作。

### 后端工作

| 工作项 | 说明 |
|---|---|
| ScopeResolver | 识别主查询、表别名、简单 from 表 |
| MetadataService | 查询输入表字段列表 |
| NameResolver | 判断 select 字段来自哪张表 |
| 字段歧义检测 | 多表同名字段返回 AMBIGUOUS_COLUMN |
| 未知字段检测 | 字段不存在返回 UNKNOWN_COLUMN |

### 数据库工作

| 对象 | 说明 |
|---|---|
| catalog_tables | 提供表解析 |
| catalog_columns | 提供字段解析 |
| metadata_versions | 提供版本上下文 |

### 最小测试

| 测试 | 验收 |
|---|---|
| 单表字段解析 | `select order_no from t` 可解析来源字段 |
| 未知字段 | 返回 UNKNOWN_COLUMN |
| 多表同名字段 | 返回 AMBIGUOUS_COLUMN |
| 默认 schema | 未写 schema 时使用 default_schema |

---

## R06｜基础 LineageIR 与字段级血缘

### 目标

生成不包含 semantics / diagnostics 的纯血缘中间表示。

### 前端工作

无直接工作。

### 后端工作

| 工作项 | 说明 |
|---|---|
| LineageNode | table / column 基础节点 |
| LineageEdge | projection / alias 基础边 |
| LineageIR | scopes / nodes / edges |
| 字段级血缘 | 输出字段 → 来源字段 |
| AnalysisResult 聚合 | 将 LineageIR 与 diagnostics 分离返回 |

### 数据库工作

读取 catalog_tables / catalog_columns。

### 最小测试

| 测试 | 验收 |
|---|---|
| 简单投影 | `source.column → output.column` |
| alias | `order_no as order_id` 生成 alias / projection 边 |
| LineageIR 纯净性 | 不包含 semantics_report / diagnostics_report |

---

## R07｜GraphViewModel 与基础血缘画布

### 目标

将 LineageIR 转成 GraphViewModel，并在前端展示基础血缘图。

### 前端工作

| 工作项 | 说明 |
|---|---|
| React Flow 集成 | 展示 nodes / edges |
| 基础节点组件 | table / column |
| 基础边组件 | projection / alias |
| 画布操作 | 拖拽、缩放、fit view |
| 预留 view mode | 当前只实现 column，但保留 table / expression / semantics / diagnostics |

### 后端工作

| 工作项 | 说明 |
|---|---|
| GraphBuilder | LineageIR → GraphViewModel |
| node_type / edge_type | 标准化节点边类型 |
| view_mode | 默认 column |
| supported_view_modes | 返回可支持视图列表 |

### 数据库工作

无直接新增。

### 最小测试

| 测试 | 验收 |
|---|---|
| GraphViewModel 快照 | 简单 SQL 输出稳定 nodes / edges |
| 前端渲染测试 | 节点和边可显示 |
| view_mode 预留测试 | response 中包含 supported_view_modes |

---

## R08b｜后端 Diagnostics 生成

### 目标

将解析、元数据、字段归属过程中的问题结构化为 DiagnosticsReport。

### 前端工作

无直接工作。

### 后端工作

| 工作项 | 说明 |
|---|---|
| Parse diagnostics | PARSE_ERROR |
| Metadata diagnostics | UNKNOWN_TABLE / UNKNOWN_COLUMN |
| Name diagnostics | AMBIGUOUS_COLUMN |
| SourceLocation 引用 | 可为空或低置信度 |
| AnalysisResult 集成 | diagnostics_report 独立返回 |

### 数据库工作

可选：暂不落库。

### 最小测试

| 测试 | 验收 |
|---|---|
| 语法错误测试 | 返回 PARSE_ERROR |
| 未知表测试 | 返回 UNKNOWN_TABLE |
| 字段歧义测试 | 返回 AMBIGUOUS_COLUMN |

---

## R08c｜诊断面板

### 目标

前端展示诊断信息，帮助用户理解 SQL 或元数据问题。

### 前端工作

| 工作项 | 说明 |
|---|---|
| DiagnosticsPanel | 展示错误、警告、提示 |
| code 映射 | DiagnosticCode → 中文说明 |
| level 样式 | error / warning / info |
| suggestion 展示 | 展示修复建议 |

### 后端工作

完善 diagnostics_report 返回。

### 数据库工作

无。

### 最小测试

| 测试 | 验收 |
|---|---|
| 错误展示测试 | UNKNOWN_COLUMN 可展示 |
| 空诊断测试 | diagnostics_report 为空时页面正常 |

---

# 8. P1 需求明细

## R09b｜SourceLocation 精准提取

### 目标

从 SQLGlot AST 或自定义 token mapping 中尽量精确提取字段、表、表达式的 SQL 位置。

### 前端工作

可选：暂不联动，只展示 source_location 调试信息。

### 后端工作

| 工作项 | 说明 |
|---|---|
| 字段位置提取 | select 字段、where 字段、join 字段 |
| 表位置提取 | from / join 表名 |
| 表达式位置提取 | 聚合、case when、函数 |
| confidence | 无法精确时标记置信度 |

### 数据库工作

无。

### 最小测试

| 测试 | 验收 |
|---|---|
| 简单字段位置 | line / col 基本准确 |
| alias 位置 | 原字段和别名可区分 |
| 无法定位 | 返回 SOURCE_LOCATION_UNAVAILABLE 或低置信度 |

---

## R10｜join / CTE / 子查询基础支持

### 目标

扩展常见数仓 SQL 结构。

### 前端工作

| 工作项 | 说明 |
|---|---|
| CTE / subquery 节点样式 | 图谱中区分中间作用域 |
| join 边展示 | 展示 join_condition 边 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| CTE scope | 识别 with 子句 |
| subquery scope | 识别 from 子查询 |
| join condition | 抽取 join 类型和 join key |
| union all 基础支持 | 多分支 lineage 合并预留 |

### 数据库工作

读取元数据；后续可引入 table_keys 支撑 join 风险。

### 最小测试

| 测试 | 验收 |
|---|---|
| CTE 字段血缘 | CTE 输出字段可回溯到源表 |
| join 字段血缘 | join key 被识别为影响关系 |
| 子查询字段血缘 | 派生表字段可回溯 |

---

## R11a｜select * 展开

### 目标

基于 SQLite 元数据展开 `select *` 和 `alias.*`。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 展开结果展示 | 可在 SQL 重写建议中展示展开字段 |
| 展开风险提示 | 元数据不完整时提示 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| `*` 展开 | 单表全部字段 |
| `alias.*` 展开 | 指定别名表字段 |
| 字段顺序 | 使用 ordinal 保持顺序 |
| 失败诊断 | STAR_EXPANSION_FAILED |

### 数据库工作

依赖 catalog_columns.ordinal。

### 最小测试

| 测试 | 验收 |
|---|---|
| 单表 `*` | 展开为所有字段 |
| `alias.*` | 展开指定表字段 |
| 缺失元数据 | 返回 STAR_EXPANSION_FAILED |

---

## R11b｜SQL completion

### 目标

给 Monaco 编辑器提供表名、字段名、函数等补全能力。

### 前端工作

| 工作项 | 说明 |
|---|---|
| CompletionProvider | 注册 Monaco 补全 |
| 表名补全 | 输入 schema / 表名前缀时提示 |
| 字段补全 | 根据当前 scope 和元数据提示字段 |
| 函数补全 | 常见 SQL 函数提示 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| completion API | 返回候选表 / 字段 / 函数 |
| context 解析 | 根据当前 SQL 片段判断补全类型 |
| 元数据搜索 | 表字段模糊搜索 |

### 数据库工作

| 对象 | 说明 |
|---|---|
| catalog_tables | 表名搜索 |
| catalog_columns | 字段名搜索 |
| 字段索引 | 可选，提升搜索性能 |

### 最小测试

| 测试 | 验收 |
|---|---|
| 表名补全 | 输入前缀返回候选表 |
| 字段补全 | 已知表别名下返回字段 |
| 空结果 | 无匹配时不报错 |

---

## R11c｜SQL hover

### 目标

给 Monaco 编辑器提供字段 hover 信息。

### 前端工作

| 工作项 | 说明 |
|---|---|
| HoverProvider | 注册 Monaco hover |
| 字段 hover 卡片 | 展示字段类型、注释、来源表 |
| 表 hover 卡片 | 展示表注释、字段数量 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| hover API | 根据 symbol 返回字段详情 |
| NameResolver 复用 | 判断 hover 字段来源 |
| 元数据查询 | 返回字段类型、注释、表信息 |

### 数据库工作

读取 catalog_tables / catalog_columns。

### 最小测试

| 测试 | 验收 |
|---|---|
| 字段 hover | 返回字段类型和注释 |
| 未知字段 hover | 返回 UNKNOWN_COLUMN 或空结果 |

---

## R09c｜SQL 与图谱双向联动

### 目标

基于 SourceLocation 实现 SQL 编辑器和图谱之间的双向定位。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 点击 SQL 高亮图节点 | editor selection → graph highlight |
| 点击图节点定位 SQL | graph node → editor reveal range |
| 诊断点击跳转 | diagnostics → editor location |
| 路径高亮 | 点击输出字段高亮上游路径 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| location_id 绑定 | node / edge / diagnostic 统一引用 SourceLocation |
| 高亮路径接口或前端算法 | 支持上游 / 下游查找 |

### 数据库工作

无。

### 最小测试

| 测试 | 验收 |
|---|---|
| 图节点定位 SQL | 点击节点能跳转到 SQL 位置 |
| SQL 定位图节点 | 选中字段能高亮图节点 |
| 无 location | 不报错，提示无法定位 |

---

# 9. P2 需求明细

## R13a｜ExpressionAnalyzer 基础抽取

### 目标

先于 SemanticsReport 建立表达式抽取能力。

### 前端工作

可选：可在节点详情中展示表达式文本。

### 后端工作

| 工作项 | 说明 |
|---|---|
| 表达式分类 | column / function / aggregate / case / window / literal |
| source column 抽取 | 找出表达式依赖字段 |
| aggregation 抽取 | sum / count / avg / count distinct |
| condition 抽取 | case when / where / having |
| ExpressionModel | 为 SemanticsReport 提供输入 |

### 数据库工作

无新增，读取字段注释辅助解释。

### 最小测试

| 测试 | 验收 |
|---|---|
| sum 表达式 | 抽取 source column 和 aggregation |
| case when | 抽取条件字段和结果字段 |
| count distinct | 识别 distinct 语义 |

---

## R12｜SemanticsReport 查询口径分析

### 目标

基于 ExpressionAnalyzer、LineageIR、Scope 和元数据生成结构化口径报告。

### 前端工作

| 工作项 | 说明 |
|---|---|
| SemanticsPanel | 展示粒度、过滤、指标、join、窗口、去重 |
| 风险卡片 | 展示 join 放大、无分区过滤、粒度不清晰 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| result_grain | group by / distinct / window partition |
| filters | where / having / partition filter |
| metrics | 指标名、公式、来源字段、聚合方式 |
| joins | join 类型、join key、主从表 |
| dedup_logic | distinct / row_number / group by |
| risks | UNKNOWN_GRAIN / MISSING_PARTITION_FILTER 等 |

### 数据库工作

| 对象 | 说明 |
|---|---|
| table_keys | 判断 join 是否可能放大 |
| table_grains | 判断结果粒度 |
| metrics | 后续指标口径匹配 |

### 最小测试

| 测试 | 验收 |
|---|---|
| group by 粒度 | 正确输出 result_grain |
| where 过滤 | 正确输出 filters |
| 聚合指标 | 正确输出 metrics |
| 缺少分区过滤 | 返回 MISSING_PARTITION_FILTER warning |

---

## R13b｜表达式级血缘增强

### 目标

将表达式抽取结果进一步转成表达式级血缘图。

### 前端工作

| 工作项 | 说明 |
|---|---|
| expression 节点 | 展示 sum / case / function / window |
| expression 边 | 展示 expression / aggregation / window 等边 |
| 表达式详情 | 展示原始表达式和依赖字段 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| ExpressionLineageEngine | 表达式模型 → LineageIR 增强节点边 |
| 聚合血缘 | source column → aggregate expression → output column |
| case 血缘 | condition columns / value columns → output column |
| window 血缘 | partition/order/source columns → output column |

### 数据库工作

无新增。

### 最小测试

| 测试 | 验收 |
|---|---|
| sum 指标血缘 | pay_amount → sum(pay_amount) → gmv |
| case when 血缘 | status / amount → case expression → output |
| window 血缘 | partition/order/source 字段都被识别 |

---

## R14｜多视图图谱

### 目标

基于 P0 已预留的 GraphViewModel 字段，实现多视图切换。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 表级视图 | 展示 table / cte / subquery |
| 字段级视图 | 展示 column lineage |
| 表达式视图 | 展示 expression nodes |
| 口径视图 | 展示 filter / join / group_by / metric |
| 诊断视图 | 高亮 diagnostic nodes / warning edges |
| 视图切换控件 | supported_view_modes 驱动 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| GraphBuilder 多视图输出 | 根据 view_mode 过滤节点边 |
| node_type / edge_type 过滤 | 支持前端按类型展示 |
| collapsed 分组 | CTE / subquery 折叠预留 |

### 数据库工作

无新增。

### 最小测试

| 测试 | 验收 |
|---|---|
| 表级视图 | 只展示表 / CTE / 子查询关系 |
| 字段级视图 | 展示字段来源 |
| 表达式视图 | 展示 expression 节点 |
| 诊断视图 | 展示错误或风险节点 |

---

# 10. P3 / P4 需求明细

## R15｜SQL 当前版本 diff 与重写辅助

### 目标

先支持当前页面内的 SQL 修改前后 diff，不依赖历史快照。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 当前 SQL diff 面板 | 对比修改前后分析结果 |
| 血缘变化展示 | 新增 / 删除 / 变化的节点边 |
| 重写建议展示 | select * 展开、字段裁剪、别名规范化 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| diff service | 对比两个 AnalysisResult |
| lineage diff | 节点边增删改 |
| semantics diff | 粒度、过滤、指标变化 |
| rewrite suggestions | 基础规则建议 |

### 数据库工作

可选，不依赖历史表。

### 最小测试

| 测试 | 验收 |
|---|---|
| 当前 SQL diff | 两段 SQL 可返回变更摘要 |
| 字段新增删除 | 能识别输出字段变化 |
| 血缘变化 | 能识别 source column 变化 |

---

## R16｜分析历史与快照

### 目标

保存分析结果，支撑历史版本追踪和历史版本 diff。

### 前端工作

| 工作项 | 说明 |
|---|---|
| 历史列表 | 展示历史分析记录 |
| 快照查看 | 查看历史 AnalysisResult |
| 历史版本 diff | 基于 R15 diff 能力比较历史快照 |

### 后端工作

| 工作项 | 说明 |
|---|---|
| AnalysisRepository | 保存 SQL、AnalysisResult、GraphViewModel |
| snapshot service | 保存快照 |
| history diff | 历史版本之间比较 |

### 数据库工作

| 对象 | 说明 |
|---|---|
| analysis_history | SQL 与分析元信息 |
| analysis_snapshots | LineageIR / SemanticsReport / GraphViewModel 快照 |
| diagnostic_events | 历史诊断记录 |

### 最小测试

| 测试 | 验收 |
|---|---|
| 保存历史 | 分析结果可落库 |
| 读取快照 | 可按 analysis_id 读取 |
| 历史 diff | 两个快照可比较 |

---

## R18｜平台化扩展预留

### 目标

为后续企业级扩展保留边界，不进入 MVP 主线。

### 扩展方向

| 方向 | 说明 |
|---|---|
| Hive Metastore 自动同步 | 替代手动 JSON 导入 |
| DataHub / OpenMetadata 对接 | 接入企业元数据平台 |
| OpenLineage 输出 | 对外输出标准 lineage event |
| 多项目空间 | 多团队 / 多业务线隔离 |
| 权限体系 | 元数据和 SQL 访问控制 |
| 批量 SQL 分析 | 扫描任务脚本和调度系统 |
| AI SQL Review | 基于血缘和口径生成审查建议 |

---

# 11. R17｜横向测试体系

R17 不再只放在阶段末尾，而是每个需求必须绑定最小测试。

## 11.1 测试分层

| 层级 | 内容 |
|---|---|
| 单元测试 | parser、resolver、lineage、expression、semantics |
| 集成测试 | analyze API、metadata import、graph builder |
| Golden Case | 固定 SQL 输入与期望输出 |
| Snapshot Test | GraphViewModel、LineageIR 结构稳定性 |
| 前端 E2E | SQL 输入、分析、画布展示、诊断展示 |

## 11.2 Golden Case 最小集合

```text
simple_select
single_table_alias
unknown_table
unknown_column
ambiguous_column
select_star
cte_basic
subquery_basic
join_basic
group_by_metric
case_when_metric
window_function
metadata_json_import
source_location_basic
graph_view_model_snapshot
```

## 11.3 每阶段测试重点

| 阶段 | 测试重点 |
|---|---|
| P0 | 简单 SQL、元数据导入、字段归属、基础血缘、诊断模型 |
| P1 | SourceLocation 精准度、CTE、join、select *、completion、hover、双向联动 |
| P2 | ExpressionAnalyzer、SemanticsReport、多视图图谱 |
| P3 | 当前 diff、历史快照、历史 diff |

---

# 12. 新版阶段规划

## 12.1 P0：最小可用闭环

目标：只覆盖简单 SQL + 基础字段血缘。

```text
R00 → R01 → R02 → R03 → R04a → R08a → R09a → R05 → R06 → R07 → R08b/R08c → R17
```

P0 明确不做：

```text
复杂 CTE
复杂子查询
select * 完整展开
completion / hover 高级能力
表达式级血缘
完整口径分析
多视图图谱切换
SQL diff
历史快照
真实 SQL 执行
```

P0 交付成功标准：

| 标准 | 说明 |
|---|---|
| JSON 元数据可导入 | 一张表字段能进入 SQLite |
| 简单 SQL 可解析 | 单表 select 可完成字段归属 |
| 基础字段血缘可展示 | source column → output column |
| 诊断可返回 | 未知表、未知字段、字段歧义有结构化错误码 |
| 图谱可展示 | React Flow 展示基础节点和边 |
| API 契约稳定 | `/api/sql/analyze` 返回 AnalysisResult |

---

## 12.2 P1：真实 SQL 结构增强

```text
R09b → R10 → R11a → R11b/R11c → R09c → R17
```

交付重点：

| 能力 | 说明 |
|---|---|
| SourceLocation 精准提取 | 为联动和诊断跳转做基础 |
| CTE / join / subquery | 覆盖常见数仓 SQL 结构 |
| select * 展开 | 基于元数据展开字段 |
| completion / hover | SQL 编辑器增强 |
| SQL 与图谱联动 | 点击定位与路径高亮 |

---

## 12.3 P2：表达式和口径增强

```text
R13a → R12 → R13b → R14 → R17
```

交付重点：

| 能力 | 说明 |
|---|---|
| ExpressionAnalyzer | 先抽取表达式结构 |
| SemanticsReport | 再做口径分析 |
| 表达式级血缘 | 展示函数、聚合、case、window |
| 多视图图谱 | 表级、字段级、表达式级、口径级、诊断级 |

---

## 12.4 P3：SQL diff 与历史快照

```text
R15 → R16 → R17
```

说明：

```text
当前 SQL diff 可先做，不依赖历史快照。
历史版本 diff 必须依赖 R16 的分析历史与快照。
```

---

## 12.5 P4：平台化扩展

```text
R18
```

P4 不影响 MVP 主线，等 P0-P3 稳定后再推进。

---

# 13. 关键风险与控制

| 风险 | 控制方式 |
|---|---|
| SourceLocation 后补导致前端返工 | R09a 提前定义模型 |
| Diagnostics 后补导致 API 返工 | R08a 提前定义 DiagnosticCode |
| SemanticsReport 先做导致逻辑空泛 | 先做 R13a ExpressionAnalyzer |
| 多视图后做导致 GraphViewModel 返工 | R07 提前预留 view_mode / node_type / edge_type |
| select * / completion / hover 混杂 | R11 拆分为三块独立需求 |
| P0 范围过大 | P0 只覆盖简单 SQL + 基础字段血缘 |
| 测试滞后 | 每个需求绑定最小测试 |

---

# 14. 最终结论

当前需求拆分总体合理，可以继续推进；本版 v0.6 的核心修正是把以下底层支撑能力提前：

```text
1. SourceLocation 数据模型
2. DiagnosticCode 诊断模型
3. ExpressionAnalyzer 表达式抽取能力
4. GraphViewModel 多视图预留字段
5. 每个需求绑定最小测试
```

最终推进主线应保持为：

```text
P0：简单 SQL + 基础字段血缘闭环
P1：真实 SQL 结构 + SourceLocation + 编辑器增强
P2：表达式抽取 + 口径分析 + 多视图图谱
P3：SQL diff + 历史快照
P4：平台化扩展
```

最重要的工程原则：

```text
不要先追求复杂功能覆盖。
先稳定 API 契约、诊断模型、位置模型、LineageIR、GraphViewModel。
否则后续 SQL 与图谱联动、口径分析、多视图图谱都会反向改动 P0 已完成的核心结构。
```
