# 贡献与构建指南

欢迎纠正事实、改善解释或完善阅读体验。只读报告无需构建，见 [README](README.md)。

## 先选一种参与方式

- **指出问题：**提交 Issue，写明章节／工具编号、原文、建议改法与官方来源。没有修改代码的经验也可以参与。
- **改进内容：**先确认下表中的编辑入口，再改生成器及其输入，重新生成正文。
- **改进界面：**修改 HTML 生成器或目录脚本，生成 HTML 后检查相关行为。

较大的结构调整请先说明解决什么阅读问题。一个 PR 尽量解决一个明确问题；不要顺带更新全部产品版本或改变工具分类。AI 可以辅助整理，但来源和验证结果必须能复核。详细研究规则见 [AGENTS.md](AGENTS.md)。

## 提交一个改动

1. Fork 仓库并克隆自己的副本，为改动建立分支：`git switch -c docs/clarify-setup`。
2. 安装构建依赖，按下表修改真正的生成输入。不要只改生成后的 Markdown 或 HTML。
3. 运行构建和检查，查看 `git diff`，确认只有预期变化。
4. 提交源码及对应的生成产物，推送到自己的 Fork，再向本仓库 `main` 发起 PR。
5. PR 说明问题、改动、来源与已运行的检查；未能完成的验证也应写明。

新增内容按 [LICENSE](LICENSE) 中对应的许可提交；第三方材料另见 [署名与许可说明](THIRD_PARTY_NOTICES.md)。

## 干净克隆后的最小流程

需要 Python 3.10 或更新版本、Node.js 20 或更新版本，以及 npm。HTML 使用锁定版本的 `marked` 解析 Markdown。

先在终端进入克隆后的仓库根目录。以下命令面向 macOS／Linux 或 Windows WSL；Windows 原生终端需自行提供可用的 `python3` 命令，本项目尚未验证该环境。

```bash
node --version
python3 --version
npm ci --ignore-scripts
npm run build
npm run check
```

安装依赖需要网络；之后生成与常规检查可以离线运行。`HARNESS_NODE_MODULES` 可显式指定已有 Node 依赖目录，`HARNESS_NODE` 可指定构建时的 Node 可执行文件；默认使用当前项目依赖和 PATH，不依赖作者的个人目录。

`npm run build` 依次整理档案、通用章节、清单、引用、图示和 HTML。只修改阅读版样式时可以运行 `npm run build:html`。产物与源码一起提交，便于读者不安装依赖就阅读。`package.json` 的 `private: true` 用于防止误发布 npm 包，与 GitHub 仓库是否公开无关。

## 在哪里修改

| 内容 | 主要编辑入口 |
|---|---|
| 工具的原理、能力、五步上手和任务示例 | `research/profile_expansions*.py` |
| 状态、恢复与排错的深入说明 | `research/profile_deepdives.py` |
| 档案中的模型候选表 | `research/profile_models.py` |
| 档案编排和通用执行图 | `research/build_profiles.py` |
| 总览结构图 | `research/profile_diagrams.py` |
| 深层架构、模块图与局部放大图 | `research/profile_architecture.py`；证据见 `research/architecture-evidence.json` |
| 工具标识 | `report/assets/logos/`、`research/logo-sources.json`；保留官方原图和来源 |
| 深浅模式 | `research/report-theme.js`、`research/report-theme.css`；回归测试见 `report-theme.test.mjs` |
| 跨工具比较、场景、模型与成本、方法等章节 | `research/integrate_report.py`，并核对其旧稿输入 |
| 产品目录、编号与维护快照 | `research/build_inventory.py`、`research/repository-snapshot.json` |
| 来源与引用 | `research/pages-*.json`、`research/citations.json`、`research/source-manifest.json` |
| 阅读版 HTML 与通用 SVG | `research/build_report.mjs`、`research/build_figures.py` |
| 分页结构、跨页链接与首页 | `research/build_site.mjs`、`research/site.css`；与单页共用已渲染正文 |
| 全站搜索、旧首页锚点与页内状态 | `research/site.js`、`research/site-search.js` |
| 目录跟随、标题筛选和移动端菜单 | `research/report-navigation.js`；生成时内嵌到 HTML |

`research/editorial-baseline/` 是旧稿与当前生成输入。不要仅修改生成后的 Markdown，也不要直接批量改旧稿中的所有事实；先辨认相应生成器怎样组合内容，避免下一次构建覆盖修改。

## 标识与架构图的维护

- 标识只采用官网或官方仓库发布的资源，保存原始文件、来源页、采集时间和 SHA-256。厂商品牌与工具独立标识要在说明中区分；不要用 GitHub 通用图标或重绘近似图代替。图片不改色、不拉伸，深色模式也保留原图。
- `profile_architecture.py` 中每个工具都有单独的模块、连线、机制解释和任务路径。布局可以复用，机制不能套模板。新增档案须同时补齐总览、细图和证据记录；检查会验证完整覆盖、来源和连线是否穿过模块。
- 架构证据保存在 `architecture-evidence.json`，默认构建不读取网页缓存。仅在有意更新且已核对相应材料时运行 `python3 research/profile_architecture.py --freeze-evidence`；该操作需要本地来源元数据，不是日常构建步骤。
- `npm run check` 包含目录、主题、标识、架构及颜色对比检查。它们不能替代浏览器中的桌面／窄屏视觉检查；有条件时分别检查深浅模式、长标题、横向滚动与目录定位，并记录对应 HTML 哈希。

## 来源缓存与验证

