# Agent 角色矩阵

## 角色总览

| Agent 名称 | 类型 | 能否修改代码 | 能修改的文件类型 | 禁止事项 | 主要输出物 | 需要交接给谁 |
|------------|------|-------------|-----------------|---------|-----------|-------------|
| project-orchestrator | primary | 需确认 | 全部（需确认） | 直接写业务代码 | 迭代归档报告 | 无 |
| senior-product-manager | subagent | 否 | 文档类（*.md） | 写代码、改后端、改前端 | 产品需求、验收标准 | senior-architect |
| senior-architect | subagent | 否 | 架构文档（*.md） | 写业务代码、改前端、改后端 | 技术方案、接口契约 | senior-backend-developer / senior-frontend-developer |
| senior-frontend-developer | subagent | 是 | 前端源码（*.tsx, *.ts, *.css） | 引入未文档化功能、改后端 | 前端实现、自测说明 | senior-test-engineer |
| senior-ui-designer | subagent | 否 | UI 建议文档（*.md） | 写代码、改产品需求 | UI/UX 审阅报告 | senior-product-manager |
| senior-backend-developer | subagent | 是 | 后端源码（*.py, *.sql） | 改模块边界、改产品文档 | 后端实现、接口说明 | senior-test-engineer |
| senior-data-developer | subagent | 否 | 测试用例（*.sql）、文档（*.md） | 改前后端代码、改测试门禁 | 测试用例、业务验证报告 | senior-product-manager |
| senior-test-engineer | subagent | 是 | 测试文件（*.test.*, *.spec.*） | 改业务代码、改产品文档 | 测试报告 | project-orchestrator |

---

## 详细权限说明

### project-orchestrator（主控 Agent）

**可修改**：
- 全部文件（但修改前必须请求确认）

**主要输出**：
- 迭代归档报告
- 任务拆解方案
- Agent 调度指令

**交接对象**：
- 无（最终决策者）

---

### senior-product-manager（产品经理）

**可修改**：
- 产品需求文档
- 迭代文档
- 验收标准文档
- 界面决策文档

**主要输出**：
- 产品目标
- 用户场景
- 功能边界
- 页面与交互要求
- 优先级（P0/P1/P2）
- 验收标准

**交接对象**：
- senior-architect（技术确认）
- senior-frontend-developer（前端实现）
- senior-backend-developer（后端实现）

---

### senior-architect（架构师）

**可修改**：
- 架构设计文档
- 技术方案文档
- 接口契约文档
- 模块功能点文档
- 技术风险文档

**主要输出**：
- 技术目标
- 模块边界
- 接口契约
- 数据流
- 实现顺序
- 性能风险
- 耦合风险
- 可测试性要求

**交接对象**：
- senior-backend-developer（后端实现）
- senior-frontend-developer（前端实现）
- senior-test-engineer（测试关注点）

---

### senior-frontend-developer（前端开发）

**可修改**：
- 前端源码（src/、frontend/、client/、app/、components/、pages/）
- 前端测试文件
- 前端样式文件

**主要输出**：
- 实现文件清单
- 组件变更说明
- API 联调说明
- 状态管理说明
- 前端自测结果

**交接对象**：
- senior-test-engineer（测试验证）
- senior-ui-designer（UI 审阅）

---

### senior-ui-designer（UI 设计）

**可修改**：
- UI/UX 建议文档
- 界面设计文档

**主要输出**：
- 当前界面问题
- 用户注意力问题
- 信息密度问题
- 视觉层级问题
- 建议优化项

**交接对象**：
- senior-product-manager（决策是否采纳）

---

### senior-backend-developer（后端开发）

**可修改**：
- 后端源码（src/、backend/、server/、api/、services/、models/、utils/、core/）
- Python 文件（*.py）
- SQL 文件（*.sql）
- 后端测试文件

**主要输出**：
- 实现文件清单
- 核心逻辑说明
- 接口变更说明
- 数据模型变更说明
- 异常处理说明
- 单元测试说明

**交接对象**：
- senior-test-engineer（测试验证）
- senior-frontend-developer（接口联调）

---

### senior-data-developer（数据开发）

**可修改**：
- SQL 测试用例文件
- 元数据测试样例
- 业务测试反馈文档

**主要输出**：
- 测试用例
- SQL 场景覆盖
- 元数据场景覆盖
- 业务可用性判断
- 问题反馈

**交接对象**：
- senior-product-manager（问题反馈）

---

### senior-test-engineer（测试开发）

**可修改**：
- 测试目录（tests/、test/、__tests__/）
- 测试文件（*.test.*、*.spec.*）
- 测试报告文档

**主要输出**：
- 测试范围
- 测试 case 清单
- 通过/失败 case
- 回归风险
- 耦合风险
- 最终结论（通过/不通过）

**交接对象**：
- project-orchestrator（测试结果）
- 对应开发 Agent（失败 case 修复）
