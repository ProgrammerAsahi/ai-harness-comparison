# AI Harness 调研与选型报告

一份面向中文读者的 AI 工具研究报告：解释 Claude Code、Codex、OpenCode 等工具怎样把大模型变成能执行任务的代理，以及如何按自己的任务选择工具与模型。

**[在线阅读完整报告 →](https://programmerasahi.github.io/ai-harness-comparison/)**

覆盖 **55 份工具档案、40 个任务场景、60 幅架构与原理图**。内容包括工作原理、上手路线、模型搭配、成本和验收方法，适合从头阅读，也适合按需查阅。

本项目使用 AI 辅助研究、编写与维护。结论依据公开资料和部分核心代码路径，未对所有产品或模型组合进行统一实测；型号、价格和维护状态应连同来源日期阅读。研究范围见[方法与证据边界](report/08-方法与参考资料.md)。

## 开始阅读

**只看报告，不需要安装 Python、Node.js 或任何 AI 工具。**

- **在线交互版（推荐）：**[直接打开报告](https://programmerasahi.github.io/ai-harness-comparison/)，无需下载，支持目录搜索和阅读位置跟随。
- **GitHub 文字版：**从下方章节目录进入，Markdown 正文和图表可直接查看。
- **离线交互版：**打开 [HTML 文件](AI-Harness调研报告.html)，点击文件页的 **Download raw file（下载原始文件）**，再用浏览器打开下载的文件。不要把 GitHub 文件展示页另存为报告。
- **下载整个项目：**仓库首页选择 **Code → Download ZIP**，解压后打开根目录的 `AI-Harness调研报告.html`。这样也能访问报告旁的来源记录和文档。

HTML 内含全部章节、图示和脚本，可离线阅读。左侧目录支持标题搜索和阅读位置跟随；全文搜索使用 `Ctrl+F`（macOS：`⌘F`），侧栏底部可打印或另存为 PDF。单独下载 HTML 时，报告外的研究文件需要联网查看仓库或下载完整项目。

## 按需查阅

| 想解决的问题 | 阅读入口 |
|---|---|
| Harness、Agent、上下文到底是什么？ | [01 从零理解](report/01-从零理解.md) |
| 有哪些值得了解的工具？ | [02 全景清单与维护状态](report/02-全景清单.md) |
| 终端和开放编程代理怎样选？ | [03A Claude Code、Codex、Pi 等](report/03A-终端与开放编程代理.md) |
| 编辑器、云端开发和托管工作台怎样选？ | [03B Cursor、Zed 与托管工作台](report/03B-编辑器与托管工作台.md) |
| 个人助理、聊天和知识库怎样选？ | [03C Hermes、Chatbox、Open WebUI 等](report/03C-个人助理与知识工作台.md) |
| 工作流、研究框架和旧项目有什么区别？ | [03D 相邻路线与维护观察](report/03D-相邻路线与维护观察.md) |
| 各种架构的收益和代价是什么？ | [04 架构分类与取舍](report/04-架构分类与取舍.md) |
| 我的具体任务适合哪种组合？ | [05 按 40 个细分场景选型](report/05-按场景选择组合.md) |
| 怎样选模型、控制预算、考虑本地部署？ | [06 模型搭配与成本](report/06-模型搭配与成本.md) |
| 怎样试用、迁移并判断任务完成？ | [07 试用迁移与验收](report/07-试用迁移与验收.md) · [评估记录模板](templates/选型评估记录.csv) |
| 结论从哪里来，有哪些未验证项？ | [08 研究方法](report/08-方法与参考资料.md) · [来源索引](report/参考资料索引.md) |

55 份档案包括 46 个核心工具／产品家族、5 个相邻项目和 4 个维护观察条目。每份档案按同样七个部分组织；收录不代表推荐，篇幅不代表成熟度或实测质量。

## 纠错与参与

发现事实过时、命令不准确或链接失效，请[提交 Issue](https://github.com/ProgrammerAsahi/ai-harness-comparison/issues/new/choose)，提供**章节位置、原文、建议改法和官方来源**。界面问题请附浏览器、窗口宽度和复现步骤；不要上传密钥或含私人信息的截图。

欢迎提交小范围、可核查的改进。正文大多由脚本生成，修改前请看[贡献与构建指南](CONTRIBUTING.md)，避免下次构建覆盖改动。使用 AI 协作时，还应阅读 [AGENTS.md](AGENTS.md)。

## 本地构建

仅修改报告或页面时需要。准备 Git、**Node.js 20+（含 npm）**、**Python 3.10+**。在 macOS／Linux 或 Windows WSL 终端运行：

```bash
git clone https://github.com/ProgrammerAsahi/ai-harness-comparison.git
cd ai-harness-comparison
npm ci --ignore-scripts
npm run build
npm run check
```

成功后，打开根目录的 `AI-Harness调研报告.html`。依赖安装需要网络，后续构建与常规检查可离线运行；无需模型 API Key，也不会安装或运行报告中研究的工具。

常见问题、编辑入口和可选来源核验见[贡献与构建指南](CONTRIBUTING.md)。研究记录说明见 [research](research/研究材料说明.md)，历史恢复依据见 [HISTORY.md](HISTORY.md)。

## 许可与引用

报告正文与原创图表采用 **CC BY 4.0**，构建和交互代码采用 **MIT**；第三方材料保留其原有权利。具体范围见 [LICENSE](LICENSE)，第三方说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

引用建议：**ProgrammerAsahi，《AI Harness 调研与选型报告》，仓库链接，所引用的提交 SHA 或标签**。转载或改编正文时请保留署名、许可链接，并说明是否修改。
