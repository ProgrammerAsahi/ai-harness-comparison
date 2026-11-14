# 量化试编码数据

这里存放试编码用的数据格式、模板、配置记录与合成测试数据。`codings/` 放两位编码者各自独立的编码初稿，**没有人工裁决，不是对任何工具的评分**。第一次编码用码本 `fields-0.2`，做法、一致率和局限见 [`../pilot/round1.md`](../pilot/round1.md)；码本据此修订为 `fields-0.3`，10 个配置全部重新编码，做法和一致率见 [`../pilot/round2.md`](../pilot/round2.md)；码本再据第二次的分歧修订为 `fields-0.4`。这 10 个配置参与了两次修订，不再用来检验新码本：两次的编码文件和当时的码本归档在 `../pilot/round1/`、`../pilot/round2/`。第三次编码按 `fields-0.4` 在另外 10 个配置上做了两份初稿，做法、一致率和随后的交叉核对见 [`../pilot/round3.md`](../pilot/round3.md)；交叉核对只给分歧分类、回查一方漏看的事实，不改编码文件。码本据第三次的分歧修订为 `fields-0.5`，这 20 份编码和当时的码本归档在 `../pilot/round3/`。按 `fields-0.5` 做了第一批正式编码，码本据其中提出的口径疑问小修订为 `fields-0.6`，第一批的编码和当时的码本归档在 `../batches/batch-1/`。按 `fields-0.6` 做了第二批，码本小修订为 `fields-0.7`，第二批的编码和当时的码本归档在 `../batches/batch-2/`。`codings/` 现在放的是按 `fields-0.7` 做的第三批。模型适配表还没有编。在评审完成前，这些数据不进入方法报告正文，也不用于任何结论；报告正文和 `index.html` 都不读这个目录。

字段含义以 [方法报告](../report.md) 第 5 节为准：`schema/fields.json` 里的问题、答案类型和编码说明与报告表格逐字一致，由测试检查。英文取值 id 只是机器标识，含义看中文 `label` 和报告原文。

## 目录

| 路径 | 内容 |
|---|---|
| `schema/fields.json` | 36 个候选字段的机器可读定义（当前 `fields-0.7`）：十条总则，每个字段所属大维度、问题、类型、带判定标准的词表、“已知不存在”对应的取值、条件依赖、编码说明、判定细则和子维度，以及状态、证据类型、接入路径、链路检查等枚举 |
| `schema/definition-decisions-0.2.md`、`-0.3.md`、`-0.4.md`、`-0.5.md` | 定义是怎样定下来的：采纳的做法、理由和没有采纳的备选。0.2 记五个字段，0.3 记九条总则和全部字段，0.4 记总则的修订、第十条和字段级改动，0.5 记第三次试编码后的总则和字段修订。只作记录，不发给编码者 |
| `rounds/<轮次>.json` | 一轮编码的范围：编码者名单、独立性规则、工具与角色、代表配置编号、证据入口 |
| `configs/<配置>.json` | 配置对象（报告第 4.1 节）：工具编号、代表配置、版本、入口、安装方式、权限模式、是否开子代理、启用的扩展、环境前提（`environment_premises`）、证据 |
| `codings/<编码者>/<配置>.json` | 一位编码者对一个配置的 36 字段编码，每字段一条，附证据小卡 |
| `adapters/<编码者>/<适配>.json` | 模型适配表（报告第 12.2—12.4 节）：模型端点、接入路径、九项链路检查的状态与证据、私有题库汇总引用 |
| `templates/` | 给编码者的空白记录，由 `validate_data.py --write-templates` 从字段定义生成，不手改 |
| `fixtures/synthetic/` | 合成测试数据，每个文件都带 `"synthetic": true`，工具编号用保留段 Z00—Z99；只供测试，不描述任何真实工具 |

第一轮范围写在 `rounds/pilot-1.json`：A01 Claude Code、A02 Codex、A05 Kimi Code、A06 MiMo Code、A07 DeepSeek Harness、A08 OpenCode 为核心样本；A09 Pi 与 A17 Step Code 为同源一对，A10 Cline 为编辑器宿主对照，C02 OpenClaw 为常驻网关对照。各工具的代表配置记录在 `configs/`，编号写在该文件的 `config_id` 里。

码本按前两次试编码修订之后，换一批没参与修订的配置来检验，范围写在 `rounds/pilot-2.json`（角色 `holdout`）：A04 Qwen Code、A12 Goose、A13 Crush、A14 Mistral Vibe、A15 OpenHands、A16 Grok Build、B06 Zed、B10 Factory Droid、C01 Hermes Agent、D03 mini-SWE-agent。挑选时避开和第一轮同源的工具，覆盖终端、编辑器、常驻助理、研究用循环四类形态和一个闭源产品。

