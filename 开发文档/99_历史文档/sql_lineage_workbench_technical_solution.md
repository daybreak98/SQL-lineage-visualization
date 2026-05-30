# SQL 血缘解析工作台技术方案

## 0. 文档说明

本文档用于描述一个面向数仓工程师、数据开发和数据分析人员的在线 SQL 血缘解析工作台。项目核心技术路线为：

```text
后端：Python + FastAPI + SQLGlot + SQLite
前端：React + TypeScript + Monaco Editor + React Flow + ELK.js
```

本方案重点保留架构级设计、核心功能、模块职责、项目目录和开发阶段，不展开过细的表结构、接口请求格式和字段级实现细节。这些内容可在后续开发过程中持续迭代。

---

## 1. 项目定位

本项目不是简单的 SQL Parser，而是一个围绕 SQL 开发、SQL 理解、字段级血缘分析、查询口径解释和 SQL 重写辅助构建的在线工作台。

核心目标：

```text
SQL 输入
  → 元数据补全
  → SQL AST 解析
  → 表级 / 字段级 / 表达式级 / 子查询级血缘推导
  → 查询口径分析
  → 字段注释增强
  → 点线图画布展示
  → SQL 风险诊断
  → SQL 重写辅助
```

最终产品形态：

> 一个面向数仓工程师的 SQL 编译分析工作台：既能看字段从哪来，也能看指标怎么算，还能通过 JSON 快速维护元数据，并辅助用户分析 SQL 风险和重写 SQL。

---

## 2. 总体架构

```text
┌────────────────────────────────────────────────────┐
│                    前端工作台                       │
│ SQL 编辑器 / 血缘画布 / 元数据导入 / 口径分析 / 诊断 │
└─────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────┐
│                    Python 后端服务                  │
│ SQL 解析 / 元数据查询 / JSON 导入 / 血缘推导 / 口径分析 │
└─────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────┐
│                    SQLite 元数据仓库                │
│ 表字段 / 字段注释 / 指标定义 / 导入历史 / 解析历史    │
└────────────────────────────────────────────────────┘
```

## 2.1 架构原则

| 原则 | 说明 |
|---|---|
| 解析与元数据解耦 | SQLGlot 负责 SQL 结构解析，元数据服务负责字段补全、字段消歧和注释增强 |
| 血缘与图展示解耦 | 后端生成稳定 Graph JSON，前端只负责渲染和交互 |
| 口径分析与血缘推导解耦 | 血缘回答“字段从哪来”，口径分析回答“结果怎么算” |
| 元数据导入独立模块化 | JSON、DDL、CSV 等导入方式统一进入 Metadata Import Service |
| 前端交互优先 | 画布、编辑器、口径面板、诊断面板需要形成强联动 |
| 结果可诊断 | 每次解析都要能解释失败原因、字段歧义、元数据缺失和 SQL 风险 |
| 模块高内聚低耦合 | 每个模块只解决一个核心问题，模块之间通过稳定数据模型交互 |

---

## 3. 技术选型

| 模块 | 技术选型 | 说明 |
|---|---|---|
| SQL 解析核心 | SQLGlot | 负责 SQL AST、方言处理、字段引用分析、基础 lineage 和 SQL 重写基础能力 |
| API 服务 | FastAPI | 负责前后端 API、解析任务、元数据导入任务和分析任务编排 |
| 元数据存储 | SQLite | 负责表字段元数据、字段注释、指标定义、导入历史和解析历史 |
| SQL 编辑器 | Monaco Editor | 负责在线 SQL 编辑、补全、错误提示和字段 hover |
| 血缘画布 | React Flow | 负责节点、边、拖拽、缩放、折叠和路径高亮 |
| 自动布局 | ELK.js | 负责复杂血缘图的 DAG 自动布局 |
| 前端状态管理 | Zustand | 负责 SQL、图谱、元数据、面板状态管理 |
| 测试体系 | pytest + 前端 E2E | 保证解析结果、元数据导入和图谱结果稳定 |

---

## 4. 核心功能范围

## 4.1 SQL 解析能力

