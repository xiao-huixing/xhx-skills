# 面向 AI 的可执行研发工作流：一手资料调研与设计建议

> 调研日期：2026-08-07。资料仅采用项目官方文档或官方源码。本文讨论的“工作流”覆盖 PRD、规格、实现、验证、发布及可追溯的变更历史；不是把一次 Agent 会话包装成线性 prompt。

## 结论

推荐建设一个**以 Git 中的工件目录为事实源（source of truth）**、以“当前产品基线 + 不可变的变更包（change package）+ 可验证执行状态”为核心的工作流。每一次需求改版都新建或显式修订一个变更包，绝不静默覆盖已批准/已发布的需求；变更完成后把 delta 合入当前基线，并保留整个变更包归档。

这比直接照搬 `goal-workflow` 更适合“需求会反复变化”的场景：

- 用 OpenSpec 的“主规格 + change delta + archive”解决需求语义演进与历史回看。
- 用 Spec Kit 的 feature-folder、验收场景、计划与任务可追溯结构解决 AI 可执行性。
- 用显式的 `state.yaml`、事件记录、Git/CI/发布证据解决跨 Agent 恢复，而不是依赖聊天上下文。
- 仅在确有跨天、异步、重试、人工审批等待的系统编排需求时，引入 LangGraph 或 Temporal；二者都不应成为需求文档的唯一存储位置。
- Git/GitHub 的 Issue、PR、commit、CI 和 deployment 作为外部交付证据，与变更包双向链接；发布和合并仍必须经过明确门禁。

## 目标与非目标

### 目标

1. AI 在新的会话、换模型或中断恢复后，能从仓库工件还原：当前需求、已确认决策、待做任务、执行到哪一步、验证结果及外部链接。
2. 同一能力允许多轮改版；可明确回答“当前生效行为是什么”“这次为什么改”“由哪次发布交付”。
3. PRD 到发布均有可验证的输入、输出、责任人和状态迁移；流程既能自动推进，也能在有风险时等待人工批准。
4. 过程文件集中在一个项目目录，并由 Git 版本化、可审阅、可回滚。

### 非目标

- 不记录 Agent 的完整对话、隐藏推理或原始 token 流。它们既噪声大又难审阅；应记录的是**结论、依据、命令、输出摘要与链接**。
- 不将任意一个 AI 框架的 checkpoint/history 当产品需求的唯一事实源。
- 不允许 Agent 因任务状态为“完成”就自动合入主干、关闭需求或发布生产；这些都是需要单独授权的外部副作用。

## 一手资料机制与取舍

