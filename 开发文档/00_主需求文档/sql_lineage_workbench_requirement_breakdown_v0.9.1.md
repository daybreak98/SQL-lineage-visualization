# SQL 血缘解析工作台｜需求拆分与整体规划 v0.9.1

> 版本定位：在 v0.9.1 收敛冻结版基础上，合入最终小幅检查建议，形成进入 P0 实施前的冻结小修版主需求文档。  
> 本版原则：不扩展产品范围，不新增大模块，不重排阶段，只合入冻结前会影响 P0/P1 落地的一致性、术语和模型小修。  
> 核心目标：冻结主开发文档，后续工作转入 P0 实施验证、Golden Case、Contract Test 与局部小变动审阅。

---

## 0. 文档说明

### 0.1 本版目标

本项目的核心目标保持不变：

```text
以 SQLGlot + Python + SQLite 为后端核心，
以 Monaco Editor + React Flow 为前端交互核心，
构建一个面向数仓工程师的数据血缘与 SQL 理解工作台。
```

系统需要支持：

```text
SQL 静态解析
→ SQLite 元数据补全
→ 字段归属判断
→ 表级 / 字段级 / 表达式级 / 子查询级血缘
→ 查询口径结构化分析
→ 字段注释接入
→ 诊断与风险提示
→ SQL 编辑器与图谱画布联动
→ 可拖拽、可折叠、可扩展的血缘点线图
```

第一阶段不做真实 SQL 执行引擎，不连接 Hive / Spark / StarRocks 执行查询。

---

### 0.2 主文档收敛原则

当前主文档不再承担审阅纪要、版本差异报告、采纳裁决记录等职责。

后续只允许以下类型内容进入主文档：

| 类型 | 合入原则 |
|---|---|
| 会影响 P0 开发顺序的内容 | 合入主文档 |
| 会影响前后端契约稳定性的内容 | 合入主文档 |
| 会影响血缘语义正确性的实体模型 | 合入主文档 |
| 会影响 Monaco 定位准确性的坐标规范 | 合入主文档 |
| 会影响调试排查的阶段状态字段 | 合入主文档 |
| 复杂实现细节、工具链细节、布局算法细节 | 不进入主文档，拆到后续专题文档 |

---

### 0.3 当前稳定约束摘要

以下约束视为当前主开发文档的稳定基线，后续小变动审阅原则上不再推翻。

| 约束项 | 稳定口径 | 开发影响 |
|---|---|---|
| 后端主链路 | AnalysisOrchestrator 编排式 Pipeline | 每个阶段输入输出可观测、可测试、可降级 |
| 最小表达式抽取 | P0 使用 ProjectionExtractor / MinimalExpressionExtractor | LineageEngine 之前先稳定 select item、alias、literal、简单字段引用 |
| 契约治理 | P0 保留 Pydantic / OpenAPI / 手工 TS 类型 / 基础 Contract Test | 避免前后端字段漂移，但不被完整工具链拖慢 |
| 实体 ID | 区分 table、column、scope、scope_relation、scope_column、output_column、expression、node | 支撑血缘、定位、Graph、diff、快照和折叠状态稳定 |
| SourceLocation | 固定 original_sql + Monaco 1-based line/column + UTF-16 offset | 避免中文别名、跨行表达式、格式化 SQL 导致定位漂移 |
| GraphViewModel | 后端只返回图数据，前端维护 GraphInteractionState | 避免拖拽、折叠、选中状态污染后端分析结果 |
| 降级策略 | unsupported_features + diagnostics_report + stage_statuses + confidence_level | 复杂 SQL 不能伪装成完全成功 |
| 测试体系 | Contract Test + Golden Case + Snapshot Test 横向覆盖 | 每个阶段交付都必须可回归验证 |

## 1. 项目定位

### 1.1 产品定位

```text
SQL Analysis Workbench
= SQL 静态解析
+ SQLite 元数据补全
+ 字段级血缘
+ 表达式抽取
+ 子查询作用域分析
+ 查询口径解释
+ 字段注释增强
+ 诊断提示
+ SQL 与图谱联动
+ 前端交互式血缘画布
```

它不是：

```text
不是真实 SQL 执行平台
不是 Hive / Spark / StarRocks 查询入口
不是只把 SQLGlot lineage 结果直接画出来的 demo
不是完全依赖大模型推断血缘的非确定性系统
```

它应该是：

```text
一个面向数仓工程师的数据血缘与 SQL 理解工作台：
既能看字段从哪来，
也能看指标怎么算，
还能通过元数据、字段注释、诊断和图谱联动帮助用户理解复杂 SQL。
```

---

### 1.2 第一阶段边界

第一阶段重点是最小闭环：

```text
简单 SQL
→ 元数据导入
→ 字段归属判断
→ 基础字段血缘
→ 基础图谱展示
→ 基础诊断提示
→ 契约稳定
```

P0 明确不做：

```text
复杂 CTE 全覆盖
复杂子查询全覆盖
完整 select * 展开
高级 completion / hover
表达式级血缘图谱
完整口径分析
SQL diff
历史快照
真实 SQL 执行
OpenLineage / DataHub 对接
AI Review / 大模型辅助解释
```

---

## 2. 总体推进顺序

### 2.1 推荐阶段顺序

```text
P0：最小可用闭环
R00 → R01 → R02 → R03 → R04a → R04b → R08a → R09a → R05 → R06 → R07 → R08b/R08c → R17

P1：真实 SQL 结构增强
R09b1 → R10 → R11a → R11b/R11c → R09c → R17

P2：表达式血缘与口径分析
R13a → R09b2 → R12 → R13b → R14 → R17

P3：SQL diff 与历史快照
R15 → R16 → R17

P4：平台化扩展
R18
```

---

### 2.2 顺序设计理由

