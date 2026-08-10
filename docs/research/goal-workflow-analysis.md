# goal-workflow 一手资料研究

> 研究日期：2026-08-07。本文以仓库 `master` 在 `6807e6dfcc0a` 的源码和官方 README/使用指南为准；未安装或执行该工作流。

## 结论

`goal-workflow` 是一套把 AI 编程工作拆成“需求 → 技术契约（可选）→ 可实施 Issue → 实现/审查/留痕/交付”的 Markdown Skill 工作流，而不是一个独立的工作流执行引擎。它用各 Agent 已有的读写代码、运行测试、Git 与 GitHub CLI 能力完成动作；Skill 本身主要定义输入、产物、门禁和恢复规则。[仓库 README][readme] [工作流主文档][guide] [技能目录][tree]

最有价值的部分是把 Issue 的可验收性、交付前 self-review、实现决策记录和 GitHub 交付闭环显式化。最需要谨慎采用的部分是 `/loop-it` 与 `/ship-it`：前者会自动按 Issue 批量推进，后者可推送、创建并合入 PR、关闭 Issue，必须与团队的审批、分支保护和权限模型配套。[`loop-it`][loop] [`ship-it`][ship]

## 目标与边界

- 官方定位是从 PRD 到已交付代码的 AI 驱动研发流程，安装入口为 `npx skills add smallnest/goal-workflow`。[README][readme]
- 主链路为 `/prd → /prd-to-spec（可选）→ /to-issues → /loop-it`，每个 Issue 在实现、审查、笔记、交付后再继续下一个；也可以只单独使用任一 Skill。[README][readme] [使用指南 FAQ][guide]
- `/prd-to-spec` 明确区分“做什么”的 PRD 和“怎么做”的 SPEC；官方建议中小功能可跳过它，而多人/多 Agent、跨模块、合规评审或 PRD 模糊时应保留它。[`prd-to-spec`][prd-spec] [使用指南][guide]

## 目录与核心 artefact

当前 `skills/` 下有 17 个 Skill 目录；README 的技能表只列出其中工作流主链路及部分附属项，并将不在仓库目录中的 Claude Code 内置 `/goal` 也计入表中。因此，评估安装内容应以实际 [`skills/` 目录][tree] 为准，而不能只依据 README 表格。[技能目录][tree] [README][readme] [使用指南 FAQ][guide]

| 阶段 / Skill | 主要输入 | 产物或持久状态 | 作用 |
| --- | --- | --- | --- |
| `/prd` | 功能描述与澄清答复 | `tasks/prd-[feature-name].md` | 生成含 User Story、可验证验收标准、FR、非目标等的 PRD；确认前不实施代码。[`prd`][prd] |
| `/prd-to-spec` | PRD，及可选的现有代码上下文 | 通常为 `tasks/spec-[feature-name].md` | 产出架构、数据模型、API、错误处理、安全、性能、测试和实施映射的技术契约。[`prd-to-spec`][prd-spec] |
| `/to-issues` | PRD 和/或 SPEC | GitHub Issue、`.autoresearch/issues/issue-NNN-*.md`，或 Baidu iCafe 卡片 | 将故事按依赖、优先级、类型与验收标准拆成单 Agent 会话可完成的单位；创建前要求用户确认。[`to-issues`][issues] |
| `/loop-it` | GitHub Open Issues、干净 Git 工作树 | `.loop-state.json`、功能分支、代码改动 | 建依赖图、拓扑排序、逐个处理；每个状态转换写检查点，供中断后恢复。[`loop-it`][loop] |
| `/review-it` | 未提交改动或相对基线的 diff | 审查结论；分支模式可生成 `/tmp/review-it.diff` | 对不同 Agent 选择审查命令，并要求验证可采纳发现、修复后重跑测试与审查。[`review-it`][review] |
| `/note-it` | 当前 Issue、实现与 PRD/SPEC | `docs/issue#XXXX.html` | 记录设计决策、偏离、取舍、开放问题；在交付前运行，但在 loop 中是 best-effort。[`note-it`][note] [`loop-it`][loop] |
| `/ship-it` | 已完成且经审查的 Issue 改动 | commit、远端分支、PR、Issue 总结评论与关闭状态 | 经 `gh` 提交、推送、建 PR、检查、合入并关闭 Issue。[`ship-it`][ship] |

