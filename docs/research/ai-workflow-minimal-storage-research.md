# AI Workflow 最小运行时存储调研

> 调研时间：2026-08-11（CST）
>
> 来源范围：仅采用 OpenAI、Agent Skills、SQLite、Git、JSON Lines、YAML 与 POSIX 规范所有者的一手资料。

标注约定：官方资料并未规定 AI workflow 必须使用以下任一文件数量或组合。下文引用链接所支撑的是格式、transaction、并发和 Git 行为事实；所有具体目录、字段、推荐与迁移触发条件均明确视为**工程推论**。

## 结论

**工程推论（推荐）：**目标项目的 Git canonical storage 收敛为“每工作项两个文本文件”：

```text
.ai-workflow/
└── work-items/
    └── <WORK-ITEM-ID>/
        ├── work-item.yaml  # 当前快照，唯一 current-state source of truth
        └── events.jsonl    # 追加式审计日志，只记录已提交的状态转换
```

- `work-item.yaml` 合并身份、当前 revision、计划、任务、生命周期、审批、审核结论和 evidence refs；读取状态不需要 replay 全部历史。
- `events.jsonl` 保留恢复、幂等、审计所需的转换历史；不再用它反向推导所有当前字段，快照通过 `last_event_id` 与日志对齐。
- 不持久化 `active`、`catalog`、`context`、`state`、`handoff` 等派生副本；CLI 按需扫描 `work-item.yaml`，性能缓存应可删除、可重建并默认不纳入 Git。
- 不推荐把一个项目级 `events.jsonl` 或一个纳入 Git 的 SQLite DB 作为 MVP 权威存储。前者让所有分支写同一路径，后者失去普通文本 diff/merge；这两点是由 Git 的文本与二进制合并机制推导出的工程结论。[Git `gitattributes`](https://git-scm.com/docs/gitattributes)
- SQLite 适合作为后续的非 Git canonical store，或作为可重建的本地查询缓存：其持久化内容通常收敛在一个 main database file 中，并提供 SQL 查询和 ACID transaction；但运行时可能同时出现 rollback journal、`-wal`、`-shm` 等 sidecar，而且每个 database file 同时仍只有一个 writer。[SQLite 单文件格式](https://sqlite.org/onefile.html) [SQLite 临时文件](https://sqlite.org/tempfiles.html) [SQLite transaction](https://sqlite.org/transactional.html) [SQLite 适用边界](https://sqlite.org/whentouse.html)

如果 runtime 本来就不要求进入 branch/PR diff，则另一条可行路线是让本地 `.ai-workflow/runtime.sqlite3` 成为 canonical store，并用 SQLite backup 管理备份；文本文件只作 export，不再双写成第二权威源。**工程推论的选择规则**是：要求 Git diff、人工 review 和分支协作时选 tracked 双文本文件；要求本机复杂查询、原子 multi-item update 或高并发 reader 且 writer 可串行时选 local SQLite。SQLite 官方明确说明 many simultaneous writers 不是它的优势，此时应升级 client/server DB。[SQLite appropriate uses](https://sqlite.org/whentouse.html)

### 一句话决策阈值

以下阈值是**工程推论**，不是 SQLite、Git 或 JSON Lines 规范规定的产品规模：

- 只要“workflow 状态必须在 PR 中逐字段 diff、由不同 branch 独立修改后合并”是硬要求，就选 **A：每需求 `work-item.yaml + events.jsonl`**。
- 只要“多个工作项与其事件必须在一次 crash-atomic transaction 中共同提交”是硬要求，就选 **B：项目级 SQLite**；双文本文件无法从格式本身获得该保证。
- 本机跨工作项查询只有在真实数据基准的 p95 超过产品预算，且扫描或 ignored derived index 不能达标时，才由 A 升级 B；不以工作项个数拍脑袋切换。
- B 仅适用于 writer 可以排队的单机/本地文件系统场景。若业务要求多个 writer 同时提交且不能排队，或多台主机直接打开同一文件，则 A/B 都不是靠换格式就能解决的问题，应使用 application server/client-server DB。[SQLite appropriate uses](https://sqlite.org/whentouse.html)

## 1. 必须分开的两个平面

### Skill 包的 progressive disclosure

Skill 是可复用工作流的作者包：`SKILL.md` 加可选的 `scripts/`、`references/`、`assets/`。OpenAI 的 progressive disclosure 是模型 context 的加载策略：启动时加载 `name`/`description`，选择 Skill 后加载完整 `SKILL.md`，supporting resources 再按需加载；选中后并不会只读 `SKILL.md` 的一部分。[OpenAI Build skills](https://learn.chatgpt.com/docs/build-skills) [Agent Skills specification](https://agentskills.io/specification#progressive-disclosure)

因此 Skill 包应保持为静态、可发布的 instructions/references/scripts；确定性的文件校验或状态转换可以放在 script 中，但项目执行产生的工作项、进度和事件不属于 Skill 包，也不应写回 Skill 目录。OpenAI 同样建议保持 `SKILL.md` 精简，并将确定性 computation/file processing 放进 script。[OpenAI plugin skill authoring](https://developers.openai.com/plugins/build/skills#add-supporting-resources)

### 目标项目生成的 runtime storage

Runtime storage 是每个目标仓库中不断变化的业务状态，解决的是 persistence、恢复、并发、审计、Git review 和 schema evolution。它不受 Agent Skills progressive-disclosure 文件结构约束；“只加载目标工作项”是本项目的查询策略，不是 Skill 标准所说的 progressive disclosure。两者只通过 CLI contract 相连：Skill 决定何时调用，CLI 独占写入和校验 runtime storage。

## 2. 候选方案比较

| 方案 | Git diff / merge | 当前状态读取 | 原子性与并发 | 人工维护 | 结论 |
|---|---|---|---|---|---|
| 单个项目级 SQLite DB | SQLite 文件是二进制 application file；Git 对 binary 默认不生成普通文本 patch，binary merge 没有内建语义时会保留冲突待人工处理。[Git `gitattributes`](https://git-scm.com/docs/gitattributes) | SQL filter、index、join 直接，适合跨工作项查询；SQLite 官方也将多维 sift/sort/query 列为适用场景。[SQLite appropriate uses](https://sqlite.org/whentouse.html) | 单 transaction 可在 crash/power failure 下保持 ACID；WAL 允许 reader 与 writer 并行，但同一 WAL 仍一次只有一个 writer，且不适合 network filesystem。[SQLite transaction](https://sqlite.org/transactional.html) [SQLite WAL](https://sqlite.org/wal.html) | 需 SQLite 工具和 migration；不适合直接在 PR 中逐行审阅 | 不作为 Git canonical MVP；可作 derived cache，或后期改为非 Git canonical store |
| 单个项目级 `events.jsonl` | JSON Lines 是 UTF-8、每行一个完整 JSON value、以换行分隔的文本格式；天然适合逐行处理。[JSON Lines](https://jsonlines.org/) | 必须 replay 全日志或另建 checkpoint/index 才能得到 current state | JSON Lines 只规定 serialization，不提供 transaction、locking 或 checkpoint；这些都必须由 writer 实现。单文件也会成为所有工作项共同写入点 | 可读、可追加，但跨工作项历史持续增长 | 只适合严格单 writer、短历史或导出流；不作项目主存储 |
| 每工作项仅一个 `work-item.yaml` | YAML 是 human-friendly data serialization；普通文本可用 Git 的内建 three-way text merge。[YAML 1.2.2](https://yaml.org/spec/1.2.2/) [Git `gitattributes`](https://git-scm.com/docs/gitattributes) | 直接读取 current snapshot | 需要 writer lock 与同 filesystem 的 temp + atomic replace；POSIX `rename()` 要求替换期间目标路径始终指向旧文件或新文件。[POSIX `rename`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/rename.html) | 最少文件、最容易手查；但 Git commit 之前没有独立的转换审计/幂等 ledger | 可用于无需恢复和审计的极简、低风险流程 |
| 每工作项 `work-item.yaml + events.jsonl` | 两者均为文本；不同工作项通常改不同路径。Git 按项目文件快照保存 commit，并对普通文本提供 three-way merge。[Git snapshots](https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F#_snapshots_not_differences) [Git `gitattributes`](https://git-scm.com/docs/gitattributes) | current state 直接读 YAML；只有 history/recovery 才读日志 | 单工作项内由同一 CLI serialise writer；snapshot replace 与 event append 仍需 crash test，跨工作项不承诺 transaction | 保留可读 snapshot 与逐事件审计，且冲突范围局部化 | 推荐的 Git canonical MVP |

补充判断：不能用 Git 的 `merge=union` 把项目级日志冲突当成已解决。Git 官方明确说明 `union` 可能以随机顺序保留双方新增行，需要人工验证；对有 sequence、审批先后或状态机前置条件的 event log，这不足以保证语义正确。[Git built-in merge drivers](https://git-scm.com/docs/gitattributes#_built_in_merge_drivers)

### 2.1 SQLite 是否始终单文件、能否随时复制

**官方事实：SQLite 不是“运行时始终只有一个物理文件”。**SQLite 将完整数据库内容放在一个主文件中，这是其 single-file database 的含义；但 transaction 和恢复协议会创建辅助文件。[SQLite single-file database](https://sqlite.org/onefile.html) 默认 rollback 模式会出现 `-journal`，WAL 模式会出现 `-wal` 与通常基于 `-shm` 文件的 wal-index；`-wal` 通常在最后一个连接正常关闭时删除，异常退出后可以继续存在。[SQLite WAL temporary file](https://sqlite.org/tempfiles.html#write_ahead_log_wal_files) [SQLite shared-memory file](https://sqlite.org/tempfiles.html#shared_memory_files) SQLite 官方还明确指出 WAL 是数据库 persistent state 的一部分，复制或移动时若把主文件与 WAL 分离，可能丢失已提交 transaction 或造成损坏。[SQLite WAL file](https://sqlite.org/wal.html#the_wal_file)

**官方事实：不能把运行中的主 DB 随时裸 `cp` 当作备份。**在 transaction 中复制主文件，副本可能混合旧页和新页而损坏；只有复制期间没有 transaction，或先通过 SQLite API 持有 shared lock，普通文件复制才安全。若上一次 write transaction 失败，还必须让对应 hot `-journal` 或 `-wal` 与主文件配套。[SQLite “Backup or restore while a transaction is active”](https://sqlite.org/howtocorrupt.html#_backup_or_restore_while_a_transaction_is_active) [SQLite shared-lock copy procedure](https://sqlite.org/backup.html#using_the_sqlite_online_backup_api) 因此“项目级 SQLite 只有一个需要关心的文件”只在连接已正常关闭、没有 hot journal/WAL 的 quiescent checkpoint 上成立。

**官方事实：live database 应使用 SQLite-aware backup。**Online Backup API 可以增量复制，只在实际读取 source page 的短时间持锁，并在完成后得到 source 开始复制时的一致 snapshot；相较于长时间持 shared lock 再 `cp`，它允许其他用户在备份期间继续使用数据库。[SQLite Online Backup API](https://sqlite.org/backup.html) `VACUUM INTO` 也是 live database 的一致 snapshot 方案，输出更紧凑并清除已删除内容的残留，但 CPU 开销更高、不能像 Backup API 一样增量执行；若命令被掉电或异常关机中断，尚未完成的输出文件可能不完整或损坏。[SQLite `VACUUM INTO`](https://sqlite.org/lang_vacuum.html#vacuuminto)

**工程推论：**若选择项目级 SQLite，运行时应把主 DB 与 `-journal`、`-wal`、`-shm` 都视为 SQLite 管理的内部集合，禁止外部进程单独移动、覆盖或提交其中任一文件。频繁在线备份优先 Online Backup API；需要紧凑且清除 deleted-content residue 的离线工件时选择 `VACUUM INTO`，并只在命令成功后发布输出文件。若必须把 runtime 随 branch 进入 PR，让评审者逐字段 diff 并在不同工作项上并行 merge，则选择每工作项 `work-item.yaml + events.jsonl`；SQLite 的 binary `textconv` 只能提供不可应用的展示 diff，binary merge 默认也没有良定义的内容语义。[Git binary `textconv`](https://git-scm.com/docs/gitattributes#_performing_text_diffs_of_binary_files) [Git built-in merge drivers](https://git-scm.com/docs/gitattributes#_built_in_merge_drivers)

## 3. 从当前约 13 个持久化路径收敛到两个文件

当前协议中的文件数量随 track 和可选工件变化；这里按“canonical + derived + revision/semantic files + indexes”的约 13 个持久化路径描述。收敛不是删除信息，而是删除重复 source of truth。

| 当前职责 | 新位置 | 规则 |
|---|---|---|
| `manifest`：ID、类型、track、revision、base commit | `work-item.yaml.identity`、`revision`、`provenance` | 稳定 ID 不因标题或状态改变 |
| `tasks` | `work-item.yaml.tasks[]` | DAG、acceptance、status 和 evidence refs 同处；CLI 校验 transition |
| `execution/state` | `work-item.yaml.lifecycle` | `phase/state/next_action/delivery` 只保存一份 |
| revision `input/plan` | `work-item.yaml.revision.input/plan` | 当前批准 revision 进入 snapshot；旧 revision 的不可变事实由 event 与 Git commit 保留 |
| `decisions/review/handoff/context` | `work-item.yaml.decisions/review/summary` | 仅存有业务含义的内容；可从其他字段确定性生成的段落不落盘 |
| `evidence/` | `work-item.yaml.evidence[].ref` | 测试报告、PR、commit、外部工件保留在其原生位置，runtime 只存 ref/hash，不复制 raw output |
| `execution/events.ndjson` | `events.jsonl` | 统一扩展名；每行一个完整 event object，末行写换行。[JSON Lines format](https://jsonlines.org/) |
| `indexes/active`、`indexes/catalog` | 不作为 canonical file | CLI 扫描 snapshot；若 profiling 证明需要，则生成 ignored SQLite cache |
| project overview/modules/capabilities | 正常项目文档，非 runtime state | 仅在确有长期语义时保留；不要因每次 workflow run 重写 |

建议的最小 envelope：

```yaml
schema_version: 1
identity: {id: REQ-..., type: requirement, title: ...}
revision: {id: R001, input: ..., plan: ..., approved_at: null}
lifecycle: {phase: plan, state: active, next_action: plan_ready, delivery: not_started}
tasks: []
decisions: []
review: {result: null, findings: []}
summary: ...
evidence: []
provenance: {base_commit: ..., last_event_id: EVT-000001}
```

```json
{"schema_version":1,"event_id":"EVT-000001","work_item_id":"REQ-...","sequence":1,"at":"...","actor":"...","type":"created","idempotency_key":"...","payload":{},"refs":[]}
```

`schema_version`、稳定 `work_item_id`、单工作项单调 `sequence`、全局唯一 `event_id` 和 `idempotency_key` 应从第一版就保留。这是后续 import、去重和 replay 的设计约束；JSON object 本身由 JSON 标准定义，而 JSON Lines 要求每行都是独立的有效 JSON value。[RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) [JSON Lines](https://jsonlines.org/)

## 4. 写入协议

1. 只有 workflow CLI 可以修改这两个文件；agent 和人工只通过 command 提交 transition。
2. CLI 获取“单工作项 writer lock”，读取 snapshot 和日志末事件，验证 `last_event_id`、`sequence`、idempotency key 与合法 transition。
3. 先在内存生成新 event 与新 snapshot；以一次完整 write 追加 event 并同步，再将完整 snapshot 写到同 filesystem 临时文件、同步并 atomic replace。POSIX 保证 successful `rename()` 的 atomic name replacement，但 JSON Lines/YAML 格式自身并不保证 durability；上述顺序与 recovery 设计均是工程推论。[POSIX `write`](https://pubs.opengroup.org/onlinepubs/9699919799/functions/write.html) [POSIX `fsync`](https://pubs.opengroup.org/onlinepubs/009695399/functions/fsync.html) [POSIX `rename`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/rename.html)
4. event append 与 snapshot replace 跨两个普通文件并非天然 transaction，因此 CLI 必须定义 recovery：启动时若日志领先 snapshot，则按最后一个完整且已校验 event 重建 snapshot；若 snapshot 引用不存在的 event，则拒绝继续并报告 corruption。不要宣称两文件方案具有 SQLite 的 ACID crash guarantee；SQLite 的该保证来自 database transaction engine。[SQLite transaction](https://sqlite.org/transactional.html)
5. 对 mutation 做 injected-interruption tests：event append 前、完整行写后、snapshot replace 前后、lock owner crash。日志末尾不完整行必须报错或由明确 recovery policy 隔离，不能静默跳过。

若业务必须保证“event 与 snapshot 在 power failure 下要么都提交、要么都不提交”，而不接受上述 recoverable protocol，应直接使用 SQLite transaction，不应继续为普通文件叠加复杂 transaction directory。[SQLite atomic transaction](https://sqlite.org/transactional.html)

## 5. 迁移边界

### 单 YAML 升级为双文件

出现任一条件即增加 per-item `events.jsonl`：需要未 commit 状态的 crash recovery、幂等 retry、审批/actor 审计、状态机违规诊断，或需要回答“如何到达当前状态”。迁移时为现有 snapshot 写一个 `snapshot_imported` genesis event，并让 snapshot 的 `last_event_id` 指向它；无需伪造更早历史。

### 双文件升级为 SQLite

不设拍脑袋的“工作项数量”阈值，以测量和能力需求触发：

- 跨工作项 filter/join/aggregate 的 p95 已超过产品预算，且 ignored cache 不能解决；SQLite 官方明确适合需要多维 sift/sort/query 的本地数据。[SQLite appropriate uses](https://sqlite.org/whentouse.html)
- 必须对多个工作项做一个原子 transaction，或两文件 recovery protocol 已成为主要维护成本；SQLite 对单 transaction 提供 ACID crash guarantee。[SQLite transaction](https://sqlite.org/transactional.html)
- Runtime 不再以 Git PR 为协作/审计界面，而由一个本机 application service 串行协调 writer，需要稳定 SQL schema、indexes 与 online backup。SQLite 提供单文件稳定格式与 online backup API。[SQLite file format](https://sqlite.org/onefile.html) [SQLite Backup API](https://sqlite.org/backup.html)
- 查询量和并发 reader 增长，但 writer 可以排队且都在同一主机；WAL 可并行 readers 与 writer，但同一 DB 仍只允许一个 writer。[SQLite WAL concurrency](https://sqlite.org/wal.html#concurrency)

反边界：若需求是多台机器直接访问同一 database file，或许多 writer 必须同时写，SQLite 官方建议改用 client/server database；WAL 也不适用于 network filesystem。[SQLite appropriate uses](https://sqlite.org/whentouse.html#situations_where_a_clientserver_rdbms_may_work_better) [SQLite WAL](https://sqlite.org/wal.html)

### 可逆迁移步骤

1. 先发布稳定的 logical schema 与 `schema_version`，让 text store 和 SQLite adapter 共享同一 validator。
2. 暂停 writer，校验全部 snapshot/event，再在一个 SQLite transaction 中导入 `work_items`、`tasks`、`events`、`evidence_refs`。
3. 对比工作项数、每项末 sequence、current lifecycle、`last_event_id` 和 canonical JSON hash；任何差异都不切换。
4. 切换前必须有 `SQLite -> work-item.yaml/events.jsonl` exporter。若 DB 成为 canonical，`.db`、`-wal`、`-shm` 不再提交 Git，并使用 SQLite backup API，而不是在 DB open 时直接复制文件；官方说明直接复制 live DB 可能产生损坏的 backup，online backup 会产生一致 snapshot。[SQLite Backup API](https://sqlite.org/backup.html) [SQLite WAL file handling](https://sqlite.org/wal.html#the_wal_file)
5. 迁移窗口可以短期 shadow-read 比较，但不要长期 dual-write 两套 canonical stores；最终只能有一个 writer contract 和一个 source of truth。

## 最终建议

采用 per-work-item `work-item.yaml + events.jsonl`，并把项目级索引降为可重建 cache。这一方案保留 Git 文本审阅和人工可恢复性，同时把 current-state 读取从全日志 replay 变为单 snapshot 读取；其代价是跨两文件不具备数据库 transaction 的天然 ACID，因此必须由单 CLI writer、atomic snapshot replace、末事件指针、幂等键和 recovery tests 明确定义边界。

SQLite 不应被否定：它是查询、原子 multi-item update 和非 Git runtime 的清晰升级路径。但在“项目状态要随 branch/PR 进行人类 diff/merge”这一前提下，将一个 binary DB 纳入 Git 会牺牲最重要的协作界面；MVP 应先用双文本文件，把未来迁移所需的 stable IDs、schema version 和 event sequence 预埋好。[Git binary diff/merge](https://git-scm.com/docs/gitattributes) [SQLite single-file/transaction guarantees](https://sqlite.org/onefile.html)
