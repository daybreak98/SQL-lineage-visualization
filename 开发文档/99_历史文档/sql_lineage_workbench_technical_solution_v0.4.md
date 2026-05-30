# SQL 血缘解析工作台技术方案 v0.4

## 0. 版本说明

本文档是在 v0.3 技术方案基础上，合并新一轮审阅建议后的 **v0.4 工程化版本**。

本版重点不是继续扩展功能，而是进一步明确以下工程边界：

1. 统一 SQL 分析核心链路。
2. 明确 `LineageIR` 与 `AnalysisResult` 的职责边界。
3. 为 `/api/sql/analyze` 增加最小 API 契约。
4. 增加 `SourceLocation`，支撑 SQL 与图谱双向联动。
5. 明确 JSON 元数据导入标准格式。
6. 增加元数据版本上下文。
7. 增加诊断错误码枚举。
8. 收缩 P0 范围，避免 MVP 阶段过大。

---

## 1. 本版采纳的修改点

| 位置 | 原问题 | 本版调整 | 采纳原因 |
|---|---|---|---|
| 第 5 节 / 第 9.1 节 | 核心链路顺序不一致 | **统一为 `ScopeResolver → MetadataService → NameResolver`** | 先建立 SQL 作用域，再获取候选元数据，最后进行字段归属消歧，链路更符合字段级血缘推导逻辑 |
| 第 6.3 节 | `LineageIR` 包含 `semantics / diagnostics` | **改为 `AnalysisResult` 聚合，`LineageIR` 只表达血缘中间结果** | 避免血缘模型、语义报告、诊断报告职责混杂 |
| 第 12 节 | API 只有能力范围，没有契约 | **增加 `/api/sql/analyze` 最小请求响应结构** | 让前后端协作具备稳定数据契约 |
| 第 7 节 / 第 6.5 节 | SQL 与图谱联动缺少位置映射 | **增加 `SourceLocation` 模型** | 支撑点击 SQL 高亮图节点、点击图节点定位 SQL、诊断跳转 |
| 第 8 节 | JSON 导入缺少标准格式 | **增加 `schema_version` 和 `tables / columns` 标准结构** | 避免 JSON 元数据导入格式混乱，便于后续版本兼容 |
| 第 10 节 | SQLite 元数据合理，但缺少版本上下文 | **增加 `metadata_version / case_sensitive / default_schema`** | 支撑元数据版本追溯、大小写策略、默认库解析 |
| 第 11 节 | 诊断类型合理，但缺少错误码 | **增加 `DiagnosticCode` 枚举** | 方便前端展示、测试断言、问题排查和自动修复建议 |
| 第 13 节 | P0 仍偏大 | **明确 P0 只覆盖简单 SQL + 基础字段血缘** | 控制第一阶段边界，先保证正确性，再扩展复杂 SQL |

---

## 2. 项目定位

本项目定位为面向数仓工程师、数据开发和数据分析人员的 **SQL 血缘解析与 SQL 理解工作台**。

它不是简单 SQL Parser，也不是第一阶段就连接 Hive / Spark 执行 SQL 的查询平台，而是一个围绕 SQL 静态理解构建的分析系统：

```text
SQL 输入
  → SQLGlot AST
  → ScopeResolver 作用域解析
  → MetadataService 获取元数据上下文
  → NameResolver 字段归属消歧
  → LineageIR 血缘中间表示
  → SemanticsReport 查询口径分析
  → DiagnosticsReport 诊断报告
  → GraphViewModel 多视图图模型
  → React Flow 血缘画布展示
```

项目核心目标：

| 目标 | 说明 |
|---|---|
| SQL 静态解析 | 基于 SQLGlot 解析 SQL AST |
| 元数据增强 | 基于 SQLite 维护表、字段、注释、主键、粒度、指标等信息 |
| 字段级血缘 | 自动推导输出字段与来源字段之间的依赖 |
| 表达式级血缘 | 展示字段经过的函数、聚合、case when、窗口函数等加工 |
| 子查询级血缘 | 展示 CTE、子查询、派生表之间的依赖 |
| 查询口径分析 | 解释当前 SQL 的粒度、过滤、聚合、join、指标公式 |
| 前端图谱交互 | 用可拖拽点线图帮助用户理解 SQL 依赖关系 |
| SQL 与图谱联动 | 支持 SQL 片段和图节点双向定位 |
| 元数据导入 | 支持前端 JSON 元数据导入，并更新 SQLite 元数据仓库 |
| 诊断与风险提示 | 识别字段歧义、元数据缺失、join 风险、分区风险等问题 |

---

