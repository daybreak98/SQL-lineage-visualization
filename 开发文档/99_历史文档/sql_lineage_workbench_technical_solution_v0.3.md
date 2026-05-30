# SQL 血缘解析工作台技术方案 v0.3

> 版本定位：在 v0.2 的基础上，吸收技术方案审阅结果中的 5 条核心建议，将方案从“产品级技术蓝图”升级为更可落地的“工程架构方案”。

---

## 0. 版本修订记录

| 版本 | 变更内容 | 说明 |
|---|---|---|
| v0.1 | 初版技术方案 | 明确 SQLGlot + Python + SQLite + 前端画布的总体架构 |
| v0.2 | 增加前端 JSON 元数据导入能力 | 支持用户上传 / 粘贴 JSON 元数据，并更新 SQLite 元数据仓库 |
| v0.3 | 合并 5 条核心架构补强建议 | 增加 ScopeResolver、LineageIR、SemanticsReport、多视图 GraphViewModel，并明确不能走 `SQLGlot → React Flow` 直连架构 |

---

# 1. 项目定位

本项目定位为面向数仓工程师、数据开发和数据分析人员的 **在线 SQL 血缘解析与 SQL 理解工作台**。

它不是简单 SQL Parser，也不是第一阶段就连接 Hive / Spark / StarRocks 执行 SQL 的查询平台，而是一个围绕 SQL 静态分析构建的 **SQL Analysis Workbench**。

核心目标：

```text
SQL 输入
  → 元数据补全
  → SQL AST 解析
  → 作用域解析
  → 字段消歧
  → 表级 / 字段级 / 表达式级 / 子查询级血缘推导
  → 查询口径结构化分析
  → 字段注释增强
  → 诊断与风险提示
  → 多视图点线图画布展示
  → SQL 重写辅助
```

---

# 2. 技术主线

```text
后端：Python + FastAPI + SQLGlot + SQLite
前端：React + TypeScript + Monaco Editor + React Flow + ELK.js
```

| 模块 | 技术选型 | 说明 |
|---|---|---|
| SQL 解析核心 | SQLGlot | 负责 SQL AST、方言处理、字段引用分析、基础 lineage 和 SQL 重写底层能力 |
| API 服务 | FastAPI | 负责前后端接口、解析任务、元数据导入任务 |
| 元数据存储 | SQLite | 负责表字段元数据、字段注释、指标定义、解析历史、导入历史 |
| SQL 编辑器 | Monaco Editor | 负责在线 SQL 编辑、补全、错误提示、字段 hover |
| 血缘画布 | React Flow | 负责节点、边、拖拽、缩放、折叠、路径高亮 |
| 自动布局 | ELK.js | 负责复杂 DAG 的自动布局 |
| 前端状态管理 | Zustand | 负责 SQL、图谱、元数据、面板状态管理 |
| 测试体系 | pytest + 前端 E2E | 保证解析结果、血缘结果和图谱结果稳定 |

---

# 3. 总体架构原则

## 3.1 不采用 `SQLGlot → React Flow` 直连架构

不建议：

```text
SQLGlot
  → React Flow
```

原因：

1. SQLGlot 的 AST / lineage 输出是解析器视角，不是产品级语义模型。
2. React Flow 的 nodes / edges 是 UI 展示模型，不适合承载业务血缘语义。
3. 直接耦合会导致后续无法稳定支持口径分析、诊断、图谱多视图、SQL diff、OpenLineage / DataHub 扩展。
4. 字段级血缘准确性依赖元数据、作用域、字段消歧，不是单纯 AST 遍历可以完成。

推荐架构：

```text
SQLGlot
  → AST
  → ScopeResolver / NameResolver
  → MetadataCatalog
  → LineageIR
  → SemanticsReport
  → DiagnosticsReport
  → GraphViewModel
  → React Flow
```

## 3.2 分层职责