| 功能 | 说明 |
|---|---|
| SQL AST 解析 | 将 SQL 转成结构化语法树 |
| 方言支持 | 优先支持 Hive / Spark SQL，后续扩展 StarRocks / Doris / MySQL |
| SQL 标准化 | 格式化 SQL、统一别名、清理无效结构 |
| CTE 解析 | 支持多层 CTE 和 CTE 之间依赖 |
| 子查询解析 | 支持 from 子查询、select 子查询、where 子查询 |
| insert 解析 | 支持 insert overwrite / insert into 场景 |
| create table as select | 支持建表血缘 |
| union all | 支持多分支血缘合并 |
| 聚合解析 | 支持 group by、count、sum、avg、count distinct |
| 窗口函数解析 | 支持 partition by、order by、row_number、rank 等 |
| case when 解析 | 支持条件表达式血缘 |
| select * 展开 | 基于元数据展开真实字段 |

## 4.2 元数据能力

元数据是字段级血缘准确性的基础。项目需要维护轻量级本地元数据仓库，用于支持 SQL 解析、字段消歧、字段注释展示和口径分析。

| 功能 | 说明 |
|---|---|
| 表元数据维护 | 维护库、表、表注释、表类型等基础信息 |
| 字段元数据维护 | 维护字段名、字段类型、字段注释、分区标识等 |
| 字段注释查询 | 支持前端 hover 和字段详情面板 |
| 表字段搜索 | 支持 SQL 编辑器补全 |
| 字段消歧 | 根据表字段元数据判断无前缀字段来源 |
| select * 展开 | 根据表字段元数据展开真实字段 |
| 指标定义维护 | 支持指标口径解释 |
| 业务主键 / 粒度配置 | 支持 join 风险和查询粒度分析 |
| 元数据导入历史 | 记录每次元数据导入来源、结果和影响范围 |
| 元数据版本管理 | 后续支持同一张表不同版本字段对比 |

## 4.3 JSON 元数据导入能力

前端页面需要新增 JSON 元数据导入功能。用户可以上传或粘贴 JSON 元数据，系统校验通过后，将其中的表字段信息加载到 SQLite 元数据仓库中，并对已有表字段进行更新。

### 功能入口

建议在前端顶部工具栏或左侧元数据面板中增加：

```text
导入元数据
  ├── 上传 JSON 文件
  ├── 粘贴 JSON 内容
  ├── 导入预览
  ├── 校验结果
  └── 确认写入 SQLite
```

### 导入流程

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
返回导入结果
        ↓
