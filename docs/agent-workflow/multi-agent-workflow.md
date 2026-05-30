# Multi-Agent 开发工作流 v2.0

## 概述

本文档定义了 SQL 血缘解析可视化项目的多 Agent 协作开发流程。

---

## 完整开发流程图

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

---

## 阶段详细说明

### 阶段 1：需求输入与 Feature Task Brief

**执行者**：project-orchestrator

**触发条件**：用户提出新需求或进入新一轮迭代

**动作**：
1. 理解用户需求
2. 创建本轮 Feature Task Brief
3. 明确本轮目标、范围、预期产出

**Feature Task Brief 格式**：
```markdown
## Feature Task Brief - [功能名称]

### 本轮目标
[目标描述]

### 需求来源
[来源说明]

### 预期产出
- [产出1]
- [产出2]

### 约束条件
- [约束1]
- [约束2]

### 优先级
P0/P1/P2
```

---

### 阶段 2：读取文档

**执行者**：project-orchestrator

**必须读取的文档**：
- 当前模块功能点文档
- 当前迭代文档
- 产品需求文档
- 架构设计文档
- 接口契约文档
- 已有测试文档

**规则**：
- 如果缺少必要文档，应先创建或补全文档，再进入开发

---

### 阶段 3：DoR 前置评审（Definition of Ready）

**执行者**：所有相关 Agent 并行评审

**评审内容**：

#### senior-product-manager 评审
- 产品目标是否清晰
- 功能边界是否明确
- 验收标准是否可度量
- 用户场景是否完整

**输出**：产品侧 DoR 确认

#### senior-architect 评审
- 技术方案是否可行
- 模块边界是否清晰
- API 契约是否稳定
- 风险判断是否充分

**输出**：技术侧 DoR 确认

#### senior-data-developer 评审
- 真实 SQL/元数据 case 是否准备
- 业务使用约束是否明确
- 测试场景覆盖是否充分

**输出**：数据侧 DoR 确认

#### senior-test-engineer 评审
- 测试计划是否完整
- 回归范围是否明确
- 阻断标准是否清晰

**输出**：测试侧 DoR 确认

#### senior-ui-designer 评审
- UI/UX 前置注意事项
- 界面一致性要求
- 交互规范要求

**输出**：UI 侧 DoR 确认

---

### 阶段 4：冻结 Feature Contract

**执行者**：project-orchestrator

**动作**：
1. 合并各 Agent 的 DoR 评审结果
2. 解决评审中发现的问题
3. 冻结 Feature Contract

**Feature Contract 格式**：
```markdown
## Feature Contract - [功能名称]

### 产品要求
[来自 senior-product-manager]

### 技术要求
[来自 senior-architect]

### 数据要求
[来自 senior-data-developer]

### 测试要求
[来自 senior-test-engineer]

### UI/UX 要求
[来自 senior-ui-designer]

### 接口契约
[API 定义]

### 验收标准
[可度量的验收标准]

### 冻结时间
[时间戳]
```

---

### 阶段 5：产品/架构冲突判断

**执行者**：senior-product-manager + senior-architect

**判断规则**：

#### 优先采用产品经理方案的条件
1. 技术可实现
2. 性能有保障
3. 架构边界不破坏
4. 不引入明显过度耦合

#### 技术风险高的处理
1. 架构师给出风险说明
2. 架构师给出替代方案
3. 产品经理二次裁决
4. 记录决策过程

---

### 阶段 6：并行开发

**执行者**：多个 Agent 并行

#### senior-backend-developer
- 后端核心功能实现
- 按照 Feature Contract 实现
- 保持模块高内聚、低耦合
- 提供单元测试

#### senior-frontend-developer
- 前端功能实现
- 与后端 API 联调
- 按照接口契约实现
- 处理加载状态和错误提示

#### senior-data-developer
- 补充业务 SQL case
- 补充元数据 case
- 补充 gold case（标准测试用例）
- 构造边界测试数据

#### senior-test-engineer
- 补充测试 case
- 编写回归脚本
- 准备测试数据
- 编写测试文档

---

### 阶段 7：开发 Agent 自检

**执行者**：各开发 Agent

**自检内容**：

#### 后端开发自检
- 功能是否按 Feature Contract 实现
- 单元测试是否通过
- 接口是否符合契约
- 异常处理是否完善

#### 前端开发自检
- 功能是否按 Feature Contract 实现
- API 联调是否正常
- 用户交互是否流畅
- 错误处理是否完善

#### 数据开发自检
- 测试 case 是否覆盖核心场景
- 数据是否贴近真实业务
- 边界 case 是否充分

#### 测试开发自检
- 测试 case 是否完整
- 回归脚本是否可用
- 测试数据是否准备

