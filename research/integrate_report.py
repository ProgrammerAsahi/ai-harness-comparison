#!/usr/bin/env python3
"""Integrate all tools into generic comparison chapters, without editorial-addition banners."""
from pathlib import Path
import re
from editorial import read_baseline
ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'research/editorial-baseline'; OUT=ROOT/'report'

architecture=r'''## 4.12 同源核心、不同产品：怎样判断继承了什么，又改变了什么

软件可以沿用同一套执行核心，再在账户、模型、权限、任务控制和交付上作出不同选择。源码血缘有助于解释结构相似，却不能直接预测当前体验。比较时先看不变的底座，再看产品层改变了哪些默认行为，最后看实际发行包启用了什么。

| 演化关系 | 可以合理预期的共同点 | 必须重新核对的部分 | 选型时的含义 |
|---|---|---|---|
| Pi → Step Code | 会话、代理循环与扩展的部分结构来源相同 | 原生 Provider、工具名称、权限默认值、子代理和高级编排 | 简洁可定制与现成产品流程是两种选择；不能由血缘推断权限相同 |
| OpenCode → MiMo Code | 可以辨认的会话与执行结构 | 模型特定工具、任务模式、记忆与检查点 | 重点比较模型与工具协同的实际方式 |
| OpenCode 相关核心 → 当前 Kilo | 会话与工具核心存在共同结构 | Kilo 账户、路由、恢复、云服务和费用 | 开放底座与商业整合可以并存，共同代码不等于同一产品 |
| Gemini CLI 历史结构 → Qwen Code | 部分设计源于相近的终端代理路线 | 当前协议、预算、子任务、沙箱与目录限制 | 分支持续演化，比较时核对当前版本的实际行为 |

上述关系分别依据各工具档案中的固定源码与官方说明；更细的实现和边界见 [A 类档案](03A-终端与开放编程代理.md)。其中 Step 的派生关系有明确[许可声明](https://github.com/stepfun-ai/Step-Code/blob/adcf37b0572ff568b3fbff759f52267690c98c32/LICENSE-STATUS.md)，MiMo 的模型适配有独立[架构文档](https://github.com/XiaomiMiMo/MiMo-Code/blob/1579e7d9ee5fca87b707c3892dc725316674a9d6/docs/architecture/codex-microkernel-runtime.en.md)。这张表用于比较结构与产品取舍；性能需要另设任务验证。

用 Pi 与 Step Code 举例：Pi 将不少工作方式留给扩展，默认没有内置的系统权限限制；Step 在派生底座上提供自己的模型入口、权限档位和任务控制，但当前默认 Bypass 仍不等于操作系统沙箱。前者需要用户自己决定更多，后者减少部分组装，又引入产品默认值与发行包差异。两者都值得研究，选择取决于你愿意自己维护哪些决定。[Pi 权限说明](https://github.com/earendil-works/pi/blob/b4588f26af2f74f7b1387b548e04a3c8d81da75b/README.md)、[Step 权限实现](https://github.com/stepfun-ai/Step-Code/blob/adcf37b0572ff568b3fbff759f52267690c98c32/packages/coding-agent/src/step/permissions.ts)

**能力存在于源码、能力被注册、能力在你的安装里可用，是三件事。** 例如某个脚本编排需要原生模块，独立二进制未必能装载；某个团队模式可能只在 CLI 开放，编辑器扩展尚不支持。Step 的 workflow 注册门控与 Cline 的团队入口差异分别展示了这两种情况。迁移时应检查实际构建、注册条件和可用入口，确认功能是否已启用。[运行环境门控](https://github.com/stepfun-ai/Step-Code/blob/adcf37b0572ff568b3fbff759f52267690c98c32/packages/coding-agent/src/features/workflow/registration-gate.ts)、[团队入口范围](https://github.com/cline/cline/blob/078f82b1e2617a6be421e34c08d35af1c3a78d87/docs/cli/agent-teams.mdx)

## 4.13 任务能保存、能继续、能交付，分别由什么保证

| 看似相近的承诺 | 实际需要的机制 | 常见误解 | 对照例子 |
|---|---|---|---|
| 记住任务 | 会话、摘要、项目文件或数据库 | 存在磁盘上就等于下一轮全部读到 | Pi 会话树、Hermes 记忆、Chatbox 上下文快照 |
| 持续推进 | 目标状态、停止条件、预算与取消 | 代理说完成就等于目标达到 | ZCode Goal Mode、Step goal、Factory 验证流程 |
| 到点执行 | 调度器与持续运行的进程／服务 | 定时记录落盘后关机也会执行 | 本机 cron 路线与 Hermes／OpenClaw 服务、n8n 流程 |
| 隔开并行工作 | 独立上下文、目录与系统边界 | 独立会话等于文件隔离，工作树等于沙箱 | 子代理、Git 工作树、容器分别解决不同问题 |
| 交付成果 | 产物保存、验证、发布或审查 | 能上传网页等于能托管完整应用 | 静态发布、PR、托管应用是不同交付范围 |

目标控制适合让当前任务继续，但完成判断仍要看实际成果。定时触发只决定何时发起；它是否能长期可靠执行，取决于电脑是否在线、服务是否恢复、失败是否重试以及重复动作怎样避免。配置一个时间表达式不能替代这些机制。各项实现依据见 [A 类](03A-终端与开放编程代理.md)、[B 类](03B-编辑器与托管工作台.md)、[C 类](03C-个人助理与知识工作台.md)和 [D 类档案](03D-相邻路线与维护观察.md)。

交付也需要分层。StepPage 可把静态目录接入托管服务；Replit 将应用环境与部署一并整合；Copilot 云端与 Jules 更接近通过代码产物进入审查。静态研究报告、带数据库的应用、准备合并的补丁，完成标准完全不同。应先选交付路径，再决定是否需要一体化平台。[静态发布范围](https://platform.stepfun.ai/docs/en/step-code/reference/steppage.md)、[Replit Agent](https://docs.replit.com/features/agent/overview.md)、[Copilot 云端](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)

更大的模型窗口与更完善的状态管理也不是互相替代。窗口解决本轮能装多少内容，检索决定装哪些，摘要帮助交接，检查点保存进度。它们配合得好，才能减少重读与遗漏；只扩大窗口可能增加重复输入，只积极压缩又可能丢掉重要条件。最终应比较同一成果需要的总调用、返工和人工检查。
'''
p=OUT/'04-架构分类与取舍.md';t=read_baseline(BASE/p.name);t=t[:t.index('## 4.12')]+architecture;p.write_text(t)

