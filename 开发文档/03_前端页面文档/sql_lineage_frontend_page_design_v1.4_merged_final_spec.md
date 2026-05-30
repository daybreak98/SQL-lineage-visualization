# SQL 血缘解析工作台｜前端页面设计文档 v1.4（Merged Final Spec）

> 基准文档：`sql_lineage_frontend_agent_implementation_checklist_v1.3_p0_core.md`  
> 合并输入：
> - `sql_lineage_frontend_page_design_v1.4_node_visual_canvas_priority_final_spec.md`
> - `sql_lineage_frontend_page_design_v1.4_node_visual_canvas_priority_review.md`
>
> 本版定位：以 v1.3 的 **P0-Core 开发任务、M1-M7 里程碑、状态单源约束、任务型验收** 为实现基线，吸收 v1.4 的 **Node Visual Taxonomy、Default Subquery Dependency View、Toolbar Deduplication、Primary CTA Emphasis、Canvas Space Budget**，形成可直接进入 Agent 开发的前端页面最终设计规格。
>
> 合并原则：**不扩功能、不增加低频控制、不改变 P0-Core 闭环；只让用户更快看懂图、更快找到主操作、更少被辅助控件干扰。**

---

## 0. 最终结论

v1.4 的核心不是继续增加业务能力，而是在 v1.3 已经稳定的任务链路上做最后一轮 UI/UX 收敛：

```text
v1.3 P0-Core Baseline
= Analyze → Search / Default Output → Current Path → DetailPanel Mapping → Locate SQL → Re-analyze

v1.4 Final UI/UX Merge
= v1.3 P0-Core Baseline
+ Default Subquery Dependency View
+ Node Visual Taxonomy
+ GraphRenderMode State Machine
+ SubqueryDependencyViewModel
+ Node State Priority Matrix
+ Toolbar Deduplication
+ Primary CTA Emphasis
+ Canvas Space Budget
+ Visual Regression Snapshots
```

最终产品阅读顺序固定为：

```text
默认先看子查询级依赖；
选输出字段后再看字段路径；
点边 / 节点后看映射；
最后才定位 SQL。
```

这意味着：**Analyze 成功后不默认展示字段级复杂全图，也不默认 Full Graph Preview；默认先展示 SQL 的结构依赖，再由用户选择输出字段进入字段级路径。**

---

## 1. 合并取舍

### 1.1 完整采纳

| 来源 | 内容 | 处理 |
|---|---|---|
| v1.3 Checklist | P0-Core 主链路 | 完整保留 |
| v1.3 Checklist | PageMode / AnalysisStatus / TrustStatus 分离 | 完整保留 |
| v1.3 Checklist | AttentionViewModel 派生模型 | 完整保留 |
| v1.3 Checklist | PathContextStore 单一事实源 | 完整保留 |
| v1.4 Final | Node Visual Taxonomy | 合入 P0-Core UI 规则 |
| v1.4 Final | Default Subquery Dependency View | 合入默认图谱入口 |
| v1.4 Final | Toolbar Deduplication | 合入 TopBar / CanvasToolbar 规则 |
| v1.4 Final | Primary CTA Emphasis | 合入 PageMode → CTA 映射 |
| v1.4 Final | Canvas Space Budget | 提升为 P0 阻塞验收 |

### 1.2 修正采纳

| v1.4 原方向 | 本版修正 |
|---|---|
| 默认进入 Subquery Dependency View | 增加 `GraphRenderMode State Machine`，明确进入、退出、是否保留 viewport、是否重算 layout |
| 强化节点视觉分类 | 增加 `Node State Priority Matrix`，避免 selected / current_path / warning / dimmed 样式冲突 |
| 输出侧可展示 OutputField / OutputGroup | 增加 OutputGroup / OutputField 展示阈值，防止 20+ 输出字段挤爆默认视图 |
| 删除重复布局按钮 | 保留 `More → Reset split ratio / Reset workspace layout` 的低频恢复入口 |
| 画布空间预算 | 增加小高度、长文案、工具栏拥挤时的自动降级规则 |
| 验收测试 | 增加固定 Visual Regression Snapshot 名称，便于 Agent 回归 |

### 1.3 明确后置

以下内容不进入 P0-Core：

```text
Raw JSON Viewer
Golden Case Save UI
Export PNG / SVG / Markdown
History / Diff
完整 Metadata Import UI
Full Semantics Report
多 SQL Tab / 多文件工作区
完整 Right Inspector 高级详情
完整快捷键帮助系统
完整小屏体验优化
```

---

## 2. P0-Core 不可变目标

| 编号 | 目标 | 验收 |
|---|---|---|
| G-01 | Monaco Editor + Lineage Canvas 双核心同屏 | 1366px 宽度下仍可同时编辑 SQL 与查看图谱 |
| G-02 | Analyze 主链路可运行 | 点击 Analyze 后能拿到 AnalysisResult 并进入 analyzed / failed |
| G-03 | 默认进入子查询级结构视图 | Analyze 成功后默认 `renderMode=subquery_dependency` |
| G-04 | 默认输出字段入口可发现 | Analyze 成功后，不输入搜索词也能选择后端返回的 default outputs |
| G-05 | 当前字段路径可读 | 选择输出字段后，Canvas 中当前路径成为 L1 主视觉 |
| G-06 | DetailPanel compact 可回答核心问题 | 能展示选中对象、mapping summary、Locate SQL |
| G-07 | Dirty / Stale 可信边界明确 | SQL 修改后旧图保留但明确 stale，Re-analyze 重新成为主 CTA |
| G-08 | 前端不推断血缘 | 字段搜索、字段路径、字段映射均来自后端 API 或 AnalysisResult |
| G-09 | React Flow / Monaco 不污染业务层 | 业务组件只依赖 Adapter Port，不直接传递第三方实例 |
| G-10 | 拖拽性能不破坏 | 拖拽节点不触发 layout、不全局 dispatch、不重算 path |
| G-11 | 节点类型一眼可分辨 | Output / Subquery / CTE / Table / Expression / Unknown 有稳定视觉区分 |
| G-12 | 画布空间预算可控 | 1366×768 analyzed 状态下图谱核心区仍具备舒适可读面积 |
| G-13 | 任务型验收可执行 | Smoke / Regression / Scenario / Visual Snapshot 均有固定用例 |

