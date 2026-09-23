import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const script=fs.readFileSync(new URL('./report-theme.js',import.meta.url),'utf8');
function setup({system=false,stored=null,blocked=false}={}){
 const listeners={};const root={dataset:{},style:{}};const attrs={};const buttons={};let storage=stored;
 const button={textContent:'',setAttribute:(k,v)=>attrs[k]=v,addEventListener:(k,v)=>buttons[k]=v};
 const media={matches:system,addEventListener:(k,v)=>listeners.media=v};
 const document={documentElement:root,addEventListener:(k,v)=>listeners[k]=v,getElementById:id=>id==='theme-toggle'?button:null};
 const localStorage={getItem:()=>{if(blocked)throw Error('denied');return storage;},setItem:(k,v)=>{assert.equal(k,'harness-report-theme');if(blocked)throw Error('denied');storage=v;}};
 vm.runInNewContext(script,{document,window:{matchMedia:()=>media},localStorage});
 return {root,attrs,button,ready:()=>listeners.DOMContentLoaded(),click:()=>buttons.click(),system:value=>listeners.media({matches:value}),stored:()=>storage};
}
test('first visit applies system theme before DOM is ready',()=>{
 for(const system of [false,true])assert.equal(setup({system}).root.dataset.theme,system?'dark':'light');
});
test('saved preference overrides system; invalid storage is ignored',()=>{
 assert.equal(setup({system:true,stored:'light'}).root.dataset.theme,'light');
 assert.equal(setup({system:false,stored:'dark'}).root.dataset.theme,'dark');
 assert.equal(setup({system:true,stored:'sepia'}).root.dataset.theme,'dark');
});
test('toggle persists, updates color scheme, label and pressed state both ways',()=>{
 const s=setup();s.ready();s.click();assert.equal(s.stored(),'dark');assert.equal(s.root.style.colorScheme,'dark');assert.equal(s.attrs['aria-pressed'],'true');assert.match(s.button.textContent,/浅色/);
 s.click();assert.equal(s.stored(),'light');assert.equal(s.attrs['aria-pressed'],'false');assert.equal(s.attrs['aria-label'],'切换到深色模式');
});
test('blocked local storage does not break loading or repeated toggles',()=>{
 const s=setup({blocked:true,system:true});s.ready();s.click();assert.equal(s.root.dataset.theme,'light');s.click();assert.equal(s.root.dataset.theme,'dark');
});
test('system changes follow only until the reader chooses explicitly',()=>{
 const s=setup();s.ready();s.system(true);assert.equal(s.root.dataset.theme,'dark');s.click();s.system(true);assert.equal(s.root.dataset.theme,'light');
});
test('published HTML contains the exact controller early in head and one accessible button',()=>{
 const html=fs.readFileSync(new URL('../AI-Harness调研报告.html',import.meta.url),'utf8');
 assert.ok(html.includes(`<script>${script}</script>`));assert.ok(html.indexOf(script)<html.indexOf('<body'));
 assert.equal((html.match(/id="theme-toggle"/g)||[]).length,1);
 assert.match(html,/<button id="theme-toggle" type="button" aria-pressed="false">/);
});
