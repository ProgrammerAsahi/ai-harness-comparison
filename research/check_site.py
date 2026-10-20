#!/usr/bin/env python3
"""Check every generated page, cross-page anchor, search route and profile body."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from collections import Counter
import json,hashlib,re
from profile_tiers import headings as expected_headings
ROOT=Path(__file__).resolve().parent.parent
manifest=json.loads((ROOT/'research/site-manifest.json').read_text())
issues=[]
class Page(HTMLParser):
 def __init__(self,text):
  super().__init__(convert_charrefs=True);self.h1=0;self.tables=0;self.diagrams=0;self.ids=[];self.links=[];self.assets=[];self.headings=[];self.heading=None;self.chapter=False;self.chapter_text=[];self.in_script=False;self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  self.h1+=tag=='h1'
  self.tables+=tag=='table'
  self.diagrams+=tag=='figure' and 'diagram' in a.get('class','').split()
  if a.get('id'):self.ids.append(a['id'])
  if tag=='a' and 'href' in a:self.links.append(a['href'])
  if tag in ('script','img','link'):
   u=a.get('src',a.get('href',''))
   if u:self.assets.append(u)
  if tag=='section' and 'chapter' in a.get('class','').split():self.chapter=True
  if self.chapter and tag in ('h1','h2','h3','h4'):self.heading=[tag,'']
  if tag in ('script','style'):self.in_script=True
 def handle_data(self,text):
  if self.heading is not None:self.heading[1]+=text
  if self.chapter and not self.in_script:self.chapter_text.append(text)
 def handle_endtag(self,tag):
  if self.heading is not None and tag==self.heading[0]:self.headings.append(tuple(self.heading));self.heading=None
  if tag=='section':self.chapter=False
  if tag in ('script','style'):self.in_script=False
pages={p['file']:Page((ROOT/p['file']).read_text()) for p in manifest['pages']}
book_text=(ROOT/'AI-Harness调研报告.html').read_text()
book=Page(book_text)
checked=0
for file,page in pages.items():
 duplicates=[k for k,v in Counter(page.ids).items() if v>1]
 if duplicates:issues.append(f'{file}: duplicate IDs {duplicates}')
 for url in page.links+page.assets:
  parsed=urlsplit(url)
  if parsed.scheme in ('http','https','mailto','data'):continue
  target=(ROOT/file).parent/unquote(parsed.path) if parsed.path else ROOT/file
  if not target.exists():issues.append(f'{file}: missing {url}');continue
  if parsed.fragment and target.suffix=='.html':
   name=str(target.resolve().relative_to(ROOT));parser=pages.get(name,book if target.name=='AI-Harness调研报告.html' else None)
   if parser is None or unquote(parsed.fragment) not in parser.ids:issues.append(f'{file}: broken anchor {url}')
  checked+=1
 for url in page.assets:
  if url.startswith(('https:','http:')):issues.append(f'{file}: remote dependency {url}')
 if page.ids.count('theme-toggle')!=1:issues.append(f'{file}: theme button missing')
 if page.ids.count('site-search')!=1:issues.append(f'{file}: search dialog missing')
 if not any('navigation.js' in u for u in page.assets):issues.append(f'{file}: tracking script missing')
 if page.h1!=1:issues.append(f'{file}: expected one article h1')
for anchor,url in manifest['routes'].items():
 file,fragment=url.split('#')
 if fragment not in pages[file].ids:issues.append('Broken legacy route '+anchor)
# All book heading IDs and direct tool anchors survive on exactly one reading page.
original_ids=re.findall(r'<h[1-6] id="([^"]+)"',book_text)+re.findall(r'<a id="([abcdh]\d{2})"',book_text)
for anchor in original_ids:
 if anchor not in manifest['routes']:issues.append('Lost original heading '+anchor)
# Each old positional ID must open the same heading it used to point to (a renumbered section may be renamed),
# or, for a section a short profile no longer shows, that tool's profile.
legacy=json.loads((ROOT/'research/legacy-anchors.json').read_text())['anchors']
book_headings={i:re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',t)).strip() for i,t in re.findall(r'<h[2-4] id="([^"]+)"[^>]*>(.*?)</h[2-4]>',book_text,re.S)}
legacy_fallbacks=0
for old,entry in legacy.items():
 route=manifest['routes'].get(old)
 if not route:issues.append('Old anchor without route '+old);continue
 target=route.split('#')[1];text=book_headings.get(target)
 number=re.match(r'\d+\.\d+ ',entry['text'])
 if text==entry['text'] or (entry['tool'] and entry['depth']==2 and target=='tool-'+entry['tool'].lower()):continue
 if text and number and text.startswith(number[0]):continue
 if entry['tool'] and target==entry['tool'].lower() and not any(h==entry['text'] for i,h in book_headings.items() if i.startswith(target+'-')):legacy_fallbacks+=1;continue
 issues.append(f'Old anchor {old} now opens {target}: {text!r}, was {entry["text"]!r}')
# Compare the complete text of each tool, including diagrams, code, tables and citations.
tools=[p for p in manifest['pages'] if p['kind']=='tool']
for tool in tools:
 start=book_text.index('<a id="'+tool['id']+'">')
 rest=book_text[start:]
 title_end=rest.index('</h2>')+5
 stop=re.search(r'<a id="[abcdh]\d{2}">|<h2\b|</section>',rest[title_end:])
 end=title_end+stop.start() if stop else len(rest)
 source=Page('<section class="chapter">'+rest[:end]+'</section>')
 actual=pages[tool['file']]
 normalize=lambda text:re.sub(r'\s+',' ',''.join(text)).strip()
 if normalize(source.chapter_text)!=normalize(actual.chapter_text):issues.append('Profile text changed/lost: '+tool['id'])
 if [text for tag,text in actual.headings if tag=='h2']!=expected_headings(tool['id'].upper()):issues.append('Profile sections changed: '+tool['id'])
 if f'read/{tool["id"]}.html'!=tool['file']:issues.append('Unstable profile URL')
if len(tools)!=58 or len(pages)!=72:issues.append('Unexpected page coverage')
if sum(p.tables for p in pages.values())!=book.tables or sum(p.diagrams for p in pages.values())!=book.diagrams:issues.append('Lost/duplicated tables or diagrams')
# Search records must point to a real heading; the full text index stays local and lazy.
index=(ROOT/'site-assets/search-index.js').read_text()
records=json.loads(index.removeprefix('globalThis.HARNESS_SEARCH=').removesuffix(';\n'))
for record in records:
 file,anchor=record['url'].split('#')
 if anchor not in pages[file].ids:issues.append('Broken search target '+record['url'])
for file,page in pages.items():
 if any('search-index.js' in src for src in page.assets):issues.append('Search index not lazy: '+file)
css=(ROOT/'site-assets/reading.css').read_text()
if '@media(max-width:740px)' not in css or ':root[data-theme="dark"]' not in css:issues.append('Missing responsive/theme CSS')
result={'method':'Static HTML parsing, exact profile text comparison and local route/asset checks; no browser rendering','pages':len(pages),'tool_pages':len(tools),'legacy_anchors':len(original_ids),'old_positional_anchors':len(legacy),'old_anchors_to_profile':legacy_fallbacks,'search_records':len(records),'local_links_checked':checked,'tables':sum(p.tables for p in pages.values()),'diagrams':sum(p.diagrams for p in pages.values()),'page_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pages},'book_sha256':hashlib.sha256(book_text.encode()).hexdigest(),'issues':issues}
(ROOT/'research/qa/site-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='page_sha256'},ensure_ascii=False,indent=2))
raise SystemExit(bool(issues))
