# 三步式 AI 研发工作流方案

## 结论

用户只需要记住一个工作流 Skill 的三个模式：`plan`、`execute`、`review`；Bug 另保留一个通用 `bug-fix` Skill。目录、状态、历史、改版和恢复都由 Skill 自动维护。

用户不需要理解内部编号。推荐对外使用 `REQ-YYYYMMDD-NNN-slug` 表示需求，`BUG-YYYYMMDD-NNN-slug` 表示缺陷；同一项改版使用 `R001`、`R002`。下面的“变更 ID”只是泛称，命令可以接受标题或别名并自动解析。

```text
ai-workflow plan <PRD 或需求>
ai-workflow execute <REQ/BUG ID>
ai-workflow review <REQ/BUG ID>

ai-workflow all <PRD 或需求>       # 三步连续执行，遇到人工门禁暂停
ai-workflow execute <REQ/BUG ID> --task TASK-003
ai-workflow execute <REQ/BUG ID> --resume
ai-workflow status [REQ/BUG ID]
ai-workflow history <关键词>
```

也应支持自然语言触发，例如“根据这个 PRD 做开发计划”“继续执行订单取消改动”“审核这次需求的实现”。显式命令用于精确控制，自然语言用于易用性。

## 三个模式

### 1. `plan`：从 PRD 到可执行计划

输入可以是 PRD 文件、Issue、聊天描述或已有变更 ID。Skill 自动完成：

1. 读取项目规则、架构摘要、当前生效能力和未完成变更。
2. 解析 PRD 的目标、范围、用户故事、验收标准和非目标。
3. 检查现有代码的入口、模块、接口、数据模型、配置、测试和部署方式。
4. 对比“PRD 期望行为”和“当前项目行为”，列出冲突、缺口和风险。
5. 只针对会改变方案的问题提问，并按批次收集回答；回答追加到决策记录，不依赖聊天上下文。
6. 生成任务依赖图、文件范围、验证命令、回滚方案和完成标准。
7. 生成计划摘要，等待用户确认；未确认前不修改业务代码。

输出至少包括：

- `manifest.yaml`：REQ/BUG ID、类型、基线版本、状态和关联历史。
- `revisions/R001/plan.md`：完整开发计划、决策、风险和回滚。
- `tasks.yaml`：带稳定 ID、依赖、文件范围、验收条件和验证命令的任务。
- `context.md`：供下一次 Agent 快速恢复的短摘要。

### 2. `execute`：完整执行开发计划

默认按依赖顺序执行全部未完成任务，也可以只执行一个任务、执行到某个任务，或从中断点恢复。

每个任务执行前后自动记录：

- `pending / in_progress / passed / failed / blocked / skipped`
- 当前分支或 worktree、代码版本、执行者、尝试次数
- 测试/构建/lint 输出摘要和证据链接
- 失败原因、下一步和是否需要重新规划

执行规则：

- 每次只领取一个原子任务，完成后立即写入状态和事件。
- 发现需求变化时暂停并创建新 revision，不静默修改原计划。
- 失败任务保留现场；可重试、跳过或等待人工决策。
- 只有明确授权时才创建 PR、合并、部署或修改外部 Issue。

### 3. `review`：审核结果

默认只读审核，不自动修改代码。审核对象是“计划、代码、测试和证据”的整体一致性：

1. 每项验收标准是否有实际实现和验证证据。
2. 计划外行为、兼容性破坏、边界条件和回归风险。
3. 测试是否真的覆盖用户场景，而不是只通过形式检查。
4. 配置、数据迁移、安全、性能和发布/回滚风险。
5. 代码、PR、CI、部署记录是否能反向追溯到变更和需求。

输出 `review.md`，状态为 `passed`、`passed_with_risks`、`needs_changes` 或 `blocked`。需要修复时，审核结果转成新的执行任务；用户也可以显式要求 `review --fix`，再回到 `execute`。

## 可选执行方式

三个模式既可以单独使用，也可以组合：

| 用法 | 行为 |
| --- | --- |
| 只 `plan` | 只分析和出计划，不写业务代码 |
| `plan → execute` | 计划确认后开发，暂不审核 |
| `execute → review` | 用户已有计划，直接开发并审核 |
| 只 `review` | 审核已有分支、PR 或历史变更 |
| `all` | 三步串联；每个需要人工确认的节点自动暂停 |
| `execute --task` | 只处理指定任务 |
| `execute --resume` | 根据状态和 handoff 从上次中断处继续 |
| `status / history` | 只读查询进度或历史，不增加流程步骤 |

`all` 的内部行为不是盲目一口气执行，而是：

```text
plan → 用户确认计划 → execute → review
                           ↑         │
                           └─ 修复任务┘
                                      ↓
                         询问是否创建 PR / 合并 / 发布
```

只有需求解释、计划批准、高风险方案、外部写操作和生产发布需要用户确认；普通代码分析、任务进度记录、定向测试和只读审核自动完成。

`status`、`resume`、`revise`、`history` 都是 `ai-workflow` 的辅助动作，不再拆成额外 Skill：

- `status`：从结构化文件即时显示阶段、完成比例、阻塞和下一步，不调用大模型。
- `resume`：校验 Git/PR/CI 当前事实后，从最后一个成功事件继续。
- `revise`：等价于对既有 REQ 运行 `plan --revise`，自动对比新旧 PRD。
- `history`：先查索引和短摘要，命中后才读取详细历史。

## 统一目录：少量核心文件 + 按需详情

