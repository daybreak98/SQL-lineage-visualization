# 迭代门禁检查清单 v2.0

## 概述

本文档定义了每轮迭代的门禁检查清单，确保迭代质量。

---

## 阶段门禁检查

### 1. DoR 前置评审门禁

**检查点**：Feature Contract 冻结前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| 产品目标清晰 | senior-product-manager | 目标可度量 |
| 功能边界明确 | senior-product-manager | 边界无歧义 |
| 验收标准可度量 | senior-product-manager | 有明确的验收条件 |
| 技术方案可行 | senior-architect | 有可行的技术路径 |
| 模块边界清晰 | senior-architect | 无边界冲突 |
| API 契约稳定 | senior-architect | 接口定义完整 |
| 风险判断充分 | senior-architect | 风险已识别和评估 |
| SQL case 准备 | senior-data-developer | 核心场景覆盖 |
| 元数据 case 准备 | senior-data-developer | 元数据完整 |
| 业务约束明确 | senior-data-developer | 约束已文档化 |
| 测试计划完整 | senior-test-engineer | 计划覆盖核心功能 |
| 回归范围明确 | senior-test-engineer | 范围已确定 |
| 阻断标准清晰 | senior-test-engineer | 标准可执行 |
| UI/UX 注意事项 | senior-ui-designer | 注意事项已列出 |

**门禁规则**：
- 所有检查项必须通过
- 未通过项必须解决后才能进入下一阶段

---

### 2. Feature Contract 冻结门禁

**检查点**：并行开发前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| 合并评审结果 | project-orchestrator | 所有评审已合并 |
| 解决评审问题 | project-orchestrator | 问题已解决 |
| 契约内容完整 | project-orchestrator | 包含所有必要信息 |
| 契约已冻结 | project-orchestrator | 时间戳已记录 |

**门禁规则**：
- Feature Contract 必须冻结后才能进入并行开发

---

### 3. 产品/架构冲突门禁

**检查点**：并行开发前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| 冲突已识别 | senior-architect | 所有冲突已列出 |
| 风险已评估 | senior-architect | 风险等级已确定 |
| 替代方案已提供 | senior-architect | 方案可执行 |
| 二次裁决完成 | senior-product-manager | 决策已记录 |

**门禁规则**：
- 冲突必须解决后才能进入并行开发
- 采用产品经理方案的条件：技术可实现、性能有保障、架构边界不破坏

---

### 4. 并行开发门禁

**检查点**：开发 Agent 自检前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| 后端功能实现 | senior-backend-developer | 功能完整 |
| 前端功能实现 | senior-frontend-developer | 功能完整 |
| 数据 case 补充 | senior-data-developer | case 完整 |
| 测试 case 补充 | senior-test-engineer | case 完整 |

**门禁规则**：
- 所有开发任务必须完成
- 未完成项必须说明原因

---

### 5. 开发 Agent 自检门禁

**检查点**：测试门禁前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| 功能按契约实现 | 各开发 Agent | 实现与契约一致 |
| 单元测试通过 | senior-backend-developer | 测试 100% 通过 |
| API 联调正常 | senior-frontend-developer | 联调无错误 |
| 测试 case 完整 | senior-data-developer | case 覆盖核心场景 |
| 回归脚本可用 | senior-test-engineer | 脚本可执行 |

**门禁规则**：
- 自检报告必须输出
- 未通过项必须修复后才能进入测试门禁

---

### 6. 测试门禁

**检查点**：业务与体验验证前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| 功能测试 | senior-test-engineer | 100% 通过 |
| API 契约测试 | senior-test-engineer | 100% 通过 |
| 回归测试 | senior-test-engineer | 100% 通过 |
| 异常与边界测试 | senior-test-engineer | 100% 通过 |
| 耦合风险检查 | senior-test-engineer | 无高风险耦合 |

**门禁规则**：
- 所有测试必须 100% 通过
- 不通过项必须由 project-orchestrator 进行失败归因并分派修复

---

### 7. 业务与体验验证门禁

**检查点**：产品经理决策前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| 业务可用性验证 | senior-data-developer | 适合日常使用 |
| 功能冗余检查 | senior-data-developer | 无明显冗余 |
| UI/UX 后置审阅 | senior-ui-designer | 审阅报告完成 |
| 美化建议文档 | senior-ui-designer | 文档已输出 |

**门禁规则**：
- 验证报告必须输出
- 问题必须记录

---

### 8. 产品经理决策门禁

**检查点**：迭代归档前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| UI 建议决策 | senior-product-manager | 决策已记录 |
| 数据反馈决策 | senior-product-manager | 决策已记录 |
| 冗余功能决策 | senior-product-manager | 决策已记录 |
| 决策写入文档 | senior-product-manager | 文档已更新 |

**门禁规则**：
- 所有决策必须记录
- 采纳项必须明确写入下一轮迭代文档

---

### 9. 迭代归档门禁

**检查点**：下一轮迭代前

| 检查项 | 责任 Agent | 通过标准 |
|--------|-----------|---------|
| 归档报告输出 | project-orchestrator | 报告完整 |
| 遗留问题记录 | project-orchestrator | 问题已记录 |
| 下一轮输入生成 | project-orchestrator | 输入文档已生成 |

**门禁规则**：
- 归档报告必须完整
- 下一轮迭代输入必须生成

---

## 门禁检查流程图

```
DoR 前置评审
  ↓
评审通过？
  ├─ 否 → 解决问题后重新评审
  └─ 是 → 冻结 Feature Contract
    ↓
  产品/架构冲突判断
    ↓
  冲突解决？
    ├─ 否 → 继续解决
    └─ 是 → 进入并行开发
      ↓
    并行开发完成
      ↓
    开发 Agent 自检
      ↓
    自检通过？
      ├─ 否 → 修复后重新自检
      └─ 是 → 进入测试门禁
        ↓
      测试通过？
        ├─ 否 → 失败归因并分派修复
        └─ 是 → 进入业务与体验验证
          ↓
        验证完成？
          ├─ 否 → 补充验证
          └─ 是 → 进入产品经理决策
            ↓
          决策完成？
            ├─ 否 → 补充决策
            └─ 是 → 迭代归档
              ↓
            归档完成？
              ├─ 否 → 补充归档
              └─ 是 → 生成下一轮输入
```

---

## 归档报告模板

```markdown
## 本轮迭代归档报告

### 本轮目标
[目标描述]

### Feature Contract
[契约摘要]

### 涉及文档
- [文档1]
- [文档2]

### 涉及代码
- [文件1]
- [文件2]

### 实现内容
- [功能点1]
- [功能点2]

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
- [问题1]
- [问题2]

### 下一轮迭代输入
- [输入内容]
```