| 机制 | 一手资料中的能力 | 可借鉴点 | 不能直接照搬处 |
| --- | --- | --- | --- |
| LangGraph checkpoint / thread / store | Checkpointer 按 `thread_id` 保存图状态；Store 保存跨 thread 的长时数据；可中断、恢复、查看状态历史、从历史 checkpoint replay。 | 每次图步骤后持久化、把“本次执行”和“跨执行知识”分开、人工审批后从中断点继续。 | checkpoint 是运行时状态，不是可 code-review 的 PRD/SPEC；内存 saver 重启即丢失，长 thread 还要做保留策略。不要把需求历史只放数据库。 |
| Temporal durable execution / replay / versioning | Workflow 以 Event History 恢复；失败从最后记录事件继续；长历史可 Continue-As-New；运行中的 workflow 代码变更需要 deterministic versioning/patch。 | 把外部动作设计成可重试、幂等的 Activity；将“等待批准/CI/部署”建模为 durable wait；为工作流定义版本与迁移策略。 | Temporal 解决的是**执行可靠性**，不是需求版本管理。它要求基础设施和确定性约束；把频繁变化的 Agent 决策树直接写入长期 Workflow，会带来 patch、replay 与 history 膨胀成本。 |
| OpenSpec 主规格、delta 和归档 | `specs/` 存当前能力；每个 `changes/<name>/` 自带 proposal/design/tasks/delta spec；archive 时合并 ADDED/MODIFIED/REMOVED/RENAMED，并保留完整上下文。OPSX 支持随时更新工件。 | “基线与变更分离”“完成变更归档但不丢上下文”“需求项有稳定可匹配标识”“冲突必须人工解决”。这是多次改版的核心。 | OpenSpec 到 archive 为止，未定义项目的 Issue、PR、CI、环境部署、权限门禁和 Agent 运行状态；需要在其上增加交付层。 |
| Spec Kit feature 工件与可执行任务 | `spec.md` 包含独立可验收 user story、Given/When/Then、FR、可量化成功标准；`plan.md` 链接 spec 并列出研究、数据模型、契约、任务；`tasks.md` 映射 story、文件路径、依赖和检查点。 | 将“能否由 AI 执行”落实为结构化输入：每项任务有范围、依赖、预期文件和验证；以验收场景而非实现细节约束结果。 | 默认 feature/branch 流程偏单次开发，模板本身没有“已发布基线 + 多轮 delta + 归档合并”语义；测试在模板中是可选项，项目应将质量门禁改为强制规则。 |
| Git / GitHub Issue、PR、分支保护 | PR 可关联 Issue，合并到默认分支可自动关闭关联 Issue；分支保护可要求 review、status checks、会话解决、部署成功及 merge queue。 | 建立从变更包到 Issue/PR/commit/CI/部署的证据链；将 PR 作为代码审查和合入门禁，利用分支保护防止 Agent 绕过。 | Issue/PR 时间线不能替代仓库中的语义规格；closing keyword 只对默认分支目标生效。不要让 Agent 仅凭 GitHub 状态推断需求已满足。 |
| Git notes / worktree | `git notes` 可附着信息但不修改对象；`git worktree` 可同时检出多个分支。 | notes 适合补充 commit 级审计信息；worktree 可隔离互不依赖的 AI 任务。 | 主流程工件仍应是普通、被提交的文件，便于 clone、diff、review 和检索；并行 worktree 仅适用于已确认无文件冲突的任务，不能绕过统一状态锁。 |

### 直接来源