## 3. 技术主线

```text
后端：Python + FastAPI + SQLGlot + SQLite
前端：React + TypeScript + Monaco Editor + React Flow + ELK.js
```

| 模块 | 技术选型 | 说明 |
|---|---|---|
| SQL 解析核心 | SQLGlot | 负责 SQL AST、方言处理、基础 lineage 和 SQL 格式化 |
| API 服务 | FastAPI | 负责前后端 API、解析任务编排、元数据导入 |
| 元数据存储 | SQLite | 负责表字段元数据、字段注释、指标定义、导入历史、解析历史 |
| SQL 编辑器 | Monaco Editor | 负责在线 SQL 编辑、补全、错误提示、字段 hover |
| 血缘画布 | React Flow | 负责节点、边、拖拽、缩放、折叠、路径高亮 |
| 自动布局 | ELK.js | 负责复杂 DAG 的自动布局 |
| 状态管理 | Zustand | 负责前端 SQL、图谱、元数据、面板状态管理 |
| 测试体系 | pytest + 前端 E2E | 保证解析结果、图谱结果和元数据导入稳定 |

---

## 4. 总体架构

```text
┌────────────────────────────────────────────────────────────┐
│                        前端工作台                           │
│ SQL 编辑器 / 血缘画布 / 元数据导入 / 口径分析 / 诊断面板       │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                        Python 后端服务                      │
│ SQL 解析 / 作用域解析 / 元数据查询 / 字段消歧 / 血缘推导       │
│ 口径分析 / 诊断报告 / GraphViewModel / JSON 元数据导入         │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                        SQLite 元数据仓库                    │
│ 表字段 / 字段注释 / 主键粒度 / 指标定义 / 元数据版本 / 导入历史 │
└────────────────────────────────────────────────────────────┘
```

核心架构原则：

| 原则 | 说明 |
|---|---|
| 解析与元数据解耦 | SQLGlot 负责 SQL 结构，MetadataService 负责元数据上下文 |
| 作用域与字段消歧解耦 | ScopeResolver 先确定可见表和查询块，NameResolver 再判断字段归属 |
| 血缘与语义解耦 | LineageIR 只表达血缘关系，SemanticsReport 单独表达查询口径 |
| 诊断独立输出 | DiagnosticsReport 不混入 LineageIR，由 AnalysisResult 统一聚合 |
| 图模型与前端库解耦 | GraphViewModel 是稳定图模型，React Flow 只是渲染实现 |
| 元数据导入独立模块化 | JSON / DDL / CSV 导入统一走 MetadataImportService |
| 前端多视图展示 | 复杂 SQL 必须通过表级、字段级、表达式级、口径级、诊断级视图分层展示 |
| MVP 边界收缩 | P0 只覆盖简单 SQL + 基础字段血缘，优先保证正确性 |

---

## 5. 核心分析链路

### 5.1 统一后的核心链路

本版统一核心链路为：

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
SemanticsAnalyzer
  ↓
DiagnosticsEngine
  ↓
GraphBuilder
  ↓
AnalysisRepository
```

### 5.2 为什么统一为 `ScopeResolver → MetadataService → NameResolver`

字段级血缘的关键不是解析 SQL 文本，而是判断字段属于哪个作用域、哪张表、哪个上游输出字段。

因此顺序必须是：

```text
1. ScopeResolver
   先识别当前 SQL 中有哪些作用域：
   - 主查询
   - CTE
   - 子查询
   - 派生表
   - 表别名
   - 查询块之间的可见性关系

2. MetadataService
   再基于作用域中识别出的真实表，加载候选元数据：
   - 表字段
   - 字段类型
   - 字段注释
   - 分区字段
   - 主键 / 业务 key
   - 表粒度
   - 指标定义

3. NameResolver
   最后基于作用域和元数据做字段归属判断：
   - 无表名前缀字段来自哪张表
   - `select *` 展开哪些字段
   - CTE 输出字段映射到哪些来源字段
   - 子查询别名字段映射到内部输出字段
   - 字段是否歧义
   - 字段是否缺失