p=OUT/'05-按场景选择组合.md';t=read_baseline(BASE/p.name);t=t[:t.index('## 5.7')]
changes={
'| 03 中型功能，涉及 API、界面和测试 | Claude Code＋Sonnet 5 | Codex＋GPT-5.6 Terra／Sol |':'| 03 中型功能，涉及 API、界面和测试 | Claude Code＋Sonnet 5 | Codex＋GPT-5.6 Terra／Sol；Step Code＋Step-5-Preview |',
'| 09 只有截图，要还原网页 | Codex＋支持图像的当前 GPT | Antigravity＋Gemini 3.1 Pro |':'| 09 截图还原网页、静态原型或交互报告 | Codex＋支持图像的当前 GPT | Antigravity＋Gemini Pro；Step Code＋Step-5-Preview＋所需浏览器／静态发布工具 |',
'| 13 单元测试与回归测试补齐 | Claude Code＋Sonnet 5 | Codex＋GPT-5.6 Terra |':'| 13 单元测试与回归测试补齐 | Claude Code＋Sonnet 5 | Codex＋GPT-5.6 Terra；Step Code＋可用 Flash／旗舰作成本对照 |',
'| 28 深度行业／竞品研究 | Hermes＋强工具模型＋搜索工具 |':'| 28 深度行业／竞品研究 | Hermes＋已适配强工具模型（含可用 Step-5-Preview 路线）＋搜索工具 |',
'| 30 技术文档随代码更新 | Claude Code＋Sonnet 5 | Codex＋GPT-5.6 Terra |':'| 30 技术文档随代码更新 | Claude Code＋Sonnet 5 | Codex＋GPT-5.6 Terra；Step Code＋Step-5-Preview |'}
for a,b in changes.items():
    assert a in t,a;t=t.replace(a,b)
