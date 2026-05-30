# SQL 血缘解析工作台技术方案检验与补强建议

## 一、结论：当前方案总体符合需求，但还需要补强 5 个关键层

当前技术方案方向是正确的。

它已经覆盖了以下核心内容：

- Python + FastAPI + SQLGlot + SQLite 后端
- React + Monaco Editor + React Flow + ELK.js 前端
- JSON 元数据导入
- 字段注释接入
- 血缘画布
- 查询口径分析
- SQL 诊断
- 测试体系
- 分阶段建设规划

但是，当前方案还有一个核心问题：

> 它更像一份“产品级技术蓝图”，但还不是一份足够可开发的“工程实现方案”。

尤其是以下能力：

- 表达式级血缘
- 子查询级血缘
- 查询口径分析
- SQL 与图谱联动
- 字段注释接入
- 前端高级交互

这些能力不能只依赖 SQLGlot 原生 lineage 能力完成，必须额外设计一层自有的语义模型与图模型。

---

## 二、需求匹配度检查

| 需求 | 当前方案覆盖情况 | 判断 |
|---|---:|---|
| SQLGlot + Python + SQLite 作为后端核心 | 已覆盖 | 满足 |
| 导入元数据到 SQLite 维护 | 已覆盖 JSON 导入、事务 upsert、导入历史 | 满足 |
| 前端可用性和互动性重点优化 | 已覆盖 Monaco、React Flow、ELK.js、画布交互 | 基本满足 |
| 在线 SQL 编译器体验 | 已覆盖 Monaco，但应明确不是“真实执行引擎” | 需澄清 |
| 表达式级血缘 | 已设计节点和边类型 | 部分满足 |
| 子查询级血缘 | 已设计 CTE / subquery 节点 | 部分满足 |
| 点线图画布 + 拖拽 | 已覆盖 React Flow | 满足 |
| 查询口径分析 | 已覆盖粒度、过滤、join、聚合、窗口等维度 | 方向正确，但需强化模型 |
| 字段注释接入 | 已覆盖字段 hover、详情面板、元数据注释 | 满足 |
| 高内聚低耦合 | 已覆盖服务拆分原则 | 满足，但需补充接口契约 |
| 前端强扩展能力 | 已覆盖模块划分 | 基本满足 |
| 问题排查能力 | 已覆盖 DiagnosticsService 和测试体系 | 满足，但需增加可观测性 |

---

## 三、最重要的可行性判断

### 1. 技术栈可行

推荐技术栈如下：

```text
后端：
Python + FastAPI + SQLGlot + SQLite

前端：
React + TypeScript + Monaco Editor + React Flow + ELK.js
```

这个组合是合理的。

其中：

- SQLGlot 适合承担 SQL AST、方言解析、SQL 标准化、基础 lineage 和 SQL 重写底层能力。
- SQLite 适合当前本地化、轻量级、单人或小团队使用的元数据仓库。
- Monaco Editor 适合构建在线 SQL 编辑器体验。
- React Flow 适合做可拖拽、可缩放、可自定义节点和边的血缘图工作台。
- ELK.js 适合复杂 DAG 的自动布局。

### 2. 产品目标可行，但不能把 SQLGlot 当成全部核心

当前项目目标不是简单 SQL Parser，而是：

```text
SQL 理解工作台
= SQL 解析
+ 元数据补全
+ 字段消歧
+ 表达式血缘
+ 子查询血缘
+ 查询口径解释
+ 字段注释增强
+ 图谱交互
+ 诊断与重写辅助
```

因此核心架构应该调整为：

```text
SQLGlot 只是 Parser / AST / 基础 Lineage 层
真正的产品核心应该是自定义 Lineage Semantic Engine
```

推荐处理链路：

```text
SQLGlot
  ↓
AST / Scope / Expression
  ↓
自定义作用域解析
  ↓
字段消歧
  ↓
表达式依赖提取
  ↓
语义口径分析
  ↓
稳定 Graph JSON
  ↓
前端 React Flow 渲染
```

