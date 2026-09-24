# Harness 架构量化方法研究

研究怎样用可核验的特征描述 Harness，比较架构差异，并进一步分析场景选型与「Harness × 模型」组合。

**[在线阅读 →](https://programmerasahi.github.io/ai-harness-comparison/studies/harness-quantification/)** · [Markdown 正文](report.md) · [返回项目](../../README.md)

报告含术语表、40 个相关项目／研究／规范条目、九组 36 个候选字段、距离与权重方法、未知信息处理、可视化建议和组合实验设计。引用与阅读范围见正文末尾；完整采集记录见 [sources.json](sources.json)。这些条目包括研究论文和方法库，不是 40 个同类商业产品。

## 阅读与复算

只读报告无需安装依赖。下载本目录的 `index.html` 后可直接在浏览器打开；正文、图示、数学公式及字体、样式、主题和目录脚本均已内嵌。外部参考资料仍需联网，数据及源码链接需要下载整个仓库后使用。

计算示例全部为虚构数据，**没有对真实 Harness 或模型打分**。在仓库根目录运行，只需 Python 3.10+：

```bash
python3 studies/harness-quantification/calculate_examples.py
python3 -m unittest discover -s studies/harness-quantification -p 'test_*.py' -v
```

第一条命令重建 [examples.json](examples.json)，包括四字段 Gower 示例、缺失值造成的三角不等式反例、摆幅赋权和组合实验数量。第二条检查手算结果、未知状态、对称性、权重缩放、组预算、上下界和非法输入。

示例实现刻意只支持固定适用字段集，不处理真实产品采集、条件分支、插补、聚类或模型实验。它不能直接充当完整评分系统。

## 修改与构建

需要 Node.js 20+ 与 Python 3.10+。从仓库根目录执行：

```bash
npm ci --ignore-scripts
npm run build:study
npm run check:study
```

安装依赖后，构建与常规检查均可离线执行。检查包括 Markdown 标记、字段表、公式及内嵌字体、计算示例和页面链接。整个过程只生成和核查报告文件。

| 要改什么 | 编辑入口 |
|---|---|
| 正文 | 本目录 `report.md`，末尾 `REFERENCES:GENERATED` 标记前为人工维护内容 |
| 来源与阅读范围 | 本目录 `sources.json`；新增来源前核验一手材料 |
| 图示 | `research/build_quantification_figures.py` |
| HTML 与样式 | `research/build_quantification.mjs`、`research/quantification.css` |
| Markdown 与公式解析 | `research/quantification-markdown.mjs`；行内用 `$…$`，独立公式用前后各占一行的 `$$` |
| 计算示例 | 本目录 `calculate_examples.py`、`test_examples.py` |

参考资料列表由来源表与正文引用共同生成，不单独修改。修改后提交正文、生成器和对应 SVG／HTML／JSON 产物。`npm run build` 与 `npm run check` 也已包含本研究报告。

## 证据与检查边界

来源表区分原文取得、浏览工具摘录和仅索引摘要；下载并不等于全文阅读。第三方全文缓存位于已忽略的 `research/pages/quantification/`，不随 Git 分发。普通检查核对记录；本地有缓存时同时核对哈希，但不会悄悄重新抓取最新版。

[validation.json](validation.json) 关联本次 HTML 哈希，记录文件结构、计算示例复算与图示检查范围；单元测试由上面的检查命令另行执行。[六幅 SVG 的视觉记录](diagram-visual-check.json)只覆盖独立图示。静态检查不能证明浏览器排版或所有外部链接始终可用。

没有进行产品运行、模型兼容性或任务表现测试。36 个字段仍是候选码本，尚未完成对主报告所有工具的试编码和覆盖验证。

正文与原创图示 CC BY 4.0，程序代码 MIT，第三方材料保留原权利；完整范围见 [LICENSE](../../LICENSE)。
