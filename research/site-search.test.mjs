import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const ctx={};vm.runInNewContext(fs.readFileSync(new URL('./site-search.js',import.meta.url),'utf8'),ctx);
const {search,snippet}=ctx.HarnessSearch;
const index={};vm.runInNewContext(fs.readFileSync(new URL('../site-assets/search-index.js',import.meta.url),'utf8'),index);
const records=index.HARNESS_SEARCH;
test('empty searches do not return the entire book',()=>{assert.equal(search(records,'  ').total,0);});
test('Chinese body terms locate a relevant subsection',()=>{
 const result=search(records,'上下文 压缩');assert.ok(result.total>5);assert.ok(result.items.some(r=>r.kind==='tool'));
 for(const r of result.items)assert.match(r.page+r.title+r.text,/压缩/);
});
test('case, full-width Latin and excess whitespace normalize',()=>{
 const a=search(records,'ｃｏｄｅｘ');const b=search(records,'  CODEX  ');assert.equal(JSON.stringify(a),JSON.stringify(b));assert.match(a.items[0].url,/a02\.html#/);
});
test('matching pages are deduplicated and ranked with exact tool names first',()=>{
 const result=search(records,'Pi');assert.match(result.items[0].url,/a09\.html#/);assert.equal(new Set(result.items.map(r=>r.url.split('#')[0])).size,result.items.length);
});
test('multi-keyword queries require every token; a missing phrase returns no result',()=>{assert.equal(search(records,'不存在的测试词xyz').total,0);assert.equal(search(records,'Codex 不存在的测试词xyz').total,0);});
test('limit preserves total and snippets show matching context without markup',()=>{
 const result=search(records,'模型',3);assert.equal(result.items.length,3);assert.ok(result.total>3);
 const excerpt=snippet('前文'.repeat(100)+'目标文字'+'后文'.repeat(100),'目标文字');assert.match(excerpt,/目标文字/);assert.ok(excerpt.length<140);assert.ok(excerpt.startsWith('…'));
});