| 顺序 | 原因 |
|---|---|
| R04b 提前到 P0 | AnalysisResult、LineageIR、GraphViewModel 都会被前后端共同消费，契约必须尽早稳定 |
| R08a 早于 R05/R06/R07 | 解析、字段消歧、血缘生成都需要统一诊断码承接异常 |
| R09a 早于图谱与编辑器联动 | SourceLocation 是 SQL 编辑器、诊断定位、图谱点击跳转的共同坐标模型 |
| R05 早于 R06 | 字段血缘必须先解决 Scope / Metadata / Name Resolution，否则 LineageIR 不可信 |
| MinimalExpressionExtractor 早于 LineageEngine | P0 至少要识别 select item、alias、literal、简单字段引用，否则 projection / alias 边不稳定 |
| R07 只消费 LineageIR | GraphBuilder 不直接依赖 SQLGlot AST，避免解析层与 UI 展示层耦合 |
| R09b1 早于 R09c | 先能定位基础 SQL 片段，再做 Monaco 与图谱双向联动 |
| R09b2 放入 P2 | CTE、子查询、union、case when、window 的 range 定位复杂，不阻塞 P1 基础联动 |
| R13a 早于 R12 | 口径分析依赖表达式抽取，不能先写 SemanticsReport 再补表达式能力 |
| R15 早于 R16 | 当前 SQL diff 可不依赖历史表，历史快照 diff 才依赖 R16 |

---

## 3. 总体分层架构

### 3.1 后端编排式 Pipeline

本文档将后端链路固定为 Orchestrator 编排式 Pipeline：

```text
AnalyzeController
  ↓
AnalysisOrchestrator
  ↓
Step 1：SqlParseService / SQLGlotAdapter
  ↓
Step 2：ScopeResolver
  ↓
Step 3：MetadataService / MetadataCatalog
  ↓
Step 4：NameResolver
  ↓
Step 5：ProjectionExtractor / MinimalExpressionExtractor
  ↓
Step 6：LineageEngine
  ↓
Step 7：SemanticsAnalyzer
  ↓
Step 8：DiagnosticsCollector / DiagnosticsEngine
  ↓
Step 9：GraphBuilder
  ↓
Step 10：ContractAssembler
  ↓
AnalysisResult
```

P0 阶段 `SemanticsAnalyzer` 默认不执行：

```text
semantics stage_status = skipped
semantics_report.status = not_supported_in_p0
```

只有当 `include_semantics=true` 且当前阶段已经支持对应口径能力时，`SemanticsAnalyzer` 才进入执行。

### 3.2 Pipeline 关键约束

| 要求 | 说明 |
|---|---|
| 每一步输入输出可序列化 | 便于调试、测试、快照和回归比较 |
| 每一步可独立失败 | 上游失败不一定导致整体 failed，可返回 partial |
| 每一步可产出 diagnostics | 解析错误、元数据缺失、字段歧义、语法不支持都要结构化返回 |
| 每一步不跨层做事 | Parser 不查 SQLite，GraphBuilder 不解析 SQL，前端不推导血缘 |
| Orchestrator 负责组装状态 | 统一维护 status、confidence_level、unsupported_features、stage_statuses、diagnostics |
| DiagnosticsCollector 贯穿全链路 | 各阶段只追加诊断，最终由 DiagnosticsEngine 归并、去重、排序和 level 归一 |

---

### 3.3 MinimalExpressionExtractor 的 P0 边界

P0 不要求完整表达式分析，只要求最小表达式抽取。

| 能力 | P0 要求 |
|---|---|
| select item 识别 | 能识别每个输出字段或输出表达式 |
| alias 识别 | 能识别 `a as b`、`expr as alias` |
| literal 识别 | 能识别常量输出并生成 literal 来源；无法解析时才降级为 unknown |
| 简单字段引用 | 能识别 `select order_no`、`select t.order_no` |
| function wrapper | 能识别 `cast(col as string)`、`nvl(col, '')` 这种简单包裹 |
| 复杂表达式 | P0 可降级，P2 由完整 ExpressionAnalyzer 处理 |

完整 ExpressionAnalyzer 仍属于 P2，用于 aggregate、case when、window function、复杂函数嵌套、指标表达式模型。

---

### 3.4 分层职责边界

| 层 | 主要职责 | 不做什么 |
|---|---|---|
| SQLGlotAdapter | SQL 解析、方言处理、AST 生成、格式化 | 不直接生成 React Flow 节点 |
| ScopeResolver | CTE、子查询、表别名、作用域栈 | 不查询 UI 状态 |
| MetadataService | SQLite 表字段、字段注释、分区字段、业务主键、元数据版本 | 不解析 SQL |
| NameResolver | 字段归属、字段消歧、未知字段识别、select * 展开基础能力 | 不生成图谱布局 |
| ProjectionExtractor / MinimalExpressionExtractor | P0 抽取 select item、alias、literal、简单字段引用 | 不处理完整指标口径 |
| LineageEngine | 基于解析结果生成稳定 LineageIR | 不包含前端拖拽、折叠状态 |
| ExpressionAnalyzer | P2 抽取聚合、case when、窗口函数、复杂函数结构 | 不负责最终自然语言口径解释 |
| SemanticsAnalyzer | 生成 SemanticsReport，解释粒度、过滤、指标、join、去重 | 不修改 SQL |
| DiagnosticsCollector / DiagnosticsEngine | 采集、归并、去重、排序诊断 | 不直接改写 SQL |
| GraphBuilder | 将 LineageIR / SemanticsReport 转为 GraphViewModel | 不消费 SQLGlot AST |
| ContractAssembler | 组装 AnalysisResult 并做契约校验 | 不做具体分析逻辑 |
| 前端 Workbench | Monaco、React Flow、面板、交互状态 | 不承担血缘推导 |

---

## 4. 核心数据模型

### 4.1 AnalysisResult 聚合模型

`AnalysisResult` 是 `/api/sql/analyze` 的唯一主返回模型。

```json
{
  "schema_version": "1.0",
  "analysis_id": "uuid",
  "status": "success | partial | failed",
  "confidence_level": "high | medium | low | unknown",
  "confidence_reasons": [
    "all_tables_resolved",
    "all_columns_resolved"
  ],
  "dialect": "spark",
  "normalized_sql": "select ...",
  "stage_statuses": [],
  "metadata_context": {},
  "unsupported_features": [],
  "lineage_ir": {},
  "semantics_report": {},
  "diagnostics_report": [],
  "graph_view_model": {},
  "source_locations": [],
  "elapsed_ms": 128
}
```