t=t.replace('原生工具循环省配置；先定接口','原生组合是试用起点，非实测胜负；先定接口')
t=t.replace('模型看图只是起点，还要浏览器检查、字体和响应式调整','看图、页面验证和发布是三步；静态托管不包含应用后端与数据库')
t+='''## 5.7 同一任务怎样在两个候选之间决定

先把候选缩到两三组，再选择一个真正影响工作的区别来验证。每轮保持其余条件稳定，逐项调整模型、工具、资料或环境，便于解释结果变化。

| 实际约束 | 更值得比较的路线 | 具体看什么 |
|---|---|---|
| 已有满意编辑器，只想换模型 | Cline／Kilo、OpenCode 或 ACP 宿主 | 工具往返、编辑与恢复是否稳定，原工作习惯能否保留 |
| 希望减少配置 | 模型原生组合或产品内置路由 | 第一次完整任务需多少手工准备，失败能否清楚定位 |
| 希望自己控制循环与扩展 | Pi、DSH、相关 SDK | 真正需要修改哪一层，升级后的配置维护成本 |
| 任务需跨多次会话 | MiMo、Kimi、Hermes、目标型工作方式 | 约束、失败方案和下一步能否准确恢复 |
| 要在离开电脑后继续 | Devin、Jules、云端代理或持续服务 | 执行环境、依赖、进程与结果取回是否独立于本机 |
| 重点是交出网页／报告／补丁 | 带对应验证和交付工具的组合 | 产物可用性、引用／测试、发布范围与长期运行费用 |

原生组合包括 Claude Code＋Claude、Codex＋GPT、Kimi Code＋Kimi、Step Code＋Step 等；它们适合先建立可工作的基线。已有工具的用户可先保留外壳，仅按官方支持路线增加模型。StepFun 对 OpenCode、Cline、Kilo、Hermes、Cherry 等有接入说明，但这指模型提供方给出了配置路径，不是双方对全部版本和功能的联合认证。[接入总览](https://platform.stepfun.ai/docs/en/step-plan/overview.md)

小说依然需要文风小样，严格离线依然需要正式权重与全链路本地部署，组织场景依然需要身份与权限。任何新旗舰都只是模型层的一个候选，不会自动补齐这些条件。
'''
p.write_text(t)

# Models are compared by a shared set of questions; specifications and billing
# examples are embedded in the relevant topic rather than a vendor supplement.
p=OUT/'06-模型搭配与成本.md';t=read_baseline(BASE/p.name);t=t[:t.index('## 6.8')]
t=re.sub(r'模型目录变化很快。原有型号依据 .*?这些型号用于说明当前候选，不是永久有效的安装清单。','模型目录变化很快。以下型号依据已收集的官方资料，采集时间见来源记录；这些型号用于说明候选路线，实际配置时应结合来源日期核对可用性。',t)
t=t.replace('详见 6.8','按本章规格、协议与成本核对')
t=t.replace('| OpenAI：GPT-6 Astra；GPT-5.6 Sol、Terra、Luna | Codex；官方已支持这些型号的多模型产品 | Astra 复杂长任务；Sol 深度与成品；Terra 日常；Luna 重复且易验收任务 | 这是官方定位基础上的选型顺序；所在入口不一定全部可选 |', '| OpenAI：GPT-6 Astra、Sol、Luna；过渡期仍提供 GPT-5.6 系列 | Codex；已明确支持相应型号的多模型产品 | Astra 复杂长任务；Sol 日常开发与多步工作；Luna 清楚、重复且易验收的任务 | GPT-6 Sol／Luna 正在推出；以账户和入口实际目录为准，不能由原生支持推断第三方已适配 |')
t=t.replace('### 型号名为什么容易误导', '官方目录已加入 GPT-6 Sol 和 Luna，并说明推出期间 GPT-5.6 系列仍可用。场景表中的 GPT-5.6 组合可作既有环境的对照；新用户先核对当前目录，再用同一任务比较新旧候选的效果与成本。[官方模型目录](https://learn.chatgpt.com/docs/models.md)\n\n### 型号名为什么容易误导')

