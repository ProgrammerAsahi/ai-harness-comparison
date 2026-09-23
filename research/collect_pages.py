#!/usr/bin/env python3
"""Fetch public documentation snapshots and plain text for evidence review."""
import concurrent.futures, datetime, hashlib, html.parser, json, pathlib, re, sys, urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
class TextParser(html.parser.HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.hide=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','svg'): self.hide+=1
        if tag in ('p','div','h1','h2','h3','h4','li','tr','br','pre','section'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style','svg'): self.hide=max(0,self.hide-1)
        if tag in ('p','h1','h2','h3','li','tr','pre'): self.parts.append('\n')
    def handle_data(self,data):
        if not self.hide: self.parts.append(data)
def fetch(item):
    key,url=item
    out=ROOT/'pages'; out.mkdir(exist_ok=True)
    if (out/(key+'.json')).exists(): return {'key':key,'status':'cached'}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (harness research)'})
        with urllib.request.urlopen(req,timeout=45) as r:
            raw=r.read(); final=r.url; ct=r.headers.get('Content-Type','')
        content=raw.decode('utf-8',errors='replace')
        if 'html' in ct:
            p=TextParser(); p.feed(content); txt=re.sub(r'\n\s*\n+','\n\n',''.join(p.parts))
        else: txt=content
        (out/(key+'.txt')).write_text(txt)
        meta={'key':key,'url':url,'final_url':final,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'content_type':ct,'sha256':hashlib.sha256(raw).hexdigest(),'chars':len(txt)}
        (out/(key+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2))
        return meta
    except Exception as e: return {'key':key,'url':url,'error':str(e)}
if __name__=='__main__':
    pages=json.loads((ROOT/sys.argv[1]).read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as p:
        for row in p.map(fetch,pages.items()): print(json.dumps(row,ensure_ascii=False),flush=True)