前端刷新元数据搜索、字段补全、字段注释
```

### JSON 导入模式

| 模式 | 说明 |
|---|---|
| 上传 JSON 文件 | 适合从 DataGrip、Hive 脚本、其他工具导出的元数据 |
| 粘贴 JSON 内容 | 适合少量表字段快速导入 |
| 单表导入 | 一次导入一张表的元数据 |
| 多表导入 | 后续支持一次导入多张表 |
| 覆盖更新 | 对已有字段更新类型、注释、扩展属性 |
| 增量更新 | 只新增或更新 JSON 中出现的字段 |
| 字段失效标记 | JSON 中未出现但数据库已有的字段，默认不物理删除，可标记为疑似过期 |

### 元数据更新策略

| 对象 | 策略 |
|---|---|
| 表不存在 | 新增表元数据 |
| 表已存在 | 更新表注释、表类型、扩展属性等信息 |
| 字段不存在 | 新增字段 |
| 字段已存在 | 更新字段类型、注释、分区标识、扩展属性 |
| JSON 未包含旧字段 | 默认保留旧字段，并标记为“本次未出现” |
| 字段名大小写差异 | 按配置决定是否大小写敏感 |
| 导入失败 | 整体事务回滚，避免部分写入 |
| 导入成功 | 写入导入历史，刷新前端元数据缓存 |

### 导入校验规则

| 校验类型 | 说明 |
|---|---|
| JSON 语法校验 | 判断是否为合法 JSON |
| 必填字段校验 | 判断是否包含库名、表名、字段列表等核心信息 |
| 字段结构校验 | 判断字段名、字段类型、字段注释结构是否合理 |
| 重复字段校验 | 同一张表内不允许重复字段名 |
| 类型合法性校验 | 对常见 Hive / Spark 类型做基础校验 |
| 空字段校验 | 表不能没有字段 |
| 危险覆盖校验 | 大量字段消失时需要提示用户确认 |
| 版本校验 | 后续可支持 JSON schema version |

### 导入结果反馈

前端导入完成后应展示：

```text
导入结果
├── 成功导入表数量
├── 新增字段数量
├── 更新字段数量
├── 未变化字段数量
├── 疑似过期字段数量
├── 失败原因
└── 导入历史记录
```

### JSON 导入对其他模块的影响

| 模块 | 影响 |
|---|---|
| SQL 编辑器 | 字段补全、字段 hover、表字段搜索立即更新 |
| 血缘解析 | 字段消歧、select * 展开、字段级血缘更准确 |
| 口径分析 | 分区字段、业务主键、指标配置可用于更准确判断 |
| 诊断模块 | 未知字段、未知表、字段歧义提示更准确 |
| 图谱展示 | 节点详情中可展示字段类型、字段注释、表注释 |
| SQL 重写 | 可基于最新元数据展开字段和做字段裁剪 |

---

## 5. 血缘模型设计

## 5.1 血缘层级

系统需要支持多层级血缘，而不是只做表到表或字段到字段。

| 层级 | 说明 |
|---|---|
| 表级血缘 | 当前 SQL 读取哪些表、写入哪些表 |
| 字段级血缘 | 输出字段来自哪些源字段 |
| 表达式级血缘 | 字段经过哪些函数、聚合、case when、窗口函数加工 |
| 子查询级血缘 | CTE、子查询、派生表之间的依赖 |
| 口径影响关系 | where、join、group by、having、window 对结果的影响 |

## 5.2 节点类型

```text
statement
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
```

## 5.3 边类型

```text
projection        直接投影
alias             字段重命名
expression        表达式派生
aggregation       聚合派生
filter_condition  过滤条件影响
join_condition    join 条件影响
group_by          分组粒度影响
window            窗口函数影响
unknown           未完全解析的依赖
```

## 5.4 直接血缘与影响血缘分离

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

应拆成三类关系：

| 类型 | 示例 | 含义 |
|---|---|---|
| 直接血缘 | `order_amt → gmv` | 输出字段由哪个字段计算得到 |
| 粒度影响 | `user_id → group_by` | 结果按什么粒度聚合 |
| 过滤影响 | `dt → filter_condition` | 哪些条件影响结果范围 |

这个设计可以让系统从“字段连线工具”升级为“SQL 语义理解工具”。

---

## 6. 查询口径分析设计

口径分析模块重点回答：

```text
当前 SQL 最终结果是按什么粒度、什么范围、什么过滤条件、什么指标公式算出来的？
```

## 6.1 口径分析维度

| 维度 | 说明 |
|---|---|
| 查询类型 | select、insert、create table as select、create view |
| 输入输出对象 | 来源表、目标表、中间 CTE |
| 最终粒度 | group by 字段、distinct 字段、窗口分区字段 |
| 过滤范围 | where、having、分区过滤、时间范围 |
| 指标公式 | count、sum、avg、count distinct、case when 指标 |
| join 关系 | join 类型、join key、主从表关系 |
| 去重逻辑 | distinct、row_number、group by |
| 窗口逻辑 | partition by、order by、排序取数 |
| 业务字段解释 | 字段注释、指标注释、表注释 |
| 风险提示 | join 放大、字段歧义、元数据缺失、无分区过滤 |

---

## 7. 前端工作台设计

## 7.1 页面整体布局

```text
┌────────────────────────────────────────────────────┐
│ 顶部工具栏：解析 / 格式化 / 导入元数据 / 导出 / 设置 │
├───────────────────────┬────────────────────────────┤
│ 左侧：SQL 编辑器       │ 右侧：血缘点线图画布         │
│ Monaco Editor         │ React Flow Canvas           │
├───────────────────────┼────────────────────────────┤
│ 下方：诊断结果 / AST   │ 下方：口径分析 / 字段注释     │
└───────────────────────┴────────────────────────────┘
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
| 重写辅助 | select * 展开、字段裁剪、CTE 简化、别名规范化 |

## 7.4 血缘画布能力

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

## 7.5 JSON 元数据导入页面能力

建议新增独立组件：

```text
MetadataImport/
├── JsonUploadPanel       # JSON 文件上传
├── JsonPastePanel        # JSON 文本粘贴
├── JsonValidateResult    # 校验结果
├── ImportPreviewTable    # 导入预览
├── ImportConflictPanel   # 冲突与覆盖提示
├── ImportHistoryPanel    # 导入历史
└── ImportResultSummary   # 导入结果汇总
```

页面核心交互：