---

## 3. 页面主任务链路

### 3.1 用户主链路

```text
写 SQL
→ Analyze
→ 默认进入 Subquery Dependency View
→ Search / Default Output
→ Current Field Path
→ DetailPanel Mapping
→ Locate SQL
→ 修改 SQL 后 Re-analyze
```

### 3.2 分阶段主焦点

| 阶段 | 主焦点 | 页面行为 |
|---|---|---|
| empty | Empty Guide / Paste SQL | 画布不放大插画，Editor 可输入 |
| ready | Analyze Button | TopBar Analyze 是唯一主蓝 CTA |
| analyzing | Canvas Skeleton + Analyze loading | Search / Path 禁用 |
| analyzed 未选字段 | Default Outputs / SearchBar | 默认图为 `subquery_dependency` |
| 已选字段 | Current Field Path | 图谱切到 `current_field_path`，自动 fitPath |
| 已选节点 / 边 | DetailPanel Mapping | compact 三行模板展示映射 |
| locate SQL | Monaco Range Highlight | 根据 SourceLocation guard 判断强 / 弱定位 |
| dirty | Re-analyze CTA | 旧图保留但标记 stale |
| failed | Error Summary + SQL Marker | Search 禁用，Editor marker 定位错误 |

---

## 4. 状态模型

### 4.1 PageMode / AnalysisStatus / TrustStatus

```ts
export type PageMode =
  | 'empty'
  | 'ready'
  | 'analyzing'
  | 'analyzed'
  | 'dirty'
  | 'failed';

export type AnalysisStatus =
  | 'none'
  | 'running'
  | 'success'
  | 'partial'
  | 'failed'
  | 'cancelled'
  | 'timeout';

export type TrustStatus =
  | 'trusted'
  | 'stale'
  | 'untrusted';

export type StaleReason =
  | 'sql_changed'
  | 'metadata_changed'
  | 'analysis_expired';

export interface WorkbenchRuntimeState {
  pageMode: PageMode;
  analysisStatus: AnalysisStatus;
  trustStatus: TrustStatus;
  analysisId?: string;
  sqlHash?: string;
  metadataVersion?: string;
  staleReason?: StaleReason;
  lastTrustedAnalysisId?: string;
  lastTrustedSqlHash?: string;
}
```

### 4.2 状态映射

| 场景 | pageMode | analysisStatus | trustStatus |
|---|---|---|---|
| 无 SQL | empty | none | untrusted |
| 有 SQL 未分析 | ready | none | untrusted |
| 分析中 | analyzing | running | untrusted |
| 成功 | analyzed | success | trusted |
| 部分成功 | analyzed | partial | trusted |
| SQL 修改 | dirty | success / partial | stale |
| 分析失败 | failed | failed | untrusted |
| 超时但有部分结果 | analyzed | timeout / partial | trusted 或 stale，取决于是否与当前 SQL 匹配 |

### 4.3 状态一致性硬规则

```text
1. SQL 文本变化后，pageMode 必须变为 dirty。
2. dirty 状态下，Canvas / SearchBar / Output Capsule / DetailPanel / BottomStatusStrip 必须同步 stale。
3. dirty 状态下，旧图可看，但不能 exact reveal，不能请求新 path。
4. analysis_id / sql_hash / metadata_version 不匹配时，不执行 SourceLocation exact reveal。
5. partial 不是 failed，可用路径继续展示，但必须说明影响范围。
6. failed 状态下，SearchBar 禁用，Canvas 显示错误摘要，Editor marker 指向错误位置。
```

---

## 5. AttentionViewModel：注意力只派生，不作为事实源

### 5.1 设计原则

注意力模型用于表达“当前用户应该看哪里”，但它不能成为新的事实源。`primaryFocus` 必须从 `WorkbenchRuntimeState + PathContextStore + SelectionState + Diagnostics` 派生。

禁止：

```ts
setPrimaryFocus('current_path')
```

### 5.2 接口

```ts
export interface AttentionViewModel {
  primaryFocus:
    | 'empty_guide'
    | 'analyze'
    | 'search_default_output'
    | 'current_path'
    | 'detail_mapping'
    | 'monaco_range'
    | 're_analyze'
    | 'error_summary';

  taskStage:
    | 'empty'
    | 'ready'
    | 'analyzing'
    | 'analyzed_no_field'
    | 'path_selected'
    | 'object_selected'
    | 'locating_sql'
    | 'dirty'
    | 'failed';

  reason: string;

  source:
    | 'page_mode'
    | 'path_context'
    | 'selection'
    | 'diagnostic'
    | 'editor_dirty';
}
```

### 5.3 派生规则

| 条件 | primaryFocus |
|---|---|
| pageMode = empty | empty_guide |
| pageMode = ready | analyze |
| pageMode = analyzing | analyze |
| pageMode = failed | error_summary |
| pageMode = dirty | re_analyze |
| pageMode = analyzed 且没有 selectedOutputEntityId | search_default_output |
| selectedEdgeMappingId 存在 | detail_mapping |
| selectedEntityId 存在且 DetailPanel 打开 | detail_mapping |
| selectedOutputEntityId 存在 | current_path |
| 正在 reveal SQL | monaco_range |

---

## 6. PathContextStore：当前路径唯一事实源

### 6.1 单源原则

以下区域只能消费 `PathContextStore`，不得维护第二套当前路径状态：

```text
Output Capsule
Current Path Anchor
Canvas Highlight
DetailPanel Header
BottomStatusStrip selected entity
Toolbar path mode
```

### 6.2 接口

```ts
export interface PathContextStore {
  selectedOutputEntityId?: string;
  selectedOutputDisplayName?: string;

  pathMode: 'none' | 'upstream' | 'downstream' | 'full';

  pathStatus:
    | 'idle'
    | 'ready'
    | 'partial'
    | 'stale'
    | 'low_confidence'
    | 'failed';

  pathRef?: PathRef;

  nodeCount?: number;
  mappingCount?: number;
  warningCount?: number;
  unresolvedCount?: number;

  confidenceLevel?: 'high' | 'medium' | 'low' | 'unknown';

  staleReason?: 'sql_changed' | 'metadata_changed' | 'analysis_expired';
}
```

