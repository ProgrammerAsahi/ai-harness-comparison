#!/usr/bin/env python3
"""Check logo provenance, architecture geometry/evidence and dark reading contrast.

Static validation complements Node interaction tests; it is not browser rendering
or a product-runtime test. No network or research cache is required.
"""
from pathlib import Path
from html.parser import HTMLParser
import base64,hashlib,json,re,xml.etree.ElementTree as ET
from profile_architecture import DETAIL,SUPPLEMENTS,expected_figures,evidence
R=Path(__file__).resolve().parent.parent
page=(R/'AI-Harness调研报告.html').read_text();issues=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
logos=json.loads((R/'research/logo-sources.json').read_text())['logos']
if {x['id'] for x in logos}!=set(DETAIL) or len(logos)!=55:issues.append('Logo/profile coverage mismatch')
class Headings(HTMLParser):
 def __init__(self):super().__init__();self.in_heading=False;self.logo_headings=0;self.logos=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='h2':self.in_heading='tool-heading' in a.get('class','');self.logo_headings+=self.in_heading
  if tag=='img' and self.in_heading:self.logos+=1
 def handle_endtag(self,tag):
  if tag=='h2':self.in_heading=False
h=Headings();h.feed(page)
if (h.logo_headings,h.logos)!=(55,55):issues.append('Expected one embedded logo on each profile H2')
for m in logos:
 raw=(R/m['file']).read_bytes()
 if sha(raw)!=m['sha256'] or len(raw)!=m['bytes']:issues.append(m['id']+': logo integrity mismatch')
 if not all(m.get(k) for k in ['source_page','source_url','retrieved_at','note','modifications']):issues.append(m['id']+': missing provenance')
 uri='data:'+m['mime_type']+';base64,'+base64.b64encode(raw).decode()
 if uri not in page:issues.append(m['id']+': embedded logo differs from source asset')
 if m['mime_type']=='image/svg+xml':
  root=ET.fromstring(raw)
  for n in root.iter():
   if n.tag.split('}')[-1] in ['script','foreignObject']:issues.append(m['id']+': active SVG content')
   for k,v in n.attrib.items():
    if k.split('}')[-1] in ['href','src'] and not v.startswith(('#','data:')):issues.append(m['id']+': external SVG asset')
  if re.search(r'@import|url\(\s*[\"\']?https?://',raw.decode()):issues.append(m['id']+': remote SVG style')

refs=evidence();source_manifest=json.loads((R/'research/source-manifest.json').read_text())['files'];byurl={m['url']:m for m in source_manifest}
if set(refs)!=set(DETAIL):issues.append('Architecture evidence coverage mismatch')
for key,records in refs.items():
 if not records:issues.append(key+': no architecture evidence')
 for m in records:
  if '/blob/' in m['url']:
   original=byurl.get(m['url'])
   if not original or original['sha256']!=m['sha256']:issues.append(key+': architecture source mismatch')
  if not m['retrieved_at'] or not re.fullmatch('[0-9a-f]{64}',m['sha256']):issues.append(key+': incomplete architecture provenance')

# No edge segment may run through a module's interior (endpoints on borders are OK).
geometry=[]
for key in DETAIL:
 for file in expected_figures(key)[1:]:
  svg=ET.parse(R/'report'/file).getroot();ns='{http://www.w3.org/2000/svg}'
  boxes=[tuple(float(n.attrib[k]) for k in ['x','y','width','height']) for n in svg.findall(ns+'rect') if n.get('data-node')]
  paths=[n for n in svg.findall(ns+'path') if n.get('data-edge')]
  if len(boxes)!=8 or len(paths)<6:issues.append(file+': missing module/flow detail')
  if svg.find(ns+'title') is None or svg.find(ns+'desc') is None:issues.append(file+': inaccessible diagram')
  for n in paths:
   numbers=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',n.get('d'))));pts=list(zip(numbers[::2],numbers[1::2]))
   for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
    if x1!=x2 and y1!=y2:issues.append(file+': diagonal edge was not checked');continue
    for x,y,w,ht in boxes:
     through=(x<x1<x+w and max(min(y1,y2),y)<min(max(y1,y2),y+ht)) if x1==x2 else (y<y1<y+ht and max(min(x1,x2),x)<min(max(x1,x2),x+w))
     if through:issues.append(file+': edge '+n.get('data-edge')+' crosses a module')
  geometry.append(dict(file=file,nodes=len(boxes),edges=len(paths),sha256=sha((R/'report'/file).read_bytes())))
if len(geometry)!=55+len(SUPPLEMENTS):issues.append('Detailed diagram coverage mismatch')

def luminance(hex):
 rgb=[int(hex[i:i+2],16)/255 for i in [1,3,5]]
 rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
 return sum(a*b for a,b in zip(rgb,[.2126,.7152,.0722]))
def contrast(a,b):
 x,y=sorted([luminance(a),luminance(b)]);return (y+.05)/(x+.05)
pairs=[('正文','#dce7e3','#18211f'),('次要文字','#a1b4ae','#141d1a'),('链接','#81d4be','#18211f'),('已访问链接','#b1cfc5','#18211f'),('表头','#d4ecdf','#25362d'),('代码','#d6e9df','#101b19'),('目录当前项','#dcfff0','#254639'),('图中强调模块','#d1e8d9','#294b3c'),('图注','#a9c0b1','#17231f')]
css=(R/'research/report-theme.css').read_text();ratios=[]
for name,fg,bg in pairs:
 ratio=contrast(fg,bg);ratios.append(dict(element=name,foreground=fg,background=bg,ratio=round(ratio,2)))
 if fg not in css or bg not in css:issues.append(name+': contrast test color differs from theme')
 if ratio<4.5:issues.append(name+': insufficient dark text contrast')
result=dict(method='Static asset/hash, frozen-evidence, orthogonal SVG geometry and calculated dark-theme contrast; no browser rendering',html_sha256=sha(page.encode()),logos=len(logos),profile_detail_diagrams=55,subsystem_diagrams=len(SUPPLEMENTS),architecture_layouts=sorted({p['layout'] for p in DETAIL.values()}),dark_text_contrast=ratios,geometry=geometry,issues=issues)
(R/'research/qa/enhancements-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['geometry','dark_text_contrast']},ensure_ascii=False,indent=2));raise SystemExit(bool(issues))