t=t.replace('[Grok](https://docs.x.ai/build/settings)。','[Grok](https://docs.x.ai/build/settings)、[Step](https://platform.stepfun.ai/docs/en/guides/models/step-5-preview)。')
open_weights='''**开放状态要按型号核对。** Qwen3-Coder、gpt-oss 等已有官方模型卡的候选，与仅提供云端服务或仍在计划开放的型号不能混为一类。Step-5-Preview 的官方发布页说明产品与 API 已提供，权重计划于 2026 年 10 月 15 日开放；所收集资料没有证明官方完整权重和最终许可已可获得。第三方同名上传不替代官方发布证据。Harness 的 MIT 许可也不能自动转移给其调用的模型。[模型发布与开放计划](https://www.stepfun.com/step-5-preview)

大型 MoE 尤其不能只按活跃参数买硬件。例如 Step-5-Preview 公布约 600B 总参数、每 Token 激活 27B；全部参数按 16 bit 保存的理论原始权重约 1.2 TB，理想化 4 bit 约 300 GB，还没有算额外数据和上下文缓存。它与几十 B 的本地候选是不同的容量级别。这只是算术下限，不是实际发行包或部署承诺。[参数来源](https://www.stepfun.com/step-5-preview)

'''
t=t.replace('## 6.5 成本要按',open_weights+'## 6.5 成本要按')
billing='''### 把标价换算成任务费用

按量服务至少分未缓存输入、缓存命中输入和输出三项；订阅的 Credits 则可能另有换算规则。不同地区分别采用当地公布的价格、币种与计费规则。下面用公开价目提供一个可复算示例，**用量是演算假设，不是实测任务**，也不是跨厂商价格排名。

| 计价例子 | 未缓存输入／百万 Token | 缓存命中输入／百万 Token | 输出／百万 Token | 10 万未缓存输入＋2 万输出的模型费 |
|---|---:|---:|---:|---:|
| Step-5-Preview 中国区标准 API | ¥7 | ¥0.35 | ¥20 | `0.1×7＋0.02×20＝¥1.10` |
| 同型号海外标准 API | US$1.00 | US$0.05 | US$2.70 | `0.1×1＋0.02×2.7＝US$0.154` |

这是所引官方页面的标价，购买时重新核对。该服务的推理过程与最终回答都计入输出，首次缓存写入按未命中输入收费。工具、托管、网关和人工成本另算。换成其他模型时，沿同一公式代入其实际价格与计费定义。[中国区价目](https://platform.stepfun.com/docs/zh/guides/pricing/details.md)、[海外价目](https://platform.stepfun.ai/docs/en/guides/pricing/details.md)

### 套餐和平台额度怎样比较

| 计费形态 | 例子 | 应比较什么 | 常见误读 |
|---|---|---|---|
| Token 按量 | 官方 API 与支持的网关 | 输入、缓存、推理、输出及重试总量 | 把最终答案长度当作全部输出成本 |
| 产品档位／路由 | Cursor Auto、Amp 档位、Replit 能力路线 | 完成任务的总消费及实际提供能力 | 把档位永久绑定某个型号 |
| BYOK 加平台能力 | Qoder、Factory 等入口 | 自有模型账单与辅助能力／平台消费 | 认为自有 Key 覆盖所有功能费用 |
| Credits 套餐 | Step Plan 等额度池 | 扣除倍率、期限、加油包、可用模型与渠道 | 直接把 Credits 数量当 Token 数量 |
| 自部署 | 本地推理与自托管环境 | 硬件、并发、速度、维护与停机 | 没有 API 账单就认为没有成本 |

一个具体额度池示例：Step Plan 的 Flash Mini／Plus／Pro／Max 月额度依次为 400M／1,600M／8,000M／40,000M Credits，中国区月标价为 ¥49／99／199／699，海外为 US$6.99／9.99／29／99。Credits 是记账单位，按模型与输入输出规则换算，并非同量 Token；文档说明按月发放、未用不结转，另有加油包。购买前，用自己的任务样本估算实际扣除量，再比较套餐能覆盖多少日常工作。[中国区套餐](https://platform.stepfun.com/docs/zh/step-plan/overview.md)、[海外套餐](https://platform.stepfun.ai/docs/en/step-plan/overview.md)、[计费说明](https://platform.stepfun.ai/docs/en/step-plan/upgrade-notice.md)

上述不同形态的来源与入口边界见 [Cursor 模型](https://cursor.com/docs/models)、[Amp 档位](https://ampcode.com/docs/markdown/models-and-subagents)、[Replit 预算](https://docs.replit.com/billing/managing-spend.md)、[Qoder 自定义模型](https://docs.qoder.com/qoder/custom-models.md)、[Factory BYOK](https://docs.factory.ai/model-independence/byok.md)。模型服务与网页托管、远程工作机、发布服务又可能分开收费，最终应画出整套方案的账单路径。

'''
t=t.replace('## 6.6 订阅',billing+'## 6.6 订阅')
t+='''## 6.8 从规格表到可用能力：用同一套问题读所有模型

型号不同，真正要核对的问题相同。先区分模型本身、服务端点、Harness 适配和当前账户这四层。任何一层不支持，宣传页上的能力都未必能进入你的任务。

| 规格或能力 | 通俗解释 | 如何核对 | 不同路线中的例子 |
|---|---|---|---|
| 实际 ID 与版本 | 请求究竟交给哪个模型 | 保存服务返回、别名映射和版本 | Claude 别名、kimi-for-coding、deepseek-flash 都可能变化 |
| 上下文与最大输出 | 一次可读多少、一次最多生成多少 | 模型上限、服务配置、客户端元数据分别看 | Kimi 的档位、本地服务设置、Step 的百万窗口都需入口配合 |
| 输入模态 | 能接文字、图像还是视频 | 检查实际消息与上传路径 | Gemini／GPT／Step 的模型能力不等于每个 CLI 都有同样附件入口 |
| 推理设置 | 允许为困难问题投入多少思考 | 查该服务支持的字段、档位和计费 | 某家的 low／medium／high 不能直接替换为别家的 max |
| 工具调用 | 模型能否生成工具请求并利用结果 | 至少跑一次成功、失败、纠错和多轮往返 | 原生适配、兼容网关、本地模板的效果可能不同 |
| 结构化输出 | 能否按规定的数据形状返回 | 区分 JSON Mode 与 JSON Schema 支持范围 | 正常聊天成功不能证明严格字段与工具参数可用 |
| 缓存 | 重复输入是否按优惠规则计费 | 查看实际命中量与服务计费说明 | 稳定规则和工具前缀有帮助；摘要和路由变化会影响复用 |
| 开放与部署 | 能否取得权重、怎样合法运行 | 官方权重、许可、资源和推理服务 | 可下载的 Qwen／gpt-oss 与计划开放的型号要分开 |

以一个规格较齐全的型号示范：Step-5-Preview 的模型 ID 是 `step-5-preview`，官方列出 1M Token 上下文、64k 最大输出，支持文本／图像／视频输入与文本输出，以及工具调用、流、JSON Mode／Schema、缓存和 low／medium／high 推理档位。这些字段共同描述模型服务；其中任何一项都不能直接推导出 Step Code 或第三方客户端已完整支持。[模型规格](https://platform.stepfun.ai/docs/en/guides/models/step-5-preview)、[推理参数](https://platform.stepfun.ai/docs/en/guides/developer/reasoning.md)

同样的核对方式也适用于其他家族：Gemini 要看具体 Flash／Pro 以及服务渠道；Claude 要看直连与云供应商的模型映射；GPT 要看实际产品目录而非另一入口的选项；本地 Qwen 要看推理服务实际启动的窗口和工具模板。这些都不能只靠模型名字判断。[Gemini 目录](https://ai.google.dev/gemini-api/docs/models)、[Claude 配置](https://code.claude.com/docs/en/model-config.md)、[OpenAI 产品模型](https://learn.chatgpt.com/docs/models.md)、[Qwen 模型卡](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct/raw/main/README.md)

**客户端元数据可能成为实际瓶颈。** 例如 Step 的服务模型页写百万窗口，但 Step Code 获取元数据失败时有 256,000 的后备值；成本也有零值后备。于是“模型有大窗口”“当前会话按大窗口管理”“界面费用估算准确”是三种不同结论。自定义 Provider 和本地模型同样应核对上下文、最大输出和价格元数据。[模型发现与后备值](https://github.com/stepfun-ai/Step-Code/blob/adcf37b0572ff568b3fbff759f52267690c98c32/packages/providers/src/step-provider/index.ts)

视觉能力尤其需要端到端检查。Step 模型页列出的图片数量与视频上传方式属于服务接口限制；当前 Step Code 可确认文本与图像路径，不能因此声称所有视频都能直接送入。其他模型也有同样问题：先确认客户端确实发出了附件，再讨论模型有没有读懂。[输入限制](https://platform.stepfun.ai/docs/en/guides/models/step-5-preview)、[客户端工具](https://platform.stepfun.ai/docs/en/step-code/reference/tools.md)

## 6.9 接入路径与兼容性：模型地址、协议、账户分别配置

| 路线 | 配置责任 | 适合的起点 | 必须单独验证 |
|---|---|---|---|
| 厂商原生组合 | 产品处理主要适配与账户流程 | Claude Code＋Claude、Codex＋GPT、Kimi Code＋Kimi、Step Code＋Step | 实际账户开放、权限、版本与费用 |
| 多 Provider Harness | 用户选择服务、协议和模型 | OpenCode、Cline、Kilo、Pi、Hermes 等 | 工具、推理字段、窗口、压缩与附件 |
| 兼容 API／网关 | 服务声明兼容某协议，客户端配置端点 | OpenAI 风格或 Messages 兼容服务 | 支持的是哪个协议版本和功能子集 |
| ACP 外部代理 | 编辑器连接一个完整代理 | Zed、Neovim 插件、其他宿主 | 外部代理自己的认证、模型、工具与恢复 |
| 本地推理服务 | 用户同时管理服务端与客户端 | 开放模型加兼容 Harness | 模板、上下文、量化、资源及错误恢复 |

“官方支持”还应写明是谁的官方。以 StepFun 的接入材料为例，它列出 OpenCode、Cline、Kilo、Hermes、Cherry、DSH 和 Claude Code 等路线，证明模型提供方给出了配置办法，不等于所有客户端团队共同担保全部版本兼容。Claude Code 的 Messages 路线还注明客户端版本与窗口设置，说明仅改模型名不一定获得完整能力。[OpenCode](https://platform.stepfun.ai/docs/en/step-plan/integrations/open-code.md)、[Cline](https://platform.stepfun.ai/docs/en/step-plan/integrations/cline.md)、[Kilo](https://platform.stepfun.ai/docs/en/step-plan/integrations/kilo-code.md)、[Hermes](https://platform.stepfun.ai/docs/en/step-plan/integrations/hermes-agent.md)、[Cherry](https://platform.stepfun.ai/docs/en/step-plan/integrations/cherry-studio.md)、[DSH](https://platform.stepfun.ai/docs/en/step-plan/integrations/deepseek-harness.md)、[Messages 接入](https://platform.stepfun.ai/docs/en/step-plan/integrations/claude-code.md)

**地址会决定账单渠道。** 例如海外 Step 标准 API 使用 `https://api.stepfun.ai/v1`，Step Plan 使用 `https://api.stepfun.ai/step_plan/v1`；Messages 的相应基地址规则又不同，不能机械加 `/v1`。中国区使用对应 `.com` 服务与账户。其他模型服务同样要区分产品订阅、API 与网关，凭据和额度不能想当然通用。[渠道说明](https://platform.stepfun.ai/docs/en/step-plan/overview.md)、[Messages 接口](https://platform.stepfun.ai/docs/en/api-reference/chat/messages-create.md)

下面是 **OpenAI 风格 Chat Completions 兼容端点**的文本连通示例，不是跨协议通用客户端，也不包含 Agent 循环。需要安装 SDK、配置环境变量和开通相应服务；本报告没有实际付费运行此示例。

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["MODEL_API_KEY"],
    base_url=os.environ["MODEL_BASE_URL"],
)
reply = client.chat.completions.create(
    model=os.environ["MODEL_ID"],
    messages=[{"role": "user", "content": "说明这段代码的输入、输出与边界：……"}],
    max_tokens=4096,  # 仅适用于支持此字段的目标端点
)
print(reply.choices[0].message.content)
```

例如用 Step 海外标准 API 时，地址与 ID 分别为上述标准地址和 `step-5-preview`；其推理设置可按文档另外传入 `reasoning_effort="medium"`。换服务时必须重新核对字段；有的模型或协议并不接受同一套参数。文本连接成功后，再依次测试工具失败、纠错、附件和压缩恢复，确认完整流程可用。[接口示例与字段](https://platform.stepfun.ai/docs/en/api-reference/chat/chat-completion-create)、[推理字段](https://platform.stepfun.ai/docs/en/guides/developer/reasoning.md)

## 6.10 模型分数怎样还原成一套完整系统

| 要问的问题 | 为什么影响结论 |
|---|---|
| 用了哪个 Harness、提示与工具？ | 同模型换工具接口，可能改变任务完成率 |
| 任务是什么版本，环境怎样准备？ | 数据集、依赖与评测器会影响成功定义 |
| 单次尝试还是多次尝试统计？ | 成功率与成本需要按相同尝试次数比较 |
| 推理、步数、时间和重试预算是多少？ | 同时记录额外计算带来的效果、费用与等待时间 |
| 成绩由谁发布，能否独立复现？ | 厂商自报、内部基准与独立评测证据强度不同 |
| 与自己的任务相似吗？ | 修复软件的分数不能直接代表中文小说或管理报告质量 |

例如 Step 官方发布页给出的 DeepSWE v1.1 为 67.7%，注明采用 SWE-agent；内部 StepCodeBench 为 49.0%（avg@4），FrontierFinance 为 66.4%。这些数字能帮助理解厂商定位，却不能直接当作 Step Code 外壳胜过其他工具的证明，也不能把不同统计口径拼成总排名。[官方成绩与设置](https://www.stepfun.com/step-5-preview)

同理，mini-SWE-agent 的基准主张、IDE 厂商的任务分数和模型厂商的发布图，都需要还原为模型、工具、环境与预算组合。读者真正要选的是日常可用系统，应再用第七章的任务集验证结果、成本和人工负担。[mini 项目说明](https://github.com/SWE-agent/mini-swe-agent/blob/04d809ceab9df28f9adaed044884180159172930/README.md)、[试用与验收](07-试用迁移与验收.md)
'''
p.write_text(t)