| 字段 | 说明 |
|---|---|
| schema_version | API 响应结构版本 |
| status | 整体分析状态，允许 success / partial / failed |
| confidence_level | 用户可理解的可信等级，不使用伪精确小数作为主展示 |
| confidence_reasons | 可信或不可信的规则原因 |
| stage_statuses | 各分析阶段状态与耗时 |
| unsupported_features | 当前 SQL 中识别到但暂不支持的结构 |
| lineage_ir | 后端内部血缘中间表示 |
| semantics_report | 查询口径报告，P0 可返回 not_supported_in_p0 |
| diagnostics_report | 诊断结果 |
| graph_view_model | 前端图谱视图模型 |
| source_locations | SQL 源码位置映射 |
| elapsed_ms | 整体分析耗时 |

numeric confidence 如需保留，只能作为内部实验指标，不作为 P0 用户主展示字段。

---

### 4.2 stage_statuses 模型

```json
{
  "stage": "parse | scope_resolution | metadata_lookup | name_resolution | projection_extraction | lineage_build | semantics | diagnostics | graph_build | contract_assembly",
  "status": "success | partial | failed | skipped",
  "elapsed_ms": 12,
  "diagnostic_codes": ["UNKNOWN_COLUMN"]
}
```

约束：

```text
1. stage_statuses 只描述阶段状态，不承载详细诊断文案。
2. 详细错误仍进入 diagnostics_report。
3. skipped 用于上游 failed 后未执行的阶段。
4. elapsed_ms 是阶段耗时，不要求 P0 做复杂 tracing。
5. P0 中 semantics 阶段默认为 skipped，除非显式开启且当前能力已支持。
```

---

### 4.3 Stable Entity ID 规范

系统必须区分物理实体、SQL 作用域实体、图节点实体和前端交互状态。

| 实体 | ID 模式 | 示例 |
|---|---|---|
| 物理表 | `table:<catalog>.<schema>.<table>` | `table:default.ihotel_default.mdw_order_v3_international` |
| 物理字段 | `column:<catalog>.<schema>.<table>.<column>` | `column:default.ihotel_default.mdw_order_v3_international.order_no` |
| SQL 作用域 | `scope:<scope_path_hash>` | `scope:main` / `scope:cte:base_order` |
| 作用域关系引用 | `scope_relation:<scope_id>:<alias_or_relation>` | `scope_relation:scope:main:a` |
| 作用域输出字段 | `scope_column:<scope_id>:<column_or_alias>` | `scope_column:scope:cte:base_order:order_no` |
| 最终输出字段 | `output_column:<scope_id>:<alias_or_ordinal>` | `output_column:scope:main:paid_gmv` |
| 表达式 | `expression:<scope_id>:<expr_hash>` | `expression:scope:main:8f2a...` |
| 图节点 | `node:<view_mode>:<hash(entity_id)>` | `node:column:ab12...` |
| 图边 | `edge:<view_mode>:<hash(source_entity_id,target_entity_id,edge_type)>` | `edge:column:9a81...` |
| 交互状态 | `selected:<node_id>` / `collapsed:<node_id>` | `collapsed:node:column:ab12...` |

关键约束：

```text
1. 物理字段 entity_id 必须来自 MetadataContext。
2. FROM / JOIN 中的表、CTE、子查询别名必须先建模为 scope_relation，再映射到物理 table、CTE scope 或 subquery scope。
3. 字段引用应优先解析为 scope_column，再通过 scope_relation 回溯到物理 column 或上游 scope_column。
4. CTE / 子查询 / 输出字段必须使用 scope_column 或 output_column，不能伪装成物理 column。
5. GraphViewModel 节点必须同时包含 node_id 与 entity_id。
6. SourceLocation 可以绑定 physical column、scope_relation、scope_column、output_column 或 expression。
7. DiagnosticsReport 的 related_entity_ids 引用 entity_id，不引用前端 interaction_id。
8. SQL diff 和历史快照优先按 entity_id 比较，不能按 label、node_id 或前端坐标比较。
9. 如果名称中包含空格、点号、反引号、中文或特殊字符，entity_id 的名称段应使用 normalized_name 或 hash_name；原始展示名保留在 label / display_name 字段中。
```

---

### 4.4 LineageIR 模型

`LineageIR` 只表达血缘语义，不表达前端展示状态。

```json
{
  "ir_version": "1.0",
  "nodes": [],
  "edges": [],
  "scopes": [],
  "unresolved_references": [],
  "partial": false,
  "confidence_level": "high | medium | low | unknown",
  "confidence_reasons": []
}
```

#### 节点类型

```text
statement
scope
table
cte
subquery
column
scope_column
output_column
expression
metric
filter
join
group_by
window
literal
unknown
```

#### 边类型

P0 强制支持：

```text
projection
alias
unknown
```

P1+ / P2 扩展支持：

```text
expression
aggregation
filter_condition
join_condition
group_by
window_partition
window_order
having
order_by
union_mapping
```

#### 重要原则

字段级血缘要区分：

| 类型 | 示例 | 含义 |
|---|---|---|
| 直接血缘 | `order_amt → gmv` | 输出字段由哪个字段计算得到 |
| 过滤影响 | `dt → filter_condition` | 哪些字段影响统计范围 |
| 粒度影响 | `user_id → group_by` | 哪些字段决定结果粒度 |
| Join 影响 | `a.user_id / b.user_id → join_condition` | 哪些字段影响记录匹配关系 |

常量输出处理原则：

```text
1. literal 用于表达常量输出，例如 1 as is_valid、'hotel' as biz_type。
2. unknown 只用于无法解析、无法归属或暂不支持的结构，不用于可确定的常量来源。
```

---

### 4.5 SourceLocation 模型

`SourceLocation` 从 P0 开始定义模型，P1 做基础精准提取与双向联动，P2 扩展复杂结构定位。

```json
{
  "location_id": "loc_001",
  "entity_id": "column:default.ihotel_default.mdw_order_v3_international.order_no",
  "entity_type": "column | table | scope_relation | scope_column | output_column | expression | filter | join | cte | subquery | diagnostic | alias",
  "source_sql_id": "sql_original_hash",
  "source_text_kind": "original_sql",
  "start_line": 3,
  "start_col": 8,
  "end_line": 3,
  "end_col": 16,
  "line_col_base": "one_based",
  "column_encoding": "utf16_code_unit",
  "start_offset_utf16": 42,
  "end_offset_utf16": 50,
  "raw_text": "order_no",
  "range_type": "exact | approximate | inferred | synthetic | unavailable",
  "origin": "sqlglot | tokenizer | resolver | metadata | synthetic",
  "confidence_level": "high | medium | low | unknown"
}
```

