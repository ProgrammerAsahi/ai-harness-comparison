#!/usr/bin/env python3
import json,pathlib,re,sys,urllib.request,hashlib,datetime
R=pathlib.Path(__file__).resolve().parent
spec=json.loads((R/'review-selection.json').read_text())
names=sys.argv[1:]
logfile=R/'review-log.json'
log=json.loads(logfile.read_text()) if logfile.exists() else []
for repo,paths in spec.items():
 if names and repo not in names:continue
 manifest=json.loads((R/'repos'/repo/'manifest.json').read_text())
 for path in paths:
  p=R/'repos'/repo/'files'/path
  url=f"https://github.com/{manifest['repo']}/blob/{manifest['sha']}/{path}"
  if not p.exists():
   try:
    raw=f"https://raw.githubusercontent.com/{manifest['repo']}/{manifest['sha']}/{path}"
    data=urllib.request.urlopen(raw,timeout=30).read();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   except Exception as e: print('MISSING',repo,path,str(e));continue
  t=p.read_text(errors='replace');lines=t.splitlines()
  isdoc=p.suffix in ['.md','.mdx']
  limit=100 if isdoc else 65
  indices=list(range(min(len(lines),limit)))
  terms=r'while |async .*run|async .*execute|async .*step|def .*loop|fn .*run|fn .*execute|def .*memory|function.*compact|class .*Agent|snapshot|checkpoint|sandbox|permission|context window|subagent|provider'
  for i,line in enumerate(lines):
   if i>=limit and re.search(terms,line,re.I):
    indices.extend(range(max(limit,i-1),min(len(lines),i+3)))
    if len(set(indices))>150:break
  indices=sorted(set(indices));print('\n### '+repo+'/'+path+' ('+str(len(lines))+' lines)')
  print('\n'.join(str(i+1)+': '+lines[i] for i in indices)[:10500])
  entry={'repo':repo,'path':path,'url':url,'lines':len(lines),'review':'targeted excerpts and structure','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  log=[x for x in log if (x['repo'],x['path'])!=(repo,path)]+[entry]
logfile.write_text(json.dumps(log,ensure_ascii=False,indent=2))
