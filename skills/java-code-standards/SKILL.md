---
name: java-code-standards
description: Apply Java and Spring coding standards when writing, modifying, analyzing, or reviewing Java code. Covers type safety, Optional/Stream usage, architecture, Controller/Service/DAO responsibilities, reusable Query/VO models, complexity and extraction boundaries, and mandatory functional comments on every explicitly declared type, method, and complex-flow step.
---

# Java 代码规范

## 使用方式

1. 读取目标项目的 AGENTS.md / CLAUDE.md 及适用的项目代码规则。
2. 完整读取 [规范索引](references/index.md) 和 [核心编码、基础写法与功能注释](references/01-core.md)。
3. 按下表读取当前代码涉及的专题，再进行分析或修改；已读取且未变化的内容不重复加载。
4. 以用户当前要求、项目具体约定、通用规则的顺序处理差异，复用现有组件，只处理本次授权范围。

本技能的规范正文随包提供，使用相对路径读取，可独立安装。

## 必须执行的功能注释

- 每个显式声明的类、接口、枚举、record、嵌套类型必须说明其功能和职责。
- 每个显式声明的方法和构造器必须有中文功能 Javadoc，包含 private、@Override 和显式声明的 getter/setter，说明做什么及产生什么结果。
- 复杂流程每一步的对应代码前必须有中文功能注释，解释该步完成的业务动作、结果或限制；方法头的总说明不能替代代码步骤注释。
- 关键分支、循环、提前返回及失败处理也说明功能。隐式生成的方法不手工展开。

## 专题路由

| 当前任务涉及 | 必读规范 |
|---|---|
| 分层、架构、复杂逻辑、拆方法/拆类 | [架构与复杂逻辑](references/02-layering-and-methods.md) |
| Controller、Query、VO、Result、CRUD、分页 | [Web API](references/03-web-api.md) |
| 异常、提示、日志、审计 | [异常与日志](references/04-exception-and-logging.md) |
| DAO、Mapper、SQL、事务 | [数据访问与事务](references/05-database-and-transaction.md) |
| Feign、外部调用、幂等、消息、缓存、并发 | [外部调用与并发](references/06-integration-and-concurrency.md) |
| 用户输入、权限、文件、秘密、外部地址 | [安全编码](references/07-security.md) |
| 请求核对代码规范 | [代码核对表](references/09-review-checklist.md) |

## 设计尺度

- 普通业务默认 Controller → Service → DAO / Mapper，其他层次按实际职责引入。
- Query、VO 按业务语义命名并合理复用，不强制 Create / Update / List / Detail 等操作词。
- 复杂入口展示有功能注释的业务步骤；先抽当前类的方法，存在独立职责、不同边界或真实复用时再拆类。
- 复用项目已有 Result、分页、异常、权限和日志能力，保持已发布协议与既有框架边界。
- 遇到无法从要求或代码判定且会改变业务含义的差异，说明具体问题后澄清；已明确的用户选择直接执行。