其余目录属于扩展工具箱：`code-to-spec` 做既有代码的逆向规格，`to-design` 写设计提案，`graph` 以 DAG/独立 worktree 并行推进，`refactor`、`modern-go`、`smell` 面向质量演进，另有图表、文档图标、文档去 AI 痕迹和 TTS 等辅助 Skill。[技能目录][tree] [使用指南的并行图说明][guide]

## 实际流程与控制点

1. `/prd` 对歧义提出按复杂度伸缩的问题，生成 PRD 后先让用户确认；其验收标准要求可观察、可测试或可由工具验证。[`prd`][prd]
2. 需要提前锁定技术方案时运行 `/prd-to-spec`；它要求将 PRD 的故事、FR 和验收标准映射到业务逻辑、API 和测试策略。[`prd-to-spec`][prd-spec]
3. `/to-issues` 把输入拆为带依赖、类型和优先级的 Issue；大故事会拆分，小故事可合并，且用户确认后才写入 GitHub、本地或 iCafe。[`to-issues`][issues]
4. `/loop-it` 先验证 `gh` 登录、Git 仓库、工作树、分支、远端和已有状态；随后读取最多 100 个 Open Issue、解析正文依赖、做拓扑排序并严格串行执行。未完成依赖会标为 `blocked`，失败会分类、限次重试并保留失败分支。[`loop-it`][loop]
5. 单 Issue 的当前实现定义是“agent 读 Issue/相关 PRD/SPEC、改代码、跑构建/测试/lint”的内联行为，随后 `/review-it` 最多两轮、`/note-it` 留痕、`/ship-it` 交付；成功或失败都会写 checkpoint。[`loop-it`][loop]

## 与一般 Skill / Agent 的关系

```text
Skill Markdown（约束、步骤、产物）
             ↓ 由宿主 Agent 解释并执行
Agent 的代码分析、编辑、测试、Git/gh 能力
             ↓
PRD / SPEC / Issue / 代码 / 审查结果 / PR 等项目 artefact
```

- 该仓库的 Skill 是可组合的行为说明，不是替代 Agent 的程序。官方文档列出 Claude Code、Codex、OpenCode 与 DeepSeek TUI 的兼容性；`review-it` 则明确为多 Agent 审查收尾适配层。[平台矩阵][guide] [`review-it`][review]
- `/goal` 是 Claude Code 内置能力，仓库没有 `skills/goal/`；文档建议 Codex 用 `codex --goal` 替代。因而它不是可随包移植的普通 Skill。[使用指南 FAQ][guide]
- 最新的 `loop-it/SKILL.md` 已不再要求调用外部 `/goal`，而是要求 Agent 内联实现，理由是本环境不能把 `goal` 当作 Skill 调用。README 和网页流程图仍写作 `/goal`，这是文档与当前执行定义的漂移。[README][readme] [`loop-it`][loop] [相关提交][commit-goal]
- `review-it` 把审查结果定位为 advisory，并要求审查真实代码路径；官方 FAQ 也说明它是提交前 self-review，不替代团队 code review。[`review-it`][review] [使用指南 FAQ][guide]

## 适用场景、优势与限制

**适用。** 有明确产品需求、可拆成小 Issue、使用 Git，并愿意让 Agent 在单次会话完成一个任务的项目。GitHub 项目最能使用全链路；非 GitHub 时 PRD、技术 SPEC、Local Issue 与本地审查仍可用，但 `ship-it` 依赖 GitHub `gh` CLI。[`to-issues`][issues] [使用指南 FAQ][guide]

**优势。**

- 将模糊需求变为可验证验收条件，再变为有依赖信息的可实施单位，降低 Agent 自行扩大范围的概率。[`prd`][prd] [`to-issues`][issues]
- `loop-it` 的状态机、失败分类、限次重试和分支清理为长任务提供断点恢复和可观察性。[`loop-it`][loop]
- 审查、测试、实现笔记与 PR/Issue 回链均被放进交付闭环，减少“代码完成但决策与验证缺失”的情况。[`review-it`][review] [`note-it`][note] [`ship-it`][ship]
- 支持把需求、设计与任务的产物保存在仓库，便于人与不同 Agent 接力；复杂改动可用 SPEC 显式共享技术约定。[`prd-to-spec`][prd-spec] [使用指南][guide]