```

### 5.3 后端模块职责

| 模块 | 核心职责 | 不应该负责 |
|---|---|---|
| SqlParseService | 调用 SQLGlot 生成 AST、格式化 SQL、识别方言 | 不查 SQLite、不做字段归属 |
| ScopeResolver | 解析 CTE、子查询、表别名、查询块作用域 | 不访问前端图模型 |
| MetadataService | 查询 SQLite 元数据、字段注释、主键、粒度、指标定义 | 不解析 SQL |
| NameResolver | 字段归属消歧、`select *` 展开、unknown 字段识别 | 不生成 React Flow 节点 |
| LineageEngine | 生成字段、表达式、表、子查询血缘 IR | 不负责口径报告和诊断报告 |
| SemanticsAnalyzer | 分析粒度、过滤、join、聚合、窗口、去重、指标口径 | 不负责字段消歧 |
| DiagnosticsEngine | 生成错误码、风险提示、修复建议 | 不改写 SQL |
| GraphBuilder | LineageIR + SemanticsReport + DiagnosticsReport → GraphViewModel | 不解析 SQL |
| MetadataImportService | JSON / DDL / CSV 导入、预览、事务 upsert | 不参与 SQL 分析链路 |
| AnalysisOrchestrator | 编排完整分析流程 | 不承载具体解析细节 |

---

## 6. 核心领域模型

### 6.1 AnalysisResult

`AnalysisResult` 是一次 SQL 分析的总结果聚合对象。

它负责聚合以下结果：

```text
AnalysisResult
├── analysis_id
├── request_context
├── normalized_sql
├── metadata_context
├── lineage_ir
├── semantics_report
├── diagnostics_report
├── graph_view_model
└── analysis_summary
```

设计原则：

```text
AnalysisResult 可以聚合一切分析结果；
LineageIR 不应该包含 SemanticsReport 和 DiagnosticsReport。
```

---

### 6.2 LineageIR

`LineageIR` 是内部血缘中间表示，只表达血缘相关信息，不包含语义报告和诊断报告。

```text
LineageIR
├── statements
├── scopes
├── tables
├── columns
├── expressions
├── subqueries
├── lineage_nodes
└── lineage_edges
```

职责边界：

| 应包含 | 不应包含 |
|---|---|
| 表级血缘 | 查询口径结论 |
| 字段级血缘 | 诊断错误码 |
| 表达式级血缘 | 前端节点坐标 |
| 子查询级血缘 | SQL Review 建议 |
| 血缘边类型 | API 响应状态 |
| 血缘置信度 | 导入历史 |

---

### 6.3 SemanticsReport

`SemanticsReport` 负责表达当前 SQL 的查询口径。

```text
SemanticsReport
├── query_type
├── input_objects
├── output_objects
├── result_grain
├── filters
├── metrics
├── joins
├── windows
├── dedup_logic
├── order_by
└── semantic_risks
```

核心分析维度：

| 维度 | 说明 |
|---|---|
| result_grain | 当前 SQL 最终输出粒度 |
| filters | where、having、分区过滤、时间条件 |
| metrics | 指标名、公式、来源字段、聚合方式 |
| joins | join 类型、join key、主从表、基数风险 |
| windows | partition by、order by、窗口函数 |
| dedup_logic | distinct、row_number、group by 去重 |
| semantic_risks | 粒度混杂、join 放大、无分区过滤等 |

---

### 6.4 DiagnosticsReport

`DiagnosticsReport` 负责表达错误、警告、风险和修复建议。

```text
DiagnosticsReport
├── diagnostics
│   ├── code
│   ├── level
│   ├── message
│   ├── suggestion
│   ├── source_location
│   ├── related_nodes
│   └── metadata_context
└── summary
```

---

### 6.5 GraphViewModel

`GraphViewModel` 是前端图谱视图模型，不直接等同于 React Flow 的 nodes / edges。

```text
GraphViewModel
├── view_modes
├── nodes
├── edges
├── groups
├── layouts
├── collapsed_state
├── highlight_paths
├── filters
├── source_locations
└── diagnostics_overlay
```

支持的视图模式：

| 视图 | 作用 |
|---|---|
| table | 表级视图，快速看输入表、输出表、CTE、子查询关系 |
| column | 字段级视图，看输出字段来自哪些源字段 |
| expression | 表达式视图，看函数、聚合、case when、窗口函数加工过程 |
| semantics | 口径视图，看过滤、分组、join、去重、窗口对结果的影响 |
| diagnostics | 诊断视图，高亮未知字段、歧义字段、join 风险、分区风险 |

---

### 6.6 SourceLocation

`SourceLocation` 用于描述 SQL 文本中的位置，支撑 SQL 与图谱双向联动。

```json
{
  "start_line": 3,
  "start_column": 8,
  "end_line": 3,
  "end_column": 22,
  "start_offset": 41,
  "end_offset": 55,
  "text": "sum(order_amt)"
}
```

适用对象：

| 对象 | 用途 |
|---|---|
| 字段节点 | 点击图节点定位 SQL 字段 |
| 表节点 | 点击图节点定位 from / join 表引用 |
| 表达式节点 | 点击表达式节点定位表达式片段 |
| 诊断事件 | 点击诊断跳转到 SQL 错误位置 |
| Graph edge | 点击边时定位相关表达式或条件 |
| Semantics item | 点击过滤条件、join 条件、group by 字段定位 SQL |

必须支持的联动：

```text
SQL 选中字段 → 高亮图节点
图节点点击 → 定位 SQL 片段
诊断点击 → 定位 SQL 错误位置
口径项点击 → 定位 SQL 中过滤 / join / group by / window 片段
```

---

## 7. 血缘模型设计

### 7.1 血缘层级

| 层级 | 说明 |
|---|---|
| 表级血缘 | 当前 SQL 读取哪些表、写入哪些表 |
| 字段级血缘 | 输出字段来自哪些源字段 |
| 表达式级血缘 | 字段经过哪些函数、聚合、case when、窗口函数加工 |
| 子查询级血缘 | CTE、子查询、派生表之间的依赖 |
| 口径影响关系 | where、join、group by、having、window 对结果的影响 |

### 7.2 节点类型

```text
statement
scope
table
cte
subquery
column
expression
metric
filter
join
group_by
window
unknown
```

### 7.3 边类型

```text
projection          直接投影
alias               字段重命名
expression          表达式派生
aggregation         聚合派生
case_when           条件表达式派生
filter_condition    过滤条件影响
join_condition      join 条件影响
group_by            分组粒度影响
window_partition    窗口分区影响
window_order        窗口排序影响
union_branch        union 分支合并
unknown             未完全解析的依赖
```

### 7.4 直接血缘与影响血缘分离

字段级血缘不能只表示“字段从哪来”，还要表示“哪些字段影响了结果”。

示例：

```sql
select
    user_id,
    sum(order_amt) as gmv
