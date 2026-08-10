# ai-workflow 性能与可靠性审计

审计时间：2026-08-10（CST）

## 结论

`ai-workflow` 慢的主因不是 `SKILL.md` 单文件过长，而是**把确定性状态机、索引、初始化、状态查询和事件写入都交给 Agent 临场完成**，并且所有模式共用重型启动流程。效果不稳定的主因是**协议只有自然语言，没有可执行 schema、合法状态迁移、原子写入和可运行 eval 闭环**。

当前实现适合作为流程草案，不适合作为可靠执行器。应先完成 P0：确定性 CLI、严格 schema/状态机、模式快速路径、可运行 eval；再压缩提示词和增加缓存。否则只改文案，速度和质量不会稳定改善。

本次未拿到真实运行 trace、token 和延迟记录，因此“慢”的判断是结构性审计结论；优化前必须先建立实测基线。

## 本地证据

### 1. 慢的结构性来源

| 发现 | 本地证据 | 影响 |
| --- | --- | --- |
| 所有模式先执行同一套启动流程 | `skills/ai-workflow/SKILL.md:45-61` 要求任何模式读取仓库规则、README、构建/测试/安全说明及 4 个项目索引；`status/history` 也没有快速路径 | 简单查询也产生多轮文件发现、读取和判断；仓库越大越慢 |
| 只读 helper 会触发初始化 | `SKILL.md:47-52` 对“任何模式”要求缺目录时初始化；但 `SKILL.md:16,104-114` 和原方案 `three-step-workflow-proposal.md:85-106` 把 `status/history` 定义为只读 | 查询可能变成写操作，增加延迟且违反权限边界 |
| 确定性工作仍靠 Agent 手工完成 | 原方案要求 `init/status/index/validate` 脚本（`three-step-workflow-proposal.md:191-212`）；实际 `scripts/` 只有 `validate_workflow.py` | 每次都重新推理目录、ID、索引、状态和摘要，增加 token、工具调用及格式漂移 |
| 未实现扫描复用 | 原方案 `three-step-workflow-proposal.md:182-188` 要求复用规划扫描结果和文件哈希；现有 manifest/context/task schema 无扫描快照或 hash 字段 | `execute/review/resume` 会重复查项目事实，无法判断缓存是否仍有效 |
| 没有风险分层 | 原方案要求低风险轻量模板、高风险才展开完整回滚和门禁（`three-step-workflow-proposal.md:182-188`）；当前 `plan.md:33-66` 对所有需求要求同一组完整工件 | 小改动承担与高风险改动相同的分析和写文件成本 |
| instruction 基线仍偏重 | 单模式触发后，`SKILL.md + storage + mode` 为 11.4–12.7 KB；`all` 的五个 instruction 文件约 17.1 KB，尚未计入项目文件和会话历史 | 不是唯一瓶颈，但会放大长会话、重复读取和指令冲突 |

### 2. 效果差或不可靠的根因

| 严重性 | 发现 | 本地证据与后果 |
| --- | --- | --- |
| P0 | “schema”不可执行，validator 几乎只验文件存在 | `references/schemas.md` 只是示例；`validate_workflow.py:13-86` 不解析 YAML，不检查字段、枚举、引用、依赖、门禁或迁移。测试甚至把 manifest/tasks/state 写成 `{}` 并判定合法（`tests/test_validate_workflow.py:14-48`） |
| P0 | schema 和初始化资源未形成闭环 | `SKILL.md:32-43` 没有任何分支要求读取 `schemas.md`；storage tree 需要项目索引、revision、events、handoff、review 等文件，但 `templates/` 只有 5 个模板，且没有 init 脚本。Agent 只能临场补全格式 |
| P0 | 状态定义自相矛盾 | `storage-protocol.md:64-66` 的示例值是 `waiting_plan_approval`，同一行允许值却不包含它；`SKILL.md:73-75` 和 `plan.md:57-66` 又强制使用该值。不同 Agent 会产生不同状态表示 |
| P0 | 状态更新不是事务 | `execute.md:22-31` 要依次写 event、task、traceability、context、handoff，但没有原子写入、提交顺序、恢复点或幂等键；中断后多个事实源可能互相冲突 |
| P0 | lease 只有名词，没有协议 | `execute.md:5-14` 要求取得 single-writer lease，`templates/state.yaml` 仅有 `lease: null`；没有 owner、过期、续租、抢占、释放和冲突处理规则 |
| P0 | eval 文件不可运行 | `evals/evals.json` 只有 4 个 prompt 和自然语言 expectation，没有 runner、fixture、grader、trial、基线或结果文件；execute/resume 用例的 `files` 还是空数组，无法构造所声称的前置状态 |
| P1 | helper/revise 契约不足 | `SKILL.md:104-114` 每个 helper 只有一句描述；没有输入错误、唯一匹配、输出 schema、无结果语义、索引损坏或 Git drift 的确定性处理 |
| P1 | 声明的 task 契约与 schema 不一致 | `plan.md:46-51` 要求 expected behavior、rollback、done condition；`schemas.md:30-45` 和模板均缺这些字段，也缺 attempt、failure、owner 和时间信息 |
| P1 | review 结论无结构化落点 | `review.md:19-30` 定义 4 种结果，但 manifest schema 没有 `review.result`；“整改任务”也没有来源 finding、严重度或验证回链字段 |
| P1 | ID alias 无数据模型 | `SKILL.md:56-57` 要按 ID/title/alias 解析，manifest schema 没有 alias，catalog 也没有 schema 或生成器 |
| P1 | 触发范围过宽 | frontmatter `description`（`SKILL.md:3-10`）覆盖“分析项目、计划、执行、review、进度”等常见研发请求，容易与普通 review、implement、planning 类 Skill 竞争，造成误触发和额外流程 |

