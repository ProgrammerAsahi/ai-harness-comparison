#!/usr/bin/env python3
"""Resolve report citations against the captured public-source snapshot."""
import pathlib,json,re,csv
ROOT=pathlib.Path(__file__).resolve().parent.parent
R=ROOT/'research'
refs={}
for p in R.glob('pages-*.json'):
 refs.update(json.loads(p.read_text()))
citations=[]
def resolve(match):
 kind,key,*tail=match.group(1).split(':',2)
 if kind=='doc':
  meta=R/'pages'/f'{key}.json'
  url=json.loads(meta.read_text()).get('final_url',refs[key]) if meta.exists() else refs[key]
  citations.append({'kind':'official-document','key':key,'path':'','url':url})
  return url
 m=json.loads((R/'repos'/key/'manifest.json').read_text())
 url='https://github.com/'+m['repo']
 if kind=='src':
  path=tail[0]
  if not (R/'repos'/key/'files'/path).exists():raise ValueError('Missing cited source: '+key+'/'+path)
  url+='/blob/'+m['sha']+'/'+path
  citations.append({'kind':'pinned-source','key':key,'path':path,'url':url})
 else:citations.append({'kind':'repository','key':key,'path':'','url':url})
 return url
for p in sorted((ROOT/'report').glob('*.md')):
 t=p.read_text();t=re.sub(r'\{\{((?:src|repo|doc):[^}]+)\}\}',resolve,t);p.write_text(t)
old=R/'citations.json'
if old.exists():citations+=json.loads(old.read_text())
citations=list({(x['kind'],x['url']):x for x in citations}.values())
old.write_text(json.dumps(citations,ensure_ascii=False,indent=2))
with (R/'citations.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['kind','key','path','url']);w.writeheader();w.writerows(citations)
print('Resolved citation records:',len(citations))