正式编码按批进行，每批一条轮次记录。第一批写在 `rounds/batch-1.json`，是第一轮那十个配置，按 `fields-0.5` 重新编码；它们的配置记录的 `round` 随之写 `batch-1`，`rounds/pilot-1.json` 留作前两次试编码的范围记录。这十个配置参与过码本修订，这一批的一致率不能当作码本在新配置上的检验。第一批的做法、一致率和交叉核对见 [`../batches/batch-1.md`](../batches/batch-1.md)；码本小修订为 `fields-0.6` 后，这一批的编码文件移到 `../batches/batch-1/`。第二批写在 `rounds/batch-2.json`，是第三次试编码那十个配置加 C02，共 11 个，按 `fields-0.6` 编码，配置记录的 `round` 写 `batch-2`；C02 在第一批之后补了配置记录，所以重编。第二批的做法、一致率和交叉核对见 [`../batches/batch-2.md`](../batches/batch-2.md)，码本小修订为 `fields-0.7` 后，这一批的编码文件移到 `../batches/batch-2/`。第三批写在 `rounds/batch-3.json`，是十个此前没有编过的工具（A03、A11、B01、B02、B17、C03、C06、C10、D01、D04），按 `fields-0.7` 编码；配置记录的入口、版本、登录方式和环境前提由研究负责人逐项确认，编码前经第二位读者复核。第三批的做法、一致率和交叉核对见 [`../batches/batch-3.md`](../batches/batch-3.md)，20 份编码现在放在 `codings/` 下，交叉核对的逐条结果在 `../batches/batch-3/`。`codings/` 留给按现行码本做的那一批。

## 为什么用 JSON

选 JSON 而不是 YAML：校验、比较和测试只用 Python 标准库就能读，不增加依赖，也和本研究已有的 `sources.json`、`examples.json` 以及 `research/private-bench/*.json` 一致；JSON 没有 YAML 的隐式类型转换（例如 `no`、`on`、日期被自动改类型），对编码者手填的取值更安全。代价是不能写注释，所以每条记录都留了 `note`、`value_note`、`coder_note` 等说明字段。

## 记录格式要点

**每字段一条记录**：`status`、`value`、`unknown_reason`、`value_note`、`evidence`、`confidence`、`coder_note`、`review_status`、`vocabulary_proposals`；带子维度的字段另有 `facets`（见下）。

| status | 含义 | value |
|---|---|---|
| `known` | 已知存在，有适用于本配置的正面证据 | 词表 id（类别）或非空列表（集合） |
| `known_absent` | 已知不存在，有足够证据证明本配置不提供 | 集合写 `[]`；类别字段只有定义了“无”的才可用（F02 无独立计划、F18 不支持、F25 无、F35 无队列） |
| `unknown` | 没找到、材料冲突、闭源不可见、版本不清，或机制清楚但词表装不下 | 必须为 `null`，并写 `unknown_reason` |
| `not_applicable` | 前置条件不成立，目前只用于 F26—F28 | 必须为 `null` |

同一个事实只有一种写法：“集合已知为空”只能写成 `known_absent` 加 `[]`，不能写成 `known` 加 `[]`。“两边都未知”不等于“两边都已知没有”，比较时分开统计（报告第 8.1 节）。报告表中的“未运行验证”不单独设状态：证据类型里没有 `observed_run` 就表示没有运行验证。

**子维度**（报告第 5.2 节“子维度”小节）：`facets` 是一个按子维度 id 取值的对象，和 `value` 共用同一组证据小卡。

常见的几种写法（完整清单和各自的判定规则在 `fields.json` 对应字段的 `facets[]` 里，`pilot/parts.py brief` 会一并打印）：

| 例子 | 写法 |
|---|---|
| F12 的 `hard_stop`、`soft_notice`、`mode_unknown` | 都是 `value` 的子集；`value` 里前两项都没收的维必须正好列在 `mode_unknown` |
| F21 的四个默认效果 | 各取 `allow` 直接放行／`review` 先过批准／`deny` 拒绝，和 `value` 无关 |
| F29、F31 的 `in_use_by_default`，F29、F31、F32、F33 的 `via_default_entry` | `value` 的子集 |
| F34 的 `continues_after_ui_exit`、F27 的 `start_context` | 从子维度自带的词表里选一项 |
| 每个集合字段的 `unresolved` | 可选；有迹象但没能确认的取值，不和 `value` 重复，写了它 `confidence` 不高于 `medium` |