#### 坐标规范

```text
1. Monaco Editor 的定位以 1-based line/column 为主。
2. column 按 UTF-16 code unit 计算。
3. offset 固定使用 UTF-16 code unit，并命名为 start_offset_utf16 / end_offset_utf16。
4. SourceLocation 默认绑定 original_sql，不绑定格式化后的 normalized_sql。
5. 如果用户点击“格式化 SQL”，必须重新分析或重新生成 SourceLocation。
```

#### 分阶段策略

| 阶段 | 能力 |
|---|---|
| P0 / R09a | 定义模型，允许粗粒度、synthetic、unavailable |
| P1 / R09b1 | 覆盖 select / from / where / group by / order by 的字段、表、别名位置 |
| P1 / R09c | Monaco Editor 与 React Flow 图谱双向定位 |
| P2 / R09b2 | 覆盖 CTE、子查询、join condition、union、case when、window function 的 range 定位 |

---

### 4.6 GraphViewModel 与 GraphInteractionState 分离

#### 后端 GraphViewModel

后端只返回可渲染、可测试、可快照的图数据。

```json
{
  "view_mode": "column",
  "supported_view_modes": ["table", "column", "expression", "semantics", "diagnostics"],
  "nodes": [
    {
      "id": "node:column:hash_xxx",
      "entity_id": "column:default.ihotel_default.mdw_order_v3_international.order_no",
      "scope_entity_id": "scope:main",
      "node_type": "column",
      "label": "order_no",
      "source_location_id": "loc_001",
      "metadata_ref": {
        "catalog": "default",
        "schema": "ihotel_default",
        "table": "mdw_order_v3_international",
        "column": "order_no"
      }
    }
  ],
  "edges": [
    {
      "id": "edge:column:hash_xxx",
      "edge_type": "projection | alias | expression | aggregation | filter_condition | join_condition | group_by | unknown",
      "source": "node:column:src_hash",
      "target": "node:column:dst_hash",
      "source_entity_id": "column:default.ihotel_default.mdw_order_v3_international.order_no",
      "target_entity_id": "output_column:scope:main:order_no",
      "source_location_id": "loc_002"
    }
  ]
}
```

#### 前端 GraphInteractionState

前端自行维护交互状态，不回写后端主模型。

```json
{
  "selected_node_ids": [],
  "selected_edge_ids": [],
  "collapsed_node_ids": [],
  "collapsed_entity_ids": [],
  "highlighted_path_ids": [],
  "viewport": {
    "x": 0,
    "y": 0,
    "zoom": 1
  },
  "layout_mode": "elk | manual"
}
```

运行时可以使用 `node_id` 控制当前画布状态；跨分析复用、工作区恢复、历史快照恢复时应优先使用 `entity_id`。

#### 拆分原因

| 拆分点 | 原因 |
|---|---|
| GraphViewModel | 是后端分析产物，应可测试、可快照、可 diff |
| GraphInteractionState | 是用户当前 UI 操作状态，应由前端维护 |
| 不混放 | 否则后端快照、历史 diff、前端拖拽状态会互相污染 |

---

### 4.7 DiagnosticsReport 模型

```json
{
  "code": "AMBIGUOUS_COLUMN",
  "level": "error | warning | info",
  "message": "字段 user_id 在多个输入表中同时存在",
  "suggestion": "请显式写成 a.user_id 或 b.user_id",
  "source_location_id": "loc_002",
  "related_entity_ids": ["table:default.a", "table:default.b"]
}
```

#### P0 诊断码

```text
PARSE_ERROR
UNKNOWN_TABLE
UNKNOWN_COLUMN
AMBIGUOUS_COLUMN
METADATA_VERSION_MISMATCH
METADATA_IMPORT_INVALID_JSON
METADATA_IMPORT_DUPLICATE_COLUMN
SOURCE_LOCATION_UNAVAILABLE
UNSUPPORTED_DIALECT_FEATURE
PARTIAL_ANALYSIS
```

#### P1+ 诊断码

```text
STAR_EXPANSION_FAILED
JOIN_CARDINALITY_UNKNOWN
JOIN_EXPANSION_RISK
MISSING_PARTITION_FILTER
UNKNOWN_GRAIN
DUPLICATE_ALIAS
UNSUPPORTED_CTE_PATTERN
UNSUPPORTED_SUBQUERY_PATTERN
UNSUPPORTED_WINDOW_PATTERN
```

---

### 4.8 SemanticsReport 模型

`SemanticsReport` 用于回答“当前查询结果怎么算”。P0 默认不执行 `SemanticsAnalyzer`，返回 `not_supported_in_p0`；P2 开始强制证据链。

```json
{
  "status": "success | partial | not_supported_in_p0",
  "result_grain": {
    "type": "group_by | distinct | detail | unknown",
    "columns": [],
    "evidence_refs": ["expr:group_by:user_id", "loc_021"]
  },
  "filters": [
    {
      "filter_id": "filter_001",
      "expression_text": "dt = '2026-05-01'",
      "source_columns": ["column:default.table.dt"],
      "source_location_id": "loc_010",
      "evidence_refs": ["loc_010"]
    }
  ],
  "metrics": [],
  "joins": [],
  "dedup_rules": [],
  "window_functions": [],
  "risks": []
}
```

#### 口径分析维度

| 维度 | 说明 |
|---|---|
| 结果粒度 | group by、distinct、窗口 partition、明细粒度 |
| 统计范围 | where、having、分区条件、时间条件 |
| 指标公式 | sum、count、avg、count distinct、case when |
| Join 关系 | join 类型、join key、主从关系、潜在放大 |
| 去重逻辑 | distinct、row_number、group by、max/min 保留 |
| 风险说明 | join 放大、粒度混杂、无分区过滤、字段歧义 |

#### 证据链原则

```text
1. SemanticsReport 中每个确定性结论都必须能追溯到 ExpressionModel、LineageIR、MetadataContext 或 SourceLocation。
2. 如果缺少证据，输出 unknown / partial，不输出确定口径。
3. P0 只预留模型，P2 开始作为验收项。
```

---

