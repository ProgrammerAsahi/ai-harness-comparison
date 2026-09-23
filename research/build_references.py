#!/usr/bin/env python3
import pathlib,re,csv,json,collections
ROOT=pathlib.Path(__file__).resolve().parent.parent
R=ROOT/'research'
refs={}
for p in sorted((ROOT/'report').glob('*.md')):
 if p.name=='参考资料索引.md':continue
 for label,url in re.findall(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',p.read_text()):
  r=refs.setdefault(url,{'url':url,'labels':set(),'chapters':set()});r['labels'].add(label);r['chapters'].add(p.name)
rows=[{'url':u,'labels':' / '.join(sorted(x['labels'])),'chapters':' / '.join(sorted(x['chapters']))} for u,x in sorted(refs.items())]
with (R/'external-references.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['url','labels','chapters']);w.writeheader();w.writerows(rows)
cit=json.loads((R/'citations.json').read_text());byurl={x['url']:x for x in cit}
repo_meta=json.loads((R/'repository-snapshot.json').read_text())
repo_map={x['id']:x for x in repo_meta}
groups=collections.defaultdict(list);docs=[]
for u,x in refs.items():
 c=byurl.get(u)
 if c and c['kind']=='pinned-source':groups[c['key']].append(c)
 else:docs.append((u,x))
out=['# 参考资料索引\n\n资料时间与版本按各来源记录。正文中的具体事实优先链接相应源码或官方页面；这里提供集中查阅入口。星数与提交详情另见[仓库快照](../research/repository-snapshot.csv)。本表不表示全部来源已逐行阅读，研究边界见[方法说明](08-方法与参考资料.md)。\n\n## 一、固定提交的源码与仓库内文档\n']
for k,items in sorted(groups.items()):
 m=repo_map[k];out.append(f"\n### {m['repository']}\n\n固定提交：`{m['sha']}`；采集时间见[仓库快照](../research/repository-snapshot.csv)。\n\n")
 for x in sorted(items,key=lambda x:x['path']):out.append(f"- [{x['path']}]({x['url']})\n")
out.append('\n## 二、官方网页与项目入口\n\n以下包括正文参考和全景表的官方入口；网页可能持续更新。\n\n| 来源 | 使用章节 |\n|---|---|\n')
for u,x in sorted(docs,key=lambda v:v[0]):
 label=' / '.join(sorted(x['labels']));chap='、'.join(n.split('-')[0] for n in sorted(x['chapters']))
 out.append(f'| [{label}]({u}) | {chap} |\n')
out.append('\n## 三、机器可读来源记录\n\n[全部正文外链](../research/external-references.csv)；[固定引用记录](../research/citations.csv)；[产品清单](../research/catalog.json)。\n')
(ROOT/'report/参考资料索引.md').write_text(''.join(out))
print('external sources',len(refs),'pinned source files',sum(map(len,groups.values())))