| 层级 | 主要职责 | 不应该做什么 |
|---|---|---|
| SQLGlot Adapter | SQL 解析、方言处理、AST 生成、格式化 | 不直接生成前端图 |
| ScopeResolver | 解析 CTE、子查询、别名、字段作用域 | 不负责 UI 展示 |
| MetadataCatalog | 查询表字段、字段注释、业务主键、粒度、指标配置 | 不解析 SQL |
| LineageIR | 承载稳定的内部血缘中间表示 | 不绑定 React Flow |
| SemanticsReport | 结构化输出查询口径 | 不做字段补全 |
| DiagnosticsReport | 输出错误、歧义、风险、修复建议 | 不修改 SQL |
| GraphViewModel | 将内部血缘模型转换为图谱视图模型 | 不重新解析 SQL |
| React Flow | 渲染和交互 | 不承载血缘推导逻辑 |

---

# 4. 总体系统架构

```text
┌──────────────────────────────────────────────────────────────┐
│                          前端工作台                           │
│ SQL Editor / Metadata Import / Lineage Canvas / Semantics Panel│
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                         Python API 层                         │
│ AnalyzeController / MetadataImportController / EditorController│
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                        AnalysisOrchestrator                   │
│ 统一编排 SQL 解析、作用域解析、血缘推导、口径分析、诊断、图构建 │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                        核心分析引擎层                         │
│ SQLGlotAdapter / ScopeResolver / LineageEngine / SemanticsAnalyzer│
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                         SQLite 元数据仓库                     │
│ 表字段 / 字段注释 / 指标定义 / 主键粒度 / 导入历史 / 分析快照   │
└──────────────────────────────────────────────────────────────┘
```

---

# 5. 核心分析链路

```text
1. 用户输入 SQL
        ↓
2. 前端提交 SQL、方言、默认 catalog / schema
        ↓
3. SqlParseService 调用 SQLGlot 生成 AST
        ↓
4. ScopeResolver 构建作用域模型
        ↓
5. MetadataService 从 SQLite 获取表字段元数据
        ↓
6. NameResolver 执行字段补全、字段消歧、select * 展开
        ↓
7. LineageEngine 生成 LineageIR
        ↓
8. SemanticsAnalyzer 生成 SemanticsReport
        ↓
9. DiagnosticsEngine 生成 DiagnosticsReport
        ↓
10. GraphBuilder 生成 GraphViewModel
        ↓
11. 前端根据视图模式渲染 React Flow 图谱
        ↓
12. SQL 编辑器、图谱、字段注释、口径面板联动展示
```

---

# 6. 五条核心补强设计

## 6.1 补强一：明确禁止 `SQLGlot → React Flow` 直连

### 设计原则

SQLGlot 只是解析层，不是完整产品语义层。React Flow 只是展示层，不是血缘存储模型。

必须引入中间语义层：

```text
AST
  → Scope Model
  → LineageIR
  → SemanticsReport
  → GraphViewModel
```

### 工程收益

| 收益 | 说明 |
|---|---|
| 降低耦合 | 解析器、语义模型、前端图谱互不强依赖 |
| 便于测试 | 可以单独测试 LineageIR 和 SemanticsReport |
| 便于扩展 | 后续支持 SQL diff、OpenLineage、DataHub、报告导出 |
| 便于排查 | 血缘错、口径错、图展示错可以分层定位 |
| 便于换前端 | React Flow 可替换为 G6 / Cytoscape.js，不影响核心引擎 |

---

## 6.2 补强二：增加 ScopeResolver / NameResolver

### 设计目标

字段级血缘准确性的核心不是 AST，而是 **字段归属判断**。

例如：

```sql
select user_id
from order_table a
join user_table b
  on a.user_id = b.user_id;
```

如果 `a` 和 `b` 都存在 `user_id` 字段，系统不能猜测来源，必须识别为字段歧义。

### ScopeResolver 职责

