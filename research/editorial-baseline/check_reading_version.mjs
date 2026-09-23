import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const require=createRequire(import.meta.url);
// Historical script only; Playwright is not part of the default build.
const {chromium}=process.env.HARNESS_NODE_MODULES
 ? require(path.join(process.env.HARNESS_NODE_MODULES,'playwright'))
 : require('playwright');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'research/qa');fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
const errors=[];const remote=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url())});
await page.goto(pathToFileURL(path.join(root,'AI-Harness调研报告.html')).href);
await page.screenshot({path:path.join(out,'desktop-cover.png')});
const dom=await page.evaluate(()=>{
 const ids=[...document.querySelectorAll('[id]')].map(x=>x.id);
 const missing=[...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.hash);
 return{title:document.title,sections:document.querySelectorAll('.chapter').length,diagrams:document.querySelectorAll('svg').length,missingAnchors:missing,duplicateIds:ids.filter((x,i)=>ids.indexOf(x)!==i),horizontalOverflow:document.documentElement.scrollWidth>innerWidth};
});
await page.locator('#toc-search').fill('DeepSeek');
const search=await page.locator('nav a:visible').allTextContents();
await page.locator('#toc-search').fill('');
await page.locator('.diagram').first().scrollIntoViewIfNeeded();
await page.screenshot({path:path.join(out,'desktop-diagram.png')});
await page.locator('h2').filter({hasText:'5.3 写作'}).scrollIntoViewIfNeeded();
await page.screenshot({path:path.join(out,'desktop-scenarios.png')});
await page.setViewportSize({width:430,height:932});await page.evaluate(()=>scrollTo(0,0));
await page.screenshot({path:path.join(out,'mobile-cover.png')});
const mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
const overflowDetails=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,items:[...document.querySelectorAll('main *')].filter(e=>{const b=e.getBoundingClientRect();return b.right>innerWidth+1&&!e.closest('.table-scroll,.diagram')}).slice(0,14).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.slice(0,90),right:e.getBoundingClientRect().right}))}));
await page.locator('#toggle-nav').click();const mobileNav=await page.locator('nav').isVisible();
await browser.close();
const result={dom,searchResults:search,mobileOverflow,overflowDetails,mobileNav,errors,remoteRequests:remote};
fs.writeFileSync(path.join(out,'reading-version-check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
if(errors.length||dom.missingAnchors.length||dom.duplicateIds.length||dom.horizontalOverflow||mobileOverflow||!mobileNav||remote.length)process.exitCode=1;
