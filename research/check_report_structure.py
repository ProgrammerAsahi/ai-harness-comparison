#!/usr/bin/env python3
"""Static, product-neutral QA for profile completeness and the reading artifact."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
import hashlib,json,re,xml.etree.ElementTree as ET,unicodedata

ROOT=Path(__file__).resolve().parent.parent
expected=['定位与设计理念','工作原理与架构图','能力、状态与边界','从安装到完成第一个任务','典型任务与验收方法','模型搭配、适用方向与取舍','资料依据与继续阅读']
issues=[];profiles=[]
for file in sorted((ROOT/'report').glob('03*.md')):
    text=file.read_text()
    for m in re.finditer(r'^## ([ABCDH]\d{2}) (.+)\n([\s\S]*?)(?=^## |\Z)',text,re.M):
        key,title,body=m.groups()
        headings=re.findall(r'^### (.+)$',body,re.M)
        figures=re.findall(r'!\[[^\]]*\]\((figures/profiles/[^)]+)\)',body)
        tables=len(re.findall(r'^\|---',body,re.M))
        usage=body.split('### 从安装到完成第一个任务\n')[1].split('### 典型任务与验收方法\n')[0]
        steps=re.findall(r'^([1-5])\. ',re.sub(r'```[\s\S]*?```','',usage),re.M)
        codeblocks=len(re.findall(r'^```(?:bash|vim|text|python|json|yaml)',body,re.M))
        citations=len(set(re.findall(r'\]\((https?://[^)]+)\)',body)))
        if headings!=expected:issues.append(f'{key}: inconsistent section structure {headings}')
        if len(figures)!=1 or tables<2 or steps!=['1','2','3','4','5'] or not codeblocks or not citations:
            issues.append(f'{key}: missing diagram/table/steps/example/source')
        profiles.append(dict(id=key,title=title,sections=len(headings),diagrams=len(figures),tables=tables,steps=len(steps),code_blocks=codeblocks,cited_sources=citations,chinese_characters=len(re.findall('[\u4e00-\u9fff]',body))))
if len(profiles)!=55:issues.append(f'Expected 55 profiles, found {len(profiles)}')
ids=[x['id'] for x in profiles]
if len(ids)!=len(set(ids)):issues.append('Duplicate profile ID')

class Parser(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.links=[];self.assets=[];self.h2=[];self.heading=None;self.chapters=0;self.diagrams=0;self.tables=0;self.nav_links=[];self.in_nav=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='nav':self.in_nav=True
        if tag=='a' and a.get('href'):
            self.links.append(a['href'])
            if self.in_nav:self.nav_links.append(a['href'])
        if tag=='h2':self.heading={'id':a.get('id'),'text':''}
        self.chapters+=tag=='section' and a.get('class')=='chapter'
        self.diagrams+=tag=='figure' and 'diagram' in a.get('class','').split()
        self.tables+=tag=='table'
        if tag in ('img','script','iframe','source','video','audio'):
            u=a.get('src','')
            if u.startswith(('http:','https:')):self.assets.append(u)
    def handle_data(self,data):
        if self.heading is not None:self.heading['text']+=data
    def handle_endtag(self,tag):
        if tag=='nav':self.in_nav=False
        if tag=='h2' and self.heading is not None:self.h2.append(self.heading);self.heading=None

page=(ROOT/'AI-Harness调研报告.html').read_text(); parser=Parser();parser.feed(page)
duplicates=[k for k,v in Counter(parser.ids).items() if v>1]
missing=sorted(set(u for u in parser.links if u.startswith('#') and unquote(u[1:]) not in parser.ids))
for u in parser.links:
    if not u.startswith(('http:','https:','#','mailto:')) and not (ROOT/unquote(u.split('#')[0])).exists():issues.append('Missing local link '+u)
for key in ids:
    if key.lower() not in parser.ids:issues.append('Missing direct profile anchor '+key)
special=[h for h in parser.h2 if 'Step' in h['text'] and not h['text'].startswith('A17 ')]
if special:issues.append('Vendor-specific comparison headings remain')
if any(s in page for s in ['Step 新增专题','Step 专项','增补条目','9 月 23 日','09-23']):issues.append('Editorial addition banner/date remains')
if duplicates or missing or parser.assets:issues.append('Duplicate IDs, broken anchors, or remote asset dependency')
if parser.chapters!=12 or parser.diagrams!=60:issues.append('Unexpected chapter/diagram count')
if re.search(r'\{\{(?:doc|src|repo):',page):issues.append('Unresolved source reference')

svg_checks=[]
for f in sorted((ROOT/'report/figures/profiles').glob('*.svg')):
    root=ET.parse(f).getroot();title=root.find('{http://www.w3.org/2000/svg}title')
    if title is None:issues.append('Missing accessible SVG title: '+f.name)
    # Conservative estimate for the six fixed-width node labels; no browser is launched.
    for node in root.findall('{http://www.w3.org/2000/svg}text'):
        if node.attrib.get('font-size')=='15':
            width=sum(15 if unicodedata.east_asian_width(c) in 'WF' else 8.3 for c in (node.text or ''))
            if width>247:issues.append(f'{f.name}: node label may overflow ({width:.1f}px): {node.text}')
    svg_checks.append({'file':f.name,'viewBox':root.attrib.get('viewBox'),'accessible_title':title is not None})

result=dict(method='Static Markdown / HTML / SVG checks; no browser execution',profiles=len(profiles),core_profiles=sum(x['id'][0] in 'ABC' for x in profiles),adjacent_profiles=5,history_profiles=4,chapters=parser.chapters,diagrams=parser.diagrams,tables=parser.tables,profile_coverage=profiles,missing_anchors=missing,duplicate_ids=duplicates,remote_assets=parser.assets,special_vendor_headings=special,svg_checks=svg_checks,html_sha256=hashlib.sha256(page.encode()).hexdigest(),browser_visual_qa='Not performed for this revision; earlier local HTML preview was blocked by the browser URL policy. No alternate browser route used.',issues=issues)
(ROOT/'research/qa/report-structure-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('profile_coverage','svg_checks')},ensure_ascii=False,indent=2))
raise SystemExit(bool(issues))