| 能力 | 说明 |
|---|---|
| 表别名解析 | 识别 `order_table a` 中的 `a` |
| CTE 作用域解析 | CTE 名优先于真实表名 |
| 子查询作用域解析 | 派生表字段来自内部 select 输出 |
| 多层作用域管理 | 支持主查询、CTE、子查询、union 分支 |
| 临时输出字段解析 | 识别子查询输出字段和别名 |
| 作用域覆盖规则 | 内层作用域优先，CTE / subquery 优先于 catalog table |

### NameResolver 职责

| 能力 | 说明 |
|---|---|
| 无表名前缀字段消歧 | 依赖 SQLite 字段元数据判断字段来源 |
| `select *` 展开 | 按表字段顺序展开真实字段 |
| `a.*` 展开 | 展开指定表别名下的字段 |
| 字段不存在识别 | 元数据中找不到字段时输出 unknown |
| 字段歧义识别 | 多张表存在同名字段时输出诊断 |
| 输出别名映射 | 建立 `source_col → output_alias` 的关系 |

### 建议目录

```text
backend/app/domain/
├── scope_model.py
├── name_resolution_model.py

backend/app/services/
├── scope_resolver.py
├── name_resolver.py
```

---

## 6.3 补强三：增加 LineageIR 中间表示

### 设计目标

LineageIR 是后端内部稳定血缘模型，用于解耦：

```text
SQLGlot AST
LineageEngine
SemanticsAnalyzer
GraphBuilder
React Flow
```

GraphBuilder 只能消费 LineageIR，不应该直接消费 AST。

### LineageIR 核心内容

```text
LineageIR
├── analysis_id
├── dialect
├── statements
├── scopes
├── lineage_nodes
├── lineage_edges
├── unresolved_references
├── metadata_context
├── semantics
└── diagnostics
```

### lineage_nodes 类型

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

### lineage_edges 类型

```text
projection
alias
expression
aggregation
filter_condition
join_condition
group_by
window_partition
window_order
having
order_by
unknown
```

### 关键设计：直接血缘与影响血缘分离

字段级血缘不能只表达“字段从哪来”，还必须表达“哪些字段影响了结果”。

例如：

```sql
select
    user_id,
    sum(order_amt) as gmv
from order_table
where dt = '2026-05-01'
group by user_id;
```

应该分成：

| 类型 | 示例 | 含义 |
|---|---|---|
| 直接血缘 | `order_amt → gmv` | 输出字段由哪个字段计算得到 |
| 粒度影响 | `user_id → group_by` | 结果按什么粒度聚合 |
| 过滤影响 | `dt → filter_condition` | 哪些条件影响结果范围 |

### 工程收益

| 收益 | 说明 |
|---|---|
| 可测试 | 可以用 Golden Case 直接断言 IR |
| 可复用 | Graph、Diff、Export、AI Review 都可复用 |
| 可扩展 | 后续可映射 OpenLineage / DataHub |
| 可排查 | 判断错误发生在解析、作用域、血缘还是图展示层 |

---

## 6.4 补强四：增加 SemanticsReport 结构化口径模型

### 设计目标

口径分析不能只是自然语言描述，需要结构化输出，回答：

```text
当前 SQL 最终结果是按什么粒度、什么范围、什么过滤条件、什么指标公式算出来的？
```

### SemanticsReport 核心内容

```text
SemanticsReport
├── query_type
├── input_objects
├── output_objects
├── result_grain
├── filters
├── metrics
├── joins
├── aggregations
├── windows
├── dedup_logic
├── time_range
├── partition_filters
└── risks
```

### 口径分析维度

| 维度 | 输出内容 |
|---|---|
| 查询类型 | select、insert、create table as select、create view |
| 输入输出对象 | 来源表、目标表、CTE、子查询 |
| 最终粒度 | group by、distinct、window partition |
| 统计范围 | where、having、分区条件、时间范围 |
| 指标公式 | sum、count、avg、count distinct、case when |
| join 关系 | join 类型、join key、主从表、基数风险 |
| 去重逻辑 | distinct、row_number、group by |
| 窗口逻辑 | partition by、order by、row_number、rank |
| 风险说明 | join 放大、粒度混杂、无分区过滤、字段歧义 |