### 4.9 MetadataContext 模型

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

所有分析结果必须带 `metadata_context`，避免同一 SQL 在不同元数据版本下结果不同却无法追踪。

---

## 5. API 与契约治理

### 5.1 R04a：`/api/sql/analyze` 最小接口

#### 请求结构

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

#### 响应要求

P0 可以返回 `partial`，也允许部分数组为空，但结构必须稳定。

| 字段 | P0 要求 |
|---|---|
| schema_version | 必须返回 |
| analysis_id | 必须返回 |
| status | 必须返回，允许 success / partial / failed |
| confidence_level | 必须返回 |
| confidence_reasons | 必须返回，允许空数组 |
| stage_statuses | 必须返回，至少包含已执行阶段 |
| elapsed_ms | 必须返回 |
| metadata_context | 必须返回 |
| diagnostics_report | 必须返回，允许空数组 |
| lineage_ir | 必须返回，允许部分字段为空 |
| graph_view_model | 必须返回，允许 nodes / edges 为空 |
| semantics_report | 可返回 not_supported_in_p0 |
| source_locations | 可返回粗粒度、synthetic 或空数组 |
| unsupported_features | 必须返回，允许空数组 |

---

### 5.2 R04b：Contract Schema 与类型生成

#### 目标

为 `AnalysisResult`、`LineageIR`、`SemanticsReport`、`DiagnosticsReport`、`GraphViewModel`、`SourceLocation` 建立统一契约，避免前后端字段漂移。

#### 分阶段边界

| 阶段 | 必须做 | 暂缓 |
|---|---|---|
| P0 | Pydantic Model、FastAPI OpenAPI、schema_version、前端手工 TS 类型、基础 Contract Test | 自动 TS 类型生成、完整 schema snapshot、跨版本兼容矩阵 |
| P1 | JSON Schema 导出、OpenAPI TypeScript 自动生成、核心 Contract Snapshot | 复杂兼容策略 |
| P2+ | 跨版本兼容测试、历史快照 schema migration | - |

#### P0 验收标准

| 标准 | 说明 |
|---|---|
| 后端有 Pydantic Model | API 响应由模型约束 |
| OpenAPI 可访问 | FastAPI 自动暴露基础契约 |
| 前端有 TS 类型 | 可先手工维护，不要求自动生成 |
| Contract Test 可运行 | 至少验证 `/api/sql/analyze` 成功、partial、failed 三类响应结构 |
| 字段漂移可发现 | 删除 / 改名 / 必填字段缺失会导致测试失败 |

---

## 6. SQLite 元数据仓库

### 6.1 元数据导入标准格式

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

### 6.2 SQLite 核心表

| 表 | 说明 |
|---|---|
| metadata_versions | 元数据版本记录 |
| catalog_tables | 表信息，包含 catalog、schema_name、table_name、normalized_table_name、comment、source_type、quality_status |
| catalog_columns | 字段信息，包含 table_id、column_name、normalized_column_name、data_type、comment、ordinal、is_partition、quality_status |
| import_jobs | 导入任务记录 |
| import_errors | 导入失败明细 |
| analysis_history | P3 引入，保存分析历史 |
| analysis_snapshots | P3 引入，保存 AnalysisResult 快照 |

### 6.2.1 推荐唯一约束与索引

```text
unique(metadata_version, catalog, schema_name, normalized_table_name)
unique(metadata_version, table_id, normalized_column_name)
index(metadata_version, normalized_table_name)
index(metadata_version, table_id)
index(metadata_version, normalized_column_name)
```

### 6.3 P0 导入规则

| 规则 | 要求 |
|---|---|
| schema_version | 必填 |
| tables | 必填且非空 |
| table schema/name | 至少 schema + name 必填 |
| normalized_table_name | 按 case_sensitive 策略生成 |
| columns | 必填且非空 |
| column.name | 必填 |
| normalized_column_name | 按 case_sensitive 策略生成 |
| column.data_type | 建议必填，允许 unknown 但产生 warning |
| column.comment | 可选 |
| 导入方式 | 支持前端粘贴 JSON / 上传 JSON 文件 |
| 冲突处理 | 同一 metadata_version 内同表同字段 upsert 或报错需明确 |

---

## 7. 需求拆分总表 v0.9.1