当前方案里已经设计了 LineageService、SemanticsService、GraphService，但需要进一步明确：

> 不要直接把 SQLGlot 输出结果裸传给前端。

建议设计中间层：

```text
SQLGlot AST
  → Internal Lineage IR
  → Semantic Model
  → Graph View Model
```

---

## 四、当前方案最大的问题

### 问题 1：缺少“作用域模型 Scope Model”的明确设计

字段级血缘最难的地方不是解析 SQL，而是判断字段到底属于谁。

示例：

```sql
select
    user_id,
    order_amt
from order_table a
join user_table b
  on a.user_id = b.user_id;
```

如果 SQL 里写的是：

```sql
select user_id
```

而不是：

```sql
select a.user_id
```

系统必须判断：

```text
user_id 来自 a？
user_id 来自 b？
还是字段歧义？
```

所以需要补充核心模块：

```text
ScopeResolver / NameResolver
```

职责如下：

| 能力 | 说明 |
|---|---|
| 表别名解析 | `order_table a` → `a` |
| CTE 作用域解析 | CTE 名覆盖真实表名时优先识别 CTE |
| 子查询作用域解析 | 派生表字段来自内部 select 输出 |
| 无表名前缀字段消歧 | 依赖 SQLite 元数据判断字段来源 |
| select * 展开 | 依赖元数据展开字段 |
| 字段歧义识别 | 多表同名字段时输出诊断 |
| 字段不可解析识别 | 元数据缺失或字段不存在时输出 unknown |

建议新增文件：

```text
backend/app/services/scope_service.py
backend/app/domain/scope_model.py
```

---

### 问题 2：缺少“血缘中间表示 IR”

当前方案有 GraphService，但 GraphService 不应该直接从 AST 生成前端节点。

正确分层应该是：

```text
AST
  ↓
ScopeGraph
  ↓
LineageIR
  ↓
SemanticReport
  ↓
GraphViewModel
```

建议定义内部血缘模型：

```json
{
  "analysis_id": "uuid",
  "dialect": "spark",
  "statements": [],
  "scopes": [],
  "lineage_nodes": [],
  "lineage_edges": [],
  "semantics": {},
  "diagnostics": []
}
```

GraphService 只做一件事：

```text
把 LineageIR 转成前端 React Flow 可消费的 nodes / edges
```

这样后续要更换前端画布、增加导出、做 diff、接入 OpenLineage，都不会影响核心血缘引擎。

---

### 问题 3：查询口径分析不能只靠 AST，需要独立语义层

口径分析要回答的是：

```text
当前 SQL 最终结果是按什么粒度、什么范围、什么过滤条件、什么指标公式算出来的？
```

因此建议将口径分析拆成结构化输出：

```json
{
  "query_type": "select",
  "result_grain": {
    "type": "group_by",
    "columns": ["user_id", "dt"]
  },
  "filters": [
    {
      "type": "partition_filter",
      "column": "dt",
      "operator": "=",
      "value": "${biz_date}"
    }
  ],
  "metrics": [
    {
      "name": "gmv",
      "formula": "sum(order_amt)",
      "source_columns": ["order_amt"],
      "aggregation": "sum"
    }
  ],
  "joins": [
    {
      "type": "left join",
      "left_table": "a",
      "right_table": "b",
      "keys": ["user_id"],
      "risk": "unknown_cardinality"
    }
  ],
  "risks": []
}
```

口径分析至少要分 6 类：

| 口径维度 | 需要输出什么 |
|---|---|
| 结果粒度 | group by、distinct、window partition |
| 统计范围 | where、having、分区条件、时间条件 |
| 指标公式 | sum、count、avg、count distinct、case when |
| join 关系 | join 类型、join key、主从表 |
| 去重逻辑 | distinct、row_number、group by |
| 风险说明 | join 放大、粒度混杂、无分区过滤、字段歧义 |

---

### 问题 4：前端“高级 SQL 编译器”应定义为 SQL Workbench，而不是执行引擎

“先进的在线 SQL 编译器”需要先明确边界。