### 工程收益

| 收益 | 说明 |
|---|---|
| 可前端展示 | SemanticsPanel 可以直接渲染结构化结果 |
| 可测试 | 可以对 result_grain、metrics、filters 做断言 |
| 可扩展 | 后续支持 SQL 口径对比、指标一致性校验 |
| 可解释 | 让用户理解 SQL 结果是如何计算出来的 |

---

## 6.5 补强五：前端图谱支持多视图，而不是一张全量图

### 设计目标

复杂 SQL 不能把所有节点一次性画出来。真实数仓 SQL 中可能同时存在：

```text
表
字段
表达式
case when
filter
join
group by
having
window
CTE
subquery
diagnostics
```

如果全部展示在一张图里，图谱会不可读。

因此前端必须支持多视图。

### 推荐视图模式

| 视图 | 用途 |
|---|---|
| 表级视图 | 快速看输入表、输出表、CTE、子查询之间的关系 |
| 字段级视图 | 查看输出字段来自哪些源字段 |
| 表达式视图 | 查看 sum、case when、window、function 的加工过程 |
| 口径视图 | 查看过滤、分组、join、去重、窗口对结果的影响 |
| 诊断视图 | 高亮未知字段、歧义字段、join 风险、分区风险 |

### 多视图实现原则

```text
LineageIR
  → GraphViewModel
      ├── table_view
      ├── column_view
      ├── expression_view
      ├── semantics_view
      └── diagnostics_view
  → React Flow
```

### 图谱交互能力

| 能力 | 说明 |
|---|---|
| 节点拖拽 | 手动调整图谱结构 |
| 自动布局 | 一键整理复杂血缘图 |
| 节点折叠 | 折叠上游、下游、CTE、表达式细节 |
| 路径高亮 | 点击字段后高亮完整上游 / 下游路径 |
| 搜索定位 | 按表名、字段名、CTE 名快速定位 |
| 边类型过滤 | 只看字段来源、过滤影响、join 依赖等 |
| 节点详情抽屉 | 展示字段注释、表达式、来源表、风险说明 |
| SQL 联动 | 点击图节点定位 SQL；点击 SQL 字段定位图节点 |
| 导出能力 | 导出图片、JSON、分析报告 |
| Diff 模式 | 对比 SQL 修改前后的血缘变化 |

---

# 7. 前端工作台设计

## 7.1 页面整体布局

```text
┌────────────────────────────────────────────────────────────┐
│ Header：项目空间 / 方言 / 解析 / 格式化 / 导入元数据 / 导出 │
├───────────────────────┬────────────────────────────────────┤
│ Monaco SQL Editor     │ React Flow Lineage Canvas           │
│ - SQL 高亮            │ - 表级 / 字段级 / 表达式级 / 口径级切换│
│ - 表字段补全          │ - 拖拽 / 缩放 / 折叠 / 自动布局       │
│ - hover 注释          │ - 路径高亮 / 搜索 / 过滤              │
│ - diagnostics 标记    │ - 诊断结果叠加                       │
├───────────────────────┼────────────────────────────────────┤
│ SQL Outline / AST     │ Semantics / Diagnostics / Metadata  │
└───────────────────────┴────────────────────────────────────┘
```

## 7.2 前端核心模块

```text
frontend/
├── src/
│   ├── app/
│   ├── pages/
│   │   └── Workbench/
│   ├── components/
│   │   ├── SqlEditor/
│   │   ├── LineageCanvas/
│   │   ├── GraphViewSwitcher/
│   │   ├── MetadataPanel/
│   │   ├── MetadataImport/
│   │   ├── ImportPreview/
│   │   ├── SemanticsPanel/
│   │   ├── DiagnosticsPanel/
│   │   └── Toolbar/
│   ├── stores/
│   ├── services/
│   ├── types/
│   └── utils/
```

## 7.3 SQL 编辑器能力