| ID | 需求 | 阶段 | 前端 | 后端 | 数据库 | 核心说明 |
|---|---|---|---:|---:|---:|---|
| R00 | 项目初始化与工程骨架 | P0 | 是 | 是 | 否 | 建立前后端工程、启动脚本、代码规范 |
| R01 | SQLite 元数据仓库初始化 | P0 | 否 | 是 | 是 | 建立元数据存储与版本上下文 |
| R02 | JSON 元数据导入 | P0 | 是 | 是 | 是 | 支持标准 JSON 导入并更新 SQLite |
| R03 | SQL 编辑器基础能力 | P0 | 是 | 是 | 否 | Monaco 基础输入、格式化、提交分析 |
| R04a | SQL 分析 API 最小契约 | P0 | 是 | 是 | 否 | `/api/sql/analyze` 请求与响应结构 |
| R04b | Contract Schema 与类型对齐 | P0 | 是 | 是 | 否 | Pydantic / OpenAPI / 手工 TS 类型 / 基础 Contract Test |
| R08a | DiagnosticCode 诊断模型 | P0 | 是 | 是 | 否 | 错误码、级别、建议、定位引用 |
| R09a | SourceLocation 数据模型 | P0 | 是 | 是 | 否 | 固定 Monaco/UTF-16 坐标规范，允许粗粒度 / synthetic |
| R05 | ScopeResolver / MetadataService / NameResolver | P0 | 否 | 是 | 是 | 作用域解析、元数据补全、字段消歧 |
| R06 | 基础 LineageIR | P0 | 否 | 是 | 否 | 简单 SQL 字段血缘中间表示，P0 强制 projection / alias / literal / unknown |
| R07 | 基础 GraphViewModel 与 React Flow 画布 | P0 | 是 | 是 | 否 | 基础节点边渲染，GraphViewModel 保留 entity_id，不含交互状态 |
| R08b | Diagnostics 生成 | P0 | 否 | 是 | 否 | unknown table / column / ambiguous column 等诊断 |
| R08c | Diagnostics 前端面板 | P0 | 是 | 否 | 否 | 展示错误、警告、建议 |
| R09b1 | SourceLocation 基础精准提取 | P1 | 否 | 是 | 否 | 覆盖 select/from/where/group by/order by 的字段、表、别名位置 |
| R10 | CTE / 子查询 / Join / Union 结构增强 | P1 | 部分 | 是 | 否 | 支持真实数仓 SQL 常见结构，并明确降级边界 |
| R11a | select * / a.* 展开 | P1 | 部分 | 是 | 是 | 依赖元数据展开字段 |
| R11b | Monaco Completion | P1 | 是 | 是 | 是 | 表名、字段名、别名补全 |
| R11c | Monaco Hover | P1 | 是 | 是 | 是 | 字段注释、血缘摘要、诊断 hover |
| R09c | SQL 与图谱双向定位 | P1 | 是 | 是 | 否 | 点击 SQL 高亮图谱，点击图谱定位 SQL |
| R13a | ExpressionAnalyzer 基础能力 | P2 | 否 | 是 | 否 | 抽取表达式、聚合、case when、窗口函数结构 |
| R09b2 | SourceLocation 复杂结构提取 | P2 | 否 | 是 | 否 | 覆盖 CTE、子查询、join condition、union、case when、window function 的 range 定位 |
| R12 | SemanticsReport 查询口径分析 | P2 | 是 | 是 | 否 | 粒度、过滤、指标、join、去重、风险；确定性结论必须有 evidence_refs |
| R13b | 表达式级血缘图谱 | P2 | 是 | 是 | 否 | expression 节点和 expression edge 可视化 |
| R14 | 多视图图谱 | P2 | 是 | 是 | 否 | table / column / expression / semantics / diagnostics 视图切换 |
| R15 | 当前 SQL diff | P3 | 是 | 是 | 否 | 对比两段 SQL 的血缘、字段、口径变化 |
| R16 | 分析历史与快照 | P3 | 是 | 是 | 是 | 保存 SQL、AnalysisResult、GraphViewModel 快照 |
| R17 | 横向测试体系 | 全阶段 | 是 | 是 | 是 | 每个需求绑定单测、集成、Golden Case、快照测试 |
| R18 | 平台化扩展预留 | P4 | 是 | 是 | 是 | Hive Metastore、OpenLineage、权限、多项目、批量分析 |

---

## 8. 阶段规划与验收标准

### 8.1 P0：最小可用闭环

#### 目标

```text
用户可以导入一份表字段元数据，
输入一段简单 SQL，
系统能返回基础字段血缘、基础诊断、基础图谱，
并保证 API 契约稳定。
```

#### 范围

```text
R00 → R01 → R02 → R03 → R04a → R04b → R08a → R09a → R05 → R06 → R07 → R08b/R08c → R17
```

#### 验收标准

| 标准 | 说明 |
|---|---|
| 元数据可导入 | JSON 元数据可写入 SQLite |
| 简单 SQL 可解析 | 单表 select 可完成字段归属 |
| MinimalExpressionExtractor 可用 | 能识别 select item、alias、literal、简单字段引用；常量输出不进入 unknown |
| 基础血缘可返回 | source column → output column |
| 基础图谱可展示 | React Flow 展示表 / 字段节点和边 |
| GraphViewModel 保留 entity_id | node / edge 不只依赖 label 或 node_id |
| 基础诊断可展示 | 未知表、未知字段、字段歧义可结构化提示 |
| API 契约稳定 | AnalysisResult 结构通过基础 Contract Test |
| SourceLocation 可引用 | 即使粗粒度，也能被 diagnostics / graph 引用 |
| stage_statuses 可观测 | 每个阶段有 success / partial / failed / skipped |
| Partial 可解释 | 不支持的结构进入 unsupported_features，不伪装成 success |

---

### 8.2 P1：真实 SQL 结构增强

#### 目标

```text
覆盖数仓 SQL 中最常见的 CTE、子查询、Join、Union、select *，
并完成 SQL 编辑器与图谱之间的基础双向联动。
```

#### 范围

```text
R09b1 → R10 → R11a → R11b/R11c → R09c → R17
```

#### R10 能力边界

| 结构 | P1 必须支持 | P1 允许降级 |
|---|---|---|
| CTE | 非递归 CTE、多个 CTE、CTE 间简单依赖 | recursive CTE 返回 unsupported |
| 子查询 | from 子查询、简单 select 子查询 | 复杂 correlated subquery 返回 partial |
| Join | inner / left / right / full join 的字段归属和 join key 抽取 | 真实数据基数不在 P1 强判断 |
| Union All | 同名输出字段多来源合并 | 复杂类型对齐、union distinct 语义可 partial |
| Lateral / explode | 识别并诊断 | 不要求精确字段血缘 |

#### 验收标准

| 标准 | 说明 |
|---|---|
| CTE 可解析 | CTE 输出字段可追溯到内部来源 |
| 子查询可解析 | 派生表字段能映射到内部 select 输出 |
| Join 字段消歧 | 多表同名字段能识别歧义或明确归属 |
| select * 可展开 | 单表和别名星号可依赖元数据展开 |
| Completion 可用 | Monaco 能补全表名、字段名、别名 |
| Hover 可用 | Hover 显示字段注释、来源、诊断摘要 |
| 双向定位可用 | SQL 片段与图节点能互相跳转 |
| 降级边界清晰 | unsupported_features 和 diagnostics_report 能说明未支持结构 |

---

### 8.3 P2：表达式血缘与查询口径分析

#### 目标

```text
从“字段从哪来”升级到“指标怎么算、范围怎么定、粒度是什么、风险在哪里”。
```

#### 范围

```text
R13a → R09b2 → R12 → R13b → R14 → R17
```

#### 验收标准

| 标准 | 说明 |
|---|---|
| 表达式可抽取 | sum、count distinct、case when、窗口函数能结构化识别 |
| 复杂 SourceLocation 可定位 | CTE、子查询、join condition、union、case when、window function 可定位或可解释降级 |
| 指标公式可解释 | 输出字段能展示公式和来源字段 |
| 粒度可解释 | group by / distinct / window partition 可识别 |
| 过滤范围可解释 | where / having / partition filter 可展示 |
| Join 风险可提示 | join key、join 类型、潜在放大风险可提示 |
| evidence_refs 可追溯 | 每个确定性口径结论都有证据引用 |
| 多视图可切换 | table / column / expression / semantics / diagnostics 视图可用 |

