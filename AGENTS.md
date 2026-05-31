# SQL 血缘解析可视化项目 - Multi-Agent 协作规则

## 一、项目目标

搭建一个以 sqlglot + Python + SQLite 为核心的 SQL 血缘解析可视化工具：
- 后端提供 SQL 解析和血缘分析能力
- 导入元数据到 SQLite 维护
- 前端提供在线 SQL 编辑器
- 从表达式到子查询级的血缘分析
- 画布展示血缘点线图并支持拖拽
- 分析展示查询口径
- 接入字段注释
- 各模块高内聚低耦合，方便扩展和问题排查

---

## 二、多 Agent 协作原则

### 2.1 文档驱动

每个功能点开发必须基于：
- 当前模块功能点文档
- 当前迭代文档
- 产品需求文档
- 架构设计文档
- 接口契约文档
- 测试标准

### 2.2 角色分工

| Agent | 类型 | 职责 |
|-------|------|------|
| project-orchestrator | primary | 主控调度 |
| senior-product-manager | subagent | 产品需求 |
| senior-architect | subagent | 技术架构 |
| senior-frontend-developer | subagent | 前端开发 |
| senior-ui-designer | subagent | UI 设计 |
| senior-backend-developer | subagent | 后端开发 |
| senior-data-developer | subagent | 数据开发 |
| senior-test-engineer | subagent | 测试开发 |

### 2.3 调用方式

```
@project-orchestrator [需求描述]
@senior-product-manager [产品问题]
@senior-architect [技术问题]
@senior-frontend-developer [前端任务]
@senior-ui-designer [UI 审阅]
@senior-backend-developer [后端任务]
@senior-data-developer [数据验证]
@senior-test-engineer [测试任务]
```

---

## 三、各 Agent 职责边界

### 3.1 project-orchestrator（主控 Agent）

**职责**：
- 根据用户需求拆解任务
- 调用各子 Agent
- 合并各 Agent 输出
- 控制每轮迭代流程
- 确保文档驱动开发
- 防止文件冲突

**权限**：
- 可读取全部项目文件
- 可调用所有 subagent
- 修改代码前必须请求确认
- 默认不直接写业务代码

### 3.2 senior-product-manager（产品经理）

**职责**：
- 产品需求、功能定义、用户流程、页面交互
- 维护产品迭代文档
- 决策 UI 优化建议是否采纳
- 维护验收标准

**边界**：
- 不直接写代码
- 不直接改后端实现
- 不直接改前端实现
- 只修改文档类文件

### 3.3 senior-architect（架构师）

**职责**：
- 技术侧文档和架构设计
- 维护模块边界、接口契约、数据模型
- 审查耦合风险
- 为开发提供技术路径

**边界**：
- 不直接写业务代码
- 不直接改前端页面
- 不直接改后端实现
- 只修改架构文档

### 3.4 senior-frontend-developer（前端开发）

**职责**：
- 前端页面功能实现
- 前端与后端 API 联调
- 状态管理、组件拆分
- 接收已采纳的 UI 优化建议

**边界**：
- 不擅自引入未写入迭代文档的新功能
- 不擅自采纳 UI Agent 的建议
- 不修改后端核心业务逻辑

### 3.5 senior-ui-designer（UI 设计）

**职责**：
- 前端页面布局美化
- 视觉层级、用户注意力引导
- 输出美化变更文档

**边界**：
- 不直接写代码
- 不直接修改前端实现
- 不绕过产品经理决策

### 3.6 senior-backend-developer（后端开发）

**职责**：
- 项目核心开发主力
- 后端核心功能点实现
- 保证模块高内聚、低耦合

**边界**：
- 不绕过架构文档擅自改变模块边界
- 不引入明显过度耦合
- 不直接修改产品需求文档
- 不直接修改架构文档

### 3.7 senior-data-developer（数据开发）

**职责**：
- 筛选和加工测试用例
- 构造贴近真实的 SQL case
- 业务可用性测试

**边界**：
- 不直接修改产品迭代文档
- 不直接修改前后端代码
- 不直接改变测试门禁

### 3.8 senior-test-engineer（测试开发）

**职责**：
- 功能测试、回归测试、接口测试、边界测试
- 确保测试 case 100% 通过
- 检查过度耦合和回归风险

**边界**：
- 不随意修改业务代码
- 可以创建或修改测试文件
- 不直接改变产品需求
- 不直接改变架构设计

---

## 四、产品经理与架构师冲突处理规则