### 6.3 禁止事项

```text
1. 禁止 Output Capsule 自己维护 selectedOutputField。
2. 禁止 DetailPanel Header 自己拼接 pathStatus。
3. 禁止 Canvas Highlight 和 PathContextStore 分别维护 pathRef。
4. 禁止 BottomStatusStrip 自己维护 selected field。
5. 禁止 path partial / stale / warning 在各组件中分别计算。
```

---

## 7. GraphRenderMode State Machine

### 7.1 renderMode 类型

```ts
export type GraphRenderMode =
  | 'subquery_dependency'
  | 'current_field_path'
  | 'focus_field'
  | 'semantic_mode'
  | 'large_graph'
  | 'full_graph_preview';
```

### 7.2 状态迁移接口

```ts
export interface GraphRenderModeTransition {
  from: GraphRenderMode;
  event:
    | 'ANALYZE_SUCCESS'
    | 'SELECT_OUTPUT_FIELD'
    | 'FOCUS_FIELD'
    | 'OPEN_SEMANTIC_MODE'
    | 'ENTER_LARGE_GRAPH'
    | 'OPEN_FULL_PREVIEW'
    | 'CLEAR_SELECTION'
    | 'REANALYZE'
    | 'ANALYZE_FAILED';
  to: GraphRenderMode;
  preserveViewport: boolean;
  recomputeLayout: boolean;
}
```

### 7.3 迁移规则

| 当前状态 | 事件 | 目标状态 | viewport | layout | 说明 |
|---|---|---|---|---|---|
| 任意 | ANALYZE_SUCCESS | subquery_dependency | 否 | 是 | 首次展示结构图，可 fitView |
| subquery_dependency | SELECT_OUTPUT_FIELD | current_field_path | 否 | 否 | 请求 path patch，不全图重算 |
| current_field_path | FOCUS_FIELD | focus_field | 是 | 否 | 局部展开字段节点 |
| current_field_path | OPEN_SEMANTIC_MODE | semantic_mode | 是 | 否 | 展示 Join / Filter / Aggregate 影响 |
| 任意 | ENTER_LARGE_GRAPH | large_graph | 是 | 否 | 渲染降级，不代表失败 |
| 任意 | OPEN_FULL_PREVIEW | full_graph_preview | 否 | 可选 | 必须用户主动触发 |
| current_field_path / focus_field / semantic_mode | CLEAR_SELECTION | subquery_dependency | 否 | 否 | 回到默认结构图 |
| 任意 | ANALYZE_FAILED | subquery_dependency | 否 | 否 | 图谱展示错误摘要，不伪展示结果 |

### 7.4 硬规则

```text
1. ANALYZE_SUCCESS 可以触发 fitView，但不展开字段节点。
2. SELECT_OUTPUT_FIELD 只请求 path patch，不重新全图布局。
3. CLEAR_SELECTION 回到 subquery_dependency。
4. OPEN_FULL_PREVIEW 必须用户主动触发。
5. large_graph 是渲染降级模式，不等于能力失败。
```

---

## 8. SubqueryDependencyViewModel

### 8.1 定位

`SubqueryDependencyViewModel` 是 GraphAdapter 从 Graph Fact Layer 派生出的默认结构视图。它只决定当前可见节点和边，不删除字段级实体，不修改后端 GraphViewModel。

### 8.2 接口

```ts
export interface SubqueryDependencyViewModel {
  renderMode: 'subquery_dependency';

  nodes: Array<
    | TableSummaryNode
    | CteSummaryNode
    | SubquerySummaryNode
    | OutputGroupNode
    | OutputFieldNode
    | ExpressionGroupNode
  >;

  edges: Array<DependencySummaryEdge>;

  hiddenFieldEntityIds: string[];
  hiddenSemanticEdgeIds: string[];

  defaultOutputEntityIds: string[];

  diagnosticsSummary: DiagnosticsSummary;
}
```

### 8.3 生成规则

```text
1. FieldNode 默认不进入 nodes，但 field entity 必须保留在 Graph Fact Layer。
2. Join / Filter dependency 默认不进入主边层，只进入 edge metadata 或 semantic layer。
3. OutputGroup 必须稳定存在，即使最终只有一个输出字段。
4. Subquery 无 alias 时使用稳定 subquery_n，不能用渲染顺序随机生成。
5. 同源同目标多字段映射聚合为 DependencySummaryEdge。
6. CTE / Subquery 层级必须稳定，不允许与 Table 随机混层。
7. 表到 CTE / Subquery 的边与字段级边必须分离。
8. defaultOutputEntityIds 由后端或 GraphAdapter 基于输出字段事实生成，前端不得从 SQL 文本猜测。
```

### 8.4 字段级血缘不降级

**Subquery Dependency View 是默认阅读视图，不是血缘能力上限。**

验收：

```text
1. Subquery Dependency View 不展示全量字段节点。
2. 字段级实体仍保留在 Graph Fact Layer。
3. 选择 output field 后能进入 Current Field Path。
4. DetailPanel 能展示 source_field → target_field。
5. Focus Field Mode 能局部展开字段节点。
6. SourceLocation 仍能定位字段级 SQL range。
```

---

## 9. OutputGroup / OutputField 默认展示规则

| 输出字段数量 | 默认展示 | 原因 |
|---:|---|---|
| 1-5 | 可展示 OutputField 节点 | 字段少，直接展示更直观 |
| 6-20 | 展示 OutputGroup + Search / Default Output Capsule | 避免首屏被字段节点占满 |
| 20+ | 必须只展示 OutputGroup | 防止默认结构图被输出字段挤爆 |

规则：

```text
1. 20+ 输出字段不得在 Subquery Dependency View 中默认全部渲染为 OutputField 节点。
2. 字段级路径入口仍由 Search / Default Output Capsule 承担。
3. OutputGroup 点击后 DetailPanel 展示输出字段数量、默认 outputs、warning 摘要。
4. OutputGroup 必须有稳定 entity_id，不能按渲染顺序生成。
```