p=OUT/'07-试用迁移与验收.md';t=read_baseline(BASE/p.name);t=t[:t.index('## 7.8')]+'''## 7.8 按能力选验收项：同一张卡适用于不同产品

下表提供待执行的试用方案，本报告未运行这些测试。按自己的需求和候选实际提供的能力选取检查项即可。

| 检查点 | 怎样验证 | 通过标准 | 适用例子 |
|---|---|---|---|
| 版本与有效权限 | 记录版本、入口、安装方式和实际生效策略，尝试受限操作 | 行为与配置一致，不靠旧默认值印象 | Claude Code、Codex、Step、Grok、IDE Agent |
| 模型和账单 | 核对实际模型 ID、地区、服务地址及服务侧用量 | 额度和计费渠道一致，界面估算与真实账单分开 | 原生订阅、BYOK、平台路由、Step Plan |
| 工具完整往返 | 读取、修改、执行检查，再故意提供一次无效输入 | 错误可解释，能够纠正，工具结果没有断链 | 所有执行型代理 |
| 多模态输入 | 使用已知内容的图片或其他支持附件 | 附件能经当前客户端完整传入，并得到符合内容的处理 | Gemini、GPT、Step 等模型与相应入口 |
| 窗口与压缩 | 核对上下文、输出限制和实际压缩行为 | 保留关键约束，不悄悄沿用旧型号窗口 | Kimi、OpenCode、Step、自定义 Provider |
| 中断与恢复 | 留下进度、失败原因和不能重复的动作，退出后继续 | 不重做有副作用的动作，能核对真实文件与外部状态 | Codex、Pi、MiMo、Hermes、目标型产品 |
| 子代理与团队 | 两个独立调查，再测试取消、目录及用量 | 状态可跟踪，权限正确，集成与总费用可解释 | Cline Teams、Factory、Qwen、Step、OmO |
| 安装包与实验能力 | 核对构建、依赖、注册和功能开关 | 能明确识别是否支持，并核对当前安装中的实际启用状态 | 原生模块、脚本编排、后台代理、ACP 后端 |
| 长期目标 | 暂停、继续、修改目标和结束 | 停止条件有效，最终成果另有检查 | ZCode、Step、任务型平台 |
| 触发与长期在线 | 停止进程、恢复服务、重复触发同一任务 | 明确是否继续、是否重试、是否重复写入 | n8n、Hermes、OpenClaw、本机定时能力 |
| 知识与记忆 | 更新一项事实，重新提问并检查来源 | 旧信息能纠正，资料不足能说明，权限范围正确 | AnythingLLM、Open WebUI、Hermes、Chatbox |
| 交付与迁出 | 打开文件、检查 PR 或测试发布样例，再导出配置 | 产物可用，退出方案清楚，托管范围符合需求 | Replit、StepPage、Copilot、桌面工作台 |

公平比较有两条路线：研究模型时尽量固定 Harness、工具和材料；研究完整产品时允许各自使用原生组合，但同时记录费用、环境和人工介入。比如在同一 OpenCode 中比较 Claude 与 Step，回答的是模型适配问题；比较 Claude Code、Step Code 与 Codex 的原生组合，回答的是整套产品是否适合工作。两类结果应分开保存。
''';p.write_text(t)