如果目标是：

```text
像 DataGrip / VS Code 一样写 SQL、补全、格式化、诊断、hover、定位血缘
```

那么 Monaco Editor 是正确选择。

如果目标是：

```text
真实连接 Hive / Spark / StarRocks 并执行 SQL 返回结果
```

那当前方案没有覆盖，也不建议第一阶段做。

建议第一阶段定义为：

```text
SQL Analysis Workbench
```

第一阶段建议支持：

| 能力 | 第一阶段是否做 |
|---|---:|
| SQL 高亮 | 做 |
| SQL 格式化 | 做 |
| 表字段补全 | 做 |
| 字段 hover | 做 |
| 解析错误标注 | 做 |
| 字段歧义标注 | 做 |
| 点击字段定位图节点 | 做 |
| 点击图节点定位 SQL | 做 |
| 真正执行 SQL | 暂不做 |
| 连接 Hive / Spark 查询结果 | 暂不做 |

Monaco Editor 适合承载编辑器底座，但 SQL 补全、hover、diagnostics、code action 这些智能能力需要通过后端 API 或类 LSP 服务实现。

---

### 问题 5：复杂血缘图必须支持“多视图”，不能只做一张全量图

如果把表、字段、表达式、filter、join、group by、window、subquery 全部放到一张图里，真实 SQL 一复杂就会不可读。

建议前端图谱提供 5 种视图：

| 视图 | 作用 |
|---|---|
| 表级视图 | 快速看输入表、输出表、CTE、子查询关系 |
| 字段级视图 | 看输出字段来自哪些源字段 |
| 表达式视图 | 看 sum、case、window、function 的加工过程 |
| 口径视图 | 看过滤、分组、join、去重、窗口对结果的影响 |
| 诊断视图 | 高亮未知字段、歧义字段、join 风险、分区风险 |

这样画布才会真正可用。

---

## 五、建议调整后的后端架构

### 1. 后端核心链路

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

### 2. 后端模块职责重定义

| 模块 | 核心职责 | 禁止做什么 |
|---|---|---|
| SqlParseService | SQLGlot AST、格式化、方言解析 | 不查 SQLite |
| MetadataService | 表字段、注释、主键、粒度、指标定义 | 不解析 SQL |
| ScopeResolver | CTE、子查询、别名、字段归属 | 不生成前端节点 |
| LineageEngine | 生成字段、表达式、子查询血缘 IR | 不关心 UI 布局 |
| SemanticsAnalyzer | 粒度、过滤、join、聚合、窗口、口径解释 | 不做字段补全 |
| DiagnosticsEngine | 错误、歧义、风险、修复建议 | 不改写 SQL |
| GraphBuilder | LineageIR → React Flow Graph JSON | 不解析 SQL |
| RewriteService | 格式化、select * 展开、字段裁剪建议 | 不写元数据 |
| MetadataImportService | JSON / DDL / CSV 导入、预览、事务 upsert | 不参与 SQL 解析 |

### 3. 建议新增目录

```text
backend/app/
├── domain/
│   ├── ast_model.py
│   ├── scope_model.py
│   ├── lineage_ir.py
│   ├── semantics_model.py
│   ├── diagnostics_model.py
│   └── graph_view_model.py
│
├── services/
│   ├── analysis_orchestrator.py
│   ├── sql_parse_service.py
│   ├── scope_resolver.py
│   ├── name_resolver.py
│   ├── lineage_engine.py
│   ├── expression_lineage_engine.py
│   ├── semantics_analyzer.py
│   ├── diagnostics_engine.py
│   ├── graph_builder.py
│   └── rewrite_service.py
```

---

## 六、SQLite 元数据模型需要补强

当前方案已经包含表字段、字段注释、指标定义、导入历史、解析历史，这是正确方向。

但为了支撑字段级血缘和口径分析，建议至少设计这些表：