from order_table
where dt = '2026-05-01'
group by user_id
```

应拆成：

| 类型 | 示例 | 含义 |
|---|---|---|
| 直接血缘 | `order_amt → gmv` | 输出字段由哪个字段计算得到 |
| 粒度影响 | `user_id → group_by` | 结果按什么粒度聚合 |
| 过滤影响 | `dt → filter_condition` | 哪些条件影响结果范围 |

---

## 8. JSON 元数据导入标准

### 8.1 标准 JSON 结构

前端 JSON 元数据导入必须支持统一格式，避免每次导入结构不同。

最小标准结构如下：

```json
{
  "schema_version": "1.0",
  "metadata_version": "2026-05-28-001",
  "case_sensitive": false,
  "default_catalog": "default",
  "default_schema": "ihotel_default",
  "source": {
    "type": "manual_json",
    "name": "user_uploaded_metadata",
    "exported_at": "2026-05-28T10:00:00"
  },
  "tables": [
    {
      "catalog_name": "default",
      "schema_name": "ihotel_default",
      "table_name": "mdw_order_v3_international",
      "table_type": "table",
      "table_comment": "国际酒店订单宽表",
      "grain": "order_no",
      "primary_keys": ["order_no"],
      "business_keys": ["order_no"],
      "partition_columns": ["dt"],
      "columns": [
        {
          "column_name": "order_no",
          "data_type": "string",
          "column_comment": "订单号",
          "ordinal_position": 1,
          "nullable": false,
          "is_partition": false
        },
        {
          "column_name": "dt",
          "data_type": "string",
          "column_comment": "分区日期",
          "ordinal_position": 99,
          "nullable": false,
          "is_partition": true
        }
      ]
    }
  ]
}
```

### 8.2 JSON 字段说明

| 字段 | 是否必填 | 说明 |
|---|---:|---|
| schema_version | 是 | JSON 元数据格式版本 |
| metadata_version | 建议 | 本批元数据版本号 |
| case_sensitive | 建议 | 字段名和表名是否大小写敏感 |
| default_catalog | 可选 | 默认 catalog |
| default_schema | 可选 | 默认 schema / database |
| source | 可选 | 元数据来源说明 |
| tables | 是 | 表数组 |
| tables[].table_name | 是 | 表名 |
| tables[].schema_name | 建议 | schema / database 名 |
| tables[].columns | 是 | 字段数组 |
| columns[].column_name | 是 | 字段名 |
| columns[].data_type | 建议 | 字段类型 |
| columns[].column_comment | 可选 | 字段注释 |
| columns[].is_partition | 可选 | 是否分区字段 |

### 8.3 JSON 导入更新策略

| 场景 | 策略 |
|---|---|
| 表不存在 | 新增表元数据 |
| 表已存在 | 更新表注释、粒度、key、扩展属性 |
| 字段不存在 | 新增字段 |
| 字段已存在 | 更新字段类型、注释、分区标识、顺序 |
| JSON 未包含旧字段 | 默认不物理删除，标记为本批未出现 |
| 字段类型变化 | 记录变更，前端提示用户确认 |
| 字段大量减少 | 标记高风险，要求二次确认 |
| 导入失败 | 整体事务回滚 |
| 导入成功 | 生成 import_batch 和 import_changes |

---

## 9. 元数据上下文设计

### 9.1 MetadataContext

每次 SQL 分析都必须携带元数据上下文，保证解析结果可追溯。

```text
MetadataContext
├── metadata_version
├── case_sensitive
├── default_catalog
├── default_schema
├── resolved_tables
├── missing_tables
├── missing_columns
├── ambiguous_columns
└── metadata_snapshot_id
```

### 9.2 关键上下文字段

| 字段 | 说明 |
|---|---|
| metadata_version | 本次分析使用的元数据版本 |
| case_sensitive | 表名 / 字段名匹配是否大小写敏感 |
| default_catalog | SQL 未显式指定 catalog 时使用的默认 catalog |
| default_schema | SQL 未显式指定 schema 时使用的默认 schema |
| resolved_tables | 成功解析到元数据的表 |
| missing_tables | 元数据中找不到的表 |
| missing_columns | 元数据中找不到的字段 |
| ambiguous_columns | 多张表中同时存在、无法消歧的字段 |
| metadata_snapshot_id | 后续支持元数据快照复现 |

### 9.3 为什么需要版本上下文

字段级血缘结果依赖元数据。如果同一段 SQL 在不同元数据版本下解析，结果可能不同。

例如：

```text
2026-05-01 版本：表 a 中没有字段 user_id
2026-05-28 版本：表 a 新增字段 user_id
```

同一段 SQL 的字段归属可能发生变化。因此每次分析必须记录：

```text
SQL 版本
元数据版本
大小写策略
默认库策略
```

---

## 10. 查询口径分析设计

### 10.1 SemanticsReport 最小结构

```json
{
  "query_type": "select",
  "result_grain": {
    "type": "group_by",
    "columns": ["dt", "country_name"]
  },
  "filters": [
    {
      "type": "partition_filter",
      "column": "dt",
      "operator": "=",
      "value": "${biz_date}",
      "source_location": {}
    }
  ],
  "metrics": [
    {
      "name": "gmv",
      "formula": "sum(order_amt)",
      "source_columns": ["order_amt"],
      "aggregation": "sum",
      "source_location": {}
    }
  ],
  "joins": [
    {
      "type": "left_join",
      "left": "a",
      "right": "b",
      "keys": ["user_id"],
      "risk": "unknown_cardinality",
      "source_location": {}
    }
  ],
  "windows": [],
  "dedup_logic": [],
  "semantic_risks": []
}
```

### 10.2 口径分析维度

| 维度 | 说明 |
|---|---|
| 查询类型 | select、insert、create table as select、create view |
| 输入输出对象 | 来源表、目标表、中间 CTE |
| 最终粒度 | group by 字段、distinct 字段、窗口分区字段 |
| 过滤范围 | where、having、分区过滤、时间范围 |
| 指标公式 | count、sum、avg、count distinct、case when 指标 |
| join 关系 | join 类型、join key、主从表、基数风险 |
| 去重逻辑 | distinct、row_number、group by |
| 窗口逻辑 | partition by、order by、排序取数 |
| 业务字段解释 | 字段注释、指标注释、表注释 |
| 风险提示 | join 放大、字段歧义、元数据缺失、无分区过滤 |

---

## 11. 诊断错误码设计

### 11.1 DiagnosticCode 枚举

```text
PARSE_ERROR
UNSUPPORTED_DIALECT
UNKNOWN_TABLE
UNKNOWN_COLUMN
AMBIGUOUS_COLUMN
STAR_EXPANSION_FAILED
MISSING_METADATA
MISSING_PARTITION_FILTER
JOIN_CARDINALITY_UNKNOWN
JOIN_EXPANSION_RISK
UNKNOWN_GRAIN
DUPLICATE_ALIAS
UNSUPPORTED_FUNCTION
UDF_BLACK_BOX
SOURCE_LOCATION_MISSING
METADATA_VERSION_MISMATCH
JSON_SCHEMA_INVALID
JSON_REQUIRED_FIELD_MISSING
JSON_DUPLICATE_COLUMN
JSON_IMPORT_CONFLICT
```

### 11.2 Diagnostic 结构

```json
{
  "code": "AMBIGUOUS_COLUMN",
  "level": "warning",
  "message": "字段 user_id 同时存在于 a 和 b，无法判断来源",
  "suggestion": "请显式写成 a.user_id 或 b.user_id",
  "source_location": {
    "start_line": 2,
    "start_column": 8,
    "end_line": 2,
    "end_column": 15
  },
  "related_nodes": ["column:a.user_id", "column:b.user_id"],
  "metadata_context": {
    "metadata_version": "2026-05-28-001"
  }
}
```

### 11.3 诊断等级

| 等级 | 含义 |
|---|---|
| error | 解析失败或无法继续生成可靠结果 |
| warning | 可以生成结果，但存在歧义或风险 |
| info | 信息提示，例如使用了 `select *` 展开 |
| debug | 调试信息，仅开发模式展示 |

---

## 12. API 最小契约

### 12.1 `/api/sql/analyze`

用途：

```text
提交 SQL，返回一次完整的静态分析结果，包括血缘、口径、诊断、图模型和元数据上下文。
```

### 12.2 最小请求结构

```json
{
  "sql": "select order_no, sum(order_amt) as gmv from default.order_table where dt='2026-05-28' group by order_no",
  "dialect": "hive",
  "analysis_level": "column",
  "default_catalog": "default",
  "default_schema": "ihotel_default",
  "metadata_version": "latest",
  "case_sensitive": false,
  "options": {
    "include_expression_lineage": true,
    "include_semantics": true,
    "include_diagnostics": true,
    "include_graph": true,
    "include_source_location": true
  }
}
```

### 12.3 最小响应结构

```json
{
  "analysis_id": "uuid",
  "status": "success",
  "dialect": "hive",
  "normalized_sql": "SELECT order_no, SUM(order_amt) AS gmv FROM default.order_table WHERE dt = '2026-05-28' GROUP BY order_no",
  "metadata_context": {
    "metadata_version": "2026-05-28-001",
    "case_sensitive": false,
    "default_catalog": "default",
    "default_schema": "ihotel_default",
    "resolved_tables": [],
    "missing_tables": [],
    "missing_columns": [],
    "ambiguous_columns": []
  },
  "lineage_ir": {
    "statements": [],
    "scopes": [],
    "tables": [],
    "columns": [],
    "expressions": [],
    "lineage_nodes": [],
    "lineage_edges": []
  },
  "semantics_report": {
    "query_type": "select",
    "result_grain": {},
    "filters": [],
    "metrics": [],
    "joins": [],
    "windows": [],
    "dedup_logic": [],
    "semantic_risks": []
  },
  "diagnostics_report": {
    "diagnostics": [],
    "summary": {
      "error_count": 0,
      "warning_count": 0
    }
  },
  "graph_view_model": {
    "view_modes": ["table", "column", "expression", "semantics", "diagnostics"],
    "nodes": [],
    "edges": [],
    "groups": [],
    "source_locations": [],
    "diagnostics_overlay": []
  }
}
```

### 12.4 API 契约原则

| 原则 | 说明 |
|---|---|
| 请求必须包含 sql | SQL 是唯一必填输入 |
| dialect 应显式传入 | 不建议完全依赖自动识别 |
| metadata_version 默认 latest | 但响应必须返回实际使用版本 |
| case_sensitive 可配置 | 默认 false，适配 Hive / Spark 常见场景 |
| source_location 可关闭 | 大 SQL 可在性能优先时关闭 |
| diagnostics 永远返回 | 即使成功也可能有 warning |
| graph_view_model 可选 | 后端批处理场景可以只返回 IR 和报告 |

---

## 13. 前端工作台设计

### 13.1 页面布局

```text
┌────────────────────────────────────────────────────────────┐
│ Header：项目空间 / 方言 / 解析 / 格式化 / 导入元数据 / 导出 │
├───────────────────────┬────────────────────────────────────┤
│ Monaco SQL Editor     │ React Flow Lineage Canvas           │
│ - 补全                │ - 表级 / 字段级 / 表达式级 / 口径级  │
│ - hover 注释          │ - 拖拽 / 缩放 / 折叠 / 自动布局      │
│ - diagnostics 标记    │ - 路径高亮 / 搜索 / 过滤             │
├───────────────────────┼────────────────────────────────────┤
│ SQL Outline / AST     │ Semantics / Diagnostics / Metadata  │
└───────────────────────┴────────────────────────────────────┘
```

### 13.2 前端多视图

| 视图 | 说明 |
|---|---|
| 表级视图 | 快速查看 SQL 依赖哪些表、产生哪些中间查询块 |
| 字段级视图 | 查看输出字段与来源字段之间的依赖 |
| 表达式级视图 | 查看函数、聚合、case when、窗口函数加工过程 |
| 口径视图 | 查看 where、join、group by、window 如何影响结果 |
| 诊断视图 | 高亮未知表、未知字段、字段歧义、join 风险 |

### 13.3 SQL 与图谱联动

| 交互 | 依赖模型 |
|---|---|
| 点击 SQL 字段 → 高亮图节点 | SourceLocation |
| 点击图节点 → 定位 SQL 片段 | SourceLocation |
| 点击诊断项 → 跳转错误位置 | Diagnostic.source_location |
| 点击口径项 → 定位过滤 / join / group by 条件 | SemanticsReport.source_location |
| 点击边 → 展示依赖表达式和 SQL 片段 | GraphEdge.source_location |

---

## 14. 后端项目目录

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── sql_api.py
│   │   ├── metadata_api.py
│   │   └── analysis_api.py
│   ├── domain/
│   │   ├── ast_model.py
│   │   ├── scope_model.py
│   │   ├── metadata_model.py
│   │   ├── metadata_context.py
│   │   ├── source_location.py
│   │   ├── lineage_ir.py
│   │   ├── semantics_report.py
│   │   ├── diagnostics_report.py
│   │   ├── graph_view_model.py
│   │   └── analysis_result.py
│   ├── services/
│   │   ├── analysis_orchestrator.py
│   │   ├── sql_parse_service.py
│   │   ├── scope_resolver.py
│   │   ├── metadata_service.py
│   │   ├── name_resolver.py
│   │   ├── lineage_engine.py
│   │   ├── semantics_analyzer.py
│   │   ├── diagnostics_engine.py
│   │   ├── graph_builder.py
│   │   ├── rewrite_service.py
│   │   └── metadata_import_service.py
│   ├── repositories/
│   │   ├── metadata_repository.py
│   │   ├── metadata_import_repository.py
│   │   ├── analysis_repository.py
│   │   └── metric_repository.py
│   ├── adapters/
│   │   ├── sqlglot_adapter.py
│   │   ├── json_metadata_importer.py
│   │   ├── ddl_importer.py
│   │   ├── csv_importer.py
│   │   └── hive_export_importer.py
│   ├── diagnostics/
│   │   ├── diagnostic_code.py
│   │   ├── diagnostic_rule.py
│   │   └── diagnostic_registry.py
│   └── config/
├── tests/
└── pyproject.toml
```