```text
.ai-workflow/
├── README.md                 # 恢复协议和命令说明
├── project.md                # 项目级规则、架构和质量基线
├── index.yaml                # 活动需求、Bug、能力、路径和外部链接索引
├── capabilities/             # 当前生效行为的短规格
│   └── <capability>.md
├── work-items/
│   └── 2026/REQ-.../
│       ├── manifest.yaml     # 机器状态、基线、父变更、关联对象
│       ├── context.md        # 始终优先读取的短上下文
│       ├── summary.md        # 历史检索优先读取的最终摘要
│       ├── revisions/
│       │   └── R001/
│       │       ├── input.md  # 原始 PRD 或需求来源
│       │       ├── questions.md
│       │       ├── plan.md   # 当前 revision 的完整计划
│       │       └── delta.md  # 相对上一 revision 的变化
│       ├── tasks.yaml        # 任务和进度的唯一机器来源
│       ├── decisions.md      # 重要决策和需求回答，追加式
│       ├── execution/
│       │   ├── state.yaml    # 当前阶段、任务、阻塞和下一步
│       │   ├── events.ndjson # 追加式事件日志
│       │   └── handoff.md    # 给下一次 Agent 的接力摘要
│       ├── review.md         # 审核结果
│       └── evidence/         # 脱敏证据或外部证据引用
└── archive-index.yaml        # 历史索引；工作目录本身不移动，避免链接失效
```

用户不需要手动填写这些文件。Skill 负责创建、更新和生成索引；人只确认关键内容。

`manifest.yaml` 将三个容易混淆的状态分开记录：

- `phase`：`plan / execute / review / done`
- `state`：`active / waiting_input / blocked / paused / completed / cancelled`
- `delivery`：`not_started / implemented / merged / deployed / verified`

这样“代码开发完成”“已经合并”和“已经上线验证”不会被错误地当成同一个状态。

### 历史检索协议

每次新会话默认只读取：

1. `project.md`
2. `index.yaml`
3. 目标变更的 `manifest.yaml`、`context.md`、`tasks.yaml`、`state.yaml` 和 `handoff.md`
4. 当前能力规格中被该需求/缺陷引用的部分

只有在需要解释“为什么这样改”或分析回归时，才按 `REQ-*`、`BUG-*`、能力 ID、受影响路径、发布版本或日期检索 `decisions.md`、`events.ndjson` 和历史工作项。禁止默认把全部历史读入上下文。

每次任务完成都重新生成 `context.md`，只保留：当前目标、已确认决策、已完成任务、阻塞、下一步和证据链接。详细过程进入事件日志，摘要进入索引。

## 需求改版

- 计划尚未确认：可以在同一个变更中产生新 revision，Git 保留 diff。
- 计划已确认或已经执行：同一需求下新建 revision；已发布后的新产品迭代则新建 REQ，并填写 `parent`/`supersedes`，重新计算影响范围。
- 已发布能力：只通过新变更的 delta 更新 `capabilities/`，不直接覆盖历史规格。
- 新需求与旧需求冲突：暂停执行，列出冲突和受影响任务，等待用户确认。

这样用户只需说“在上次订单取消需求上增加退款限制”，Skill 就能定位旧 REQ、读取当前版本并提出差异问题，不要求重新粘贴历史。

## 一个通用 `bug-fix` Skill

Bug 不再拆成多个技术型 Skill。`bug-fix` 将问题作为 `kind: bugfix` 的变更处理，复用同一目录和进度模型，内部固定执行：

```text
完整读取 → 环境确认 → 修复前基线 → 根因分析
→ 处理决策 → 最小修复 → 原场景/回归验证 → 发布观察
```

首次未复现不能直接结案；若发现是需求或规则变化，则生成普通变更并退出 Bug 修复路径。UI、API、异步、性能等只改变验证适配器，不增加新的 Skill。

## 性能与易用性设计

- `status`、恢复和进度展示只读 YAML/摘要，不调用大模型。
- 规划阶段按需扫描代码，后续执行任务复用扫描结果和文件哈希。
- 只有互不依赖且文件范围不重叠的任务才并行。
- 低风险改动使用轻量模板；高风险改动才展开完整设计、回滚和人工门禁。
- 事件日志追加写入，状态文件使用单写者/租约，避免两个 Agent 同时覆盖进度。
- 原始日志、Token、个人信息和业务数据不直接进入 Git；只存脱敏摘要和可控证据引用。

## Skill 包结构

`ai-workflow` 对用户是一个 Skill，但内部按需加载，避免每次执行都把完整流程塞入上下文：

```text
skills/ai-workflow/
├── SKILL.md                   # 动作路由、公共协议、权限边界
├── references/
│   ├── plan.md                # 仅 plan/all 时读取
│   ├── execute.md             # 仅 execute/all 时读取
│   ├── review.md              # 仅 review/all 时读取
│   ├── storage-protocol.md    # 目录、状态、恢复和检索协议
│   └── schemas.md             # manifest/tasks/events 字段约束
├── templates/                 # 过程文件模板
└── scripts/                   # init、validate、status、index 等确定性操作

skills/bug-fix/
├── SKILL.md                   # 通用证据驱动缺陷闭环
└── references/               # 按问题类型选择验证方法
```

路由、状态更新、索引和 schema 校验尽量使用确定性脚本；项目理解、问题澄清、计划生成、代码实现和审核交给 Agent。两个 Skill 通过项目内版本化的数据协议协作，不依赖聊天上下文。

## MVP 实施顺序

1. 先实现一个 `ai-workflow` Skill，支持 `plan/execute/review/all/status/resume/revise/history`；另实现一个 `bug-fix` Skill。
2. 只使用 Markdown/YAML/Git，不引入 Temporal 或 LangGraph。
3. 为三个真实场景写验收：新需求、执行中改版、执行中断恢复；再增加一个 Bug 场景。
4. 当目录模型稳定后，再开发 `workflow validate` 和 GitHub/CI 集成。
5. 只有出现跨天审批、异步部署和大量重试时，才引入专用工作流引擎。