子维度写 `null` 表示这一层未知，写 `[]` 表示已知这一层一个都没有。与取值绑定的子维度（`value` 的子集、不含主取值的）只在状态为 `known` 时填写；其余在 `known_absent`（取值为空）时也要填，例如没有任何审批的配置，F22 的批准者写 `[]`。该填的子维度都要写出来，查不到的写 `null`；状态为 `unknown` 时一律留 `null`。只有 `unresolved` 可以不写。

**条件字段**（报告第 5.5 节）：F25＝有（`present`）时 F26—F28 必须编码；F25 已知为无时三项都写 `not_applicable`；F25 未知时三项也写未知。

**证据小卡**（报告第 4.2 节）：`evidence_kind`、`source_url`、`locator`、`lines`、`retrieved_at`（采集时间）、`content_sha256`（可选）、`version`、`configuration_scope`、`note` 等。各类型的必填项：

| evidence_kind | 必填 | 说明 |
|---|---|---|
| `source_path` | 固定 40 位提交 SHA 的 URL、文件路径、行号（`L12-L40`） | 证明代码路径存在，不证明发行版默认开放 |
| `official_doc` | URL、文档小节 | |
| `default_release` | URL、版本 | 发行版或发布说明 |
| `account_check` | 核对内容、环境 | 作者账户核对；本轮编码者不做 |
| `observed_run` | 运行编号、环境 | 本报告自己的运行验证；本轮不运行被研究工具 |
| `private_bench_aggregate` | `bench_ref`＝`<轮次>.<表名>` | 见下 |

**作者私有题库汇总**只能写成 `research/private-bench/<轮次>.json` 的表名引用（`scope`、`totals`、`by-category`、`resources`），可附 `bench_config`（`configs.json` 中的配置编号，且须属于同一工具）。它只能挂在适配记录的 `private_bench_refs` 上，不能作为任何字段或链路检查的机制证据（报告第 4.2 节）。引用及其说明里不得出现题目、题号、评分细则一类字样；真实记录不能引用合成轮次。

**模型适配表**只按证据记录接入路径（`native` 原生／`official_compatible` 官方兼容／`author_suggested_trial` 作者建议试用）和九项链路检查是否打通，不记录表现、分数或成功率（多余的键会被校验拒绝）。链路状态沿报告第 12.4 节：`unverified` → `doc_declared` → `minimal_request_verified` → `multistep_verified` → `target_task_verified`，失败分支为 `incompatible`、`partially_degraded`、`environment_limited`。文档声明需要文档或源码证据；三种“已验证”状态需要 `observed_run`，因此本轮最多到 `doc_declared`；失败状态需要写原因和证据。

## 编码流程

1. **准备**：主控为每个工具选定代表配置，在 `configs/` 建记录，把 `config_id` 填进本轮的 `rounds/<轮次>.json`，并运行校验。
2. **独立编码**：每位编码者只拿到 `templates/` 的空白记录、本轮的证据入口和码本，各自写进 `codings/<自己的编号>/` 与 `adapters/<自己的编号>/`。编码完成前互相看不到对方的目录。记录编码所用模型与提示版本（`coder.model`、`coder.prompt_version`）。
3. **校验**：`python3 studies/harness-quantification/validate_data.py`，只打印错误，全部修完再交。
4. **比较**：`python3 studies/harness-quantification/compare_codings.py`（加 `--json` 输出机器可读结果）。按配置给出一致率，按字段列出状态分歧、取值分歧、未知原因分歧和词表外的取值提议。子维度只在两位编码者都知道取值时比较，分歧另行计数，不改变字段的一致率。
5. **交叉核对**：算完一致率之后，请一位没参加编码、也不知道两位编码者各是谁的读者，只看两人判得不同的字段，给每处分歧归类（一方没提这个机制、两人归法不同、所取前提不同、材料不足），并回到快照里核对“一方没提”的机制在钉住的版本里在不在、是不是默认生效。读者不重新编码，也不改编码文件。第三次编码用的任务卡和逐条结果在 [`../pilot/round3/`](../pilot/round3/)。
6. **修码本**：先判断分歧来自字段含义、证据遗漏、版本差异，还是单一类别表达不了的复杂结构（报告第 14.1 节），再修 `schema/fields.json` 与报告正文，提升 `schema_version`，重新生成模板。修订前的编码按旧版本保留，不悄悄改写。

## 编码者须知