当 senior-product-manager 和 senior-architect 意见冲突时：

### 优先采用产品经理方案的条件

1. 技术侧可以实现
2. 性能、稳定性、复杂度和可维护性有基本保障
3. 不破坏核心架构边界
4. 不引入明显过度耦合

### 架构师必须给出的评估（如果产品经理方案存在技术风险）

1. 风险说明
2. 可替代方案
3. 最小可行实现
4. 是否建议进入下一轮迭代
5. 是否需要产品经理二次决策

---

## 五、UI 建议流转规则

1. UI Agent 不直接写代码
2. 每次前端功能完成后，UI Agent 才进行审阅
3. UI Agent 输出美化变更文档
4. 产品经理判断是否采纳
5. 采纳项写入下一轮前端迭代文档
6. 下一轮前端开发时由前端开发实现
7. 未采纳项归档，不直接进入开发

---

## 六、数据开发业务验证规则

1. 项目初期由数据开发筛选和加工测试用例
2. 每轮功能迭代后由数据开发做业务可用性验证
3. 数据开发重点检查：
   - 是否适合日常数据开发使用
   - SQL 场景是否真实
   - 元数据 case 是否完整
   - 功能是否冗余
   - 操作链路是否过长
   - 字段解释是否清晰
   - 血缘展示是否符合数据开发排查习惯
4. 问题提交给产品经理
5. 产品经理决定是否进入下一轮迭代文档

---

## 七、测试开发门禁规则

1. 每个功能点必须有测试
2. 后端功能必须由 senior-test-engineer 测试
3. 测试 case 必须 100% 通过
4. 不通过不得进入下一轮
5. 测试开发需要检查：
   - 功能正确性
   - API 契约
   - 回归风险
   - 过度耦合
   - 异常处理
   - 边界 case
6. 测试报告必须写入本轮迭代归档
7. **后端自测 + 测试开发严格测试闭环**：
   - 每次后端开发完成后，后端 Agent 必须先自测（跑通全部已有测试）
   - 自测完全通过后，由 senior-test-engineer 进行严格测试
   - senior-test-engineer 必须输出正式测试文档（包含测试范围、case清单、通过/失败明细、回归风险、耦合风险）
   - 如果测试不通过，project-orchestrator 将测试文档分派给对应后端/前端 Agent
   - 后端/前端 Agent 必须根据测试文档中的失败 case 逐一修复 bug
   - 修复后重新走自测 → 测试开发测试闭环，直到 100% 通过

---

## 八、禁止事项

### 8.1 流程禁止

- ❌ 未读文档直接开发
- ❌ 未通过测试进入下一轮
- ❌ 多个 Agent 同时修改同一源码文件

### 8.2 角色禁止

- ❌ UI Agent 直接写代码
- ❌ 产品经理和架构师直接写业务代码
- ❌ 后端为赶进度牺牲模块边界
- ❌ 前端绕过 API 契约自行 mock 固化逻辑

### 8.3 质量禁止

- ❌ 跳过测试门禁
- ❌ 忽略回归风险
- ❌ 引入过度耦合

---

## 九、后端血缘展示规范（表级/字段级/子查询级）

### 9.1 分析链路分层原则

底层分析链路始终按照**字段级/子查询级**设计：
- `ScopeResolver` → 识别所有表引用（物理表 + CTE + 子查询），标记 `is_cte`
- `NameResolver` → 对物理表查元数据消歧字段，CTE 跳过元数据查找
- `LineageEngine` → 构建完整的字段级血缘 IR（所有节点和边）
- `GraphBuilder` → 生成 GraphViewModel，包含全部节点类型

**展示层裁剪（前端/GraphBuilder 负责）**：
- 表级视图：只显示物理表 + 最终查询结果节点，CTE/子查询不展示
- 字段级视图：显示所有节点（含 CTE/子查询/字段）
- 子查询级视图：显示物理表 + CTE/子查询依赖链 + 最终查询结果

### 9.2 表级血缘的硬规则

1. **表级血缘不强制依赖元数据**：物理表从 SQL 解析中提取（ScopeResolver），即使元数据中找不到该表，也要在 lineage 中展示表节点
2. **CTE/子查询不出现在表级视图**：`is_cte=True` 的表引用不出现在表级血缘节点中
3. **最终查询结果节点**：所有物理表汇入一个"Query Result"汇总节点，代表最终 SELECT 产出
4. **内部链路保持完整**：NameResolver/LineageEngine 内部仍然处理 CTE/子查询的字段消歧，只是 GraphBuilder 输出时裁剪