| 交互 | 说明 |
|---|---|
| 上传 JSON | 选择本地 JSON 文件 |
| 粘贴 JSON | 在编辑框直接粘贴元数据 JSON |
| 格式校验 | 前端先判断是否为合法 JSON |
| 结构校验 | 后端判断字段结构是否符合元数据导入规范 |
| 导入预览 | 展示新增、更新、未变化、疑似过期字段 |
| 冲突提示 | 提示字段类型变化、字段注释覆盖、字段大量缺失 |
| 确认导入 | 用户确认后才写入 SQLite |
| 导入历史 | 记录每次导入时间、导入表、字段变化、导入状态 |
| 刷新元数据 | 导入成功后刷新字段补全、字段注释、解析上下文 |

---

## 8. 后端服务设计

## 8.1 后端目录

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── domain/
│   │   ├── sql_model.py
│   │   ├── metadata_model.py
│   │   ├── metadata_import_model.py
│   │   ├── lineage_model.py
│   │   ├── semantics_model.py
│   │   └── graph_model.py
│   ├── services/
│   │   ├── sql_parse_service.py
│   │   ├── metadata_service.py
│   │   ├── metadata_import_service.py
│   │   ├── lineage_service.py
│   │   ├── semantics_service.py
│   │   ├── graph_service.py
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

## 8.2 后端模块职责

| 模块 | 职责 |
|---|---|
| SqlParseService | 调用 SQLGlot 完成 SQL AST 解析、方言识别、SQL 标准化 |
| MetadataService | 查询 SQLite 元数据，提供表、字段、注释、业务主键、指标配置 |
| MetadataImportService | 处理 JSON / DDL / CSV 元数据导入、校验、预览、写入 |
| LineageService | 结合 AST 和元数据，生成表级、字段级、表达式级血缘 |
| SemanticsService | 分析查询口径，包括粒度、过滤、聚合、join、窗口函数、指标公式 |
| GraphService | 把血缘结果转换成前端可消费的节点和边 |
| RewriteService | SQL 格式化、字段展开、方言转换、基础重写建议 |
| DiagnosticsService | 识别解析失败、字段歧义、元数据缺失、join 风险、分区风险 |

---

## 9. SQLite 元数据仓库设计

SQLite 在本项目中承担轻量级本地元数据仓库角色。

## 9.1 元数据目录

```text
metadata/
├── sqlite/
│   ├── schema/
│   ├── migrations/
│   └── seeds/
├── importers/
│   ├── json_importer.py
│   ├── ddl_importer.py
│   ├── csv_importer.py
│   └── hive_export_importer.py
└── samples/
```

## 9.2 需要维护的元数据对象

| 元数据对象 | 用途 |
|---|---|
| 库表信息 | 识别 SQL 中引用的真实表 |
| 字段信息 | 支持字段级血缘、字段补全、字段消歧 |
| 字段注释 | 支持前端 hover、字段解释、业务理解 |
| 分区字段 | 支持分区过滤风险检测 |
| 业务主键 / 粒度配置 | 支持 join 风险和结果粒度判断 |
| 指标定义 | 支持指标口径识别和解释 |
| 导入历史 | 支持 JSON 导入追踪和问题回溯 |
| 解析历史 | 支持 SQL 分析结果复用和版本对比 |

---

## 10. 核心分析流程

```text
1. 用户输入 SQL
        ↓
2. 前端提交 SQL、方言、默认库信息
        ↓
3. 后端使用 SQLGlot 解析 SQL AST
        ↓
4. 构建作用域模型：主查询、CTE、子查询、派生表
        ↓
5. 从 SQLite 获取表字段元数据和字段注释
        ↓
6. 字段补全与字段消歧
        ↓
7. 推导表级、字段级、表达式级、子查询级血缘
        ↓
8. 分析查询口径：粒度、过滤、聚合、join、窗口函数
        ↓
9. 生成诊断结果：歧义、缺失、风险、不支持语法
        ↓
10. 输出 Graph JSON 和语义分析结果
        ↓
11. 前端渲染点线图，并与 SQL 编辑器联动
```

---

## 11. JSON 元数据导入流程