---

## 15. 前端项目目录

```text
frontend/
├── src/
│   ├── app/
│   ├── pages/
│   │   └── Workbench/
│   ├── components/
│   │   ├── SqlEditor/
│   │   ├── LineageCanvas/
│   │   ├── GraphViewModeTabs/
│   │   ├── MetadataPanel/
│   │   ├── MetadataImport/
│   │   ├── ImportPreview/
│   │   ├── SemanticsPanel/
│   │   ├── DiagnosticsPanel/
│   │   └── Toolbar/
│   ├── stores/
│   │   ├── sqlStore.ts
│   │   ├── graphStore.ts
│   │   ├── metadataStore.ts
│   │   └── analysisStore.ts
│   ├── services/
│   │   ├── sqlApi.ts
│   │   ├── metadataApi.ts
│   │   └── analysisApi.ts
│   ├── types/
│   │   ├── analysis.ts
│   │   ├── lineage.ts
│   │   ├── semantics.ts
│   │   ├── diagnostics.ts
│   │   └── graph.ts
│   └── utils/
└── package.json
```

---

## 16. 推荐开发阶段

### 16.1 P0：最小可用闭环

P0 必须收缩范围，只做简单 SQL + 基础字段血缘。

目标：

```text
证明 SQLGlot + SQLite 元数据 + 字段消歧 + 基础血缘图这条链路可行。
```

