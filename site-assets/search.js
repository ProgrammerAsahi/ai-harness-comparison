/* Pure search functions are shared by the browser and Node regression tests. */
(() => {
 const normalize=value=>value.normalize('NFKC').toLowerCase().replace(/\s+/g,' ').trim();
 function search(records,query,limit=30) {
  const terms=normalize(query).split(' ').filter(Boolean);if(!terms.length)return {total:0,items:[]};
  const byPage=new Map();
  for(const record of records) {
   const title=normalize(record.title);const page=normalize(record.page);const body=normalize(record.text);
   if(!terms.every(t=>(page+' '+title+' '+body).includes(t)))continue;
   const score=terms.reduce((n,t)=>n+(title===t?100:0)+(title.includes(t)?20:0)+(page.includes(t)?8:0),0);
   const key=record.url.split('#')[0];const prior=byPage.get(key);
   if(!prior||score>prior.score)byPage.set(key,{...record,score});
  }
  const items=[...byPage.values()].sort((a,b)=>b.score-a.score||a.url.localeCompare(b.url));
  return {total:items.length,items:items.slice(0,limit)};
 }
 function snippet(text,query) {
  const terms=normalize(query).split(' ').filter(Boolean);const lower=normalize(text);
  const positions=terms.map(t=>lower.indexOf(t)).filter(n=>n>=0);const at=positions.length?Math.min(...positions):0;
  const start=Math.max(0,at-28);return (start?'…':'')+text.slice(start,start+135)+(text.length>start+135?'…':'');
 }
 globalThis.HarnessSearch={search,snippet};
})();