| 表 | 用途 |
|---|---|
| `catalog_tables` | 库、表、表注释、表类型、owner |
| `catalog_columns` | 字段名、类型、注释、是否分区、字段顺序 |
| `table_keys` | 主键、唯一键、业务 key |
| `table_grains` | 表粒度说明，例如 order_no 粒度、user_id + dt 粒度 |
| `metrics` | 指标名、公式、口径描述 |
| `metric_columns` | 指标依赖字段 |
| `import_batches` | 元数据导入批次 |
| `import_changes` | 每次导入新增、更新、缺失字段 |
| `analysis_history` | SQL 解析历史 |
| `analysis_snapshots` | 血缘图和口径分析结果快照 |
| `sql_examples` | Golden Case 样例 SQL |
| `diagnostic_events` | 解析失败和风险记录 |

其中尤其关键的是：

```text
table_keys
table_grains
```

因为没有它们，系统只能说：

```text
这个 SQL 使用了 join
```

但不能判断：

```text
这个 join 是否可能一对多放大
```

---

## 七、前端方案建议升级

### 1. 页面布局建议

```text
┌────────────────────────────────────────────────────────────┐
│ Header：项目空间 / 方言 / 解析 / 格式化 / 导入元数据 / 导出 │
├───────────────────────┬────────────────────────────────────┤
│ Monaco SQL Editor     │ React Flow Lineage Canvas           │
│ - 补全                │ - 表级/字段级/表达式级/口径级切换   │
│ - hover 注释          │ - 拖拽/缩放/折叠/自动布局           │
│ - diagnostics 标记    │ - 路径高亮/搜索/过滤                │
├───────────────────────┼────────────────────────────────────┤
│ SQL Outline / AST     │ Semantics / Diagnostics / Metadata  │
└───────────────────────┴────────────────────────────────────┘
```

### 2. 前端必须重点做的交互

| 交互 | 价值 |
|---|---|
| 点击输出字段 → 高亮上游来源 | 最核心 |
| 点击 SQL 中字段 → 高亮图节点 | 强联动 |
| 点击图节点 → 定位 SQL 片段 | 强可解释 |
| 节点折叠表达式细节 | 防止图过大 |
| 按边类型过滤 | 区分直接血缘、过滤影响、join 影响 |
| 表级 / 字段级 / 表达式级切换 | 降低认知负担 |
| 字段 hover 展示注释 | 接入元数据价值 |
| 诊断结果点击跳转 | 提升排查效率 |
| Diff 模式 | 对比 SQL 修改前后影响 |
| 导出 Graph JSON | 方便调试和复现 |

---

## 八、推荐 API 设计

至少需要这些接口：

| API | 用途 |
|---|---|
| `POST /api/sql/analyze` | SQL 解析、血缘、口径、诊断一体化分析 |
| `POST /api/sql/format` | SQL 格式化 |
| `POST /api/sql/rewrite/select-star` | select * 展开 |
| `POST /api/sql/diff` | SQL 修改前后血缘差异 |
| `POST /api/metadata/import/preview` | 元数据导入预览 |
| `POST /api/metadata/import/commit` | 确认写入 SQLite |
| `GET /api/metadata/tables/search` | 表搜索 |
| `GET /api/metadata/columns/search` | 字段搜索 |
| `GET /api/metadata/table/{table_id}` | 表字段详情 |
| `GET /api/analysis/{analysis_id}` | 查询历史分析结果 |
| `GET /api/diagnostics/{analysis_id}` | 查询诊断详情 |

---

## 九、建议的核心返回结构

`POST /api/sql/analyze` 不要只返回图，要返回完整分析结果：

```json
{
  "analysis_id": "uuid",
  "status": "success",
  "dialect": "spark",
  "normalized_sql": "...",
  "lineage": {
    "tables": [],
    "columns": [],
    "expressions": [],
    "subqueries": [],
    "edges": []
  },
  "semantics": {
    "query_type": "select",
    "result_grain": {},
    "filters": [],
    "metrics": [],
    "joins": [],
    "windows": [],
    "dedup_logic": []
  },
  "diagnostics": [],
  "graph": {
    "nodes": [],
    "edges": [],
    "view_modes": ["table", "column", "expression", "semantics"]
  },
  "metadata_context": {
    "resolved_tables": [],
    "missing_tables": [],
    "missing_columns": [],
    "ambiguous_columns": []
  }
}
```