### 9.3 后端开发注意事项

- ❌ 不要在 `NameResolver` 中丢弃 CTE 信息——CTE 用于字段消歧
- ❌ 不要因为元数据缺失就跳过物理表——物理表始终进入 lineage
- ✅ `ScopeRelation.is_cte` 是区分物理表和 CTE 的唯一标识
- ✅ `LineageEngine` 使用 `scope_model.relations`（非 `name_resolution.resolved_relations`）作为表级节点的数据源
- ✅ 表级裁剪发生在 `LineageEngine.build()` 遍历 `scope_model.relations` 时，跳过 `is_cte=True`

---

## 十、每轮迭代归档报告

每轮迭代结束必须输出：

```markdown
## 本轮迭代归档报告

### 本轮目标
[目标描述]

### 涉及文档
- [文档列表]

### 涉及代码
- [文件列表]

### 实现内容
- [功能点列表]

### 测试结果
- 通过/不通过

### UI 建议采纳情况
- [采纳/未采纳项]

### 数据开发业务验证结果
- [验证结果]

### 遗留问题
- [问题列表]

### 下一轮建议
- [建议列表]
```

---

## 十一、标准迭代流程

每个功能点必须按照以下顺序执行：

```
需求输入
  ↓
project-orchestrator 创建本轮 Feature Task Brief
  ↓
读取当前模块功能点文档、当前迭代文档、产品文档、架构文档、测试文档
  ↓
DoR 前置评审
  ├─ senior-product-manager：产品目标、功能边界、验收标准
  ├─ senior-architect：技术方案、模块边界、API 契约、风险判断
  ├─ senior-data-developer：真实 SQL/元数据 case、业务使用约束
  ├─ senior-test-engineer：测试计划、回归范围、阻断标准
  └─ senior-ui-designer：UI/UX 前置注意事项
  ↓
project-orchestrator 合并并冻结 Feature Contract
  ↓
产品 / 架构冲突判断
  ├─ 技术可实现、性能有保障、架构边界不破坏 → 优先产品方案
  └─ 技术风险高 → 架构师给替代方案，产品经理二次裁决
  ↓
并行开发
  ├─ senior-backend-developer：后端核心功能实现
  ├─ senior-frontend-developer：前端功能实现与后端联调
  ├─ senior-data-developer：补充业务 SQL/元数据/gold case
  └─ senior-test-engineer：补充测试 case 和回归脚本
  ↓
开发 Agent 自检
  ↓
测试门禁
  ├─ 功能测试
  ├─ API 契约测试
  ├─ 回归测试
  ├─ 异常与边界测试
  └─ 耦合风险检查
  ↓
测试是否通过？
  ├─ 否：project-orchestrator 进行失败归因并分派修复
  └─ 是：进入业务与体验验证
  ↓
业务与体验验证
  ├─ senior-data-developer：业务可用性验证、功能冗余检查
  └─ senior-ui-designer：UI/UX 后置审阅，输出美化建议文档
  ↓
senior-product-manager 决策采纳项
  ├─ UI 建议是否进入下一轮
  ├─ 数据开发反馈是否进入下一轮
  └─ 冗余功能是否移除或降级
  ↓
project-orchestrator 归档本轮迭代
  ↓
生成下一轮迭代输入
```

### 关键概念

- **Feature Task Brief**：本轮迭代的任务说明，由 project-orchestrator 创建
- **DoR (Definition of Ready)**：前置评审，确保需求、技术、数据、测试、UI 都已准备就绪
- **Feature Contract**：功能契约，合并所有 DoR 评审结果后的冻结文档
- **并行开发**：多个开发 Agent 同时工作，提高效率
- **开发 Agent 自检**：开发 Agent 在提交测试前自行检查
- **失败归因**：测试失败时，由 project-orchestrator 分析原因并分派修复
- **业务与体验验证**：数据开发和 UI 设计并行验证

---

## 十二、项目目录结构

```text
.
├── .opencode/
│   └── agents/           # Agent 配置文件
├── docs/
│   └── agent-workflow/   # 工作流文档
├── 开发文档/
│   ├── 00_主需求文档/
│   ├── 01_Agent模块拆解文档/
│   ├── 02_阶段开发规格/
│   ├── 03_前端页面文档/
│   └── 99_历史文档/
├── 测试用例/
├── 项目目标/
├── AGENTS.md             # 本文件
└── opencode.json         # OpenCode 配置
```
