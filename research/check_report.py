#!/usr/bin/env python3
import pathlib,re,json,urllib.parse,collections
ROOT=pathlib.Path(__file__).resolve().parent.parent
issues=[];checked=0
files=[ROOT/'README.md',*sorted((ROOT/'report').glob('*.md'))]
for p in files:
 t=p.read_text()
 if '{{doc:' in t or '{{src:' in t or '{{repo:' in t:issues.append(str(p)+': unresolved source')
 if t.count('```')%2:issues.append(str(p)+': unclosed code fence')
 for label,url in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',t):
  if url.startswith(('http://','https://','#','mailto:')):continue
  target=(p.parent/urllib.parse.unquote(url.split('#')[0])).resolve();checked+=1
  if not target.exists():issues.append(f'{p.name}: missing {url}')
 ids=re.findall(r'^## ([ABCD]\d{2}) ',t,re.M)
 if len(ids)!=len(set(ids)):issues.append(p.name+': duplicate product ids')
alltext='\n'.join(p.read_text() for p in files)
ids=re.findall(r'^## ([ABC]\d{2}) ',alltext,re.M)
scenario_text=(ROOT/'report/05-按场景选择组合.md').read_text()
scenes=re.findall(r'^\| (\d{2}) ',scenario_text,re.M)
expected_core=sum(x['id'][0] in 'ABC' for x in json.loads((ROOT/'research/catalog.json').read_text()))
if len(ids)!=expected_core:issues.append(f'Expected {expected_core} core profiles, got {len(ids)}')
if len(scenes)!=40 or len(set(scenes))!=40:issues.append(f'Expected 40 scenarios, got {len(scenes)}')
refs=json.loads((ROOT/'research/citations.json').read_text());source_count=0
for r in refs:
 if r['kind']=='pinned-source':
  source_count+=1
  if not (ROOT/'research/repos'/r['key']/'files'/r['path']).exists():issues.append('Missing source '+r['url'])
metrics={'markdown_files':len(files),'core_profiles':len(ids),'scenarios':len(scenes),'local_links_checked':checked,'cited_source_files':source_count,'chinese_characters':len(re.findall(r'[\u4e00-\u9fff]',alltext)),'issues':issues}
(ROOT/'research/report-check.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2))
print(json.dumps(metrics,ensure_ascii=False,indent=2));raise SystemExit(bool(issues))