```text
1. 用户打开“导入元数据”面板
        ↓
2. 上传 JSON 文件或粘贴 JSON 内容
        ↓
3. 前端做基础 JSON 格式检查
        ↓
4. 后端做结构校验、字段校验、冲突检测
        ↓
5. 生成导入预览
        ↓
6. 前端展示：
   - 新增表
   - 更新表
   - 新增字段
   - 更新字段
   - 未变化字段
   - 疑似过期字段
   - 冲突和风险
        ↓
7. 用户确认导入
        ↓
8. 后端开启事务执行 upsert
        ↓
9. 写入或更新 SQLite 元数据
        ↓
10. 写入导入历史
        ↓
11. 前端刷新元数据缓存
        ↓
12. SQL 编辑器补全、字段 hover、血缘解析立即使用最新元数据
```

---

## 12. 诊断与风险提示设计

诊断模块目标不是简单提示“解析失败”，而是告诉用户：哪里错了、为什么错、会带来什么风险、应该怎么修。

## 12.1 SQL 诊断类型

| 类型 | 说明 |
|---|---|
| 语法解析失败 | SQLGlot 无法解析当前 SQL |
| 未知表 | 元数据仓库中找不到引用表 |
| 未知字段 | 表中找不到引用字段 |
| 字段歧义 | 多张表都有同名字段，但 SQL 未写表别名 |
| select * 风险 | 字段来源依赖元数据展开，可能不稳定 |
| join 放大风险 | join key 不唯一或缺少主键配置 |
| 缺少分区过滤 | 大表扫描风险 |
| 聚合粒度不清晰 | group by、distinct、窗口函数粒度混杂 |
| UDF 黑盒风险 | 无法解析 UDF 内部字段语义 |
| 方言兼容风险 | 当前 SQL 使用了目标方言不支持的语法 |

## 12.2 元数据导入诊断类型

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

## 13. 扩展能力设计

## 13.1 元数据扩展

| 扩展方向 | 说明 |
|---|---|
| Hive Metastore 接入 | 自动同步 Hive 表字段元数据 |
| DataGrip DDL 导入 | 适配本地已有元数据缓存或导出文件 |
| JSON 元数据导入 | 前端上传或粘贴 JSON，并更新 SQLite |
| CSV / Excel 导入 | 适合人工维护字段说明 |
| dbt manifest 导入 | 支持 dbt 模型和字段描述 |
| DataHub / OpenMetadata 对接 | 接入企业级元数据平台 |
| 字段注释搜索 | 基于 SQLite FTS5 做本地字段检索 |

## 13.2 血缘能力扩展

| 扩展方向 | 说明 |
|---|---|
| 多 SQL 文件批量分析 | 支持任务级、项目级血缘分析 |
| 调度任务血缘 | 解析任务脚本中的 SQL |
| OpenLineage 输出 | 兼容通用 lineage event 格式 |
| 血缘版本对比 | 对比不同 SQL 版本的字段变化 |
| 影响分析 | 判断某字段变更会影响哪些输出字段 |
| 字段变更影响评估 | 结合元数据版本判断字段删除或类型变更影响范围 |

## 13.3 SQL 重写与智能辅助扩展

| 扩展方向 | 说明 |
|---|---|
| 字段裁剪 | 找出无用字段和冗余 CTE |
| join 优化提示 | 识别潜在数据膨胀 |
| 口径一致性校验 | 对比两个 SQL 的指标口径差异 |
| 方言转换 | Hive / Spark / StarRocks SQL 转换 |
| AI Review | 基于血缘和口径结果生成 SQL 审查建议 |
| SQL 修改影响分析 | 对比修改前后字段血缘和输出口径变化 |

---

## 14. 推荐开发阶段

## 14.1 第一阶段：MVP 闭环

目标：先跑通 SQL → 元数据 → 字段级血缘 → 画布展示。

核心交付：

```text
1. SQLite 元数据仓库
2. JSON 元数据导入
3. SQLGlot 解析
4. 表级血缘
5. 字段级血缘
6. 基础表达式血缘
7. React Flow 画布
8. Monaco SQL 编辑器
9. 字段注释展示
10. 基础口径分析
11. 基础诊断提示
```

## 14.2 第二阶段：数仓 SQL 增强

目标：覆盖真实数仓开发中高频 SQL。

重点增强：

```text
1. CTE 多层嵌套
2. 子查询
3. insert overwrite
4. create table as select
5. union all
6. group by 聚合
7. case when
8. window function
9. select * 展开
10. join 风险检测
11. 分区过滤检测
```

## 14.3 第三阶段：高级交互工作台