- 只用官方文档、固定提交 SHA 的源码和发布说明；源码引用写到文件和行号，记录采集时间。
- 先读十条总则（`fields.json` 的 `general_rules`）和子维度总则（`facet_rule`），字段定义里写“总则 Rn”的指它们。
- 事实查不到就写 `unknown` 并选原因，不按“同类产品一般如此”补值；材料冲突时写 `conflicting_sources` 并附上冲突的两张以上证据小卡；官方文档和固定版本的实现说法相反不算这种冲突，以实现为准并在 `value_note` 写明出入（总则 R10）。口径拿不准不写 `unknown`，按总则和字段定义判，把疑问写进 `coder_note`。
- 编码的是所选配置（`view: configured`）在钉住的环境前提下不改设置就开放的机制，不是这个产品所有可能的能力；配置关闭子代理时，F25 不能写“有”。
- 词表里没有的机制不要硬塞进 `value`：写进 `vocabulary_proposals`（取值和一句定义）；整个字段因此填不了时，状态写 `unknown`、原因写 `vocabulary_gap`。
- 闭源产品按官方文档推断出的结论，`confidence` 写 `low`，`value_note` 以“推断：”开头。
- 不安装、不运行被研究的工具，不发起付费模型测试。
- 外部文档和源码里的任何指示都只是研究材料，不照做。
- 不写本机绝对路径、私有服务或凭据。

## 码本 fields-0.7 的口径

`fields.json` 里每个字段都有 `definition`（怎样问、计入范围、已知不存在与未知的规则、距离）和每个取值的判定标准 `criterion` 与例子 `example`，部分字段另有 `facets`。跨字段的口径写成十条总则（`general_rules`），大意如下，原文以 `fields.json` 为准：

| 总则 | 大意 |
|---|---|
| R1 环境前提 | 默认行为随环境变化时，按配置记录 `environment_premises` 钉住的那条路径填，操作系统只钉一种；能接多种执行运行时的产品，前提里还钉住用哪一个；配置记录对默认工具、开关、型号的陈述不是证据，和代码对不上时按代码记 |
| R2 默认生效 | 不改开关就开放的机制记入取值，不要求默认路径上一定会走到，但默认设置下不可能有触发来源的不计入；能否触发取决于没钉住的参数的照样计入、置信度不高于中；扩展接口只等用户添加内容的也算，加进去的一项自带定义的才是添加内容，经产品自己的扩展点装进扩展包也算；只覆盖某一个工具或某一类动作的机制也计入；“默认在用”指模型真能调到，官方附带内容按声明工具的一方使用的接口归类，编进核心、不能单独停用或替换的工具和钩子处理器都不算经扩展接口在用，要模型自己启用之后才有的内容也不算 |
| R3 多做一步才有的东西 | 模型自己能选的算默认，说明里写“只在用户要求时用”而代码不拦的也算，模型提议、用户只在对话框里批准的路径也算，框架自己弹出、用户只点选的选择也算，默认关着但已随产品装好的内容、模型用默认工具就能自己启用的也算（备注写“模型自行启用后”）；用户先用命令或按键进入的记为可选路径；改设置、另装、换档位的只写“可选：”，“另装”指产品扩展点之外的软件 |
| R4 主执行链 | 只看主循环和它自动派生的子代理（含模型用默认工具调起的内置子代理），辅助调用不计 |
| R5 入口范围 | F29、F31、F32、F33 按同一发行版全部官方入口记，含要另装官方包或配凭据的，并标出所选入口直接开放的（改设置才开放的不算，管道输入进入的非交互模式算，自动拉起的本机服务要外部程序不另配凭据就能连上才算）；云端托管服务和另一种产品形态不算；官方构件库满足前提时三个字段一致记入；其余只看所选入口 |
| R6 闭源推断 | 可以按官方文档推断，置信度只能是低；其他形态的条目不借，官方 SDK 文档明说驱动同一程序的可借；旧发布说明按后来是否改写、当前文档是否覆盖分别处理 |
| R7 未知的用法 | 口径问题不写未知；字段明写和总则不同的以字段为准；词表装不下用 `vocabulary_gap`；疑似成员写进 `unresolved`，要有指向默认路径的具体出处，并对着该取值判定里的关键条件 |
| R8 一处计 | 一个机制只归一项、只在主管字段计；一个机制指同一条装载、注册或执行路径，同一份内容只是触发的一方不同的仍算一个机制；模型现写的脚本按是否接管后续多步分记，不算计划，事先写好、由框架推进的工作流定义也不算 |
| R9 单选 | 类别字段按优先规则只选一项 |
| R10 文档和实现 | 说法相反时以固定版本、所选入口能走到的实现为准；配置记录写明用快照代替所选版本时按快照编、置信度不高于中；源码默认值和发行版开关不同时以发行版为准；服务端下发的开关按本地默认值判，看不到的只是数值或型号名时机制照记 |

