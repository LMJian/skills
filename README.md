# Personal Skills

面向 AI 辅助研发的可复用 Skills 与插件集合，覆盖存量代码调研、服务端技术方案，以及从需求到验证和交付的完整 Harness 开发流程。可以单独使用专业 Skill，也可以通过 `harness-devflow` 编排研发工作，保留任务状态、产物与真实验证记录。

## 项目一览

| 项目 | 形态 | 主要用途 |
| --- | --- | --- |
| [harness-devflow](harness-devflow/README.md) | 完整研发流程插件 | 按任务选择需求、设计、测试、计划、实现、审查和交付阶段，支持恢复与证据校验。 |
| [brownfield-recon](brownfield-recon/SKILL.md) | 独立 Skill | 调研已有代码、接口契约和失败路径，形成修改前的行为基线与保留／替换／移除判断。 |
| [server-tech-design](server-tech-design/SKILL.md) | 独立 Skill | 编写、评审和优化服务端技术方案，讲清主流程、关键决策与相关工程约束。 |

## harness-devflow：通用 Harness 开发流程

当前版本为 **0.3.1**，支持 Codex 和 Claude Code 接入。运行时依赖 **Python 3.10+ 与 Git**，负责阶段编排、产物校验和任务恢复；具体研发工作由 Agent 按 Skills 执行，检查命令使用项目自己的工具链。

插件包含 **14 个流程入口与 2 个专业 Skills**，共 16 个 Skills；流程阶段目录也有 16 项，运行时根据任务配置生成实际路线，需求、计划、实现和审查验证是核心阶段。

| 流程配置 | 默认开发流程 | 默认交付终点 |
| --- | --- | --- |
| `light` | 需求 → 任务计划 → 实现 → 审查与验证 | 本地完成 |
| `standard` | 需求 → 设计 → 设计审查 → 测试设计 → 计划 → 实现 → 审查与验证 | 本地完成 |
| `release` | 标准流程，增加设计确认，随后执行远端交付与发布部署 | 部署完成 |

开发深度与交付终点独立选择：`local` 在本地验证后完成，`pr` 在创建评审请求后完成，`merged` 等待合并，`deployed` 完成发布确认和部署验证。接口更新、集成测试、知识归档按需启用；单模块默认使用当前分支，多模块可通过 worktree 按依赖批次实现与合并。

阶段推进需要实际产物与检查记录，代码或已引用产物变化会使相关证据失效。插件保留阶段状态、调用来源和失败历史，支持中断恢复、重开阶段与有界重试。

需求、设计和验证记录默认保存在本地。测试、代码评审、接口更新及部署通过项目配置的命令或适配器执行。

插件加载后，在 Codex 中可这样请求：

```text
$harness-devflow:flow 实现服务端导出功能，使用标准流程，先完成本地实现与验证。
$harness-devflow:flow 查看当前任务状态并继续。
```

完整阶段、Skills、宿主接入和配置说明见 [插件 README](harness-devflow/README.md)；专业能力的输入、产物及报告转换见 [能力接入契约](harness-devflow/references/capabilities.md)。

## brownfield-recon：存量逻辑调研

沿入口、核心实现、下游调用、配置和数据存储追踪实际行为，结合相关测试与 Git 历史核实结论。重点识别兼容约束、未确认契约，以及哪些旧行为应当保留、替换或移除，区分当前事实、目标设计和已执行的验证。

默认做与当前变更有关的聚焦调研，以简短的 `report.md` 保存代码版本、行为基线和变更判断。只有范围确实需要时，才补充契约矩阵、待确认问题或采集器生成的证据清单。调研就绪度针对下一阶段判断，不把本地调研结论当作已通过集成或发布验证。

调研本身以只读为主，按约定保存产物；如果用户已要求实施变更，调研完成后继续已授权的工作。

加载该 Skill 后的请求示例：

```text
$brownfield-recon 梳理这个仓库的请求路由、配置加载和失败处理，判断本次改造需要保留、替换或移除哪些行为。
```

具体产物规则见 [调研报告契约](brownfield-recon/references/report-contract.md)。

## server-tech-design：服务端技术方案

先明确核心问题、关键决策和完整流程，再按读者需要组织章节。接口、配置、安全、异常、监控和上线作为按需检查的维度，避免机械填充固定模板。

支持新建方案、设计审查和修改已有文档。修改时同步检查定义、示例、图和引用，合并重复内容；区分现状、设计目标、估算和已验证结果。交付目的地遵循用户要求和可用文档工具。

配套的 [章节指南](server-tech-design/references/section-guide.md)、[写作指南](server-tech-design/references/writing-style.md)、[审查清单](server-tech-design/references/review-checklist.md) 和 [可选模板](server-tech-design/references/template.md) 用于按需展开设计。

加载该 Skill 后的请求示例：

```text
$server-tech-design 根据需求和现有代码写一份本地 Markdown 技术方案，先讲清主流程和关键决策，保留必要约束。
```

## 如何选择与组合

- 只需要理解或调研现有实现：使用 `brownfield-recon`。
- 已有清楚的需求和背景，只需要方案编写或评审：使用 `server-tech-design`。
- 需要持续推进需求、实现、验证和交付，并保存可恢复状态：使用 `harness-devflow`。

两个独立 Skills 也有明确的产物交接约定，支持在不同会话中先调研、再设计：

1. `brownfield-recon` 优先遵循指定或项目已有的产物目录，默认写入 `.artifacts/brownfield-recon/<branch-key>/<run-id>/report.md`。报告记录仓库、任务范围、实际分支、代码版本、相关未提交状态和下一阶段就绪度，并在结束时给出入口路径。
2. `server-tech-design` 在仓库相关的方案工作中，先读显式提供的材料，再查项目约定位置及 `.artifacts/`，包含被 Git 忽略的文件。它按任务、范围和源码证据选择报告，不只看文件时间；自定义外部目录需要明确提供路径或项目索引。
3. 设计先读入口报告，再按需读取契约、未决问题和证据；检查相关代码的新变化，复用仍适用的结论与场景。设计引用基线并另存文档，保留原调研记录；缺少调研报告时仍可直接做必要的代码检查。

这是由 Agent 执行的 Skill 交接规则。具体格式与读取方式见 [调研输出契约](brownfield-recon/references/report-contract.md) 和 [设计输入发现规则](server-tech-design/references/recon-inputs.md)。

Harness 已在 `harness-devflow/skills/` 内包含两个专业 Skill 及必要资源，无需再安装根目录的独立版本。存量调研在 intake 内按需调用；服务端设计与设计审查使用包内 `server-tech-design`，其他领域保留通用设计路径。

## 目录与获取

```text
.
├── README.md
├── harness-devflow/        # 完整插件：宿主清单、Skills、运行时、文档和测试
├── brownfield-recon/       # 独立调研 Skill 及配套资源
└── server-tech-design/     # 独立设计 Skill 及配套资源
```

克隆本仓库后，按需使用对应目录：

- 完整开发流程：使用 `harness-devflow/`，按 [插件接入说明](harness-devflow/README.md#使用方式) 加载或安装。
- 独立调研或设计：将 `brownfield-recon/` 或 `server-tech-design/` 完整目录放入所用宿主的 Skills 目录，也可在任务中指定其 `SKILL.md` 路径使用。

分享时可以提供本仓库链接或复制所需的完整目录。复制插件时保留 `.codex-plugin/`、`.claude-plugin/` 等隐藏目录；复制 Skill 时保留配套的 `references/`、`scripts/` 等资源。
