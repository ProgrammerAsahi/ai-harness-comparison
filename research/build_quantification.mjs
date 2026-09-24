// MIT. Build the independent methodology study; no network or model calls.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dir = path.join(root, 'studies/harness-quantification');
const require = createRequire(import.meta.url);
const { marked } = process.env.HARNESS_NODE_MODULES
  ? require(path.join(process.env.HARNESS_NODE_MODULES, 'marked')) : require('marked');
const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const sha = value => createHash('sha256').update(value).digest('hex');
const sourceData = JSON.parse(fs.readFileSync(path.join(dir, 'sources.json'), 'utf8'));
let markdown = fs.readFileSync(path.join(dir, 'report.md'), 'utf8').split('<!-- REFERENCES:GENERATED -->')[0];
const cited = new Set([...markdown.matchAll(/\[(S\d{2})\]/g)].map(match => match[1]));
const sources = sourceData.sources.filter(source => cited.has(source.id));
for (const id of cited) if (!sources.find(source => source.id === id)) throw Error(`Unregistered reference ${id}`);
markdown += '<!-- REFERENCES:GENERATED -->\n\n';
markdown += `本正文引用 ${sources.length} 项来源记录；同一项目的论文、仓库和规范可能分别登记，不能把来源数当成独立项目数。完整采集表另含仅供发现与继续阅读的记录。\n\n`;
markdown += sources.map(s => `- **${s.id}** — [${s.title}](${s.url})。阅读范围：${s.reading_scope}。${s.commit ? ` 固定提交：\`${s.commit}\`。` : ''}`).join('\n\n') + '\n\n';
markdown += '综合指标研究还可从 [OECD 方法手册的官方出版页](https://www.oecd.org/en/publications/handbook-on-constructing-composite-indicators-methodology-and-user-guide_9789264043466-en.html) 继续查找。该条仅核验出版元数据；来源表中的 R proxy 手册仅下载留作线索，未用于本文论证。\n\n';
markdown += sources.map(s => `[${s.id}]: ${s.url}`).join('\n') + '\n';
fs.writeFileSync(path.join(dir, 'report.md'), markdown);

let index = 0;
const chapters = [];
let current = null;
const renderer = new marked.Renderer();
renderer.heading = function(token) {
  const id = `study-h${++index}`;
  const text = token.text.replace(/[*`]/g, '');
  if (token.depth === 2) {
    current = { id, title: text, children: [] };
    chapters.push(current);
  } else if (token.depth === 3 && current) current.children.push({ id, title: text });
  const prefix = token.depth === 2 ? (chapters.length > 1 ? '</section>' : '') + '<section class="chapter">' : '';
  return `${prefix}<h${token.depth} id="${id}">${this.parser.parseInline(token.tokens)}</h${token.depth}>\n`;
};
renderer.image = function(token) {
  if (!/^figures\/[\w-]+\.svg$/.test(token.href)) throw Error(`Unexpected image ${token.href}`);
  const svg = fs.readFileSync(path.join(dir, token.href), 'utf8');
  return `<figure class="diagram" tabindex="0">${svg}<figcaption>${escape(token.text)}。原创方法示意，涉及数值均为虚构。</figcaption></figure>`;
};
renderer.paragraph = function(token) {
  const body = this.parser.parseInline(token.tokens);
  return token.tokens.length === 1 && token.tokens[0].type === 'image' ? `${body}\n` : `<p>${body}</p>\n`;
};
const tokens = marked.lexer(markdown);
marked.walkTokens(tokens, token => {
  if (token.type === 'paragraph' && /^\s*\|[^\n]+\|\s*$/m.test(token.text)) throw Error(`Unrendered table: ${token.text.slice(0, 90)}`);
});
let body = marked.parser(tokens, { renderer, gfm: true }) + '</section>';
body = body.replaceAll('<table>', '<div class="table-scroll" tabindex="0"><table>').replaceAll('</table>', '</table></div>');
const toc = chapters.map((c, i) => `<details class="nav-group" ${i < 2 ? 'open' : ''}><summary><a href="#${c.id}">${escape(c.title)}</a></summary><div class="nav-children">${c.children.map(h => `<a href="#${h.id}">${escape(h.title)}</a>`).join('')}</div></details>`).join('');
const css = fs.readFileSync(path.join(root, 'research/quantification.css'), 'utf8');
const theme = fs.readFileSync(path.join(root, 'research/report-theme.js'), 'utf8');
const navigation = fs.readFileSync(path.join(root, 'research/report-navigation.js'), 'utf8');
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="AI Harness 架构量化方法研究：混合特征、Gower 差异、未知证据、权重、可视化和 Harness 与模型的联合评估。">
<title>把 AI Harness 变成可比较的数据｜方法研究</title><script>${theme}</script><style>${css}</style></head>
<body><a class="skip" href="#content">跳到正文</a>
<button id="toggle-nav" aria-expanded="false" aria-controls="study-sidebar">☰ 章节目录</button>
<aside class="sidebar" id="study-sidebar"><a class="brand" href="../../index.html">HARNESS / 方法研究</a><p class="sidebar-note">从证据到比较，而不是从印象到分数</p>
<label for="toc-search">查找本报告标题</label><input id="toc-search" type="search" placeholder="例如：未知、权重、模型">
<nav aria-label="报告章节">${toc}<p class="empty">没有匹配标题</p></nav><p class="sidebar-note">目录筛选只查标题；全文查找请用 Ctrl+F／⌘F。</p></aside>
<main id="content"><div class="toolbar"><a href="../../index.html">← 工具调研主报告</a><button type="button" id="theme-toggle">切换主题</button></div>${body}
<footer>ProgrammerAsahi · 正文与原创图示 <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>；程序代码 MIT。第三方材料保留原有权利。<br><a href="https://github.com/ProgrammerAsahi/ai-harness-comparison">项目仓库</a> · <a href="README.md">复算与维护说明</a></footer></main>
<script>${navigation}</script></body></html>\n`;
fs.writeFileSync(path.join(dir, 'index.html'), html);
const manifest = {
  scope: 'Independent methodology study; synthetic calculations, no product or model execution',
  markdown_sha256: sha(markdown), html_sha256: sha(html), sources_sha256: sha(fs.readFileSync(path.join(dir, 'sources.json'))),
  chapter_count: chapters.length, cited_source_count: sources.length,
  related_catalog_entries: [...markdown.matchAll(/^\*\*\d{2}｜/gm)].length,
  figures: fs.readdirSync(path.join(dir, 'figures')).filter(f => f.endsWith('.svg')).sort().map(file => ({ file, sha256: sha(fs.readFileSync(path.join(dir, 'figures', file))) })),
  shared_scripts: ['report-theme.js', 'report-navigation.js'].map(file => ({ file, sha256: sha(fs.readFileSync(path.join(root, 'research', file))) })),
};
fs.writeFileSync(path.join(dir, 'build-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(`Built methodology study: ${chapters.length} chapters, ${sources.length} cited sources, ${manifest.figures.length} original figures`);
