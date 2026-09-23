/* Build static reading pages from the same rendered chapters as the offline book. */
import fs from 'node:fs';
import path from 'node:path';
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
export const plain=s=>s.replace(/<svg[\s\S]*?<\/svg>/g,'').replace(/<[^>]*>/g,' ').replace(/&(?:amp|lt|gt|quot|#39);/g,x=>({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#39;':"'"})[x]).replace(/\s+/g,' ').trim();
const slugs=['basics','landscape','terminal-agents','coding-workspaces','personal-assistants','workflows-and-history','architecture','scenarios','models-and-costs','evaluation','methodology','references'];
const labels=['从零理解','工具全景','终端与开放代理','编辑器与托管工作台','个人助理与知识工作台','相邻路线与维护观察','架构与取舍','按场景选择','模型与成本','试用与验收','研究方法','参考资料'];
export function buildSite({root,nav,sections,book}) {
 const out=path.join(root,'read');fs.mkdirSync(out,{recursive:true});
 const assets=path.join(root,'site-assets');fs.mkdirSync(assets,{recursive:true});
 const pages=[];const chapters=[];
 for(let i=0;i<sections.length;i++) {
  const content=sections[i].replace(/^<section[^>]*>/,'').replace(/<\/section>$/,'');
  const chapter={file:`read/${slugs[i]}.html`,title:plain(nav[i].title),label:labels[i],id:nav[i].id,kind:'chapter',content,tools:[]};
  chapters.push(chapter);pages.push(chapter);
  if(!/^chapter-[3-6]$/.test(chapter.id))continue;
  chapter.kind='category';
  const blocks=[...content.matchAll(/<h2\b[^>]*>[\s\S]*?<\/h2>/g)].map(m=>{
   const key=plain(m[0]).match(/^([ABCDH]\d{2}) /)?.[1];
   return {key,heading:m[0],start:key?content.lastIndexOf(`<a id="${key.toLowerCase()}">`,m.index):m.index};
  });
  let overview=content.slice(0,blocks[0].start);
  for(let j=0;j<blocks.length;j++) {
   const block=blocks[j];const body=content.slice(block.start,blocks[j+1]?.start??content.length);
   if(!block.key){overview+=body;continue;}
   const title=plain(block.heading);
   const tool={file:`read/${block.key.toLowerCase()}.html`,id:block.key.toLowerCase(),title,label:title,kind:'tool',parent:chapter.file,content:body.replace(/<(\/?)h([234])\b/g,(_,slash,n)=>`<${slash}h${Number(n)-1}`)};
   pages.push(tool);chapter.tools.push(tool);
   const summary=plain(body.match(/<p>([\s\S]*?)<\/p>/)?.[1]||'').slice(0,115);
   overview+=`<article class="tool-card"><h2 id="browse-${tool.id}"><a href="${tool.file}">${escape(title)}</a></h2><p>${escape(summary)}${summary.length===115?'…':''}</p><a class="card-read" href="${tool.file}">阅读完整档案 →</a></article>\n`;
  }
  chapter.content=overview;
 }
 // Stable original IDs map to their new page. Keep every original anchor.
 const routes={};
 for(const p of pages)for(const m of p.content.matchAll(/\bid="([^"]+)"/g)) {
  if(routes[m[1]])throw Error('Duplicate site anchor '+m[1]);
  routes[m[1]]=p.file+'#'+m[1];
 }
 const home={file:'index.html',id:'home',title:'AI Harness 调研与选型报告',kind:'home'};
 const rel=(file,target)=>path.posix.relative(path.posix.dirname(file),target)||path.posix.basename(file);
 function links(content,p) {
  return content.replace(/href="([^"]+)"/g,(whole,href)=>{
   if(/^(?:https?:|mailto:|data:)/.test(href))return whole;
   if(href.startsWith('#')) {
    const route=routes[decodeURIComponent(href.slice(1))];
    if(!route) return whole;
    const [file,id]=route.split('#');return `href="${file===p.file?'':rel(p.file,file)}#${id}"`;
   }
   const [file,...fragment]=href.split('#');return `href="${rel(p.file,file)}${fragment.length?'#'+fragment.join('#'):''}"`;
  });
 }
 const headings=content=>[...content.matchAll(/<h([123])\b[^>]*\bid="([^"]+)"[^>]*>([\s\S]*?)<\/h\1>/g)].map(m=>({depth:+m[1],id:m[2],title:plain(m[3]),index:m.index}));
 const search=[];
 for(const p of pages) {
  const hs=headings(p.content);
  hs.forEach((h,i)=>{
   const text=plain(p.content.slice(h.index,hs[i+1]?.index??p.content.length));
   search.push({url:p.file+'#'+h.id,page:p.title,title:h.title,kind:p.kind,text});
  });
 }
 const hero=`<header class="cover"><div class="eyebrow">A field guide to AI harnesses</div><h1>理解 AI 的工作外壳，<br>再选适合你的那一个。</h1><p>从基本概念开始，看清工具的架构与取舍，再按自己的任务选择。你可以逐章阅读，也可以直接查找某个工具。</p><div class="metrics"><div class="metric"><b>55</b><span>工具档案</span></div><div class="metric"><b>40</b><span>细分场景</span></div><div class="metric"><b>120</b><span>架构与原理图</span></div><div class="metric"><b>42</b><span>公开仓库固定快照</span></div></div><p class="notice">使用 AI 辅助研究，依据公开资料和关键源码路径分析；未对所有产品与模型组合进行统一实测。</p></header>`;
 home.content=`${hero}<section class="chapter"><h2 id="start">从哪里开始？</h2><div class="entry-grid">${[['入门阅读','先读术语和工具地图，建立整体认识。','read/basics.html'],['查找工具','从分类进入，查看每种工具的完整档案。','read/landscape.html'],['按任务选型','从写代码、写作和日常工作等 40 个场景出发。','read/scenarios.html']].map(([a,b,c])=>`<a class="entry-card" href="${c}"><strong>${a} →</strong><span>${b}</span></a>`).join('')}</div><h2 id="contents">全部章节</h2><div class="chapter-list">${chapters.map((c,i)=>`<a href="${c.file}"><span>${String(i+1).padStart(2,'0')}</span><strong>${escape(c.label)}</strong>${c.tools.length?`<small>${c.tools.length} 份独立档案</small>`:''}</a>`).join('')}</div><h2 id="reading">怎样使用这份报告</h2><p>点击“搜索全站”查正文与工具；左侧目录跟随当前页的阅读位置。顶部可切换深浅模式，页尾可继续读下一页。</p><p>需要一次查找全文、离线保存或打印整份报告？打开<a href="AI-Harness调研报告.html">完整单页版</a>。下载整个仓库后，也可以离线打开本首页，使用分页与搜索。</p><p>结论请连同来源日期与研究边界阅读。<a href="read/methodology.html">查看研究方法</a> · <a href="https://github.com/ProgrammerAsahi/ai-harness-comparison">项目与纠错入口</a></p></section>`;
 const css=book.match(/<style>([\s\S]*?)<\/style>/)[1]+fs.readFileSync(path.join(root,'research/site.css'),'utf8');
 fs.writeFileSync(path.join(assets,'reading.css'),css);
 for(const [src,dest] of [['report-theme.js','theme.js'],['report-navigation.js','navigation.js'],['site.js','site.js'],['site-search.js','search.js']])fs.copyFileSync(path.join(root,'research',src),path.join(assets,dest));
 fs.writeFileSync(path.join(assets,'search-index.js'),'globalThis.HARNESS_SEARCH='+JSON.stringify(search).replaceAll('<','\\u003c')+';\n');
 fs.writeFileSync(path.join(assets,'legacy-routes.js'),'globalThis.HARNESS_ROUTES='+JSON.stringify(routes)+';\n');
 const order=[];for(const c of chapters){order.push(c,...c.tools);}
 const license=book.slice(book.indexOf('<!--'),book.indexOf('-->')+3);
 const footer=book.match(/<footer>[\s\S]*?<\/footer>/)[0];
 for(const p of [home,...pages]) {
  const isHome=p.kind==='home';const parent=chapters.find(c=>c.file===p.parent);const hs=headings(p.content);const toc=[];
  for(const h of hs){if(h.depth<3||!toc.length)toc.push({...h,children:[]});else toc.at(-1).children.push(h);}
  const localNav=toc.map((h,i)=>`<details class="nav-group" ${i<2?'open':''}><summary><a href="#${h.id}">${escape(h.title)}</a></summary><div class="nav-children">${h.children.map(c=>`<a href="#${c.id}">${escape(c.title)}</a>`).join('')}</div></details>`).join('');
  const idx=order.indexOf(p);const previous=idx>0?order[idx-1]:home;const next=order[idx+1];
  const pagination=isHome?'':`<div class="pagination" aria-label="顺序阅读"><a rel="prev" href="${rel(p.file,previous.file)}"><small>← 上一页</small>${escape(previous.label||previous.title)}</a>${next?`<a rel="next" href="${rel(p.file,next.file)}"><small>下一页 →</small>${escape(next.label||next.title)}</a>`:`<a href="${rel(p.file,'index.html')}"><small>阅读完毕</small>回到首页 →</a>`}</div>`;
  const base=isHome?'./':'../';
  const breadcrumb=`<div class="breadcrumb" aria-label="当前位置"><a href="${base}index.html">首页</a>${parent?`<span>／</span><a href="${rel(p.file,parent.file)}">${escape(parent.label)}</a>`:''}${!isHome?`<span>／</span><span>${escape(p.kind==='tool'?p.title.split('：')[0]:p.label)}</span>`:''}</div>`;
  const side=`<aside class="sidebar"><a class="brand" href="${base}index.html">HARNESS / 研究与选型</a><div class="stamp">${escape(isHome?'55 份工具档案 · 40 个任务场景':parent?.label||p.label)}</div><button type="button" class="open-search" data-open-search>搜索全站 <kbd>⌘ / Ctrl K</kbd></button><details class="site-map"><summary>全部章节</summary><div role="navigation" aria-label="全站章节">${chapters.map(c=>`<a ${c.file===(parent?.file||p.file)?'aria-current="page"':''} href="${rel(p.file,c.file)}">${escape(c.label)}</a>`).join('')}</div></details><div class="toolbar"><button id="toggle-nav" aria-expanded="false">本页目录</button></div><label class="search-label" for="toc-search">本页目录</label><input type="search" id="toc-search" placeholder="筛选本页标题" autocomplete="off"><nav aria-label="本页目录">${localNav}<p class="empty">没有匹配的本页标题。试试“搜索全站”。</p></nav><div class="nav-foot"><a href="${base}AI-Harness调研报告.html${!isHome?'#'+p.id:''}">完整单页版</a> · <button class="print" onclick="window.print()">打印本页</button><br><a href="https://github.com/ProgrammerAsahi/ai-harness-comparison">项目与纠错</a></div></aside>`;
  const dialog=`<dialog id="site-search" aria-labelledby="search-title"><div class="search-head"><h2 id="search-title">搜索全站</h2><button type="button" id="close-search" aria-label="关闭搜索">关闭 ×</button></div><label for="global-search">工具、原理或任务关键词</label><input id="global-search" type="search" placeholder="例如：Pi、小说、上下文压缩" autocomplete="off"><p id="search-status" role="status" aria-live="polite">输入关键词，搜索所有章节与工具正文。</p><ol id="search-results"></ol><noscript>搜索需要 JavaScript；也可使用首页章节入口或完整单页版的浏览器查找。</noscript></dialog>`;
  const pageContent=isHome?links(p.content,p):`<section class="chapter" data-chapter="${p.id}">${links(p.content,p)}</section>`;
  const desc=escape(isHome?'55 份 AI Harness 工具档案、40 个任务场景，理解架构、模型与取舍。':p.title+'。阅读原理、证据与实际使用方法。');
  const html=`<!doctype html>${license}<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><meta name="description" content="${desc}"><script src="${base}site-assets/theme.js"></script><title>${escape(p.title)}${!isHome?' · AI Harness 报告':''}</title><link rel="stylesheet" href="${base}site-assets/reading.css">${isHome?'<script src="site-assets/legacy-routes.js"></script>':''}</head><body id="top" class="paged-site" data-site-base="${base}">${side}<main><div class="reading-toolbar"><button class="compact-search" type="button" data-open-search>搜索全站</button><button id="theme-toggle" type="button" aria-pressed="false">☾ 深色模式</button></div>${breadcrumb}${pageContent}${pagination}${footer}</main>${dialog}<a class="to-top" href="#top">回到顶部 ↑</a><script src="${base}site-assets/search.js"></script><script src="${base}site-assets/site.js"></script><script src="${base}site-assets/navigation.js"></script></body></html>`;
  fs.writeFileSync(path.join(root,p.file),html);
 }
 const manifest={pages:[home,...pages].map(({content,tools,...p})=>p),routes,search_records:search.length};
 fs.writeFileSync(path.join(root,'research/site-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
 console.log(JSON.stringify({sitePages:pages.length+1,toolPages:pages.filter(p=>p.kind==='tool').length,searchRecords:search.length}));
}