---

### 8.4 P3：SQL diff 与历史快照

#### 目标

```text
支持用户比较 SQL 修改前后的字段、血缘和口径变化，
并保存历史分析结果用于回溯。
```

#### 范围

```text
R15 → R16 → R17
```

#### 验收标准

| 标准 | 说明 |
|---|---|
| 当前 SQL diff | 两段 SQL 可返回字段、血缘、口径变化摘要 |
| 基于 entity_id 比较 | 不按 label、node_id 或前端坐标比较 |
| 历史可保存 | SQL、AnalysisResult、GraphViewModel 可落库 |
| 快照可读取 | 可按 analysis_id 读取历史结果 |
| 历史 diff | 两个历史快照可比较 |

---

### 8.5 P4：平台化扩展

#### 目标

```text
将本地 SQL Analysis Workbench 扩展成可持续维护的平台能力。
```

#### 扩展方向

| 方向 | 说明 |
|---|---|
| Hive Metastore 自动同步 | 替代手动 JSON 导入 |
| DataHub / OpenMetadata 接入 | 接入企业元数据平台 |
| OpenLineage 输出 | 输出标准 lineage event |
| 多项目空间 | 多团队 / 多业务线隔离 |
| 权限体系 | 元数据和 SQL 访问控制 |
| 批量 SQL 分析 | 扫描任务脚本和调度系统 |
| AI SQL Review | 基于血缘和口径生成审查建议，但保持确定性解析为主线 |
| 大图性能优化 | 节点虚拟化、懒加载、分层展开 |

---

## 9. 前端工作台设计边界

### 9.1 前端主模块

```text
frontend/src/
├── components/
│   ├── SqlEditor/
│   ├── LineageCanvas/
│   ├── MetadataImport/
│   ├── MetadataPanel/
│   ├── SemanticsPanel/
│   ├── DiagnosticsPanel/
│   └── Toolbar/
├── pages/
│   └── Workbench/
├── services/
├── stores/
├── types/
└── utils/
```

### 9.2 SqlEditor

| 能力 | 阶段 | 说明 |
|---|---|---|
| SQL 输入 | P0 | Monaco Editor 基础输入 |
| SQL 格式化 | P0 | 调后端 format 或前端轻量格式化 |
| 分析提交 | P0 | 提交到 `/api/sql/analyze` |
| 错误标记 | P0/P1 | 基于 diagnostics 和 SourceLocation |
| 字段补全 | P1 | 依赖 MetadataService |
| 字段 Hover | P1 | 字段注释、血缘摘要、诊断摘要 |
| 图谱联动 | P1 | 与 React Flow 节点互相定位 |

### 9.3 LineageCanvas

| 能力 | 阶段 | 说明 |
|---|---|---|
| 基础节点边展示 | P0 | React Flow 渲染 GraphViewModel |
| 拖拽 / 缩放 | P0 | React Flow 原生能力 |
| 自动布局 | P0/P1 | ELK.js 布局，可先做基础布局 |
| 节点选中 | P0 | 写入 GraphInteractionState |
| 路径高亮 | P1 | 上游 / 下游链路高亮 |
| 节点折叠 | P1/P2 | 折叠状态归前端 GraphInteractionState |
| 多视图切换 | P2 | table / column / expression / semantics / diagnostics |

### 9.4 前端禁止事项

```text
前端不解析 SQL。
前端不判断字段归属。
前端不推导血缘。
前端不直接消费 SQLGlot AST。
前端不把拖拽位置、折叠状态混入后端 GraphViewModel。
前端可以做过滤、搜索、折叠、布局、局部高亮，但不能自行补全或修正后端血缘结果。
前端发现 GraphViewModel 缺字段、缺边、缺 location 时，只能展示降级状态或触发重新分析，不能在 UI 层静默补边。
```

---

## 10. 后端工程目录建议

```text
backend/app/
├── main.py
├── api/
│   ├── analyze_controller.py
│   └── metadata_controller.py
├── domain/
│   ├── analysis_result.py
│   ├── stage_status.py
│   ├── entity_id.py
│   ├── source_location.py
│   ├── scope_model.py
│   ├── name_resolution_model.py
│   ├── minimal_expression_model.py
│   ├── lineage_ir.py
│   ├── semantics_model.py
│   ├── diagnostics_model.py
│   ├── graph_view_model.py
│   └── contract_schema.py
├── services/
│   ├── analysis_orchestrator.py
│   ├── sql_parse_service.py
│   ├── scope_resolver.py
│   ├── metadata_service.py
│   ├── name_resolver.py
│   ├── projection_extractor.py
│   ├── lineage_engine.py
│   ├── expression_analyzer.py
│   ├── semantics_analyzer.py
│   ├── diagnostics_collector.py
│   ├── diagnostics_engine.py
│   ├── graph_builder.py
│   └── contract_assembler.py
├── repositories/
│   ├── metadata_repository.py
│   └── analysis_repository.py
├── adapters/
│   └── sqlglot_adapter.py
├── diagnostics/
├── schemas/
└── config/
```

---

## 11. 测试体系 R17

R17 不是阶段末尾补充项，而是每个需求必须绑定最小测试。

### 11.1 测试分层

| 层级 | 内容 |
|---|---|
| 单元测试 | parser、scope、resolver、projection、lineage、expression、semantics、diagnostics |
| 集成测试 | analyze API、metadata import、graph builder |
| Golden Case | 固定 SQL 输入与期望输出 |
| Snapshot Test | LineageIR、GraphViewModel、AnalysisResult 结构稳定性 |
| Contract Test | Pydantic / OpenAPI / TypeScript 类型契约 |
| 前端 E2E | SQL 输入、分析、画布展示、诊断展示 |

---

### 11.2 Golden Case 目录建议