**限制与风险。**

- 这是一组 prompt/流程契约，执行正确性仍取决于宿主 Agent 是否遵守指令、是否理解项目和是否实际运行适当质量门禁；它不提供独立的强制调度器或测试框架。这是由 Skill 都以 `SKILL.md` 形式承载、具体实现由 Agent 内联完成所作的判断。[技能目录][tree] [`loop-it`][loop]
- 自动化批处理只能读取 GitHub Open Issue，且依赖 `gh` 认证、可访问远端、干净工作树与默认分支；Local/iCafe Issue 创建模式不能直接作为 `/loop-it` 输入。[`loop-it`][loop] [`to-issues`][issues]
- `/ship-it` 具有推送、合入和关闭 Issue 的外部副作用。即使 `loop-it` 禁止强推主分支、要求审查与保留失败分支，仍应由团队在执行前控制 token/权限、分支保护、required review 以及是否允许自动 merge。[`loop-it`][loop] [`ship-it`][ship]
- 源码中的 `/loop-it` 已改为内联实现，但 README/网页的主链路还保留 `/goal` 表述；采用时应以 `SKILL.md` 为执行规范，并在本地二次封装前先消除该歧义。[`loop-it`][loop] [README][readme] [相关提交][commit-goal]
- 严格串行的 `/loop-it` 优先工作树安全而非吞吐；独立子系统才适合另用 `graph` 的 DAG/worktree 并行模式，二者不应混用为同一执行假设。[`loop-it`][loop] [使用指南的并行图说明][guide]

## 采用建议

建议把它视为可挑选的“研发治理模板”，而非一键无人值守交付器：先采纳 `/prd`、`/prd-to-spec`（按复杂度）、`/to-issues`、`/review-it` 和 `/note-it` 的 artefact 结构；再将项目已有的测试命令、CI、ADR/设计文档位置和安全审查要求写入本地约定。只有在 Issue 粒度稳定、`gh` 权限最小化、分支保护和人工合入策略明确后，才启用 `/loop-it`/`ship-it` 的自动推进能力。

## 演进信号

- 2026-05-22，仓库将 `/to-issues` 从 `/prd` 中拆出，表明 Issue 创建被设计为可独立复用的桥接环节。[对应提交][commit-issues]
- 2026-06-12 至 06-13，`loop-it` 连续修正 `/goal` 的调用假设并改为另一种内联实现模式，是上文文档漂移的直接来源。[提交 1][commit-goal-clarify] [提交 2][commit-goal]
- 2026-07-21 新增 `graph` 和状态恢复文件，显示该项目正从串行 Issue 循环扩展到有依赖图的并行编排；这属于独立扩展，而非 `loop-it` 默认行为。[对应提交][commit-graph]

[readme]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/README_CN.md
[tree]: https://github.com/smallnest/goal-workflow/tree/6807e6dfcc0a1b42190a342ff931c1e8838afc72/skills
[guide]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/docs/index_cn.html
[prd]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/skills/prd/SKILL.md
[prd-spec]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/skills/prd-to-spec/SKILL.md
[issues]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/skills/to-issues/SKILL.md
[loop]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/skills/loop-it/SKILL.md
[review]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/skills/review-it/SKILL.md
[note]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/skills/note-it/SKILL.md
[ship]: https://github.com/smallnest/goal-workflow/blob/6807e6dfcc0a1b42190a342ff931c1e8838afc72/skills/ship-it/SKILL.md
[commit-issues]: https://github.com/smallnest/goal-workflow/commit/c5eabb097362eba8c5d974b67ffd535858543adb
[commit-goal-clarify]: https://github.com/smallnest/goal-workflow/commit/38b088b2f06e0e8d0fb097fc01651f6241e733b3
[commit-goal]: https://github.com/smallnest/goal-workflow/commit/a5a1abd4e66f705c6abba618a3464b7f86376268
[commit-graph]: https://github.com/smallnest/goal-workflow/commit/6807e6dfcc0a1b42190a342ff931c1e8838afc72