目标：让用户真正通过这个工具理解和重写 SQL。

重点增强：

```text
1. SQL 与图谱双向定位
2. 上游 / 下游路径高亮
3. 表级 / 字段级 / 表达式级 / 口径级切换
4. 节点折叠和懒加载
5. SQL 重写建议
6. SQL 修改前后血缘 diff
7. 分析结果导出
8. 解析历史管理
9. 元数据导入历史管理
```

## 14.4 第四阶段：平台化扩展

目标：从本地工具升级成可持续维护的平台。

重点增强：

```text
1. Hive Metastore 接入
2. 查询日志 / 调度任务 SQL 批量解析
3. DataHub / OpenMetadata / OpenLineage 对接
4. 多项目空间
5. 元数据版本管理
6. 权限与用户体系
7. 大图性能优化
8. 自动化测试和回归基准
```

---

## 15. 测试与质量保障

字段级血缘很容易出现“图看起来对，但字段来源错”的问题，因此测试体系必须从第一阶段就建立。

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
├── metadata_tests/
├── metadata_import_tests/
├── lineage_tests/
├── semantics_tests/
├── graph_tests/
└── e2e_tests/
```

## 15.1 测试重点

| 测试类型 | 目标 |
|---|---|
| Golden Case | 固定 SQL 输入与期望血缘输出 |
| Snapshot Test | 防止图节点和边结构意外变化 |
| Metadata Test | 验证字段注释、字段类型、分区字段正确导入 |
| JSON Import Test | 验证 JSON 导入、更新、冲突、回滚 |
| Ambiguity Test | 验证字段歧义能被识别 |
| Regression Test | 防止新语法支持破坏旧逻辑 |
| E2E Test | 验证 SQL 输入、元数据导入、解析、画布展示完整链路 |

---

## 16. 最终项目目录

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
│   │   │   ├── sql_model.py
│   │   │   ├── metadata_model.py
│   │   │   ├── metadata_import_model.py
│   │   │   ├── lineage_model.py
│   │   │   ├── semantics_model.py
│   │   │   └── graph_model.py
│   │   ├── services/
│   │   │   ├── sql_parse_service.py
│   │   │   ├── metadata_service.py
│   │   │   ├── metadata_import_service.py
│   │   │   ├── lineage_service.py
│   │   │   ├── semantics_service.py
│   │   │   ├── graph_service.py
│   │   │   └── rewrite_service.py
│   │   ├── repositories/
│   │   │   ├── metadata_repository.py
│   │   │   ├── metadata_import_repository.py
│   │   │   ├── analysis_repository.py
│   │   │   └── metric_repository.py
│   │   ├── adapters/
│   │   │   ├── sqlglot_adapter.py
│   │   │   ├── json_metadata_importer.py
│   │   │   ├── ddl_importer.py
│   │   │   ├── csv_importer.py
│   │   │   └── hive_export_importer.py
│   │   ├── diagnostics/
│   │   └── config/
│   ├── tests/
│   └── pyproject.toml
│
├── metadata/
│   ├── sqlite/
│   │   ├── schema/
│   │   ├── migrations/
│   │   └── seeds/
│   ├── importers/
│   │   ├── json_importer.py
│   │   ├── ddl_importer.py
│   │   ├── csv_importer.py
│   │   └── hive_export_importer.py
│   └── samples/
│
├── docs/
│   ├── architecture.md
│   ├── lineage-model.md
│   ├── metadata-import.md
│   ├── semantics-analysis.md
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

## 17. 最终架构判断

本项目最终应形成以下能力闭环：

```text
SQLGlot 负责解析 SQL 结构
SQLite 负责维护元数据与字段注释
JSON 导入负责让用户低成本维护表字段信息
LineageService 负责生成血缘关系
SemanticsService 负责解释查询口径
DiagnosticsService 负责识别 SQL 和元数据风险
GraphService 负责生成前端图模型
React Flow 负责点线图交互
Monaco Editor 负责在线 SQL 编译器体验
```

最重要的工程边界：

> 不要把 SQL 解析、元数据导入、元数据查询、血缘推导、口径分析、前端图展示混在一起。每个模块只解决一个核心问题，模块之间通过稳定的数据模型交互。

最重要的第一性原理：

> 字段级血缘 = SQL AST + 元数据约束 + 作用域解析 + 字段依赖图。没有元数据，就只能做不可靠的文本级推断。

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
