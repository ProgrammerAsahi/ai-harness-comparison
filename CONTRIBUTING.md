# 维护与构建

开始前请阅读 [AGENTS.md](AGENTS.md)。本仓库提交作者编写的材料、引用记录和可直接阅读的产物；第三方源码、网页下载、依赖与截图缓存保留在本机。

## 干净克隆后的最小流程

需要 Python 3.10 或更新版本、Node.js 20 或更新版本，以及 npm。HTML 使用锁定版本的 `marked` 解析 Markdown。

```bash
npm ci --ignore-scripts
npm run build
npm run check
```

安装依赖需要网络；之后生成与常规检查可以离线运行。`HARNESS_NODE_MODULES` 可显式指定已有 Node 依赖目录，`HARNESS_NODE` 可指定构建时的 Node 可执行文件；默认使用当前项目依赖和 PATH，不依赖作者的个人目录。

`npm run build` 依次整理档案、通用章节、清单、引用、图示和 HTML。只修改阅读版样式时可以运行 `npm run build:html`。产物与源码一起提交，便于读者不安装依赖就阅读。

## 在哪里修改

| 内容 | 主要编辑入口 |
|---|---|
| 工具的原理、能力、五步上手和任务示例 | `research/profile_expansions*.py` |
| 状态、恢复与排错的深入说明 | `research/profile_deepdives.py` |
| 档案中的模型候选表 | `research/profile_models.py` |
| 档案编排和通用执行图 | `research/build_profiles.py` |
| 不同类型的结构图 | `research/profile_diagrams.py` |
| 跨工具比较、场景、模型与成本、方法等章节 | `research/integrate_report.py`，并核对其旧稿输入 |
| 产品目录、编号与维护快照 | `research/build_inventory.py`、`research/repository-snapshot.json` |
| 来源与引用 | `research/pages-*.json`、`research/citations.json`、`research/source-manifest.json` |
| 阅读版 HTML 与通用 SVG | `research/build_report.mjs`、`research/build_figures.py` |

`research/editorial-baseline/` 是旧稿与当前生成输入。不要仅修改生成后的 Markdown，也不要直接批量改旧稿中的所有事实；先辨认相应生成器怎样组合内容，避免下一次构建覆盖修改。

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

报告生成后若更新了验证摘要，要保证 `research/delivery-summary.json` 与当前报告和适用的 QA 记录一致。不能把没有重新完成的浏览器验收写成已完成。

提交前检查 `.gitignore` 和暂存内容，确认无凭据、依赖、下载缓存或原始会话。报告正文、作者数据、生成器和相应产物应保持一致。历史阶段与恢复依据见 [HISTORY.md](HISTORY.md)。