---

## 10. Node Visual Taxonomy

### 10.1 节点视觉优先级

```text
输出节点 > 子查询 / CTE 节点 > 源表节点 > 表达式节点 > 其他辅助节点
```

### 10.2 节点视觉总表

| 节点类型 | 视觉目标 | 边框 | 框内背景 | 左侧强调条 / 标题 | Badge | 说明 |
|---|---|---|---|---|---|---|
| Output | 最强识别 | 主蓝 2px 实线 | 很浅蓝 | 主蓝条 | OUT | 用户最终关注点 |
| Subquery | 明显区别于表 | 蓝紫虚线或双层边框 | 浅紫 | 紫色条 | SUBQ | 默认核心结构节点 |
| CTE | 中间逻辑块 | 天蓝实线 | 浅青 | 青蓝条 | CTE | 稳定逻辑块 |
| Table | 最克制 | 灰蓝细实线 | 白 / 极浅灰 | 灰蓝条，可无 badge | 可无 | 数量最多，不抢主视觉 |
| Expression | 辅助逻辑 | 紫色细边 | 很浅紫 | 紫色细条 | EXPR | 只解释派生逻辑 |
| Join / Filter | 语义辅助 | 橙灰细边或虚线 | 白 / 浅橙 | 橙色细条 | COND | 默认弱化 |
| Unknown / Unresolved | 风险明显 | 橙色 1.5-2px | 浅橙 | 橙条 + warning | ? | 必须可快速识别 |

### 10.3 节点尺寸

| 节点类型 | 默认宽度 | 默认高度 | 说明 |
|---|---:|---:|---|
| Table | 124-156px | 36px | 最常见，尽量小 |
| CTE | 132-168px | 38px | 比 Table 稍强 |
| Subquery | 140-180px | 40px | 默认结构核心 |
| Output | 144-184px | 40px | 最强识别 |
| Expression | 132-172px | 38px | 辅助节点 |
| Unknown | 124-156px | 36px | 风险态但不膨胀 |

### 10.4 节点正文规则

允许展示：

```text
table_name / alias
cte_name
subquery_alias / subquery_n
output_field_name / output_group_name
expression_type：CASE / SUM / COUNT / WINDOW / ARITH
unknown raw name
1~2 个结构摘要标签：agg / join / filter / group by
```

禁止展示：

```text
字段类型
字段注释
字段数量
完整表达式
完整库表路径
完整 SQL 片段
长诊断文本
```

### 10.5 子查询节点特殊规范

子查询节点必须成为默认图中的核心节点，不能看起来像普通表。

```text
主标题：alias 优先；无 alias 时 subquery_n
副提示：SUBQ · agg / join / filter / group by 中最多 2 个
```

规则：

```text
1. alias 优先显示。
2. 无 alias 时使用稳定 subquery_n。
3. 摘要标签最多 2 个，避免节点变高。
4. 完整 SQL 摘要进入 DetailPanel，不进入节点正文。
5. 子查询节点边框必须与 Table 明显不同。
```

### 10.6 Table 节点规范

```text
Table 节点是上下文，不是主角。
```

规则：

```text
1. 普通表默认只显示 alias 或 table_name。
2. Source Table 默认不显示 TBL badge，减少噪声。
3. self join 必须显示 alias，如 `a · user_table` / `b · user_table`。
4. 同名表不同库显示短 schema，如 `orders · mart` / `orders · ods`。
5. 完整路径进入 hover / DetailPanel。
```

### 10.7 Unknown / Unresolved 节点规范

```text
Unknown 是可信度风险，不是普通节点。
```

规则：

```text
1. 必须有非颜色提示：? badge / warning icon / dashed border。
2. 当前路径上的 unknown 应显著可见。
3. 背景 unknown 只保留小 warning dot，避免抢主路径。
4. DetailPanel 必须说明 unknown 原因：metadata_missing / ambiguous / unsupported / parse_partial。
```

---

## 11. Node State Priority Matrix

### 11.1 状态优先级

```text
selected > error > current_path > search_hit > warning > stale > hover > dimmed > normal
```

### 11.2 状态叠加规则

| 状态 | 是否改变布局尺寸 | 是否覆盖类型色 | 说明 |
|---|---|---|---|
| selected | 否 | 不覆盖 | 使用外圈 ring，不改变节点尺寸 |
| error | 否 | 可叠加红点 / 红边 | 只在 blocking 或当前路径相关时增强 |
| current_path | 否 | 不覆盖 | 背景轻蓝 + 边框增强 |
| search_hit | 否 | 不覆盖 | 短暂外圈或定位标识，禁止循环动画 |
| warning | 否 | 不覆盖 | 小点 / icon，不大面积橙色 |
| stale | 否 | 不覆盖 | 灰色 badge / opacity 微降 |
| hover | 否 | 不覆盖 | 轻背景，不抢 selected |
| dimmed | 否 | 降透明度 | selected/current_path 不被 dimmed 覆盖 |

### 11.3 验收

```text
1. selected 节点不会被 dimmed 覆盖。
2. warning 不覆盖 current_path 主视觉。
3. 状态变化不改变节点尺寸。
4. search_hit 不使用循环 pulse 或呼吸阴影。
5. dragging 时暂停 hover detail / tooltip / edge label。
```

---

## 12. CSS / data-state 实现约束

节点视觉必须通过稳定 class 和 data-state 实现，避免破坏 React.memo 和 React Flow 性能。

```tsx
<div
  className="lineage-node"
  data-node-type={nodeType}
  data-selected={selected || undefined}
  data-current-path={currentPath || undefined}
  data-warning={warning || undefined}
  data-error={error || undefined}
  data-stale={stale || undefined}
  data-dimmed={dimmed || undefined}
>
  ...
</div>
```

规则：