# README is maintained directly for public readers; only report chapters are generated.
p=OUT/'01-从零理解.md';t=read_baseline(BASE/p.name);t=re.sub(r'> 本报告原始观察截面.*?\n','> 建议先读本章，再看工具地图；已经有使用经验的读者，可以直接查工具档案和场景推荐。资料的采集时间与版本见参考索引。\n',t)
t=t.replace('增补条目中还会用到以下几个词：','任务控制、部署与资料处理还会用到以下词语：')
t=t.replace('| JSON Schema | 为数据规定字段、类型和格式的结构说明 | 格式合规不代表字段里的事实正确 |\n','')
extra_terms='''| Turn / Step / Run | 一次交互轮次／一次模型与工具步骤／一段被宿主管理的运行 | 一轮可有多个步骤；文字停止、工具结束与整段运行结束不是一回事 |
| Host / Core / Coordinator | 宿主／核心执行逻辑／协调器 | 分别可负责承载会话、推进任务、安排交接，实际边界要看具体工具 |
| State Machine / 状态机 | 用有限状态和转换规则管理过程 | 清楚区分排队、等待批准、执行、取消与完成，便于判断当前进度 |
| Event Bus / 事件总线 | 模块之间发布和接收事件的通信机制 | 实时通知不一定已经写入可恢复的日志 |
| Projection / 状态投影 | 从事件或历史记录重新计算某种可用视图 | 屏幕显示、运行状态和模型输入可能来自同一记录的不同视图 |
| Tool Registry / 工具契约 | 可用工具的登记表／参数与结果格式约定 | 模型看见哪些工具、怎样调用，由宿主和配置共同决定 |
| Buffer / 进程 / 副作用 | 编辑器中的未必已保存的内容／正在运行的程序／对文件或外部系统造成的实际改变 | 对话分叉通常不能复制进程，也不自动撤销文件和外部操作 |
| Embedding / 分块 / 变量池 | 把材料表示为可检索数字／把长文切成片段／保存流程步骤之间交接的数据 | 导入资料、检索证据和跨步骤传数据，是不同环节 |
| Bundle / Fan-out / Sidecar | 一组装配部件／从主任务分出子任务／伴随主任务工作的辅助组件 | 这些结构名称本身不能证明隔离、并行或长期保存能力 |
| YAML / JSONL | 常见配置格式／每行一条 JSON 记录的文件格式 | 前者常写模型与流程配置，后者常保存可追加的会话事件 |
| HTTP / RPC / IPC | 网络请求协议／远程过程调用／进程之间通信 | 界面、运行核心与服务不一定在同一个程序或机器里 |
| Base URL，服务基地址 | API 请求要发往的服务入口地址 | 地址可能决定地区、协议与计费渠道，不只是网络连通 |
| OAuth | 用户通过服务商登录并授予应用访问权的一套机制 | 登录成功不代表所有模型、工具或订阅额度都能共用 |
| JSON Mode / JSON Schema | 返回 JSON 的模式／约束字段和类型的规则 | 能输出 JSON 不保证字段、内容和事实都正确 |
| Streaming，流式返回 | 内容或事件产生一点就返回一点 | 界面看到文字，不代表工具已经执行或任务已经结束 |
| Spec / Steering | 可检查的需求设计材料／持续指导项目的规则 | 前者帮助对齐当前功能，后者保存更稳定的工作约定 |
| Plan / Build / Act | 常见的规划／构建／执行模式名称 | 名字相近不保证工具权限、审批或操作范围相同 |
| RepoMap / Repo Wiki | 仓库结构摘要／项目知识说明 | 都帮助理解项目，但来源、生成方式与更新时效不同 |
| Dry-run，预演 | 只展示将做的操作，尽量不真正修改对象 | 通过实际检查确认预演是否保持文件与外部状态不变 |
| 幂等 | 同一请求执行多次，不产生额外的重复效果 | 自动重试、重复触发和恢复任务时特别重要 |
| Schema / 序列化 | 数据结构约定／把对象转换成可传输或保存的形式 | 字段、类型和格式错了，下游模型再强也可能拿错材料 |
| 依赖图，DAG | 用连线说明哪些任务要等前面的任务完成 | 根据依赖安排先后顺序，再并行推进相互独立的任务 |
| SDK／解释器／构建依赖 | 程序开发接口／执行程序的环境／生成软件需要的部件 | 在这里主要提醒：项目环境没准备好，模型也无法正确验证 |
| Oracle / Librarian | 部分产品给推理咨询／资料调查等职责起的角色名 | 名称是产品约定，要看实际工具、上下文与权限 |
| Work / Mission / Quest | 不同产品给工作模式、成组任务或目标执行起的名称 | 不能凭同类营销词推断它们使用同一种调度和恢复机制 |
| k / M / B，bit / GB / TB | 千／百万／十亿；数字位数与存储容量单位 | 600B 参数约六千亿；Token 数、参数量与文件大小不能混用 |
'''
# Append rows without a blank line: a blank line ends the Markdown table.
glossary_end='\n\n## 一次任务究竟经过哪些地方'
assert t.count(glossary_end)==1, 'Expected a single glossary insertion boundary'
t=t.replace(glossary_end,'\n'+extra_terms+'\n## 一次任务究竟经过哪些地方')
p.write_text(t)
p=OUT/'08-方法与参考资料.md';t=read_baseline(BASE/p.name);t=t.replace('原始研究以 **2026 年 9 月 22 日** 的公开材料为时间截面，先做','本报告先做')
t=re.sub(r'\*\*9 月 23 日增补：\*\*[\s\S]*?\n\n','所有工具按相同的七个维度编排，配有责任分工图、能力表、操作步骤与任务卡。可见源码和商业公开资料的证据深度不同，图示明确区分依据；文字长度不作为审计深度或产品质量的评分。\n\n',t)
t=re.sub(r'Step 官方发布页的初始 HTML[\s\S]*?\n\n','动态页面可能需要读取实际呈现内容；网页、公开源码与发行二进制也可能不同步。报告按证据分别判断，不将抓到网页、找到源码或绘出概念图当作实际运行验证。各来源保留自己的采集时间，本报告没有将所有项目伪装成同一天全面重验。\n\n',t)
t=t.replace('Codex、OpenCode、Pi、Gemini、Qwen、Kimi、MiMo、DSH 等公开核心','Codex、OpenCode、Pi、Gemini、Qwen、Kimi、MiMo、DSH、Step 等公开核心')
t=re.sub(r'^\| Step Code／Step-5-Preview.*?\n','',t,flags=re.M)
t+='\n\n网页标题旁的标识用于识别工具，点击可查看官方来源。部分产品沿用厂商品牌或关联品牌，具体说明见[标识来源记录](../research/logo-sources.json)。标识保留原有权利，不代表厂商背书。每份档案的下一层架构图及局部放大图均有相邻证据；它们是针对关键路径的解释，不代表完整内部审计。\n'
t=t.replace('51 个编号档案的产品分类与章节映射','51 个主要编号档案的产品分类与章节映射；另有 H01—H04 四份维护观察档案')
t=t.replace('| `research/review-core*.txt`','| [profile-coverage.json](../research/profile-coverage.json) | 55 份档案的结构覆盖与篇幅记录 |\n| `research/review-core*.txt`')
p.write_text(t)