P0 范围：

| 能力 | 是否纳入 P0 |
|---|---:|
| 单条 select | 是 |
| 单层 from 表 | 是 |
| 简单表别名 | 是 |
| 简单字段投影 | 是 |
| 简单表达式 | 是 |
| 简单 where 条件识别 | 是 |
| 基础字段注释展示 | 是 |
| JSON 单表元数据导入 | 是 |
| 基础字段级血缘 | 是 |
| React Flow 基础图展示 | 是 |
| SourceLocation 基础定位 | 是 |
| UNKNOWN_TABLE / UNKNOWN_COLUMN / AMBIGUOUS_COLUMN 诊断 | 是 |
| 多层 CTE | 否 |
| 深层子查询 | 否 |
| union all | 否 |
| window function | 否 |
| insert overwrite | 否 |
| SQL diff | 否 |
| AI Review | 否 |
| Hive Metastore 自动同步 | 否 |
| 真正执行 SQL | 否 |

P0 示例 SQL：

```sql
select
    a.order_no,
    a.user_id,
    a.order_amt,
    a.order_amt * 0.1 as commission
from default.order_table a
where a.dt = '2026-05-28';
```

P0 验收标准：

```text
1. 可以导入单表 JSON 元数据。
2. 可以解析简单 select SQL。
3. 可以识别来源表和输出字段。
4. 可以生成基础字段级血缘。
5. 可以在画布中展示表节点、字段节点、表达式节点。
6. 可以展示字段注释。
7. 可以识别未知表、未知字段、字段歧义。
8. 可以点击图节点定位 SQL 片段。
```