```text
1. 节点视觉优先通过 CSS class / data-node-type 实现。
2. 禁止在 node.data 中塞完整样式对象导致 React.memo 失效。
3. 禁止节点使用复杂 box-shadow、filter、blur、渐变动画。
4. badge 和状态点使用纯 CSS 或轻量 icon。
5. selected / current_path / dimmed 使用 data-state 组合，不重写完整 nodes 数组。
6. Large Graph Mode 通过根 class 降级阴影、动画、label，而不是逐节点计算样式。
```

---

## 13. Edge Readability for Subquery Dependency View

### 13.1 默认边线策略

| 边类型 | 默认视觉 | 当前路径 / selected |
|---|---|---|
| Table → CTE/Subquery | 灰蓝细实线 | 蓝灰增强 |
| CTE → CTE | 青蓝实线 | 主蓝增强 |
| Subquery → Subquery | 蓝紫实线或轻虚线 | 蓝紫增强 |
| CTE/Subquery → Output | 主蓝增强线 | 主蓝 2px |
| Expression → Output | 淡紫线 | 紫色 2px |
| Join / Filter dependency | 弱虚线 | 仅 semantic_mode / selected 增强 |
| Unknown edge | 橙色虚线 | warning icon |

### 13.2 边线阅读层级

| 层级 | 内容 | 视觉 |
|---|---|---|
| L1 | selected edge / current output path edge | 2-2.5px，置顶 |
| L2 | subquery dependency edge | 1.5-2px，清晰但不重 |
| L3 | table source edge | 1.2px，低噪声 |
| L4 | semantic dependency | 虚线，低透明 |
| L5 | background edge | 低透明，不显示标签 |

### 13.3 Edge Group 规则

```text
1. 同源同目标的多条字段映射默认聚合为 edge group。
2. 当前路径内 edge group 可展开为字段级 mapping。
3. 非当前路径 edge group 不显示字段级标签。
4. hover 命中区域必须大于视觉线宽，避免 1px 线难点。
5. join/filter dependency 不是第一阅读入口，默认弱化。
```

---

## 14. SearchBar / Output Capsule / PathContext

### 14.1 40px 单行规则

Canvas 顶部仍保持 40px 单行，不允许常驻两行。

```text
左侧：Search Input
右侧：Output / Current Path Capsule
```

### 14.2 宽度响应式

| Canvas 宽度 | SearchBar 表现 |
|---:|---|
| `<560px` | 只显示 Search icon + Current Capsule；点击 Search 打开 Popover |
| `560-760px` | Search Input 使用短 placeholder；Capsule 只显示 field + status dot |
| `760-980px` | Search Input + compact Capsule 同屏 |
| `>980px` | Search Input + full Capsule 同屏 |

### 14.3 文案收敛

| 状态 | Search | Capsule | PathContext |
|---|---|---|---|
| 未选字段 | Search field, table, alias... | Choose output field | No output selected |
| 已选字段 | Search another field... | Current: order_cnt | Full path · 8 nodes · 12 mappings · 2 warnings |
| Dirty | Search disabled until re-analyze | order_cnt path stale | SQL changed · Re-analyze required |
| partial | Search field... | order_cnt · partial | Partial lineage · 2 unresolved mappings |
| low confidence | Search field... | order_cnt · low | Source uncertain · verify mapping |

### 14.4 禁止重复

```text
1. 禁止 SearchBar、Toolbar、DetailPanel 三处重复完整字段路径长文案。
2. 禁止 stale / partial 长提示同时出现在多个区域。
3. 禁止 Choose output 与 Current output 两个入口并列抢注意力。
4. 禁止 DetailPanel 重复 BottomStatusStrip 的全局状态。
```

---

## 15. Toolbar Deduplication

### 15.1 TopBar 允许项

```text
Analyze / Re-analyze
Cancel
Format
Dialect
Metadata
More
```

### 15.2 CanvasToolbar 允许项

```text
Fit Path
Center Selected
Reset Viewport
Path Direction（仅在实现后显示）
Legend（icon only）
```

### 15.3 禁止常驻项

```text
SQL Focus
Graph Focus
Max Canvas
Reset Split Ratio as visible primary control
Any duplicated layout area control
```

### 15.4 布局恢复入口

删除重复布局按钮，不等于删除恢复能力。

```text
More → Reset split ratio
More → Reset workspace layout
CanvasToolbar → Reset viewport
```

规则：

```text
1. Reset split ratio 不在 TopBar 常驻展示。
2. Reset viewport 可以在 CanvasToolbar 保留。
3. Reset layout 与 Reset viewport 要区分。
4. Reset workspace layout 需要二次确认或弱化处理，避免误点。
```

---

## 16. Primary CTA Emphasis

### 16.1 主 CTA 状态表

| PageMode | 主 CTA | 区域 | 视觉 |
|---|---|---|---|
| empty | Paste SQL / Load Example | Empty / TopBar | 次主按钮 |
| ready | Analyze | TopBar | 主蓝实心 |
| analyzing | Cancel | TopBar | loading + 次危险 |
| analyzed 未选字段 | Choose Output / Search | CanvasTopSearchBar | L1 转移到 Canvas |
| analyzed 已选字段 | Fit Path / Locate SQL | Canvas / Detail | Analyze 降权 |
| dirty | Re-analyze | TopBar | 主蓝实心 + stale 提示 |
| failed | Fix SQL / Re-analyze | TopBar / Canvas Error | 主 CTA |
| partial | Search / View Diagnostics | Canvas / Status | 按影响范围处理 |

### 16.2 视觉约束

```text
1. 任意时刻最多一个主蓝实心按钮。
2. Analyze / Re-analyze 必须明显高于 Format、View、More。
3. analyzed 后，TopBar 不再是 L1；Canvas 变成 L1。
4. dirty 后，Re-analyze 恢复为 L1。
5. failed 后，Fix SQL / Re-analyze 与 Editor marker 联动。
```

---

## 17. Canvas Space Budget

### 17.1 常驻高度预算

| 区域 | 预算 |
|---|---:|
| CanvasTopSearchBar | 40px |
| CanvasToolbar + Inline PathContext | 36px |
| DetailPanel collapsed | 36px |
| DetailPanel compact | 84-96px |
| DetailPanel expanded | 132-180px，用户主动 |
| DetailPanel max | 220px，用户主动 |

### 17.2 硬规则

