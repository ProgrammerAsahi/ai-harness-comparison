# StepFun 增补证据说明

本次核验：2026-09-23。原报告其他产品保留 2026-09-22 基线。

## 范围与采集

- 官方仓库：<https://github.com/stepfun-ai/Step-Code>。
- 固定提交：`adcf37b0572ff568b3fbff759f52267690c98c32`。
- GitHub 元数据抓取时 349 stars，最近推送 `2026-09-23T08:04:31Z`，未归档；不据此推断活跃用户数。
- 目录普查 1,408 个文件；按原有规则保存 635 个文档与源码文件。文件数代表采集范围，不代表逐行阅读范围。
- 官方页面输入列表：`pages-stepfun.json`；下载文本与元数据：`pages/step*.txt`、对应 JSON。Step Code 在线文档按官方索引收集，再围绕报告涉及的机制重点阅读。
- 阅读记录：`review-selection.json` 的 `step-code` 条目、`review-step-code.txt` 与 `review-log.json`。自动摘录不是完整审计证明；本次另外针对相关实现段落核读。
- 本次没有执行 Step Code 安装器、项目代码、模型请求或付费评测，也没有登录用户的 Step 账户。

## 动态发布页核验

来源：<https://www.stepfun.com/step-5-preview>。普通 HTML 抓取只得到空壳，`pages/step5-launch.txt` 的短内容不作为正文事实依据。

通过 Codex 浏览器工具读取页面实际呈现的无障碍文本，确认以下事实；这里是核对笔记，不冒充完整页面存档或带原始哈希的网页全文：

- 概览标明稀疏 MoE、600B 总参数、每 Token 激活 27B，支持 1M 上下文和视觉输入。
- 表格列出 Step 5 Preview High 的 DeepSWE v1.1 67.7%、StepCodeBench 49.0%、FrontierFinance 66.4%。
- 页面说明 DeepSWE 使用 SWE-agent；StepCodeBench 使用 avg@4，并明确标注部分内部自研评测。
- 对极难、较长的软件任务，页面承认仍有提升空间。
- 页面结尾说明目前通过产品和 API 提供，模型计划 10 月 15 日正式开放。按当前页面年份解释为 2026 年；没有将未来计划写成已完成发布。

第三方 Hugging Face 上传在搜索中出现，但本报告未将它们当作官方权重、最终许可证或可靠部署说明。没有为此下载权重。

## 冲突与边界处理

| 问题 | 对照依据 | 报告处理 |
|---|---|---|
| 默认 Provider 与网站多厂商登录说明不一致 | README；`providers/src/providers/all.ts`；网站 Platforms and models | 当前默认内置 Step；源码保留自定义模型路径。网站列出的其他登录不能按发行版实测确认 |
| 高级 workflow 是否开箱可用 | `features/workflow/registration-gate.ts`、`vm.ts` | `isolated-vm` 不可用时关闭；Bun 运行环境不能承载该原生模块。普通子代理单独判断 |
| 权限默认值 | `step/permissions.ts`；网站 Interaction | Bypass 为未被其他配置覆盖时的默认；未知分析与危险命令另外审批／拒绝 |
| 权限检查是否是系统沙箱 | SECURITY.md；command-permissions.md | 明确是工具审批，宿主进程仍在用户权限边界内 |
| 模型大窗口与终端大窗口 | 模型页；`providers/src/step-provider/index.ts` | API 规格 1M，缺失元数据时实现后备窗口 256,000；需检查账户目录 |
| 界面估算费用是否真实为零 | 同一模型适配源码 | 费用存在零值后备，以服务端计费为依据 |
| 配置文件路径版本冲突 | 较旧 compaction.md 与当前 step-configuration.md、网站 Sessions | 上手使用当前 `config.toml`，不照抄旧 settings.json |
| 目标停止与预算 | goal-lifecycle.md、orchestration-lifecycle.md | 目标由工作代理申报完成；预算口径不同且可能有在途超额，不宣称绝对费用封顶 |
| 可导入 MCP 是否包括所有认证和 Hooks | 网站 Migration、Plugins；mcp-import.ts | 按支持范围迁移、重新核对授权；不承诺全部插件行为一致 |
| 模型视频输入与终端工具 | 模型页、工具页、StepCode 输入类型 | 模型 API 支持视频；当前终端直接视频路径未验证，不泛化 |

## 价格核对

分别读取中国区和海外区定价、套餐页面，保留各自币种，不按汇率生成另一地区报价。Step-5 标准 API 依次为未缓存输入／缓存输入／输出，每百万 Token：中国区 ¥7／¥0.35／¥20，海外 US$1／US$0.05／US$2.70。推理输出也计费。

套餐表是当日官方文档标价；Credits 不等于 Token；标准 API、订阅和静态托管的渠道与额度分别处理。报告中的计算示例是明确给定用量后的算术，不是运行测得的任务成本。
