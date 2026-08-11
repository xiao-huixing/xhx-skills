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
- 用户已授权按调研建议实施 `ai-workflow` 双文件运行时存储；范围不包含 `bug-fix` 或 SQLite canonical store。

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

## 2026-08-10 `ai-workflow` Audit

### Local observations

- Skill package totals 678 lines; `SKILL.md` is 120 lines, and references total 345 lines. Line count itself is moderate, but every mutating mode is forced to read the 125-line storage protocol before its mode reference.
- Every mode runs the same broad startup scan: repository instructions, README, build/test/security rules, project overview, modules, capabilities, active index, target context, and structured state. This makes even `status`, targeted `execute`, and repeat-session actions pay discovery costs designed for first-time planning.
- `execute` records state and appends an event both before and after every task, then regenerates derived views after meaningful changes. The protocol does not define batching, dirty-state thresholds, or a deterministic helper, so the agent is likely to perform many small read/write/validation cycles.
- The contract mixes orchestration, persistence, requirement modeling, code execution, review, history retrieval, and release gating in one skill. This raises routing complexity and makes success dependent on the model consistently maintaining a large distributed protocol.
- Existing eval assets need inspection before judging quality coverage; current symptoms suggest latency and outcome quality must be benchmarked separately.
- The only bundled script validates file presence, work-item ID shape, JSON parsing, and required event keys. It does not validate YAML syntax or schema, legal state transitions, task dependencies, REQ/AC traceability, latest-event consistency, index freshness, or lease semantics; most fragile state work is still delegated to the model.
- Existing evals contain four prompt-only cases with no fixture repository or input files, no saved run outputs/timing, no baseline, and no machine-verifiable grading. The `expectations` are broad behavioral statements, so the eval set cannot reveal whether an optimized version is faster or more correct.
- `status` says it “should not call an LLM,” but it exists only as a mode inside an LLM-invoked Skill and has no status script. The stated performance contract is therefore not implementable by the current package.
- The proposal already required light templates for low-risk changes, reuse of scan results/file hashes, and deterministic `init`, `status`, `index`, and validation scripts. The implementation contains only the shallow validator. The primary problem is therefore an MVP implementation gap, not simply excessive prose.
- `.codex-plugin/plugin.json` injects a default prompt telling Codex to use `ai-workflow` for generic plan/execute/review requests, while the Skill description says “Use whenever” for broad development intents. This can over-trigger the heavy workflow and compete with ordinary implementation, verification, or code-review behavior.
- The structured source of truth is duplicated: `manifest.yaml` and `execution/state.yaml` both store phase/state/next action, while `context.md`, `handoff.md`, active index, catalog, summary, and progress are derived. Without deterministic transactions, each duplicate creates extra writes and possible drift.
- A mutating run loads about 1,500-1,700 words of Skill/router/storage/mode instructions before repository context. This is not catastrophic by itself; the larger latency multiplier is the number of required filesystem/tool round trips and repeated scans.

### Primary-source findings

- OpenAI Docs says a selected Skill loads its entire `SKILL.md`, while bundled references remain optional; descriptions should be concise, front-load use cases and boundaries, each Skill should focus on one job, and scripts are appropriate for deterministic behavior. This supports reducing the router body and moving state-machine work into executable helpers: https://learn.chatgpt.com/docs/build-skills
- OpenAI's agent-evaluation guidance recommends inspecting end-to-end traces first, then using graders, datasets, and repeatable eval runs to compare routing or prompt changes. This confirms that the current final-output-only evals are insufficient for diagnosing latency and wasted tool calls: https://developers.openai.com/api/docs/guides/agent-evals
- Anthropic's official authoring guidance says context is shared, only information the model does not already know should be included, and the degree of instruction freedom should match task fragility. Fragile state transitions should use low-freedom scripts; open-ended planning/review should keep higher freedom: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- The same Anthropic guide recommends executing utility scripts instead of loading their source, creating verifiable intermediate outputs, and using a `plan → validate → execute → verify` loop for complex operations. This directly fits workflow initialization, state updates, event append, index rebuild, and gate validation.

### Optimization direction

