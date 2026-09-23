import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('./site.js',import.meta.url),'utf8');
const searchSource=fs.readFileSync(new URL('./site-search.js',import.meta.url),'utf8');
class Element {
 constructor(){this.listeners={};this.children=[];this.value='';this.open=false;this.focused=false;this.textContent='';}
 addEventListener(type,fn){(this.listeners[type]||=[]).push(fn);}
 emit(type,event={}){for(const fn of this.listeners[type]||[])fn(event);}
 append(...items){this.children.push(...items);}
 replaceChildren(){this.children=[];}
 remove(){this.removed=true;}
 focus(){this.focused=true;}
 click(){this.emit('click');}
 showModal(){this.open=true;}
 close(){this.open=false;this.emit('close');}
 querySelector(selector){if(selector==='a'){return this.children.flatMap(x=>x.children).find(x=>x.tag==='a')||null;}return null;}
}
function setup({blocked=false,hash='',stored=null,routes=null,index=null}={}) {
 const elements=Object.fromEntries(['site-search','global-search','search-results','search-status','close-search'].map(k=>[k,new Element()]));
 const button=new Element();const group=new Element();group.querySelector=()=>({getAttribute:()=> '#section'});
 const document=new Element();document.body={dataset:{siteBase:'../'}};document.head=new Element();document.activeElement=button;
 document.getElementById=id=>elements[id];document.querySelectorAll=s=>s==='.nav-group'?[group]:[button];document.createElement=tag=>Object.assign(new Element(),{tag});
 const writes=[];const redirects=[];const timers=[];
 const context={document,location:{pathname:'/read/a01.html',hash,replace:x=>redirects.push(x)},sessionStorage:{getItem(){if(blocked)throw Error();return stored;},setItem(k,v){if(blocked)throw Error();writes.push([k,v]);}},setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:id=>{if(id)timers[id-1]=null;},HARNESS_ROUTES:routes,HARNESS_SEARCH:index};
 vm.createContext(context);vm.runInContext(searchSource,context);vm.runInContext(source,context);
 return {elements,button,group,document,writes,redirects,context,flush(){for(const fn of timers.splice(0))fn?.();}};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
test('known old home anchors redirect, unknown and malformed anchors stay readable',()=>{
 assert.deepEqual(setup({hash:'#a01',routes:{a01:'read/a01.html#a01'}}).redirects,['../read/a01.html#a01']);
 assert.equal(setup({hash:'#%zz',routes:{}}).redirects.length,0);assert.equal(setup({hash:'#unknown',routes:{}}).redirects.length,0);
});
test('restores group state per page, saves toggles, and tolerates unavailable storage',()=>{
 const s=setup({stored:'{"#section":true}'});assert.equal(s.group.open,true);s.group.open=false;s.group.emit('toggle');assert.match(s.writes[0][1],/false/);
 const b=setup({blocked:true});b.group.emit('toggle');b.button.click();assert.equal(b.elements['site-search'].open,true);
});
test('search opens from button or keyboard and closing restores focus',()=>{
 const s=setup();s.button.click();assert.ok(s.elements['global-search'].focused);s.elements['close-search'].click();assert.ok(s.button.focused);assert.equal(s.elements['site-search'].open,false);
 let prevented=false;s.document.emit('keydown',{ctrlKey:true,key:'k',preventDefault(){prevented=true;}});assert.ok(prevented);assert.ok(s.elements['site-search'].open);
});
test('lazy index loads once and a stale query never paints results',async()=>{
 const s=setup();const input=s.elements['global-search'];input.value='old';input.emit('input');s.flush();assert.equal(s.document.head.children.length,1);
 input.value='new';input.emit('input');s.flush();assert.equal(s.document.head.children.length,1);
 s.context.HARNESS_SEARCH=[{url:'read/a01.html#new',page:'工具',title:'new',text:'new content',kind:'tool'}];s.document.head.children[0].onload();await settle();
 assert.equal(s.elements['search-results'].children.length,1);assert.match(s.elements['search-status'].textContent,/找到 1/);assert.equal(s.elements['search-results'].querySelector('a').href,'../read/a01.html#new');
});
test('index loading failure can retry; clearing input removes stale links immediately',async()=>{
 const s=setup();const input=s.elements['global-search'];input.value='test';input.emit('input');s.flush();s.document.head.children[0].onerror();await settle();assert.match(s.elements['search-status'].textContent,/加载失败/);
 input.emit('input');s.flush();assert.equal(s.document.head.children.length,2);
 input.value='';input.emit('input');s.flush();assert.equal(s.elements['search-results'].children.length,0);assert.match(s.elements['search-status'].textContent,/输入关键词/);
});
test('results use text nodes for untrusted-looking text; Enter follows first match',async()=>{
 const s=setup({index:[{url:'read/a01.html#x',page:'test',title:'<img src=x onerror=alert(1)>',text:'test <script>text</script>'}]});s.button.click();const input=s.elements['global-search'];input.value='test';input.emit('input');s.flush();await settle();
 const a=s.elements['search-results'].querySelector('a');assert.match(a.children[0].textContent,/<img/);assert.equal(a.children[0].innerHTML,undefined);
 let clicked=false;a.addEventListener('click',()=>clicked=true);input.emit('keydown',{key:'Enter',preventDefault(){}});assert.ok(clicked);assert.equal(s.elements['site-search'].open,false);
});