```text
tests/golden_cases/
├── p0/
│   ├── simple_select/
│   │   ├── input.sql
│   │   ├── metadata.json
│   │   └── expected_analysis_result.json
│   ├── single_table_alias/
│   ├── unknown_table/
│   ├── unknown_column/
│   ├── ambiguous_column/
│   ├── metadata_json_import/
│   ├── source_location_basic/
│   ├── graph_view_model_snapshot/
│   └── contract_schema_basic/
├── p1/
│   ├── cte_basic/
│   ├── subquery_basic/
│   ├── join_basic/
│   ├── select_star/
│   └── union_all/
├── p2/
│   ├── group_by_metric/
│   ├── case_when_metric/
│   ├── count_distinct_metric/
│   ├── window_function/
│   └── join_expansion_risk/
└── p3/
    ├── current_sql_diff/
    └── history_snapshot_diff/
```

### 11.3 最小 Golden Case 集合

```text
simple_select
single_table_alias
unknown_table
unknown_column
ambiguous_column
metadata_json_import
source_location_basic
graph_view_model_snapshot
contract_schema_basic
cte_basic
subquery_basic
join_basic
select_star
group_by_metric
case_when_metric
window_function
partial_unsupported_feature
```

### 11.4 每阶段测试重点

| 阶段 | 测试重点 |
|---|---|
| P0 | 简单 SQL、元数据导入、字段归属、MinimalExpressionExtractor、基础血缘、诊断模型、契约模型、stage_statuses |
| P1 | SourceLocation 基础精准度、CTE、join、select *、completion、hover、双向联动 |
| P2 | ExpressionAnalyzer、复杂 SourceLocation、SemanticsReport、evidence_refs、多视图图谱 |
| P3 | 当前 diff、历史快照、历史 diff、entity_id 稳定比较 |

---

## 12. 降级策略与复杂 SQL 处理原则

复杂 SQL 不应强行伪装成完全成功。

### 12.1 状态分级

| 状态 | 含义 |
|---|---|
| success | 当前 SQL 的目标能力均成功解析 |
| partial | 部分结构已解析，部分结构不支持或低可信 |
| failed | 无法生成有意义的分析结果 |

### 12.2 partial 返回原则

当遇到复杂结构暂不支持时：

```text
可以返回已解析的表级 / 字段级血缘；
必须在 unsupported_features 中记录不支持结构；
必须在 diagnostics_report 中说明风险；
必须降低 confidence_level；
必须在 stage_statuses 中标记 partial / failed / skipped；
不能把未知来源伪装成确定血缘。
```

### 12.3 典型 unsupported_features

```text
recursive_cte
lateral_view
explode_complex_type
dynamic_sql_template
unsupported_window_frame
ambiguous_star_expansion
unknown_udf_semantics
correlated_subquery_complex
union_type_alignment_unknown
```

---

## 13. 文档维护原则

主需求文档只保留：

```text
稳定产品边界
架构边界
核心数据模型
需求拆分
阶段顺序
验收标准
降级原则
测试要求
```

以下内容不继续写入主需求文档：

| 内容 | 处理建议 | 理由 |
|---|---|---|
| 版本审阅、差异评分、采纳记录 | 放入 `docs/reviews/` 或 `docs/changelog/` | 主文档应服务开发 |
| 完整 Monaco provider 实现细节 | 放入 `docs/frontend-design.md` | 主文档只写边界和阶段 |
| 完整 JSON Schema / TS 自动生成流程 | 放入 `docs/contract-schema.md` | P0 不需要完整工具链细节 |
| 元数据 DDL 转 JSON 复杂规则 | 放入 `docs/metadata-import.md` | 主文档只保留需求入口 |
| SQL diff 算法细节 | 放入 P3 设计文档 | 当前不是 P0/P1 重点 |
| Graph 布局算法细节 | 放入前端设计文档 | 不应污染血缘语义模型 |
| AI Review / 大模型辅助解释 | 暂缓到 P4 | 当前项目应保持确定性解析主线 |

---

## 14. 交付入口与主文档冻结原则

当前项目主线已经收敛到可开发状态。主文档后续不再作为“大轮次审阅”的主要承载物，而作为开发、测试和验收的稳定基准。

P0 实施入口固定为：

```text
SQLite 元数据导入
→ SQLGlot 解析
→ Scope / Name Resolution
→ MinimalExpressionExtractor
→ LineageIR
→ Diagnostics
→ GraphViewModel
→ React Flow 展示
→ Contract Test + Golden Case
```

后续仍可进入主文档的小变动类型：

| 类型 | 示例 | 是否允许 |
|---|---|---:|
| 术语一致性 | 字段名、模型名、阶段名统一 | 是 |
| 验收标准细化 | 为已有需求补充可测试条件 | 是 |
| 明确不做事项 | 将容易误解的范围写入 out of scope | 是 |
| 实现验证反馈 | P0 编码发现某模型字段确实阻塞 | 是，但需说明原因 |
| 新增大模块 | 新增权限、AI Review、平台接入等 | 否，进入 P4 或专题文档 |
| 阶段大重排 | 推翻 P0/P1/P2 主顺序 | 否，除非实现验证证明原顺序不可行 |

最重要的工程原则：

```text
1. 不要让 SQLGlot 输出直连 React Flow。
2. 不要让前端承担血缘推导逻辑。
3. 不要在 P0 追求复杂 SQL 全覆盖。
4. 不要把交互状态混入后端 GraphViewModel。
5. 不要把 unsupported 结构伪装成 success。
6. 不要把 CTE / 子查询 / 输出字段伪装成物理字段。
7. 先稳定契约、IR、诊断、位置模型、entity_id 和测试，再扩展表达式级血缘与口径分析。
```

## 15. 建议后续文档拆分

主文档保持当前颗粒度，不继续膨胀。后续详细设计与实现说明拆入以下工程文档：

| 文档 | 内容 |
|---|---|
| `docs/p0-implementation-plan.md` | P0 开发执行说明：模块顺序、接口清单、最小 Golden Case、验收命令、不可做事项 |
| `docs/architecture.md` | 总体架构与 Pipeline |
| `docs/contract-schema.md` | AnalysisResult / LineageIR / GraphViewModel Schema |
| `docs/scope-resolution.md` | ScopeResolver / NameResolver 规则 |
| `docs/lineage-ir.md` | LineageIR 节点边模型 |
| `docs/source-location.md` | SourceLocation 坐标映射规则 |
| `docs/frontend-design.md` | Monaco + React Flow 前端交互细节 |
| `docs/golden-cases.md` | Golden Case 编写规范 |
| `docs/development-roadmap.md` | P0-P4 开发排期与验收 |