- [LangGraph Persistence 官方文档](https://docs.langchain.com/oss/python/langgraph/persistence)：checkpointer/store 的范围、`thread_id`、持久化限制与保留建议。
- [Temporal Workflow Execution 官方文档](https://docs.temporal.io/workflow-execution)：Event History、replay、失败恢复、状态与执行链。
- [Temporal TypeScript Workflow Versioning 官方文档](https://docs.temporal.io/develop/typescript/workflows/versioning)：运行中 workflow 的 deterministic 约束、patch 与 worker versioning。
- [Temporal Continue-As-New 官方文档](https://docs.temporal.io/workflow-execution/continue-as-new)：检查点后创建新 Run、历史大小和版本演进限制。
- [OpenSpec 官方 conventions spec](https://github.com/Fission-AI/OpenSpec/blob/main/openspec/specs/openspec-conventions/spec.md)：目录、需求 delta、合并及冲突语义。
- [OpenSpec Concepts 官方文档](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md)：change folder、自包含工件、并行变更与 archive 的审计价值。
- [OpenSpec OPSX migration guide](https://github.com/Fission-AI/OpenSpec/blob/main/docs/migration-guide.md)：工件可随时更新、非线性工作方式及续作方式。
- [Spec Kit 官方 README](https://github.com/github/spec-kit)：规格、计划、任务、实现与分析命令的职责。
- [Spec Kit spec template 源码](https://raw.githubusercontent.com/github/spec-kit/main/templates/spec-template.md)、[plan template 源码](https://raw.githubusercontent.com/github/spec-kit/main/templates/plan-template.md)、[tasks template 源码](https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md)：验收、工件链接、任务依赖和可独立验证结构。
- [GitHub：关联 PR 与 Issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)、[GitHub：保护分支](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)：追溯和合入门禁。
- [Git notes 官方手册](https://git-scm.com/docs/git-notes)、[Git worktree 官方手册](https://git-scm.com/docs/git-worktree)：补充审计和隔离工作区能力。

## 推荐的目录与数据模型

在仓库根目录建立 `.ai-workflow/`。点目录表达“供 Agent 和工程流程使用”，但其中所有 Markdown/YAML/JSON 都必须提交到 Git；不要将其加入 `.gitignore`。

```text
.ai-workflow/
├── README.md                         # 恢复协议、状态机、命令和人工门禁
├── project.md                        # 领域、架构边界、质量与安全基线
├── registry.yaml                     # 活动变更、能力与外部链接索引
├── capabilities/                     # 已发布、当前生效的产品行为基线
│   └── <capability>/spec.md
├── changes/                          # 尚未归档的变更包
│   └── CHG-20260807-001-order-cancel/
│       ├── change.yaml               # 机器可读清单、状态、版本与所有关联
│       ├── 00-intake.md              # 原始诉求、来源、澄清问题和范围
│       ├── 01-prd.md                 # 业务目标、故事、验收、非目标
│       ├── 02-research.md            # 代码/资料调研结论与来源
│       ├── 03-spec-delta/            # 对 capabilities/ 的 ADDED/MODIFIED/REMOVED/RENAMED
│       │   └── <capability>/spec.md
│       ├── 04-design.md              # 技术方案、风险、接口、数据迁移
│       ├── 05-tasks.md               # 可执行任务、依赖、文件范围、验证命令
│       ├── 06-decisions.md           # 已确认决策与拒绝方案，追加式记录
│       ├── 07-execution/
│       │   ├── state.yaml            # 当前可恢复状态，不写自由文本推理
│       │   ├── events.ndjson         # 追加式事件：动作、证据、时间、操作者
│       │   └── handoff.md            # 面向下一 Agent 的压缩上下文
│       ├── 08-verification.md        # 测试、静态检查、审查、验收和残余风险
│       ├── 09-release.md             # PR、commit、构建、环境、发布/回滚证据
│       └── traceability.md           # REQ → task → test → commit/PR → deploy 映射
└── archive/                          # 已发布或取消的完整变更包，永不重写
    └── 2026/CHG-20260807-001-order-cancel/
```

目录同时吸收 OpenSpec 的“当前基线/active change/archive”，以及 Spec Kit 的“同一个 feature 下保留 spec/plan/task/研究文件”的优点。一个 `CHG-*` 是恢复和审计的最小单位；Agent 不需要在 `docs/`、Issue、聊天记录和临时文件之间猜测当前上下文。

### `change.yaml` 的最小字段

```yaml
id: CHG-20260807-001-order-cancel
title: 订单取消规则改版
status: clarified
revision: 2
kind: feature                 # feature | bugfix | refactor | operational
base:
  git_ref: 3a4b5c6
  capability_specs:
    - order-lifecycle@8d92aa1
supersedes: CHG-20260612-004-order-cancel
depends_on: []
links:
  issue: https://github.com/org/repo/issues/123
  pull_requests: []
  deployments: []
gates:
  prd_approved: false
  design_approved: false
  release_approved: false
artifacts:
  prd: 01-prd.md
  delta: 03-spec-delta/order-lifecycle/spec.md
  tasks: 05-tasks.md
  state: 07-execution/state.yaml
```

关键不是字段名称，而是四条不可省略的约束：

1. `id` 永久不变，需求项、任务、测试也有稳定 ID，例如 `REQ-ORDER-014`、`TASK-023`、`TEST-ORDER-008`。
2. `base.git_ref` 和 `capability_specs` 固化该改版建立时所依据的版本；任何 Agent 续作前都可检测基线是否已漂移。
3. `supersedes`、`depends_on` 和外部链接显式化，不能用自然语言暗示依赖。
4. `gates` 是授权状态，不从“文件已生成”或“AI 认为完成”自动推导。

## 多轮改版规则

### 1. 区分“编辑草稿”与“新业务变更”

- 在 `draft`/`clarified` 阶段，允许在同一 `CHG-*` 中修改 PRD、设计和任务，依靠 Git commit 留存 revision；每次实质修改在 `06-decisions.md` 记 `revision`、原因和受影响的需求 ID。
- 一旦设计被批准、开始实现、开出 PR，需求发生实质变化时应创建**新的** `CHG-*`，其 `supersedes` 或 `depends_on` 指向原变更。这样旧 PRD、验证证据和发布结果仍保持可解释。
- 已发布能力只通过新变更的 delta 更新。禁止直接改写 `capabilities/<capability>/spec.md` 后声称是“小调整”。
- 取消的变更也归档，`status: cancelled` 并写明原因；它是后来 Agent 避免重复实现已否决需求的上下文。

### 2. 用 delta 表达需求变化

需求规格使用可机器匹配的 ID 和固定标题。变更包中只描述差异：`ADDED`、`MODIFIED`、`REMOVED`、`RENAMED`，每个修改保留完整的新 requirement 和变更理由。发布后校验 delta 所基于的 requirement 仍存在，再合并到 `capabilities/`；冲突必须转入人工决策，不能让 AI 选一个版本覆盖。

这是对 OpenSpec archive 机制的直接借鉴：其官方约定要求按 rename/remove/modify/add 顺序应用 delta，且对不存在的修改目标和冲突报告具体错误并要求人工解决。[来源](https://github.com/Fission-AI/OpenSpec/blob/main/openspec/specs/openspec-conventions/spec.md)

### 3. 需求与实现的双向追溯

`traceability.md` 至少维护下表；其中“证据”必须是可打开的文件路径、commit SHA、PR URL、CI run URL 或部署记录，不能填“已验证”。

| 需求 ID | 变更类型 | 任务 | 验证 | 代码/PR | 发布证据 | 当前状态 |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-ORDER-014 | MODIFIED | TASK-023, TASK-024 | TEST-ORDER-008, UAT-03 | `abc123`, PR #456 | staging run #789 | verified |

OpenSpec 的行为优先、可验证场景，以及 Spec Kit 的 independent story/test/task 组织都支持这一做法；稳定 ID 则是本方案为跨轮改版增加的约束。[OpenSpec source](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/openspec/specs/openspec-conventions/spec.md) [Spec Kit task template](https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md)

## 通用 `bug-fix` skill

Bug 只保留一个通用 `bug-fix` skill，不按 UI、API、数据、性能或部署问题拆分多个 skill。它复用相同的 `CHG-*` 变更包，令 `change.yaml` 使用 `kind: bugfix`；仅按缺陷类型选择不同的基线和验证入口。这使缺陷与原始需求、发布版本和修复代码落在同一条追溯链，而不是产生一套平行的“Bug 流程”。

该 skill 的门禁借鉴已安装的 `ysxz-bug-fix`，但去除特定项目、平台与技术栈假设：

```text
reported
  → evidence_complete → environment_ready
  → baseline_reproduced ─→ root_caused → decision_made
  → fix_planned → implemented → verified → release_candidate
  → deployed → observed → closed

baseline_inconclusive → recheck → baseline_reproduced | not_reproduced | blocked
decision_made → needs_requirement_change | no_code_change | blocked
```

### 固定产物与完成条件

| 阶段 | 必填工件 | 不可跳过的判断 |
| --- | --- | --- |
| 输入 | `00-intake.md` | 读取当前可访问的报告、附件、关联需求/变更/版本、后续评论和变更记录；记录事实、推断、未知与冲突。 |
| 基线 | `02-baseline.md` | 以真实入口、版本、身份、数据和依赖复现准确症状；首次未复现必须重新核对条件与调用路径，不能直接关闭。 |
| 定位 | `02-research.md`、`06-decisions.md` | 找到首次偏差，记录竞争假设、反证、影响范围和正确责任边界。 |
| 决策 | `06-decisions.md` | 若预期不清、规则冲突或实际属于产品改动，状态转为 `needs_requirement_change`，新建普通 `CHG-*`；不得用代码补丁伪造修复。 |
| 修复 | `04-design.md`、`05-tasks.md` | 仅修改根因的最小责任边界；可行时先把最小复现固化为回归测试。 |
| 验证 | `08-verification.md` | 相关自动化检查、原始场景、影响分析对应的回归和安全检查全部有证据；验证失败则回到定位。 |
| 发布后 | `09-release.md` | 写入版本和部署证据；在定义的观察窗口内检查告警、关键指标或原症状，才可 `closed`。 |

缺陷类型只影响“首选验证入口”，不改变上述闭环：UI 用真实浏览器路径与 console/network，API 用原始请求或集成测试，异步/并发用事件时间线和可重置测试数据，性能用同一负载下的基线/复测，配置/部署用版本和有效配置对照。skill 总是先读取当前项目的工程与安全指令，再选用项目已有测试、IDE 或浏览器工具。

### 证据与权限边界

- 原始日志、附件、Token、个人或业务数据不得直接提交。`00-intake.md`、`02-baseline.md` 只存脱敏摘要、哈希、时间和受控系统中的证据链接。
- `bug-fix` 默认只读收集证据。修改代码、创建/更新 Issue、提交 PR、部署、重启和数据修正各自需要流程策略或用户的明确授权，不能因 Bug 状态自动获得权限。
- 最终状态限于 `closed`、`not_reproduced`、`no_code_change`、`needs_requirement_change`、`blocked`；每种状态都必须带工件链接和下一步，而不是一个模糊的“已处理”。

因此，`bug-fix` 是生产反馈重新进入主工作流的唯一入口：它要么形成已验证的 `bugfix` 变更包，要么把真正的需求改版转交给普通变更包，要么留下可审计的未复现/阻塞结论。

## 可执行状态机

```text
draft
  → clarified ──(PRD 人工确认)──→ specified
  → planned   ──(设计/风险确认)──→ ready
  → implementing → verified → reviewed
  → release_candidate ──(发布批准)──→ deployed → archived

任一阶段：需求实质改变 → 新 CHG（引用被替代的 CHG）
任一阶段：基线漂移/冲突 → blocked，记录冲突后等待决策
任一阶段：验证失败 → implementing 或 planned，保留失败证据
```

建议将迁移写成可执行 validator，而不是只写在 prompt：

| 迁移 | 自动检查 | 人工门禁 | 输出 |
| --- | --- | --- | --- |
| `draft → clarified` | PRD 含目标、范围、非目标、验收标准和待澄清项 | 产品负责人确认需求解释 | `01-prd.md`、决策记录 |
| `clarified → specified` | delta 与基线 requirement ID 匹配；规格有可测试场景 | 高风险/跨团队需求确认 | `03-spec-delta/` |
| `specified → ready` | 设计、任务、依赖、文件范围和验证命令齐全；任务都能映射 REQ | 技术负责人确认架构/迁移/安全风险 | `04-design.md`、`05-tasks.md` |
| `ready → implementing` | 工作区干净或已有 worktree；状态锁可获得；基线 SHA 未漂移 | 无，除非策略要求 | branch/worktree、execution event |
| `implementing → verified` | 指定 test/lint/build/security check 全部有证据；需求到测试映射完整 | UAT/人工验收需要签核 | `08-verification.md` |
| `verified → deployed` | PR 已通过受保护分支所需检查，部署计划/回滚信息完整 | 发布批准，尤其是生产环境 | `09-release.md` |
| `deployed → archived` | 基线 spec 已合并 delta；registry 已更新；链接可解析 | 可选的发布后确认 | archive 路径、最终摘要 |

GitHub 已支持将 status checks、review、会话解决与 deployment success 设为分支保护要求，因此 validator 的结果可以以 CI check 形式接到真正的 merge gate；但生产授权仍由企业流程决定。[来源](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## AI 恢复上下文协议

把以下协议写进 `.ai-workflow/README.md`，并要求所有编排 skill 在编辑/执行前遵守。它比“让 AI 先读一堆文档”更可靠，因为顺序、入口和中止条件是确定的。

1. **定位**：读取 `registry.yaml`，选定 `CHG-*`；未给定 ID 时，只列出 active change 并请求选择，不自行挑选相似需求。
2. **重建语义**：依次读取 `change.yaml`、`00-intake.md`、`01-prd.md`、相关当前 capability spec、delta、`06-decisions.md` 和 `handoff.md`。只加载与当前任务相关的能力，避免无关上下文污染。
3. **重建执行现场**：读取 `state.yaml` 和 `events.ndjson` 最后成功事件；检查 `base.git_ref`、当前 branch/HEAD、工作树、PR/Issue、CI 和 deployment 链接是否与文件一致。
4. **检测漂移**：若 capability 基线、目标分支或外部状态已变化，写入 `blocked` event，生成影响分析；禁止沿用旧计划直接执行。
5. **计划一个原子动作**：每次只领取 `05-tasks.md` 中一个可执行任务或一个明确的 gate；先写 `started` 事件，再执行。
6. **留下接力信息**：动作成功/失败都追加 event，更新 `state.yaml`，在 `handoff.md` 用短文本写明“已完成、未完成、阻塞、下一步、证据”。必要时更新 `traceability.md`。

`state.yaml` 应是小型机器状态而非日志副本，例如：

```yaml
change: CHG-20260807-001-order-cancel
phase: implementing
active_task: TASK-023
owner: codex
lease:
  holder: codex-session-<opaque-id>
  expires_at: 2026-08-07T12:00:00+08:00
last_success:
  event: EVT-00017
  git_head: abc1234
  evidence: 08-verification.md#unit-tests
blocked_by: []
next_action: "执行 TASK-024：补充取消后库存回补的集成测试"
```

`events.ndjson` 使用追加式事件，至少含 `event_id`、`at`、`actor`、`type`、`task`、`input_refs`、`output_refs`、`git_head`、`result`。敏感参数、token、密码及完整命令输出不应写入；保留经脱敏的摘要和 CI URL 即可。

## LangGraph 与 Temporal 的正确位置

### 轻量方案：先不引入工作流引擎

多数代码仓库的第一版仅需：仓库目录、Markdown/YAML schema、一个 `workflow status|validate|resume` CLI、Git hooks/CI 和 Agent skills。它已经能处理跨会话恢复，因为事实源已在 Git 中；运维复杂度最低。

### 需要 Agent 图编排时使用 LangGraph

可将一个 `CHG-*` 作为 LangGraph `thread_id`，节点仅执行“解析变更包、生成草稿、等待批准、实施任务、运行验证、更新证据”等原子步骤。checkpointer 保存节点级恢复点，Store 保存非敏感的跨 change 检索索引。每个节点都读写 `.ai-workflow/changes/<id>/`；checkpoint 仅保存引用、当前 node、任务 ID 和短状态。

LangGraph 官方把 checkpointer 定位为单 thread 的 graph state，而 Store 用于跨 thread 的应用数据；其文档也明确内存 saver 在重启后丢失、checkpoint 会持续增长。因此生产使用持久 checkpointer 和 retention，但仍以 Git 工件为真相。[来源](https://docs.langchain.com/oss/python/langgraph/persistence)

### 需要跨天可靠编排时使用 Temporal

当流程要等待人工确认、多个 CI、异步扫描、外部部署、回滚或重试，才将一个 `CHG-*` 映射为 Temporal Workflow。每一个会产生副作用的动作都应是具幂等键的 Activity，例如 `changeId + taskId + attempt`；workflow 只存状态机与工件引用，实际工件仍提交 Git。

Temporal 可从 Event History 的最后记录事件恢复，但运行中的 Workflow 代码更新必须处理 deterministic replay 与版本兼容；官方给出 patch / worker versioning 和 Continue-As-New。故第一版不要把频繁改动的 Agent prompt/流程细节硬编码成长期 Temporal workflow，直到流程本身稳定、具备 replay test、version policy 和运维能力。[执行与恢复](https://docs.temporal.io/workflow-execution) [版本演进](https://docs.temporal.io/develop/typescript/workflows/versioning) [Continue-As-New](https://docs.temporal.io/workflow-execution/continue-as-new)

## GitHub 追溯与发布集成

### 双向链接规则

- GitHub Issue body 固定包含 `Change: CHG-...`、关联 REQ、验收场景和 `.ai-workflow/.../01-prd.md` 链接。
- branch 使用 `chg/CHG-...-short-name`；commit footer 使用 `Change: CHG-...`、`Task: TASK-...`。
- PR 描述包含变更包路径、需求/测试映射、验证命令与结果、风险和回滚方案；用 `Closes #123` 只关闭明确已完整交付的 Issue。
- `09-release.md` 写入 merge commit、CI run、环境、部署版本、操作者、发布时间与 rollback reference；不要把“PR merged”等同于“已上线”。

GitHub 对 PR/Issue 的自动关闭只能发生在合并到默认分支时，故该自动化适合更新 Issue 状态，不适合作为“需求已经在生产满足”的证据。[来源](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)

### 推荐权限模型

- Agent token：仅能创建 branch、commit、push、创建/更新 PR、读取 CI；默认不能直接 merge、创建 release、访问生产凭据或关闭关键需求。
- 分支保护：必须 PR、指定 CI、所需 review、需要时 code owner 与会话解决；新 commit 使批准失效。
- 人类批准：`prd_approved`、高风险 design、生产部署、回滚、归档时的基线合并。
- CI：运行 `workflow validate` 检查 schema、状态迁移、REQ/TASK/TEST 覆盖、所有引用的本地文件和外部 URL 格式；测试本身则用项目既有质量门禁。

这符合 GitHub 分支保护可要求 review/status check/部署成功的能力，也避免 `ship-it` 类流程把“可写 GitHub”扩大成“可直接上线”。[来源](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## 不建议直接复制的模式

1. **严格线性的固定阶段**：真实需求会回到澄清、设计或任务拆分。保留状态机门禁，但允许受控回退和新 change；OpenSpec OPSX 的“工件可随时更新”比强制 PRD→SPEC→code 的单向流更贴近现实。[来源](https://github.com/Fission-AI/OpenSpec/blob/main/docs/migration-guide.md)
2. **把所有上下文放进单个超长 Markdown**：会导致检索困难、并发冲突和上下文窗口浪费。应集中在一个根目录，但按“能力基线 + change 包 + archive”分层。
3. **用聊天记录或框架记忆作为唯一恢复点**：聊天可能不可见、被截断或跨工具不可用；checkpoint 是运行时机制，不是需求审计。
4. **根据自然语言判断任务依赖或完成状态**：依赖、状态、基线、授权、证据都要结构化；文字用于解释，YAML/ID 用于判断。
5. **无条件并行 Agent**：只有 `tasks.md` 已标明不同文件且无依赖时，才能隔离到 worktree 并行；同一 change 的 `state.yaml` 需要 lease 或单写者策略。Git worktree 支持同时检出不同分支，但并不解决业务层冲突。[来源](https://git-scm.com/docs/git-worktree)
6. **用 `git notes` 代替工件目录**：notes 可以不改动 commit 地附加说明，但不适合作为团队主流程的全部资料。目录文件应优先，因为它们可在 PR 中一起 diff/review；notes 只作可选的 commit 级摘要。[来源](https://git-scm.com/docs/git-notes)

## 最小落地路线

### 阶段 0：约定先行

建立 `.ai-workflow/` 目录、上述 schema、模板、状态机、恢复协议与一个 `workflow validate`。先用一个真实需求跑完整手工闭环，不接 Temporal/LangGraph，不允许自动发布。

验收：关闭并归档一个 `CHG-*` 后，换一个全新的 Agent 会话，能仅通过仓库工件说清需求、当前生效规格、改版原因、PR、测试、发布版本和未解决风险。

### 阶段 1：将流程变成 Agent Skill 与 CI

将新需求和改版拆为 `intake`、`clarify`、`plan`、`implement-task`、`verify`、`prepare-release`、`archive` 等原子动作（可实现为一个带子命令的 `workflow` skill/CLI）；另提供唯一的通用 `bug-fix` skill。所有动作先执行恢复协议、后执行一个状态迁移。CI 阻止不完整 traceability 和非法状态迁移；GitHub Issue/PR 模板带入 change ID。

### 阶段 2：可靠自动化

仅为长时间/外部系统步骤引入 LangGraph 或 Temporal：前者处理 Agent 节点的中断续作，后者处理 durable wait/retry/审批/部署。保持“引擎状态可丢失后由 Git 工件重建”的设计，并为 runner 编写 idempotency、replay、取消和回滚测试。

## 建议的下一步

先围绕一个将要改版的真实需求创建试点 `CHG-*`，验证目录、schema、恢复协议和人工门禁是否够用；通过一次“实施中途需求变更”的演练后，再决定是否需要开发 CLI、GitHub 集成或接入 Temporal/LangGraph。这个顺序能先验证最关键的工件模型，而不让工作流引擎成为项目早期的复杂度来源。
