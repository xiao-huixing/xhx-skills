# Task Plan: AI 可执行研发工作流方案

## Goal

形成一套以“规划、执行、审核”三步为用户入口，支持按阶段或全流程运行、反复改版、进度恢复和历史快速检索的 AI 研发工作流方案。

## Current Phase

Phase 12: `ai-workflow` P0 optimization

## Phases

### Phase 1: 需求边界与资料调研

- [x] 明确核心诉求：全生命周期、改版可追溯、统一过程目录、AI 可恢复上下文
- [x] 明确 Bug 只设计为一个通用 skill，借鉴 `ysxz-bug-fix` 的证据闭环
- [x] 调研耐久工作流、上下文持久化、规格变更与 Git 追溯的一手资料
- [x] 记录可复用机制与限制
- **Status:** complete

### Phase 2: 架构与状态模型

- [x] 定义领域对象、目录布局、状态机、变更集和可追溯关系
- [x] 定义人工审批与自动执行边界
- **Status:** complete

### Phase 3: 工作流设计

- [x] 设计 PRD、SPEC、Issue、开发、验证、发布、运行后反馈和通用 Bug 修复闭环
- [x] 设计需求改版和中断恢复流程
- **Status:** complete

### Phase 4: 落地路径与验证

- [x] 给出 MVP、技术选型和渐进式实施顺序
- [x] 核对方案能覆盖用户核心诉求
- **Status:** complete

### Phase 5: 交付

- [x] 输出结论和建议
- [x] 保存调研与方案文档
- **Status:** complete

### Phase 6: 三步交互与 Skill 边界

- [x] 将复杂研发环节收敛为规划、执行、审核三个主入口
- [x] 定义单步运行、连续运行、恢复运行和需求改版的调用方式
- [x] 定义三个 Skill 的输入、输出和完成门禁
- **Status:** complete

### Phase 7: 进度、历史与检索

- [x] 设计统一过程目录、当前摘要、历史索引和按需加载协议
- [x] 避免新会话重复输入历史信息和一次性加载全部历史
- **Status:** complete

### Phase 8: 易用性与可靠性复核

- [x] 检查正常需求、局部执行、失败恢复、需求改版和 Bug 路径
- [x] 明确自动执行与人工确认的最小边界
- **Status:** complete

### Phase 9: 方案交付

- [x] 输出综合方案与建议的 MVP
- [x] 保存方案文档
- **Status:** complete

### Phase 10: 第一版 Skill 实施

- [x] 创建 `ai-workflow` 主 skill、模式参考、存储协议和模板
- [x] 创建通用 `bug-fix` skill、证据协议和模板
- [x] 增加工作流结构与事件日志校验脚本
- [x] 增加最小单元测试和 skill eval 用例
- [x] 更新 README 的安装入口
- **Status:** complete

### Phase 11: `ai-workflow` 性能与效果审计

- [x] 审阅 Skill 入口、模式引用、存储协议、模板、脚本和现有 eval
- [x] 结合真实使用链路定位慢点、无效约束和上下文膨胀来源
- [x] 查阅最新一手资料，核验 Skill progressive disclosure、触发与评测实践
- [x] 给出按收益、风险和实施成本排序的优化方案与验证指标
- **Status:** complete

### Phase 12: `ai-workflow` P0 优化

- [x] 冻结当前 Skill 快照并建立可运行基线
- [x] 先补确定性 CLI、schema、状态迁移和只读 fast-path 的失败测试
- [x] 实现原子 `init/status/resolve/history/validate/task/review/index` CLI
- [x] 将 Skill 收敛为薄路由器，按模式加载并缩窄隐式触发
- [x] 增加 `light/standard/strict` 分级和真实 fixture eval
- [x] 运行单元测试、静态检查、差异审查和 Skill 对照评测
- **Status:** complete

## Key Questions

1. 如何把需求改版建模为可审计的变更集，而不是覆写旧文件？
2. AI 在新会话或中断后，如何可靠恢复任务、决策和当前状态？
3. 哪些动作可自动执行，哪些必须由人批准？
4. 如何让 Git、Issue/PR 与过程工件互相可追溯？
5. 如何让一个通用 Bug skill 处理不同技术栈，同时避免把需求改动误判为代码缺陷？
6. 如何让用户只理解三步，同时保留内部完整性和可恢复性？
7. 如何做到默认加载当前有效上下文，只有需要时才检索历史细节？

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 工件存储采用 Git 可读的文件优先 | 满足统一目录、人工审阅、diff、长期可追溯与 AI 检索 |
| 规划执行状态与业务工件分离 | 避免临时运行状态污染已批准的需求/设计记录 |
| Bug 采用一个通用 skill，而不是按技术栈或团队拆分 skill | 复用同一证据、根因、验证和交付门禁；由项目适配层选择具体工具 |
| 用户界面固定为规划、执行、审核三个主入口，内部环节不再暴露 | 降低使用和记忆成本，同时保留完整工程门禁 |
| 实现为一个 `ai-workflow` Skill 的 `plan/execute/review` 三种模式 | 三步可独立、串联或恢复；共用协议可避免三个 Skill 漂移 |
| 对外使用 `REQ-*` 和 `BUG-*`，同一项改版使用 `R001/R002` | 比抽象 `CHG-*` 更直观，且用户无需手工管理编号 |
| 工作项目录创建后不移动，完成状态通过索引表达 | 避免归档移动造成工件链接、PR 和历史引用失效 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| `apply_patch` 上下文不匹配 | 1 | 将大补丁拆为多个精确补丁后完成更新 |