| 能力 | 说明 |
|---|---|
| SQL 高亮 | 支持 Hive / Spark / StarRocks 等方言 |
| SQL 格式化 | 基于 SQLGlot 统一格式化 |
| 表字段补全 | 从 SQLite 元数据获取表名、字段名 |
| 字段 hover | 展示字段类型、注释、来源表 |
| 错误提示 | 展示解析错误、未知字段、未知表、字段歧义 |
| 大纲视图 | 展示 CTE、子查询、输出字段、来源表 |
| SQL 与图谱联动 | 编辑器选中字段后高亮图节点 |
| 重写辅助 | `select *` 展开、字段裁剪、CTE 简化、别名规范化 |

---

# 8. JSON 元数据导入设计

## 8.1 功能目标

前端页面提供 JSON 元数据导入功能，用户可以上传或粘贴 JSON 元数据，系统校验后将表字段信息加载到 SQLite 元数据仓库中，并对已有表字段做更新。

## 8.2 导入流程

```text
用户上传 / 粘贴 JSON
        ↓
前端进行基础 JSON 格式校验
        ↓
提交后端进行结构校验和业务校验
        ↓
生成导入预览
        ↓
展示新增表、新增字段、更新字段、疑似过期字段
        ↓
用户确认导入
        ↓
后端执行事务化 upsert
        ↓
更新 SQLite 元数据仓库
        ↓
写入导入历史
        ↓
前端刷新元数据搜索、字段补全、字段注释
```

## 8.3 导入策略

| 场景 | 策略 |
|---|---|
| 表不存在 | 新增表元数据 |
| 表已存在 | 更新表注释、表类型、扩展属性 |
| 字段不存在 | 新增字段 |
| 字段已存在 | 更新字段类型、注释、分区标识、扩展属性 |
| JSON 未包含旧字段 | 默认保留旧字段，并标记为本次未出现 |
| 字段名大小写差异 | 按配置决定是否大小写敏感 |
| 导入失败 | 整体事务回滚 |
| 导入成功 | 写入导入历史，刷新前端元数据缓存 |

## 8.4 元数据导入组件

```text
MetadataImport/
├── JsonUploadPanel
├── JsonPastePanel
├── JsonValidateResult
├── ImportPreviewTable
├── ImportConflictPanel
├── ImportHistoryPanel
└── ImportResultSummary
```

---

# 9. 后端服务设计

## 9.1 后端核心链路

```text
AnalyzeController
  ↓
AnalysisOrchestrator
  ↓
SqlParseService
  ↓
ScopeResolver
  ↓
NameResolver
  ↓
MetadataService
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

## 9.2 后端目录

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── domain/
│   │   ├── ast_model.py
│   │   ├── sql_model.py
│   │   ├── scope_model.py
│   │   ├── name_resolution_model.py
│   │   ├── metadata_model.py
│   │   ├── metadata_import_model.py
│   │   ├── lineage_ir.py
│   │   ├── semantics_model.py
│   │   ├── diagnostics_model.py
│   │   └── graph_view_model.py
│   ├── services/
│   │   ├── analysis_orchestrator.py
│   │   ├── sql_parse_service.py
│   │   ├── scope_resolver.py
│   │   ├── name_resolver.py
│   │   ├── metadata_service.py
│   │   ├── metadata_import_service.py
│   │   ├── lineage_engine.py
│   │   ├── expression_lineage_engine.py
│   │   ├── semantics_analyzer.py
│   │   ├── diagnostics_engine.py
│   │   ├── graph_builder.py
│   │   └── rewrite_service.py
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
│   └── config/
```

## 9.3 后端模块职责