- Keep one user-facing Skill, but make it a thin router. Splitting into three public Skills is not necessary initially and would increase user/trigger complexity; mode references plus a deterministic CLI preserve the three-step interface while restoring single responsibility at execution time.
- Add `light`, `standard`, and `strict` tracks selected from explicit risk facts. Small low-risk changes should avoid revisions, decisions, handoff, release, and history machinery until needed; migrations, auth, production side effects, or long-lived work use the strict track.
- Replace manual YAML/NDJSON editing with a single CLI surface: `init`, `resolve`, `status`, `task begin`, `task pass|fail|block`, `checkpoint`, `revise`, `index`, and `validate`. Each command should atomically update canonical facts, validate transitions, and regenerate only the views affected by that transition.
- Make startup mode-specific. `status` runs the status command only; `execute` loads the selected task and its acceptance/plan slice; `review` loads the target revision, diff, and evidence; only first-time `plan` performs broad project discovery. Cache discovery by Git head and relevant file hashes.
- Narrow implicit triggering and remove the plugin-level forcing prompt. For Codex, consider `agents/openai.yaml` with `policy.allow_implicit_invocation: false` if the intended usage is explicit `$ai-workflow`; otherwise constrain the description to lifecycle work with a PRD/REQ/durable-state need and state near-miss exclusions.

### Proposed priority and acceptance metrics

- P0 trigger: remove the forcing default prompt; add explicit near-miss boundaries. Measure trigger precision/recall over at least 20 realistic positive and adjacent negative prompts.
- P0 state CLI: implement atomic canonical-state commands and legal-transition/traceability validation. Acceptance: corrupted YAML, illegal transitions, dependency violations, stale last-event pointers, and missing REQ/AC mappings all fail deterministically with actionable errors.
- P0 fast path: implement `light` mode and mode-specific startup. Acceptance on a small low-risk change: no history/release/revision expansion, no full-project rescan after planning, and at least 40% fewer tool calls and 30% lower wall time than the current baseline without reducing task/test correctness.
- P1 canonical model: remove duplicated persisted phase/state fields or make one file generated only; regenerate context/handoff/index only at pause, phase transition, or completion. Acceptance: a single command leaves manifest/tasks/events and all generated views consistent after injected interruption.
- P1 evals: replace prompt-only evals with fixture repositories and assertions, snapshot the old Skill, run old/new on identical cases, capture duration/tokens/tool calls, grade behavior and filesystem state, and inspect traces for repeated reads/writes.
- P2 refinement: add risk-lane applicability so review checks security, migration, performance, observability, and rollback only when evidence makes them relevant; this should improve finding precision and reduce generic checklist noise.

## 2026-08-10 P0 Optimization Results

- `SKILL.md` 由 120 行降至 86 行，`status` 不再读取 repository rules、README、references 或 workflow history；缺失存储时 CLI 直接返回 `not_initialized` 且不创建目录。
- 新 CLI 成为结构化状态唯一 writer，覆盖 init、resolve、status、history、validate、plan-ready、approve-plan、task、review 和 refresh-index；状态写入带 lock、idempotency key、可恢复 transaction 和派生视图刷新。
- Validator 从文件/事件键存在性提升为完整 manifest/task/state schema、枚举、gate、DAG、evidence、event identity、last_event/active_task 和 state drift 校验；事务恢复拒绝目录逃逸。
- 旧模板被删除，避免模板、schema 与 CLI 三份定义继续漂移；JSON-compatible YAML 让 CLI 在没有 PyYAML 时仍能稳定写入。
- 3 个真实 fixture 的独立评分结果：current 14/14，baseline 6/14；盲比较 current 3/3 胜出。最大质量提升来自真正的 status fast path、strict money 路由和 CLI provenance，不是增加更多 prose。
- 单次 wall-time 不能支持“全面变快”的结论：status 快 61%，execute 快 14%，strict money plan 首轮慢 34%；第二轮减少重复读取/校验后比首轮快 12%，但仍比 baseline 慢 18%。后续 P1 应针对 planning discovery/cache 和可观测 tool-call telemetry，而不是弱化 strict 风险门禁。