**输出格式**：
```markdown
## 自检报告

### 功能实现
- [完成项]
- [未完成项]

### 测试情况
- [通过项]
- [失败项]

### 待确认项
- [确认项]
```

---

### 阶段 8：测试门禁

**执行者**：senior-test-engineer

**测试内容**：

#### 功能测试
- 功能是否按需求实现
- 输出结果是否正确
- 核心流程是否通畅

#### API 契约测试
- 请求格式是否正确
- 响应格式是否符合契约
- 错误码是否正确
- HTTP 状态码是否正确

#### 回归测试
- 是否影响已有功能
- 是否有破坏性变更
- 历史测试是否通过

#### 异常与边界测试
- 空输入处理
- 超大输入处理
- 特殊字符处理
- 并发情况处理

#### 耦合风险检查
- 模块间依赖是否合理
- 是否有隐藏依赖
- 是否违反模块边界

**测试结果**：
- 通过：进入下一阶段
- 不通过：project-orchestrator 进行失败归因并分派修复

---

### 阶段 9：失败归因与修复（如测试不通过）

**执行者**：project-orchestrator + 对应开发 Agent

**失败归因**：
1. 分析失败原因
2. 确定责任 Agent
3. 分派修复任务

**修复流程**：
1. 开发 Agent 接收修复任务
2. 执行修复
3. 重新自检
4. 重新测试

---

### 阶段 10：业务与体验验证

**执行者**：senior-data-developer + senior-ui-designer（并行）

#### senior-data-developer：业务可用性验证
- 是否符合数据开发日常使用习惯
- 是否有功能冗余
- SQL case 覆盖是否充分
- 元数据 case 覆盖是否充分
- 操作链路是否合理

**输出**：业务验证报告

#### senior-ui-designer：UI/UX 后置审阅
- 界面问题检查
- 用户注意力引导
- 信息密度评估
- 视觉层级评估

**输出**：UI/UX 美化建议文档

---

### 阶段 11：产品经理决策

**执行者**：senior-product-manager

**决策内容**：

#### UI 建议决策
- 哪些建议进入下一轮
- 哪些建议归档
- 优先级排序

#### 数据开发反馈决策
- 哪些反馈进入下一轮
- 哪些反馈归档
- 优先级排序

#### 冗余功能决策
- 是否移除冗余功能
- 是否降级冗余功能
- 是否合并冗余功能

**输出**：决策记录

---

### 阶段 12：迭代归档

**执行者**：project-orchestrator

**归档内容**：
```markdown
## 本轮迭代归档报告

### 本轮目标
[目标描述]

### Feature Contract
[契约内容]

### 涉及文档
- [文档列表]

### 涉及代码
- [文件列表]

### 实现内容
- [功能点列表]

### 测试结果
- 功能测试：通过/不通过
- API 契约测试：通过/不通过
- 回归测试：通过/不通过
- 异常边界测试：通过/不通过

### UI 建议采纳情况
- 采纳：[列表]
- 未采纳：[列表]

### 数据开发业务验证结果
- 业务可用性：是/否
- 问题清单：[列表]

### 遗留问题
- [问题列表]

### 下一轮迭代输入
- [输入内容]
```

---

### 阶段 13：生成下一轮迭代输入

**执行者**：project-orchestrator

**动作**：
1. 整理遗留问题
2. 整理未采纳的 UI 建议
3. 整理数据开发反馈
4. 生成下一轮迭代输入文档

**输出**：下一轮迭代输入文档

---

## 示例调用方式

### 调用主控 Agent
```
@project-orchestrator 实现 SQL 血缘解析的字段级血缘分析功能
```

### 直接调用子 Agent
```
@senior-product-manager 定义字段级血缘分析的产品需求
@senior-architect 设计字段级血缘分析的技术方案
@senior-backend-developer 实现字段级血缘分析的后端逻辑
@senior-frontend-developer 实现字段级血缘分析的前端展示
@senior-test-engineer 测试字段级血缘分析功能
@senior-data-developer 验证字段级血缘分析的业务可用性
@senior-ui-designer 审阅字段级血缘分析的 UI 设计
```

---

## 关键概念说明

### Feature Task Brief
本轮迭代的任务说明，由 project-orchestrator 创建，明确目标、范围、预期产出。

### DoR (Definition of Ready)
前置评审，确保需求、技术、数据、测试、UI 都已准备就绪，可以进入开发。

### Feature Contract
功能契约，合并所有 DoR 评审结果后的冻结文档，作为开发、测试、验收的依据。

### 并行开发
多个开发 Agent 同时工作，提高效率。

### 开发 Agent 自检
开发 Agent 在提交测试前自行检查，确保基本质量。

### 失败归因
测试失败时，由 project-orchestrator 分析原因并分派修复。

### 业务与体验验证
数据开发和 UI 设计并行验证，确保业务可用性和用户体验。