| 模块 | 核心职责 | 不负责什么 |
|---|---|---|
| AnalysisOrchestrator | 编排完整 SQL 分析流程 | 不做具体解析细节 |
| SqlParseService | SQLGlot AST、格式化、方言解析 | 不查 SQLite |
| ScopeResolver | CTE、子查询、别名、作用域归属 | 不生成前端节点 |
| NameResolver | 字段消歧、字段补全、`select *` 展开 | 不关心 UI 布局 |
| MetadataService | 表字段、注释、主键、粒度、指标定义 | 不解析 SQL |
| MetadataImportService | JSON / DDL / CSV 导入、预览、事务 upsert | 不参与 SQL 解析 |
| LineageEngine | 生成字段、表达式、子查询血缘 IR | 不关心 React Flow |
| SemanticsAnalyzer | 粒度、过滤、join、聚合、窗口、口径解释 | 不做字段补全 |
| DiagnosticsEngine | 错误、歧义、风险、修复建议 | 不改写 SQL |
| GraphBuilder | LineageIR → GraphViewModel | 不解析 SQL |
| RewriteService | 格式化、`select *` 展开、字段裁剪建议 | 不写元数据 |

---

# 10. SQLite 元数据仓库设计

SQLite 在本项目中承担轻量级本地元数据仓库角色。

## 10.1 需要维护的元数据对象

| 元数据对象 | 用途 |
|---|---|
| 库表信息 | 识别 SQL 中引用的真实表 |
| 字段信息 | 支持字段级血缘、字段补全、字段消歧 |
| 字段注释 | 支持前端 hover、字段解释、业务理解 |
| 分区字段 | 支持分区过滤风险检测 |
| 主键 / 唯一键 / 业务 key | 支持 join 风险判断 |
| 表粒度信息 | 支持结果粒度分析 |
| 指标定义 | 支持指标口径识别和解释 |
| 导入历史 | 支持 JSON 导入追踪和问题回溯 |
| 分析历史 | 支持 SQL 分析结果复用和版本对比 |
| 诊断事件 | 支持问题排查和质量分析 |

## 10.2 建议维护的逻辑表

| 逻辑表 | 用途 |
|---|---|
| catalog_tables | 库、表、表注释、表类型、owner |
| catalog_columns | 字段名、类型、注释、是否分区、字段顺序 |
| table_keys | 主键、唯一键、业务 key |
| table_grains | 表粒度说明 |
| metrics | 指标名、公式、口径描述 |
| metric_columns | 指标依赖字段 |
| import_batches | 元数据导入批次 |
| import_changes | 每次导入新增、更新、缺失字段 |
| analysis_history | SQL 解析历史 |
| analysis_snapshots | 血缘图和口径分析结果快照 |
| diagnostic_events | 解析失败和风险记录 |

---

# 11. 诊断与风险提示设计

## 11.1 诊断目标

诊断模块不是简单提示“解析失败”，而是告诉用户：

```text
哪里错了
为什么错
会带来什么风险
应该怎么修
```

## 11.2 SQL 诊断类型

| 类型 | 说明 |
|---|---|
| 语法解析失败 | SQLGlot 无法解析当前 SQL |
| 未知表 | 元数据仓库中找不到引用表 |
| 未知字段 | 表中找不到引用字段 |
| 字段歧义 | 多张表都有同名字段，但 SQL 未写表别名 |
| `select *` 风险 | 字段来源依赖元数据展开，可能不稳定 |
| join 放大风险 | join key 不唯一或缺少主键配置 |
| 缺少分区过滤 | 大表扫描风险 |
| 聚合粒度不清晰 | group by、distinct、窗口函数粒度混杂 |
| UDF 黑盒风险 | 无法解析 UDF 内部字段语义 |
| 方言兼容风险 | 当前 SQL 使用了目标方言不支持的语法 |

## 11.3 元数据导入诊断类型

| 类型 | 说明 |
|---|---|
| JSON 格式错误 | 上传内容不是合法 JSON |
| 缺少必要信息 | 缺少库名、表名、字段列表等核心信息 |
| 字段重复 | 同一表内存在重复字段 |
| 字段类型异常 | 字段类型为空或明显不合法 |
| 字段大量减少 | 可能误传了不完整元数据 |
| 字段类型变更 | 已有字段类型发生变化，需要用户确认 |
| 注释覆盖 | 已有字段注释将被新注释覆盖 |
| 表名冲突 | 同名表在不同 schema / catalog 下存在歧义 |
| 导入失败回滚 | 写入失败后整体回滚，避免部分写入 |

