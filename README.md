# Personal Skills

可复用的 AI Skill 集合，目前覆盖存量代码调研和服务端技术方案编写两个环节。

## Skill 一览

| Skill | 主要功能 | 适用场景 |
| --- | --- | --- |
| [brownfield-recon](brownfield-recon-fixed/SKILL.md) | 基于代码和历史证据，梳理已有行为、接口契约与兼容约束。 | 接手陌生仓库、改造旧系统、重构、迁移或排障前的逻辑调查。 |
| [server-tech-design](server-tech-design/SKILL.md) | 编写、评审和优化服务端技术方案，突出核心设计并覆盖相关工程约束。 | 从需求形成方案、准备设计评审、整理零散材料，或精简已有技术文档。 |

## brownfield-recon：存量逻辑调研

沿着入口、核心实现、下游调用、配置和数据存储追踪实际行为，并结合测试与 Git 历史核实结论。重点识别哪些行为必须保持兼容、哪些跨模块或跨仓库契约尚未确认，区分事实、推断和待解决问题。

主要产物包括调研报告 `report.md`、契约矩阵 `contract-matrix.md`、待确认问题 `open-questions.md` 和证据清单 `evidence.json`。默认以只读方式调研，按 Skill 约定保存调研产物，不直接修改业务代码。

加载该 Skill 后的请求示例：

```text
$brownfield-recon 帮我梳理这个仓库的请求路由、配置加载和失败处理，指出改造时需要保留的兼容行为。
```

目录名为 `brownfield-recon-fixed/`，Skill 的名称和调用名仍是 `brownfield-recon`。

## server-tech-design：服务端技术方案

先明确核心问题、关键决策和完整流程，再按读者需要组织章节。接口、配置、安全、异常、监控和上线作为按需检查的维度，避免堆砌章节和实现细节。

支持新建方案，也支持评审和修改已有文档。修改时同步检查定义、示例、图和引用，合并重复内容；明确区分现状、设计目标、估算和已验证结果。可按需求输出飞书文档或本地 Markdown。

配套材料位于 `server-tech-design/references/`，包含章节指南、写作指南、评审检查清单和可调整的文档模板。

加载该 Skill 后的请求示例：

```text
$server-tech-design 根据需求和现有代码写一份技术方案，先讲清主流程和关键决策，文字简练，保留必要约束。
```

## 如何选择

对现有实现不熟悉时，先用 `brownfield-recon` 建立有证据支持的现状，再用 `server-tech-design` 组织方案。已有清楚的需求和实现背景时，可以直接使用 `server-tech-design`。

根目录的 `brownfield-recon.zip` 和 `server-tech-design.zip` 用于打包分享；各 Skill 的具体规则以对应目录中的 `SKILL.md` 为准。