子维度只确认了一部分时：证明某项“有”，确认一项写一项；写“一个都没有”要照字段给的核对清单逐项判过，个别项拿不准的照填并写进 `coder_note`，有项根本没查的才写 `null` 并说明原因（`facet_rule`）。

例子一律用不点名的泛称，校验脚本会拒绝带编码轮次里工具编号的例子。编码者按判定标准判断，例子只帮助理解取值的意思。

定稿的理由和没有采纳的备选见 [`schema/definition-decisions-0.2.md`](schema/definition-decisions-0.2.md) 、[`schema/definition-decisions-0.3.md`](schema/definition-decisions-0.3.md)、[`schema/definition-decisions-0.4.md`](schema/definition-decisions-0.4.md) 、[`schema/definition-decisions-0.5.md`](schema/definition-decisions-0.5.md)、[`schema/definition-decisions-0.6.md`](schema/definition-decisions-0.6.md) 与 [`schema/definition-decisions-0.7.md`](schema/definition-decisions-0.7.md)。

另有两项建模参数不影响编码：G 组门控代价（报告建议在 0.5、0.75、1 几种情景下检验）与各组权重，留给距离计算阶段。

## 试编码的约定

- 对象：前两次是 10 个本地配置，即 A01 Claude Code、A02 Codex、A05 Kimi Code、A06 MiMo Code、A07 DeepSeek Harness、A08 OpenCode，以及对照 Pi、A17 Step Code、A10 Cline、C02 OpenClaw。第三次（按 `fields-0.4`）换了十个没参与码本修订的配置。从 `fields-0.5` 起改为分批正式编码：每批约十个配置、两位编码者，每批算一致率并请第三位读者盲审分歧，名单定下后各建一条轮次记录。
- 代表配置：当前正式版的默认安装与默认权限模式；入口取主产品形态（Claude Code、Codex 及其余终端工具用 CLI，Cline 用 VS Code 扩展，OpenClaw 用本机自托管网关）。只有预发布版的，写明所用预发布版本。
- 版本：配置记录建于 2026-10-20，2026-11-10 全部刷新到当天按官方默认安装方式装到的版本，编码都在刷新后的提交上做。编码期间工具再发新版，仍按记录里钉的提交编码。发行版落不到确切提交的（目前是 Step Code），记录里写明所用的近似提交和这层不确定。
- 编码者：码本字段由 `opus` 与 `gpt` 各自独立编码，互不可见；模型适配表由 `opus` 编一份，再由主控对照官方资料抽查。
- 分段：一位编码者把一个配置分三段编码（字段组 ABC、DEF、GHI，各 12 个字段），两位编码者用同一张任务卡 [`../pilot/coding-card.md`](../pilot/coding-card.md)。`../pilot/parts.py` 打印这一段的码本切片、检查单段结果，并把三段合并成 `codings/<编码者>/` 下的一条记录；用法见脚本开头。
- 环境前提：每份配置记录钉一组环境前提，统一取 macOS 或 Linux、在一个已有提交的 Git 仓库根目录启动、只配置官方快速开始要求的那一家凭据；账户档位、默认型号和信任提示逐个配置查证。工具没有自己的账户、快速开始让用户任选提供方时，由本研究选定一家并在记录里注明；工作目录由工具自己决定的（常驻服务的默认工作区）照实写。
- 读同样的材料：重新编码时两位编码者都不联网，只读同一份按配置记录钉的提交取下的源码快照（含官方文档导出）。第一次编码时一位在线读、一位读快照，材料不对等造成的分歧见 `../pilot/round1.md`。
- 单选字段（F02、F13、F18、F34 等）保持单选：按字段的优先规则只选一项，并存的其他机制记进子维度或 `value_note`（总则 R9）。
- 已知不存在：单选字段只在词表含“无”时可用；集合字段记为已知的空集合 `[]`。
- 私有题库汇总只能挂在 `adapters` 的 `private_bench_refs` 上，说明组合的汇总表现，不作任何字段的机制证据。

## 命令

在仓库根目录运行，只需 Python 3.10+：

```bash
python3 studies/harness-quantification/validate_data.py              # 真实数据与模板
python3 studies/harness-quantification/validate_data.py --fixtures   # 另含合成测试数据
python3 studies/harness-quantification/validate_data.py --write-templates
python3 studies/harness-quantification/compare_codings.py [--config <配置>] [--coders a,b] [--json]
python3 studies/harness-quantification/compare_codings.py --fixtures # 用合成数据演示
```

`npm run check:study` 会运行 `test_data_validation.py`，其中包括对真实目录的完整校验和模板同步检查。