```text
1. Canvas 上方长期常驻控件最多两层。
2. 禁止 SearchBar / Toolbar / PathContext 各自独立成三层。
3. 禁止为提示文案增加大 banner。
4. Search suggestions 以 popover 展示，不新增常驻行。
5. DetailPanel 点击节点 / 边默认只打开 compact。
6. DetailPanel 不因内容多自动撑高，内容过长内部滚动。
7. DetailPanel 开关不触发 graph layout。
8. compact 默认三行模板，不默认 Tab 化。
```

### 17.3 自动降级规则

| 场景 | 处理 |
|---|---|
| 视口高度 < 760px | DetailPanel 点击后默认 collapsed 或 84px compact |
| Search suggestions 打开 | 使用 popover，不新增常驻行 |
| PathContext 过长 | 截断为 capsule + tooltip |
| Toolbar 宽度不足 | 低频按钮进入 More |
| DetailPanel 内容过长 | 内部滚动，不撑高 |
| 1366×768 analyzed | Canvas top controls ≤ 76px，compact detail ≤ 96px |

---

## 18. CanvasBottomDetailPanel compact

### 18.1 固定三行结构

选中输出字段：

```text
第 1 行：order_cnt · Output Field · high confidence · 1 warning
第 2 行：source: pay_order.order_no → target: order_cnt · aggregate: count(distinct)
第 3 行：[Locate SQL] [Focus Path] [View Mapping]
```

选中节点：

```text
第 1 行：entity name · type · confidence
第 2 行：Upstream 3 fields · Downstream 1 output · 2 diagnostics
第 3 行：[Locate SQL] [Focus Path] [Expand]
```

选中边：

```text
第 1 行：source_field → target_field · relation_type · confidence
第 2 行：expression / aggregate / alias summary
第 3 行：[Locate SQL] [View Mapping] [Expand]
```

### 18.2 禁止

```text
1. compact 默认出现 4 个以上 Tab。
2. compact 默认展示完整 SQL。
3. compact 默认展示完整字段注释。
4. compact 内出现超过 5 个 key-value。
5. compact 与 BottomStatusStrip 重复展示全局状态。
6. compact 默认展示完整 Semantics。
```

---

## 19. Diagnostic Attention 绑定 DiagnosticCode

### 19.1 接口

```ts
export interface DiagnosticAttentionRule {
  diagnosticCode: string;
  defaultSeverity: 'info' | 'warning' | 'error';

  attentionLevel: 'L1' | 'L2' | 'L3' | 'L4';

  blocking: boolean;

  placement:
    | 'canvas_error_summary'
    | 'path_anchor'
    | 'detail_panel'
    | 'status_strip'
    | 'diagnostics_drawer'
    | 'editor_marker'
    | 'search_result_row';

  recommendedAction?:
    | 'locate_sql'
    | 'view_mapping'
    | 'reanalyze'
    | 'check_metadata'
    | 'switch_scope'
    | 'view_diagnostics';
}
```

### 19.2 默认映射

| DiagnosticCode | Attention | Placement | 动作 |
|---|---|---|---|
| PARSE_ERROR | L1 | Canvas error summary + Editor marker | locate_sql |
| UNKNOWN_TABLE | L2 / L3 | Path Anchor if current path related; otherwise StatusStrip | check_metadata |
| UNKNOWN_COLUMN | L2 | DetailPanel / Path Anchor | view_mapping |
| AMBIGUOUS_COLUMN | L2 | SearchPopover / DetailPanel | switch_scope |
| LOW_CONFIDENCE_LINEAGE | L2 | DetailPanel / SearchResultRow | view_mapping |
| PARTIAL_LINEAGE_RESULT | L2 | Path Anchor / StatusStrip | view_diagnostics |
| ANALYSIS_TIMEOUT | L1 / L2 | Canvas summary depending partial result | view_diagnostics |
| SOURCE_LOCATION_UNAVAILABLE | L2 | DetailPanel action result | view_mapping |
| STALE_ANALYSIS_RESULT | L1 | TopBar Re-analyze + Path Anchor | reanalyze |

### 19.3 规则

```text
1. blocking code → L1。
2. diagnostic related to current path → L2。
3. diagnostic unrelated to current path → L3。
4. full diagnostic detail → L4 Drawer。
5. warning 不得覆盖 Current Path L1。
6. low confidence search result 不默认强路径高亮。
```

---

## 20. Agent 开发任务更新

### FE-UI-01｜Node Visual Taxonomy

**目标**：为 Output / Subquery / CTE / Table / Expression / Unknown 建立稳定视觉体系。  
**验收**：100 个节点图中，用户可一眼分出子查询、表、输出、风险节点。

### FE-UI-02｜Default Subquery Dependency View

**目标**：Analyze 成功后默认展示子查询 / CTE / 表依赖图，选择 output field 后再进入当前字段路径。  
**验收**：Analyze 成功后，用户无需先面对字段级复杂图。

### FE-UI-03｜Toolbar Deduplication

**目标**：移除与 Splitter 重复的布局按钮，只保留真正高频图谱阅读按钮。  
**验收**：TopBar 与 CanvasToolbar 中不再出现重复的布局面积控制按钮。

### FE-UI-04｜Primary CTA Emphasis

**目标**：Analyze / Re-analyze 在不同状态下成为唯一主 CTA，辅助按钮全部降权。  
**验收**：dirty 状态下用户第一眼能看到 Re-analyze。

### FE-UI-05｜Canvas Space Budget

**目标**：压缩顶部控制和底部详情默认占高，保证主要空间留给图谱。  
**验收**：1366×768 下，图谱核心区域在 analyzed 状态仍具备舒适可读面积。

### FE-UI-06｜GraphRenderMode State Machine

**目标**：明确 `subquery_dependency / current_field_path / focus_field / semantic_mode / large_graph / full_graph_preview` 的进入和退出规则。  
**验收**：Analyze success 默认进入 subquery_dependency；选择 output field 进入 current_field_path；Full preview 只能用户主动进入。

### FE-UI-07｜SubqueryDependencyViewModel

