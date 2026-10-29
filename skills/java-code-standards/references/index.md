# Java 全局代码规范索引

## 定位与适用范围

本目录约束 Java / Spring 代码的编写、分析、修改和代码审查，涵盖基础语言写法、架构、分层、模型、业务流程、数据访问、异常日志和安全编码。

规范正文既用于本机全局约束，也随 `java-code-standards` 技能打包发布；同一版本的正文保持一致。使用时选择当前环境中的一个规范入口，避免叠加重复规则。

## 优先级与强制级别

1. 用户当前明确要求。
2. 适用于目标代码的项目个性化约定与既有公开契约。
3. 本目录通用 Java 代码规范。
4. 示例性、历史性 Pattern。

项目个性化约定与全局规范冲突时，以项目约定为准；全局规范补充项目未约定的部分。项目要求已经明确且适用于当前代码时，直接按该要求执行。

- `MUST` / “必须”“禁止”“不得”：代码约束。
- `SHOULD` / “默认”“优先”：通常采用，存在明确项目原因时可选择其他实现。
- `MAY` / “可以”“按需”：存在实际需求时使用。
- 已有项目例外按其适用条件执行，不将普通惯例自动升级为全局要求。
- 对会改变业务含义且无法从当前要求或代码确定的冲突，先说明并澄清；已经授权的选择不重复询问。

## 按需读取

任意 Java 代码任务先完整读取本索引和 `01-core.md`，再读取涉及的专题。已读取且未变化的内容不重复加载。

| 代码涉及内容 | 专题 |
|---|---|
| 类型、Optional / Stream、集合、数值与时间、资源、配置、注释 | [01-core.md](01-core.md) |
| 架构、分层、复杂逻辑、拆分与 Spring 代理 | [02-layering-and-methods.md](02-layering-and-methods.md) |
| Controller、Query、VO、Result、CRUD、校验、分页 | [03-web-api.md](03-web-api.md) |
| 异常、错误码、用户提示、日志、审计 | [04-exception-and-logging.md](04-exception-and-logging.md) |
| DAO、Mapper、SQL、数据一致性、事务 | [05-database-and-transaction.md](05-database-and-transaction.md) |
| 外部调用、幂等、消息、缓存、上下文、中断与并发 | [06-integration-and-concurrency.md](06-integration-and-concurrency.md) |
| 身份、权限、不可信输入、文件、敏感数据 | [07-security.md](07-security.md) |
| 用户请求核对代码是否符合规范 | [09-review-checklist.md](09-review-checklist.md) |

## 核心约束

- 所有显式声明的类和方法必须有中文功能注释；复杂流程每一步的对应代码前必须有功能注释，不能只在方法头概述步骤。
- Query、VO 按业务语义命名并按需复用，不强制追加 Create、Update、List、Detail 等操作词。
- 普通业务默认采用 Controller → Service → DAO / Mapper；额外层次、接口和模型由真实职责决定。
- 复杂方法保留清晰的业务流程骨架；先抽方法，有独立职责或边界再拆类。
- Controller 负责协议边界与响应包装，Service 负责业务用例，DAO / Mapper 负责数据访问。
- 复用项目已有 Result、分页、异常、权限和日志组件，保护已发布的 JSON 契约。
- 业务身份和数据范围取自可信上下文；持久化操作有明确范围和一致性条件。
- 异常不吞噬，日志不泄露敏感信息；只修改用户请求范围内的代码。

项目可以补充框架、目录、路由和公共组件的具体写法；本规范不替项目指定技术栈或创建新的工程层次。