---

### 16.2 P1：真实数仓 SQL 基础覆盖

重点支持：

```text
CTE
子查询
join
group by
case when
select * 展开
insert overwrite
```

---

### 16.3 P2：表达式级和口径级增强

重点支持：

```text
sum / count / avg / count distinct
where / having 过滤影响
join key 影响
group by 粒度
row_number 去重
window partition / order
SemanticsReport 完整展示
```

---

### 16.4 P3：前端高级交互

重点支持：

```text
SQL 与图谱完整双向定位
路径高亮
边类型过滤
节点折叠
自动布局
Diff 模式
导出报告
解析历史
```

---

### 16.5 P4：平台化扩展

后续再考虑：

```text
Hive Metastore 自动同步
DataHub / OpenMetadata / OpenLineage 对接
多项目空间
权限系统
任务级 SQL 批量解析
调度血缘
AI Review
```

---

## 17. 测试与质量保障

### 17.1 测试目录

```text
tests/
├── cases/
│   ├── p0_simple_select
│   ├── p0_alias_projection
│   ├── p0_simple_expression
│   ├── p0_unknown_table
│   ├── p0_unknown_column
│   ├── p0_ambiguous_column
│   ├── p0_json_metadata_import
│   ├── cte_nested
│   ├── subquery
│   ├── select_star
│   ├── group_by_metric
│   ├── case_when
│   ├── window_function
│   ├── union_all
│   └── insert_overwrite
├── parser_tests/
├── scope_tests/
├── metadata_tests/
├── name_resolver_tests/
├── lineage_tests/
├── semantics_tests/
├── diagnostics_tests/
├── graph_tests/
└── e2e_tests/
```