**目标**：定义从 Graph Fact Layer 到默认结构视图的可见节点 / 边生成规则。  
**验收**：字段级实体不丢失，但默认不进入 DOM；Join / Filter 不抢首屏主线；OutputGroup 稳定存在。

### FE-UI-08｜Node State Priority Matrix

**目标**：解决 selected / current_path / warning / stale / dimmed 等状态叠加冲突。  
**验收**：selected 节点不会被 dimmed 覆盖；warning 不覆盖 current_path 主视觉；状态变化不改变节点尺寸。

### FE-UI-09｜OutputGroup Display Rule

**目标**：定义 OutputGroup 与 OutputField 在默认视图中的展示阈值。  
**验收**：20+ 输出字段不会默认铺满画布；用户仍可通过 Search / Default Output Capsule 选择字段路径。

### FE-UI-10｜Visual Regression Snapshots

**目标**：将 v1.4 的 UI 收敛结果转成截图回归集。  
**验收**：至少覆盖 ready、analyzed、current path、dirty、failed、large graph、100 nodes taxonomy、1366 space budget。

---

## 21. M1-M7 开发里程碑更新

### M1｜Base Workbench + PageMode

| 任务 | 输出 |
|---|---|
| WorkbenchShell | TopBar / LeftNav / SplitWorkspace / BottomStatusStrip |
| PageModeStore | empty / ready / analyzing / analyzed / dirty / failed |
| WorkbenchRuntimeState | PageMode / AnalysisStatus / TrustStatus |
| TopBar CTA | Analyze / Cancel / Re-analyze 状态 |
| Splitter | 大热区、可拖拽、Graph Focus 边界 |

### M2｜Analyze + Dirty/Stale Loop

| 任务 | 输出 |
|---|---|
| Typed Analyze Client | 调用 `/api/sql/analyze` |
| AnalysisStore | analysisId / status / diagnostics / graphViewModel |
| Dirty Detection | sqlHash 比对 |
| TrustStatus | trusted / stale / untrusted |
| Diagnostics Compact | parse / metadata / partial 摘要 |

### M3｜Graph Foundation + Adapter

| 任务 | 输出 |
|---|---|
| CanvasEngineView / Controller | React Flow 声明式视图 + 命令式控制 |
| ReactFlowAdapter Shell | 业务层不直接依赖 React Flow 实例 |
| GraphAdapter | GraphViewModel → MinimalGraphModel |
| Graph Fact / View / Interaction 分层 | 后端事实、前端视图、交互状态分离 |
| FE-UI-06 | GraphRenderMode State Machine |

### M4｜Subquery Dependency + Node Visual

| 任务 | 输出 |
|---|---|
| FE-UI-07 | SubqueryDependencyViewModel |
| FE-UI-01 | Node Visual Taxonomy |
| FE-UI-08 | Node State Priority Matrix |
| FE-UI-09 | OutputGroup Display Rule |
| FE-UI-02 | Default Subquery Dependency View |

### M5｜Search + Field Path

| 任务 | 输出 |
|---|---|
| CanvasTopSearchBar | 40px 单行 |
| Output / Current Capsule | Choose output / Current field |
| FieldSearchApi | 后端搜索 |
| Search Request Guard | request_id / analysis_id / metadata_version |
| FieldPathApi | 当前字段路径 |
| PathContextStore | 当前路径唯一事实源 |
| Current Path Highlight | L1 当前路径，背景降噪 |

### M6｜Detail + Locate + Diagnostics

| 任务 | 输出 |
|---|---|
| CanvasBottomDetailPanel | compact 三行模板 |
| EdgeMapping Detail | source_field → target_field |
| MonacoAdapter Shell | reveal / markers / decorations |
| SourceLocation Guard | analysis_id / sql_hash / range_type |
| DiagnosticAttentionRule | DiagnosticCode → Attention |
| UxMessage Builder | reason / impact / action |

### M7｜UI Hardening + Regression

| 任务 | 输出 |
|---|---|
| FE-UI-03 | Toolbar Deduplication |
| FE-UI-04 | Primary CTA Emphasis |
| FE-UI-05 | Canvas Space Budget |
| FE-UI-10 | Visual Regression Snapshots |
| Smoke / Regression / Scenario | 任务型验收 |
| Drag Performance Contract | 拖拽不 layout、不全局 dispatch、不重算 path |

---

## 22. 验收测试

### 22.1 GraphRenderMode 验收

| 测试 | 验收 |
|---|---|
| Analyze success | renderMode=subquery_dependency |
| 选择 output field | renderMode=current_field_path |
| Focus field | renderMode=focus_field |
| 清空选择 | 回到 subquery_dependency |
| Full preview | 只能用户主动触发 |
| large graph | 不等于 failed，必须有说明 |

### 22.2 SubqueryDependencyViewModel 验收

| 测试 | 验收 |
|---|---|
| 多 CTE | CTE 节点稳定可见 |
| from 子查询 | Subquery 节点稳定可见 |
| 无 alias 子查询 | 使用稳定 subquery_n |
| 多字段映射 | 默认聚合为 summary edge |
| join/filter | 默认不进入首屏主边层 |
| 字段实体 | 不默认显示，但不丢失 |

### 22.3 Node State Priority 验收

| 测试 | 验收 |
|---|---|
| selected + dimmed | selected 优先，不被降噪 |
| current_path + warning | 当前路径仍清楚，warning 以小点表达 |
| stale + selected | selected 仍可读，stale 有提示 |
| search_hit + current_path | 不出现两个强视觉冲突 |
| hover + dragging | 拖拽中 hover detail 暂停 |

### 22.4 OutputGroup 验收

| 输出字段数 | 验收 |
|---:|---|
| 1-5 | 可展示 OutputField |
| 6-20 | 推荐 OutputGroup + Capsule |
| 20+ | 必须 OutputGroup，不默认铺字段节点 |

### 22.5 Toolbar Deduplication 验收

| 测试 | 验收 |
|---|---|
| TopBar | 只保留 Analyze / Re-analyze / Cancel / Format / Dialect / Metadata / More |
| TopBar | 不出现 SQL Focus / Graph Focus / Max Canvas |
| CanvasToolbar | 不出现布局面积控制按钮 |
| More | 可找到 Reset split ratio / Reset workspace layout |
| CanvasToolbar | Reset Viewport 与 Reset workspace layout 不混淆 |

