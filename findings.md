# Findings & Decisions

## Requirements

- 从 PRD 到需求上线形成完整 AI 可执行流程。
- 支持同一需求多次、反复改版。
- 全过程工件统一记录在一个目录，便于 AI 了解历史与当前改动。
- 后续 Bug 使用一个通用 skill，遵循证据驱动闭环；需求变更不能伪装为缺陷修复。
- 用户可提供现成 PRD；第一步需要结合现有项目进行代码、架构、接口、数据、测试和约束分析，主动提问并补齐信息，最终产出完整可执行开发计划。
- 用户希望主流程只有三步：规划、完整执行、结果审核；既能任选其中一步，也能一键连续执行全部步骤。
- 工作流必须持续记录任务进度，后续需求自动获得已发布行为与历史改动上下文，不要求用户反复描述。
- 历史规模增大后必须结构化存储并按索引、相关性和变更关系按需加载，不能把全部历史塞进模型上下文。
- 当前任务是调研与方案分析，未授权实施产品代码。

## Research Findings

- 上一轮调研显示 `goal-workflow` 提供了 PRD、SPEC、Issue、审查与交付的提示词规程，但不是持久化工作流引擎；其批量交付存在自动合并风险。
- LangGraph 将每一步图状态写入按 `thread_id` 组织的 checkpoint；可读取历史、从指定 checkpoint replay，且 `update_state` 会产生新 checkpoint 而不修改旧记录。适合作为“运行态可恢复、人工可介入”的参考，但不能替代项目工件的长期权威记录。[官方文档](https://docs.langchain.com/oss/python/langgraph/persistence)
- OpenSpec 将每次行为变化建模为独立 change 目录，包含 proposal、design、tasks 和 spec delta；完成后归档 change。该“稳定基线 SPEC + 不可覆写变更集”的结构适合需求反复改版。[官方概览](https://openspec.dev/docs/overview)
- GitHub 可通过 PR 描述中的 closing keyword 把 PR、Issue 与默认分支合并结果关联；这可作为代码实现与任务追溯的外部锚点，但不能承载全部决策上下文。[GitHub Docs](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
- GitHub Spec Kit 采用 constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge 的工件链；其 `analyze` 为只读一致性检查，`converge` 以代码、spec、plan、tasks 为依据补齐缺口。这说明质量门禁应基于工件关系而不是只检查单个阶段是否“完成”。[官方快速入门](https://github.com/github/spec-kit/blob/main/docs/quickstart.md)
- GitHub rulesets 可叠加并取更严格约束，部署环境可设置人工批准和自定义保护规则。因此“发布/合并是否可执行”应由仓库与部署平台的硬门禁约束，而不能只依赖 agent 指令。[rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)、[deployment protection](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- 已审阅 `ysxz-bug-fix` 的通用闭环：完整读取 → 环境确认 → 修复前基线 → 根因分析 → 处理决策 → 方案/测试/修改 → 验证/汇报。核心可迁移点是：首次未复现不能结案，需求/规则缺失时转为需求变更，不以代码补丁掩盖症状。
- Temporal 将长流程的崩溃、网络或基础设施故障恢复抽象为 crash-proof execution。它适合多仓库、长时、并行交付的编排层，但对本方案的 MVP 来说过重；先把业务工件和状态机设计正确，再按规模引入。[官方文档](https://docs.temporal.io/)

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| 采用“版本化工件 + 事件日志 + 可恢复运行状态”三层模型进行分析 | 同时解决变更追溯、AI 上下文恢复和长流程执行问题 |
| 基线文件不被变更直接覆写，改版使用 change set/delta 表达 | 保留历史意图、影响范围和批准记录，便于 AI 构建当前视图 |
| Bug 工件必须关联问题报告、影响需求、根因和验证证据 | 支持从线上症状反向追溯到需求、版本、代码和发布记录 |
| 用三个面向用户的 Skill 封装内部子阶段 | 用户只需记住规划、执行、审核；复杂度由工作流承担 |
| 当前有效基线与历史变更分开存储 | 默认上下文保持小而准确，历史仅在影响分析时按需检索 |
| 使用 `meta/manifest + tasks` 作为事实源，`context/progress/summary` 作为派生视图 | 机器状态可验证，AI 又能快速恢复，不让摘要冲突覆盖事实 |
| 将 `phase`、`state`、`delivery` 分开 | 明确区分当前环节、是否阻塞以及实现/合并/上线状态 |

## Three-Step Synthesis

- `ai-workflow plan`：结合 PRD、当前能力和现有代码，提出阻塞性问题并产出带依赖、文件范围、验证、回滚和 REQ/AC 映射的可执行计划。
- `ai-workflow execute`：可执行全部计划、指定任务或从检查点恢复；每个任务更新结构化状态与证据。
- `ai-workflow review`：默认只读，对照计划、验收、代码和测试证据审核；发现问题生成修复任务，再回到 execute。
- `ai-workflow all` 依次调用三步并在人工门禁暂停；`status/resume/revise/history` 是辅助动作，不增加用户需要记忆的 Skill。
- Bug 保持一个通用 `bug-fix` Skill，并复用同一 work-item、进度和检索协议。

## Issues Encountered

| Issue | Resolution |
|-------|------------|
|       |            |

## Resources

- `docs/research/goal-workflow-analysis.md`
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- OpenSpec overview: https://openspec.dev/docs/overview
- GitHub issue/PR linking: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue
- GitHub Spec Kit: https://github.com/github/spec-kit/blob/main/docs/quickstart.md
- GitHub rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- GitHub deployment protection: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- Temporal durable execution: https://docs.temporal.io/

## Visual/Browser Findings

- 无