---

# 12. API 能力范围

本方案不在此阶段展开详细请求 / 响应格式，只定义能力边界。

| API 能力 | 用途 |
|---|---|
| SQL 一体化分析 | SQL 解析、血缘、口径、诊断、图谱模型生成 |
| SQL 格式化 | 基于 SQLGlot 输出统一格式 |
| SQL 重写辅助 | 支持 `select *` 展开、字段裁剪建议 |
| SQL Diff | 对比修改前后血缘和口径变化 |
| 元数据导入预览 | JSON / DDL / CSV 导入前预览变化 |
| 元数据导入提交 | 确认写入 SQLite |
| 表字段搜索 | 支持编辑器补全和元数据面板 |
| 分析历史查询 | 查看历史 SQL 分析结果 |
| 诊断详情查询 | 查看错误、歧义、风险和修复建议 |

---

# 13. 开发阶段规划

## P0：最小可用闭环

目标：先证明核心链路可用。

```text
SQL 输入
→ SQLGlot AST
→ SQLite 元数据读取
→ ScopeResolver / NameResolver 字段消歧
→ 表级血缘
→ 字段级血缘
→ LineageIR
→ GraphViewModel
→ React Flow 展示
→ 字段注释 hover
→ 基础诊断
```

P0 重点不是做复杂交互，而是保证结果正确。

---

## P1：真实数仓 SQL 覆盖

重点支持：

```text
CTE
子查询
join
union all
group by
case when
window function
insert overwrite
create table as select
select * 展开
```

这一阶段必须建立 Golden Case 测试集，否则后续容易回归。

---

## P2：表达式级和口径级增强

重点支持：

```text
sum / count / avg / count distinct
case when 指标
where / having 过滤影响
join key 影响
group by 粒度
window partition / order
row_number 去重
SemanticsReport 结构化输出
```

这阶段开始真正变成 SQL 理解工作台。

---

## P3：前端高级交互

重点支持：

```text
SQL 与图谱双向定位
多视图图谱切换
路径高亮
边类型过滤
节点折叠
自动布局
Diff 模式
导出报告
解析历史
```

---

## P4：平台化扩展

后续再考虑：

```text
Hive Metastore 自动同步
DataHub / OpenMetadata 接入
多项目空间
权限系统
任务级 SQL 批量解析
调度血缘
AI Review
OpenLineage 输出
```

---

# 14. 测试与质量保障

字段级血缘容易出现“图看起来对，但字段来源错”的问题，因此测试体系必须从第一阶段建立。

## 14.1 测试目录

```text
tests/
├── cases/
│   ├── simple_select
│   ├── cte_nested
│   ├── subquery
│   ├── join_ambiguous_column
│   ├── select_star
│   ├── group_by_metric
│   ├── case_when
│   ├── window_function
│   ├── union_all
│   ├── insert_overwrite
│   └── metadata_json_import
├── parser_tests/
├── scope_tests/
├── name_resolution_tests/
├── metadata_tests/
├── metadata_import_tests/
├── lineage_ir_tests/
├── semantics_tests/
├── diagnostics_tests/
├── graph_view_tests/
└── e2e_tests/
```

## 14.2 测试重点

| 测试类型 | 目标 |
|---|---|
| Golden Case | 固定 SQL 输入与期望血缘输出 |
| Scope Test | 验证 CTE、子查询、别名、作用域归属 |
| Name Resolution Test | 验证字段消歧、`select *` 展开、字段歧义 |
| LineageIR Test | 验证内部血缘中间表示稳定 |
| Semantics Test | 验证粒度、过滤、指标、join、窗口等口径分析 |
| Graph Snapshot Test | 防止图节点和边结构意外变化 |
| Metadata Import Test | 验证 JSON 导入、更新、冲突、回滚 |
| Regression Test | 防止新语法支持破坏旧逻辑 |
| E2E Test | 验证 SQL 输入、元数据导入、解析、画布展示完整链路 |