现有两项 validator unit test 均通过，但只能证明“缺文件/坏 JSON 行可被发现”，不能证明工作流状态有效、可恢复或验收链完整。

## 与原设计的实现缺口

| 原设计 | 当前实现 | 缺口 |
| --- | --- | --- |
| `status`、恢复和进度读取结构化摘要，不调用模型 | 只有自然语言 helper；无 status/resume CLI | 核心性能承诺未落地 |
| `init/validate/status/index` 等确定性脚本 | 只有弱 `validate_workflow.py` | 初始化、索引、查询、迁移、上下文再生成仍由 Agent 手工完成 |
| 复用代码扫描和文件 hash | schema 无 snapshot/hash | 无缓存命中、失效和 drift 判定 |
| 低风险轻量模板、高风险完整流程 | 单一 plan 契约 | 小任务过度编排 |
| 单写者/租约 | 仅 `lease: null` | 并发安全不可执行 |
| 三个真实场景验收：新需求、执行中改版、中断恢复 | 4 个静态 prompt，无 fixtures/runner/grader | 无回归能力，无法证明效果 |
| 路由、状态更新、索引、schema 校验确定化 | 大部分仍是提示词 | 结果依赖模型理解与当次上下文 |
| 原目录为 `project.md/index.yaml/archive-index.yaml` | 实现改为 `project/overview.md`、`indexes/*` | 设计发生漂移但没有 migration/version；旧项目与新实现兼容性不明 |

另有一处实现顺序倒置：原设计把强 `workflow validate` 放在目录模型稳定后开发（`three-step-workflow-proposal.md:214-220`），当前却先加入了只检查外形的 validator，容易制造“已验证”的错误信心。

## 外部一手资料核验

