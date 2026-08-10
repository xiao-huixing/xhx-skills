# 通用 Bug 协议

## 1. 建立工作项

为每个缺陷建立稳定目录：

```text
.ai-workflow/work-items/YYYY/BUG-YYYYMMDD-NNN-slug/
├── manifest.yaml
├── summary.md
├── context.md
├── intake.md
├── baseline.md
├── root-cause.md
├── fix-plan.md
├── verification.md
├── evidence/
├── revisions/R001/
├── tasks.yaml
└── execution/
    ├── state.yaml
    ├── events.ndjson
    └── handoff.md
```

目录、ID、revision、任务和事件格式遵循
`skills/ai-workflow/references/storage-protocol.md`。`manifest.yaml` 的
`kind` 为 `bug`，用户可见 ID 以 `BUG-` 开头。

## 2. 状态门禁

推荐状态顺序如下：

```text
reported
  -> evidence_complete
  -> environment_ready
  -> baseline_reproduced
  -> root_caused
  -> decision_made
  -> fix_planned
  -> implemented
  -> verified
  -> release_candidate
  -> deployed
  -> observed
  -> closed
```

允许的分支状态：

- `not_reproduced`：记录已尝试的条件、日志和差异，不能直接关闭；补充
  信息后回到 `environment_ready`。
- `blocked`：缺少权限、环境、数据或用户决策；记录阻塞者和恢复条件。
- `no_code_change`：确认是配置、数据、依赖或操作问题，记录处置证据。
- `needs_requirement_change`：确认是预期行为或需求变化，链接对应的
  `REQ-*`，Bug 保留为可追溯记录。

只有 `verified` 之后才能进入发布候选；只有有部署和观察证据时才能进入
`deployed`、`observed` 和 `closed`。发布不是此 skill 的默认副作用。

## 3. 证据驱动步骤

### Intake

整理原始报告、影响范围、严重度、首次出现时间、版本/环境、用户角色、
输入数据、期望与实际结果、附件和关联链接。缺失信息列为问题，不用猜测
填充。

### Baseline

写明复现入口和精确步骤，并保存：

- 当前提交、构建产物、配置和依赖版本；
- 脱敏后的输入、请求、日志、截图或录屏引用；
- 复现次数、成功率、时间窗口和已尝试的变体；
- 预期结果、实际结果以及判定标准。

按缺陷类型选择验证入口：UI、API、CLI、数据、异步任务、性能、配置或
集成。入口可由项目适配层替换，但状态门禁不能省略。

### Root cause and decision

从可复现事实开始追踪调用链、数据流、边界条件和最近变更，记录根因证据
与影响边界。明确决策属于：代码缺陷、配置/数据/依赖处置、预期行为，或
需要新的需求。若需要需求变化，不在此处扩大补丁范围。

### Fix and verification

把修复拆为可恢复任务：最小代码或配置改动、回归测试、迁移/回滚说明和
端到端验证。每个任务开始和结束各写一条事件；失败时保留失败输出和下一
步，不覆盖原证据。

验证报告至少包含：

```text
baseline: <before result>
fix: <commit or files>
targeted_test: <command and result>
regression: <command and result>
e2e_or_boundary_check: <command and result, or why not applicable>
remaining_risk: <risk or none>
```

## 4. 恢复与改版

`resume` 从 `execution/state.yaml`、最后一条合法事件和 `handoff.md` 恢复，
不依赖聊天记录。若代码、环境或需求事实发生漂移，暂停执行并创建新的
revision 或 `REQ-*` 关联项。

后续评论、复现条件和修复结果追加到当前 revision；不要覆盖历史文件。任何
导致范围、预期行为或验收变化的内容都转为新的需求 revision。

## 5. 交付边界

默认只完成本地诊断、代码修改和验证。提交、创建 PR、合并、部署、生产
观察和关闭外部工单必须由用户明确授权，并在事件中记录外部链接和时间。