---

## 十、分阶段落地建议

### P0：最小可用闭环

目标：先证明这条链路真的跑通。

```text
SQL 输入
→ SQLGlot AST
→ SQLite 元数据读取
→ 字段消歧
→ 表级血缘
→ 字段级血缘
→ React Flow 展示
→ 字段注释 hover
→ 基础诊断
```

P0 不建议做太多复杂交互，重点是保证结果正确。

---

### P1：真实数仓 SQL 覆盖

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

这一阶段必须建立 Golden Case 测试集，否则后续会越改越乱。

---

### P2：表达式级和口径级增强

重点支持：

```text
sum / count / avg / count distinct
case when 指标
where / having 过滤影响
join key 影响
group by 粒度
window partition / order
row_number 去重
```

这阶段开始真正变成“SQL 理解工作台”。

---

### P3：前端高级交互

重点支持：

```text
SQL 与图谱双向定位
路径高亮
边类型过滤
节点折叠
自动布局
Diff 模式
导出报告
解析历史
```

---

### P4：平台化扩展

后续再考虑：

```text
Hive Metastore 自动同步
DataHub / OpenMetadata 接入
多项目空间
权限系统
任务级 SQL 批量解析
调度血缘
AI Review
```

---

## 十一、建议补进技术方案里的关键内容

### 必须补充

| 补充项 | 原因 |
|---|---|
| ScopeResolver / NameResolver | 字段级血缘准确性的核心 |
| LineageIR | 避免 SQLGlot、语义分析、前端图强耦合 |
| GraphViewModel | 支撑多视图、折叠、过滤、路径高亮 |
| SemanticsReport 结构 | 让口径分析可落地 |
| Diagnostics 错误码体系 | 方便问题排查 |
| Golden Case 测试集 | 防止血缘结果回归 |
| 元数据版本与导入批次 | 支撑字段注释和 schema 演进 |
| SQL 片段位置映射 | 支撑点击图节点定位 SQL |
| 大图性能策略 | 防止真实 SQL 图谱卡死 |

### 暂缓补充

| 暂缓项 | 原因 |
|---|---|
| 真正执行 SQL | 会引入连接、安全、权限、资源治理问题 |
| 多用户权限系统 | MVP 不需要 |
| Hive Metastore 自动同步 | 先用 JSON / DDL 导入闭环 |
| AI 自动改 SQL | 等血缘和口径稳定后再做 |
| OpenLineage 输出 | 后续平台化再做 |

---

## 十二、最终判断

### 方案是否符合需求？

**符合 75%～80%。**

它已经具备正确的总体方向和模块边界，但还需要从“概念方案”升级为“工程实现方案”。

### 最大优点

```text
1. 技术栈选择合理
2. 前后端边界清晰
3. 元数据意识正确
4. 不是只做字段连线，而是开始考虑口径语义
5. 已经有诊断、测试、扩展规划
```

### 最大不足

```text
1. 缺少 ScopeResolver / NameResolver 的核心设计
2. 缺少稳定的 LineageIR 中间层
3. 口径分析还停留在维度罗列，没有定义结构化输出
4. 前端图谱缺少多视图策略
5. API 契约、错误码、测试样例还不够工程化
```

---

## 十三、最终技术路线

不建议做：

```text
SQLGlot → React Flow
```

应该做：

```text
SQLGlot
  → AST
  → ScopeResolver
  → MetadataCatalog
  → LineageIR
  → SemanticsReport
  → DiagnosticsReport
  → GraphViewModel
  → React Flow
```

最终判断：

> 当前方案方向正确，可以继续推进；但必须补上“作用域解析 + 血缘中间表示 + 结构化口径模型 + 多视图图模型”这四层，否则后面会在字段级血缘准确性和前端复杂交互上卡住。