`repository-snapshot.json` 记录公开仓库、固定提交和采集时间；`source-manifest.json` 记录引用文件的路径、URL、字节数及 SHA-256。它们可随 Git 分发，全文缓存不入库。

常规检查在没有缓存时核对引用与固定记录是否一致，并明确输出 `manifest_only_source_checks`。有缓存时还检查文件内容哈希，输出 `cached_source_hashes_verified`。二者都不等于重新访问官网或重新通读源码。

需要从固定提交恢复已登记的引用正文时，可运行：

```bash
# 需要网络；只下载已登记文件，不执行第三方代码
python3 research/fetch_cited_sources.py
# 也可仅恢复某个仓库的引用文件
python3 research/fetch_cited_sources.py pi
npm run check:cached-sources
```

下载结果必须与已记录的大小和哈希一致才会保存。若上游不可用或内容不符，应排查和说明，不悄悄换成最新 HEAD。只恢复部分仓库时，全量严格检查会报告其他缓存缺失，这是正常结果。

新增来源时先读取与核验材料，再登记仓库版本和引用文件哈希；不能为消除检查错误编造来源记录。`collect_repos.py` 与 `collect_pages.py` 是进行新一轮资料采集的工具，不是默认构建步骤。`build_inventory.py --refresh-local-snapshot` 会把本地完整采集元数据合并到仓库快照，只在确实更新研究范围时使用。

## 验证与提交

内容变更后执行构建和检查，查看 Git diff，确认没有无关事实、数量或日期变化。检查结果中的源码读取、静态结构和视觉验证范围要分别解释。涉及架构图或排版的改动，再按当前环境允许的方式进行视觉检查；旧的 `editorial-baseline/check_reading_version.mjs` 仅作历史留档，不属于默认检查入口。

`npm run check` 包含目录行为回归检查，也可单独运行 `npm run test:navigation`。它通过 Node 的测试运行器与模拟页面几何，检查当前项选择、长章节、上下滚动居中、多行标题与首尾边界、父组状态、搜索、窄屏菜单和脚本内嵌；不启动浏览器，也不能代替实际排版与滚动手感的视觉验收。

报告生成后若更新了验证摘要，要保证 `research/delivery-summary.json` 与当前报告和适用的 QA 记录一致。不能把没有重新完成的浏览器验收写成已完成。

提交前检查 `.gitignore` 和暂存内容，确认无凭据、依赖、下载缓存或原始会话。报告正文、作者数据、生成器和相应产物应保持一致。历史阶段与恢复依据见 [HISTORY.md](HISTORY.md)。

## 常见问题

| 现象 | 处理方式 |
|---|---|
| 找不到 `node`、`npm` 或 `python3` | 安装上述版本的运行环境，重新打开终端，先检查版本命令能否运行。 |
| `Cannot find module marked` | 在仓库根目录运行 `npm ci --ignore-scripts`，不要在 `report/` 内安装。 |
| 下载依赖失败 | 检查 npm 网络／代理配置，重试安装；不需要下载第三方研究缓存来构建。 |
| 无缓存时出现 `manifest_only_source_checks` | 这是来源记录核对的计数，不是失败；严格核验源码正文才需要恢复缓存。 |
| 修改后又被构建覆盖 | 找到对应生成器或其输入重新修改，避免直接编辑生成产物。 |
| HTML 在 GitHub 上显示代码 | 下载原始 HTML 后用浏览器打开；GitHub 文件页不是报告的交互页面。 |

构建问题请附操作系统、Node／Python 版本、执行命令和相关错误。不要提交完整环境变量或含凭据的日志。

## 在线阅读版的发布

在线地址：<https://programmerasahi.github.io/ai-harness-comparison/>。

GitHub Pages 从 `main` 分支的根目录发布；`index.html` 是分页版首页，`read/` 保存章节与工具页，`site-assets/` 保存本地共享资源；完整单页版保留原地址，`.nojekyll` 让 GitHub 直接发布静态文件。无需另外安装网站生成器或配置服务器。

更新报告时，先运行 `npm run build` 和 `npm run check`，把 `index.html`、`read/`、`site-assets/`、完整单页 HTML 与源码一起提交。合并到 `main` 后，GitHub 会自动部署已提交的文件，Pages 不会替你重新生成报告。部署状态见仓库 **Actions**，发布来源见 **Settings → Pages**。页面未更新时先确认部署成功，再刷新浏览器。

## 分页版的维护

`npm run build` 和 `npm run build:html` 同时生成两种阅读版。不要手工修改 `read/` 或 `site-assets/`；页面取自同一次 Markdown 渲染，搜索索引也从同一内容生成，不另写一份工具正文。

- 普通章节一页；四个分类页保留导读及维护说明，每份工具档案单独成页。工具地址使用稳定编号，例如 `read/a02.html`，名称变化不应改变地址。
- 保留单页中的标题 ID 与工具锚点。生成器将跨页引用重写到目标页面；旧首页锚点通过本地映射跳转，旧单页链接仍保持有效。
- 搜索按需加载本地索引，结果指向具体小节。所有页面共用深浅模式设置；目录使用现有跟随控制器，并保存各页展开状态。
- `npm run test:site` 检查搜索、加载失败重试、键盘入口和旧锚点行为；`npm run check` 另核验全部页面链接、工具正文一致性、栏目、图表数量和搜索目标。模拟交互与静态检查不能替代浏览器视觉验收。
- 删除或迁移页面时，应显式维护旧 URL；不要批量清空输出目录，以免破坏已有引用。

离线查看分页版请保留整个项目目录，直接打开 `index.html`。不需要本地服务器；单独分享一份文件时请使用完整单页 HTML。