## Resources

- `docs/research/goal-workflow-analysis.md`
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- OpenSpec overview: https://openspec.dev/docs/overview
- GitHub issue/PR linking: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue
- GitHub Spec Kit: https://github.com/github/spec-kit/blob/main/docs/quickstart.md
- GitHub rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- GitHub deployment protection: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- Temporal durable execution: https://docs.temporal.io/

## 2026-08-11 Runtime Storage Minimization

- 当前 `init` 固定写入 12 个路径，规划阶段加入 `plan.md` 后通常达到 13 个；其中 `state`、`context`、`active` 和 `catalog` 都是可重建派生视图。
- OpenAI 的 progressive disclosure 约束 Skill 包的加载方式，不要求目标项目生成特定数量的 runtime 文件；运行时布局可以独立收敛。
- 保留 Git diff/merge 与分支隔离时，推荐每工作项仅保留 `work-item.yaml + events.jsonl`：前者是 current snapshot，后者是 append-only audit log。
- `manifest`、`tasks`、revision input/plan、decisions、review、summary 与 evidence refs 合并进 `work-item.yaml`；索引、context、handoff 和 state 由 CLI 按需输出，不持久化。
- 单个项目级 YAML/JSONL 虽然文件总数更少，但会形成跨工作项、跨分支的共同写入热点；适合严格单 writer 的小型本地流程，不适合作为默认协作模型。
- SQLite 提供单文件、查询与 transaction，但 Git 对 binary 没有普通文本 diff/merge 体验；因此适合作为 ignored cache 或非 Git canonical store，而非当前 Git-versioned MVP 的权威文件。
- 两文本文件不具备 SQLite 的天然跨文件 ACID，必须保留单 CLI writer、atomic replace、`last_event_id`、幂等键与中断恢复测试。

## 2026-08-11 Two-File Implementation Baseline

- 现有 CLI 的 canonical model 分散在 `manifest.yaml`、`tasks.yaml` 和 `execution/events.ndjson`，每次 mutation 还重写 state、context 与两个 root index。
- 规划阶段当前依赖 agent 直接编辑 `tasks.yaml` 和 revision Markdown，和“CLI 是唯一 writer”冲突；双文件布局需要增加 `set-plan` 命令，把 plan、input 与 tasks 一次导入 `work-item.yaml`。
- 双文件 schema 采用 `work-item.yaml` schema version 2，保留现有 lifecycle 字段并内联 revisions、tasks、decisions、review、summary 与 evidence refs；event 增加 schema version、work-item ID 和单调 sequence，便于校验与未来迁移。
- 旧 schema version 1 不自动删除或覆盖，validator 应给出 legacy layout 错误；本轮不执行任何真实项目数据迁移。

## 2026-08-11 Two-File Implementation Results

- `init` 现在每个需求只创建 `work-item.yaml` 和 `events.jsonl`，固定持久化文件数由 12 个降为 2 个；规划内容、任务、决策、审核与证据引用统一内联到 snapshot。
- 新增 `set-plan` 作为规划数据唯一导入入口，消除 agent 直接编辑结构化状态的例外；`plan-ready`、审批、任务迁移和审核均只提交 snapshot 与 event log。
- `review needs_changes` 可通过 `--remediation-tasks-file` 原子导入返工任务，避免 CLI-only writer 让审核返工路径变成不可达状态。
- `status`、`resolve`、`history` 和 `refresh-index` 从 snapshot 按需计算，不再写项目概览、能力清单、索引、context、state 或 handoff。
- schema version 2 event 增加 `work_item_id` 与单调 `sequence`；validator 强制每需求恰好两个文件、snapshot/event 指针一致、任务 DAG 与生命周期门禁有效。
- 旧布局只读保留并明确拒绝；`init` 在已有无效或旧布局上也会先失败，避免悄悄混写新旧 schema。
- SQLite 未引入 canonical store，原因保持不变：虽然是单文件且可拷贝，但 binary Git diff/merge 与分支协作体验不适合当前 Git-versioned 工作流。

## Visual/Browser Findings

- 无