---

# 15. 最终项目目录

```text
sql-lineage-workbench/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── pages/
│   │   │   └── Workbench/
│   │   ├── components/
│   │   │   ├── SqlEditor/
│   │   │   ├── LineageCanvas/
│   │   │   ├── GraphViewSwitcher/
│   │   │   ├── MetadataPanel/
│   │   │   ├── MetadataImport/
│   │   │   ├── ImportPreview/
│   │   │   ├── SemanticsPanel/
│   │   │   ├── DiagnosticsPanel/
│   │   │   └── Toolbar/
│   │   ├── stores/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── domain/
│   │   │   ├── ast_model.py
│   │   │   ├── sql_model.py
│   │   │   ├── scope_model.py
│   │   │   ├── name_resolution_model.py
│   │   │   ├── metadata_model.py
│   │   │   ├── metadata_import_model.py
│   │   │   ├── lineage_ir.py
│   │   │   ├── semantics_model.py
│   │   │   ├── diagnostics_model.py
│   │   │   └── graph_view_model.py
│   │   ├── services/
│   │   │   ├── analysis_orchestrator.py
│   │   │   ├── sql_parse_service.py
│   │   │   ├── scope_resolver.py
│   │   │   ├── name_resolver.py
│   │   │   ├── metadata_service.py
│   │   │   ├── metadata_import_service.py
│   │   │   ├── lineage_engine.py
│   │   │   ├── expression_lineage_engine.py
│   │   │   ├── semantics_analyzer.py
│   │   │   ├── diagnostics_engine.py
│   │   │   ├── graph_builder.py
│   │   │   └── rewrite_service.py
│   │   ├── repositories/
│   │   ├── adapters/
│   │   ├── diagnostics/
│   │   └── config/
│   ├── tests/
│   └── pyproject.toml
│
├── metadata/
│   ├── sqlite/
│   ├── importers/
│   └── samples/
│
├── docs/
│   ├── architecture.md
│   ├── scope-resolution.md
│   ├── lineage-ir.md
│   ├── semantics-report.md
│   ├── graph-view-model.md
│   ├── metadata-import.md
│   ├── frontend-design.md
│   └── development-roadmap.md
│
├── examples/
│   ├── sql/
│   ├── metadata/
│   ├── metadata-json/
│   └── expected/
│
├── scripts/
├── docker/
├── README.md
└── Makefile
```

---

# 16. 最终架构判断

v0.3 之后，本项目的核心架构从：

```text
SQLGlot + 元数据 + React Flow
```

升级为：

```text
SQLGlot
  → ScopeResolver / NameResolver
  → MetadataCatalog
  → LineageIR
  → SemanticsReport
  → DiagnosticsReport
  → GraphViewModel
  → React Flow
```

最终产品形态：

> 一个面向数仓工程师的 SQL Analysis Workbench：既能看字段从哪来，也能看指标怎么算，还能通过 JSON 快速维护元数据，并通过多视图图谱辅助用户分析 SQL 风险和重写 SQL。

最重要的工程边界：

> SQL 解析、作用域解析、元数据查询、血缘推导、口径分析、诊断报告、图谱展示必须分层。不要让 SQLGlot 输出直接进入 React Flow，也不要让前端承担任何血缘推导逻辑。

---

# 17. 参考依据

- SQLGlot 官方文档：SQL parser、transpiler、lineage API。
- FastAPI 官方文档：基于 Python type hints 构建 API。
- Monaco Editor 官方文档：浏览器端编辑器、completion、hover 等智能编辑能力。
- React Flow 官方文档：node-based editor、interactive diagrams。
- 技术方案审阅结果：强调必须补充 ScopeResolver / NameResolver、LineageIR、SemanticsReport、GraphViewModel 和多视图图谱设计。