### 22.6 Canvas Space Budget 验收

| 测试 | 验收 |
|---|---|
| 1366×768 | Canvas 上方常驻控件最多 76px |
| DetailPanel compact | 默认 84-96px，不自动撑高 |
| Search suggestions | popover，不新增常驻行 |
| PathContext | inline，不单独增加第三层 |
| 图谱主视口 | analyzed 状态下仍舒适可读 |

### 22.7 视觉回归 Snapshot

| Snapshot | 场景 |
|---|---|
| snapshot-01-ready-analyze-cta | ready 状态 Analyze 主按钮 |
| snapshot-02-analyzed-subquery-dependency | 默认子查询依赖图 |
| snapshot-03-selected-current-field-path | 当前字段路径 |
| snapshot-04-detailpanel-compact-edge-mapping | 选中边映射详情 |
| snapshot-05-dirty-reanalyze-stale | dirty / stale 可信度提示 |
| snapshot-06-failed-error-summary | failed 错误摘要 |
| snapshot-07-large-graph-subquery-summary | large graph 摘要说明 |
| snapshot-08-node-taxonomy-100-nodes | 100 节点视觉分类 |
| snapshot-09-toolbar-deduplication | 顶部 / 画布工具栏去重 |
| snapshot-10-1366-canvas-space-budget | 1366×768 空间预算 |

---

## 23. 禁止事项

```text
1. 禁止默认视图删除字段级实体；默认不展示字段节点不等于取消字段级血缘。
2. 禁止把 Subquery Dependency View 写成直接过滤 React Flow nodes 的临时代码，必须由 GraphAdapter 派生可见图。
3. 禁止 Analyze 成功后默认直接展示字段级复杂全图。
4. 禁止 20+ 输出字段在默认结构图中全部渲染为 OutputField 节点。
5. 禁止子查询节点与普通表节点仅靠文字或 badge 轻微区分。
6. 禁止 selected / current_path / warning / dimmed 等状态互相覆盖导致主路径不可读。
7. 禁止节点状态变化引发节点尺寸变化和布局抖动。
8. 禁止使用复杂 CSS 阴影、filter、循环动画来制造节点区分度。
9. 禁止在 TopBar / CanvasToolbar 中保留与 Splitter 重复的布局控制按钮。
10. 禁止为 SQL/Canvas 面积调整同时提供“拖拽 + 额外按钮”两套入口。
11. 禁止删除所有布局恢复入口；低频恢复入口应放在 More 中。
12. 禁止 SearchBar、Toolbar、DetailPanel 三处重复完整字段路径长文案。
13. 禁止默认让 DetailPanel 撑高侵占画布主阅读空间。
14. 禁止 Canvas 顶部出现长期常驻第三层控件。
15. 禁止 Search suggestions 以常驻行方式挤压画布。
16. 禁止 stale 状态下执行 exact reveal。
17. 禁止拖拽节点时触发 layout、路径重算或全局 dispatch。
18. 禁止没有视觉回归快照就认为 v1.4 UI 收敛已完成。
19. 禁止继续新增 v1.5 功能性规格打断当前开发节奏。
```

---

## 24. 变更记录表

| 变更 ID | 类型 | 内容 | 原因 |
|---|---|---|---|
| FE-V14-M01 | 保留 | v1.3 P0-Core 主链路 | 继续保障 Analyze → Search → Path → Detail → Locate SQL 闭环 |
| FE-V14-M02 | 保留 | PageMode / AnalysisStatus / TrustStatus 分离 | 避免状态混淆 |
| FE-V14-M03 | 保留 | AttentionViewModel 派生模型 | 防止注意力变成新事实源 |
| FE-V14-M04 | 保留 | PathContextStore 单源 | 避免 Capsule / Anchor / Detail 状态漂移 |
| FE-V14-M05 | 新增 | Default Subquery Dependency View | 复杂 SQL 默认先看结构 |
| FE-V14-M06 | 新增 | GraphRenderMode State Machine | 避免 renderMode 切换混乱 |
| FE-V14-M07 | 新增 | SubqueryDependencyViewModel | 明确默认结构视图如何生成 |
| FE-V14-M08 | 新增 | Node Visual Taxonomy | 解决节点区分度不足 |
| FE-V14-M09 | 新增 | Node State Priority Matrix | 解决状态叠加冲突 |
| FE-V14-M10 | 新增 | OutputGroup / OutputField 展示阈值 | 防止输出字段过多挤爆默认视图 |
| FE-V14-M11 | 新增 | CSS / data-state 实现约束 | 避免视觉增强破坏性能 |
| FE-V14-M12 | 调整 | Toolbar Deduplication | 删除与 Splitter 重复的布局入口 |
| FE-V14-M13 | 调整 | Primary CTA Emphasis | 强化 Analyze / Re-analyze 主 CTA |
| FE-V14-M14 | 新增 | Canvas Space Budget 自动降级 | 保护 1366×768 画布可读性 |
| FE-V14-M15 | 新增 | FE-UI-06 ~ FE-UI-10 | 把审阅补充项转成可开发任务 |
| FE-V14-M16 | 新增 | Visual Regression Snapshot 名称 | 让 UI 收敛结果可回归 |

---

## 25. 最终实现原则

```text
先子查询级结构，再字段级路径；
先输出和子查询强区分，再表节点克制；
先主按钮醒目，再辅助按钮降权；
先删除重复布局控制，再释放画布空间；
先 GraphAdapter 派生可见图，再 React Flow 渲染；
先保证字段级事实不丢，再控制默认 DOM 数量；
先 compact 信息摘要，再 expanded 完整信息；
先视觉回归快照，再认定 UI 收敛完成。
```

最终一句话：

```text
v1.4 是以 v1.3 P0-Core 为底座的最终 UI/UX 收敛版：
它不改变主任务闭环，而是把默认图谱入口、节点区分、按钮权重、工具栏去重和画布空间预算固化为可开发、可测试、可回归的前端实现规格。
```