### 17.2 测试重点

| 测试类型 | 目标 |
|---|---|
| Golden Case | 固定 SQL 输入与期望血缘输出 |
| Scope Test | 验证 CTE、表别名、子查询作用域 |
| NameResolver Test | 验证字段归属、歧义识别、`select *` 展开 |
| Metadata Import Test | 验证 JSON 导入、更新、冲突、回滚 |
| SourceLocation Test | 验证 SQL 片段位置映射 |
| Diagnostics Test | 验证错误码和修复建议 |
| Graph Snapshot Test | 防止图节点和边结构意外变化 |
| E2E Test | 验证 SQL 输入、元数据导入、解析、画布展示完整链路 |

---

## 18. 参考资料

以下资料用于支撑本文档中的技术选型判断：

1. SQLGlot 官方文档：https://sqlglot.com/
2. SQLGlot Lineage API 文档：https://sqlglot.com/sqlglot/lineage.html
3. FastAPI 官方文档：https://fastapi.tiangolo.com/
4. Monaco Editor 官方文档：https://microsoft.github.io/monaco-editor/
5. React Flow 官方文档：https://reactflow.dev/
6. SQLite 官方文档：https://sqlite.org/docs.html
7. SQLite FTS5 官方文档：https://sqlite.org/fts5.html
```

最终产品形态：

> 一个面向数仓工程师的 SQL Analysis Workbench：既能看字段从哪来，也能看指标怎么算，还能通过 JSON 快速维护元数据，并支持 SQL 与血缘图谱双向联动。

本版最重要的工程边界：

```text
1. LineageIR 只表达血缘，不混入语义和诊断。
2. AnalysisResult 负责聚合所有分析结果。
3. SourceLocation 是 SQL 与图谱联动的基础能力。
4. MetadataContext 保证字段血缘结果可追溯。
5. DiagnosticCode 保证错误提示可测试、可展示、可扩展。
6. P0 必须收缩，只先验证简单 SQL + 基础字段血缘闭环。
```