- OpenAI 要求 Skill 聚焦可识别的单一用户目标，明确输入、步骤、输出、禁止推断、提问/停止条件；不同 trigger、输入或成功标准应拆分。当前一个 description 承担 8 个模式，边界过宽。[OpenAI Build skills](https://developers.openai.com/plugins/build/skills)
- OpenAI 建议 `SKILL.md` 保持精简，确定性计算或文件处理放进脚本，并用直接、间接、不完整、负例和越权边界请求同时测试激活与输出。当前 helper/状态处理缺脚本，eval 也没有负例与可执行 grading。[OpenAI Build skills](https://developers.openai.com/plugins/build/skills)
- OpenAI 的现行模型指南建议每条指令只写一次、只暴露相关工具，并在代表性任务上同时比较成功率、token、延迟、成本、调用、轮次和重试；其内部 coding-agent 样本中，更精简的 system prompt 同时提高了分数并显著减少 token，但官方明确要求按自身 workload 验证。[OpenAI Model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- OpenAI eval 指南要求 eval-driven development、任务特定且接近真实分布、尽量自动评分、持续加入日志中的失败案例，并用人工反馈校准自动 grader；“感觉变好”属于反模式。该页面也注明托管 Evals 平台将在 2026-11-30 下线，因此本项目应建设本地、供应商无关的 harness，而不是绑定将退役的平台。[OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- OpenAI 把 trace grading 定义为对端到端决策、tool calls 和 reasoning trace 结构化打分，用于定位为什么成功或失败。当前 eval 只写最终期望，没有 trace、tool-call 或状态变更记录。[OpenAI Trace grading](https://developers.openai.com/api/docs/guides/trace-grading)
- Anthropic 强调 Skill 要简洁，并按任务脆弱性设置自由度：开放式 code review 应给高自由度，迁移/状态更新等脆弱操作应交给低自由度的精确脚本。当前实现正好把状态机放在高自由度自然语言中。[Anthropic Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- Anthropic 建议 references 从 `SKILL.md` 直接一层可达、复杂流程加入 validator feedback loop；预制脚本通常比临时生成更可靠，并节省 token 和时间。当前 references 分层基本合理，但缺少真正执行 init/status/index/transition 的脚本和验证闭环。[Anthropic Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- Anthropic 推荐先用代表性任务建立无 Skill baseline，再写最少指令，并反复对比；至少要覆盖真实使用场景。当前 `evals.json` 没有 baseline 和可重复执行方式。[Anthropic Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

## 优化方案

### P0：先解决“慢且不可信”

1. **实现确定性 `workflow` CLI**
   - 子命令：`init`、`resolve`、`status`、`history`、`validate`、`transition`、`append-event`、`refresh-context`、`refresh-index`。
   - `status/history` 禁止初始化、禁止读取项目代码和仓库说明；不存在时返回结构化 `not_initialized`。
   - 写入采用临时文件 + atomic rename；event 使用稳定幂等键；lease 明确 owner、acquired_at、expires_at、renew/release。

2. **把协议变成机器可验证状态机**
   - 选定一个 canonical state 模型；建议保留原设计枚举，用 `phase: plan + state: waiting_input + next_action: approve_plan` 取代未入枚举的 `waiting_plan_approval`。
   - 为 manifest/task/state/event/index 定义 versioned schema；校验枚举、必填字段、引用存在性、DAG、合法迁移、event 顺序、gate、REQ→AC→TASK→validation/evidence 覆盖。
   - 补齐 task 的 expected behavior、rollback、done condition、attempt/failure；补 `review.result` 和 finding→remediation 关系。

3. **路由后再启动，按模式读取**
   - `status/history`：只运行 CLI。
   - `resume`：只读 manifest/tasks/state/latest-event/handoff，再做 Git drift 检查。
   - `execute`：只加载当前 task、其依赖、相关文件和验证命令。
   - `review`：只加载当前 revision、diff、验收映射和证据。
   - 仅 `plan` 在项目快照失效时扫描代码；只读模式绝不创建 `.ai-workflow/`。

4. **把 evals 变成可运行的回归门禁**
   - 每个 case 提供隔离 fixture repo、初始 `.ai-workflow/`、允许/禁止修改路径、预期最终机器状态和 deterministic grader。
   - 至少覆盖：plan、批准门禁、execute `--until`、review 只读、status/history 未初始化、中断点恢复、Git drift、改版、重复事件、lease 冲突、误触发负例、越权副作用。
   - 每个非确定性场景至少多次 trial，保存 trace、最终文件树、token、tool calls、wall time 和 grader 结果；先记录当前版本 baseline。

P0 验收指标：

- `status/history` 直接 CLI 在 100 个 work item 下 p95 ≤ 1 秒；经 Agent 使用时只允许 1 次 CLI 调用、0 次项目扫描、0 次写入。
- schema mutation suite 对所有非法 fixture 拒绝率 100%，合法 fixture 通过率 100%。
- 在 event 写入、task 更新、context 更新等强制中断点恢复 10 次，最终状态一致率 100%，不产生重复 event。
- 所有只读/未授权 eval 的产品代码和外部副作用变更数为 0。
- REQ→AC→TASK→validation/evidence 的机器可验证覆盖率为 100%。

### P1：减少上下文和模式干扰

1. 将 `SKILL.md` 压成路由器，只保留模式选择、权限边界、fast path 和每个 reference 的加载条件；同一规则只出现一次。
2. 缩窄 description；若主要靠显式 `$ai-workflow` 使用，在 `agents/openai.yaml` 设置 `allow_implicit_invocation: false`。若保留隐式触发，至少移除泛化的“分析项目/review implementation”表述。
3. 为 plan 建立 `project-snapshot.json`：记录模块、入口、质量门禁、相关路径 hash 和生成版本；只在相关 hash 或 Git base 变化时增量刷新。
4. 增加 `light/standard/high-risk` 三档：轻量任务只生成 manifest、短 plan、tasks、state；数据库迁移、安全、发布等才启用完整风险/回滚/人工门禁。
5. 为 `resume/revise/history/review` 增加明确输入、输出 schema、错误码和停止条件，不让 Agent 自行发明语义。

P1 验收指标：

- 在同一 eval suite 上，成功率不得低于 P0 baseline；plan/execute/review 的 p50 loaded bytes、tool calls 和 input tokens 至少下降 50%。
- plan p50 wall time 至少下降 30%；缓存命中时重复项目扫描次数为 0。
- 平衡的正/负触发集上 precision、recall 均 ≥ 95%，普通“review 这段代码”不误触发完整工作流。
- 轻量任务生成文件数和状态写入次数较当前完整流程至少下降 50%。

### P2：在可靠基线上扩展

1. 只有 CLI 能证明依赖已满足、scope 不重叠且 lease 独立时才并行执行；否则串行。
2. 从真实失败 trace 持续扩充 eval，加入不同模型/推理档位对比；质量不提升时不使用更高推理成本。
3. 再接 GitHub/CI、PR 和部署证据；外部写操作继续保持显式授权和幂等键。
4. 若 eval 仍显示模式相互干扰，再把 plan/execute/review 拆成三个内部 Skill，保留 `ai-workflow` 作为兼容入口；不应在没有数据前先增加编排层。

P2 验收指标：并行场景 wall time 比串行下降 ≥ 30%，冲突/重复写入为 0；新增真实失败必须转成回归 case，发布前全套 eval 通过。

## 建议实施顺序

第一轮只做 P0，并冻结目录协议版本；第二轮用同一批 eval 比较精简 router、缓存和风险分层；第三轮才考虑并行及外部集成。最关键的决策是：**让 Agent 负责语义判断，让脚本负责身份、状态、索引、迁移、幂等和校验。**
