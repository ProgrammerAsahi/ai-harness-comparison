/* Local-only search, old-home anchors, and per-page navigation preferences. */
(() => {
 const base=document.body.dataset.siteBase;
 if(globalThis.HARNESS_ROUTES&&location.hash) {
  let anchor;try{anchor=decodeURIComponent(location.hash.slice(1));}catch{}
  const target=globalThis.HARNESS_ROUTES[anchor];
  if(target)location.replace(base+target);
 }
 const groups=[...document.querySelectorAll('.nav-group')];
 const storageKey='harness-nav:'+location.pathname;
 let states={};try{states=JSON.parse(sessionStorage.getItem(storageKey)||'{}')||{};}catch{}
 for(const group of groups) {
  const key=group.querySelector('summary a').getAttribute('href');
  if(typeof states[key]==='boolean')group.open=states[key];
  group.addEventListener('toggle',()=>{states[key]=group.open;try{sessionStorage.setItem(storageKey,JSON.stringify(states));}catch{}});
 }
 const dialog=document.getElementById('site-search');const input=document.getElementById('global-search');
 const list=document.getElementById('search-results');const status=document.getElementById('search-status');
 let loading;let timer;let opener;
 function loadIndex() {
  if(globalThis.HARNESS_SEARCH)return Promise.resolve();
  if(loading)return loading;
  loading=new Promise((resolve,reject)=>{
   const script=document.createElement('script');script.src=base+'site-assets/search-index.js';
   script.onload=resolve;script.onerror=()=>{script.remove();loading=null;reject(Error('load'));};document.head.append(script);
  });return loading;
 }
 async function render() {
  const query=input.value.trim();list.replaceChildren();
  if(!query){status.textContent='输入关键词，搜索所有章节与工具正文。';return;}
  status.textContent='正在准备全站搜索…';
  try{await loadIndex();}catch{if(input.value.trim()===query)status.textContent='搜索资料加载失败，请检查网络后重新输入；离线使用时请下载完整项目。';return;}
  if(input.value.trim()!==query)return;
  const result=HarnessSearch.search(globalThis.HARNESS_SEARCH,query);
  status.textContent=result.total?`找到 ${result.total} 个页面${result.total>30?'，显示前 30 个；可增加关键词缩小范围':''}。`:'没有找到匹配内容，试试工具名称或更短的关键词。';
  for(const item of result.items) {
   const li=document.createElement('li');const a=document.createElement('a');a.href=base+item.url;
   const title=document.createElement('strong');title.textContent=item.page===item.title?item.title:item.page+' · '+item.title;
   const excerpt=document.createElement('span');excerpt.textContent=HarnessSearch.snippet(item.text,query);
   a.append(title,excerpt);a.addEventListener('click',()=>dialog.close());li.append(a);list.append(li);
  }
 }
 function open(button){opener=button||document.activeElement;if(!dialog.open)dialog.showModal();input.focus();render();}
 for(const button of document.querySelectorAll('[data-open-search]'))button.addEventListener('click',()=>open(button));
 document.getElementById('close-search').addEventListener('click',()=>dialog.close());
 dialog.addEventListener('close',()=>opener?.focus());
 input.addEventListener('input',()=>{clearTimeout(timer);list.replaceChildren();timer=setTimeout(render,120);});
 input.addEventListener('keydown',event=>{if(event.key==='Enter'){const a=list.querySelector('a');if(a){event.preventDefault();a.click();}}else if(event.key==='ArrowDown'){const a=list.querySelector('a');if(a){event.preventDefault();a.focus();}}});
 document.addEventListener('keydown',event=>{if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){event.preventDefault();open();}});
})();
