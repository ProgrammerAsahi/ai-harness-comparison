#!/usr/bin/env python3
"""Freeze the old positional heading IDs (chapter-N-hM, quick-start-hM) so links keep working.

Headings used to be numbered by position, so removing a section shifted every later ID.
This records what each old ID pointed to in published HTML versions taken from Git; the
report builder resolves each entry to the current fixed ID by chapter, tool and heading
text. When versions disagree, the earlier and longer-published version wins. Run once
when a new set of positional IDs must be preserved; the output is committed.
"""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# 24e0f0a was published 2026-09-24 to 2026-10-15; the later two only filled IDs it lacked.
VERSIONS=['24e0f0a','7cefaa4','3dadfd8']
strip=lambda s:re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',s)).strip()
def inventory(commit):
    html=subprocess.run(['git','show',f'{commit}:AI-Harness调研报告.html'],cwd=ROOT,capture_output=True,text=True,check=True).stdout
    out={};h2=h3=None;tool=None
    for depth,hid,inner in re.findall(r'<h([1-4]) id="([^"]+)"[^>]*>(.*?)</h\1>',html,re.S):
        depth=int(depth);text=strip(inner)
        if depth==1:h2=h3=tool=None;continue
        if depth==2:
            h2,h3=text,None;tool=(re.match(r'([ABCDH]\d{2}) ',text) or [None,None])[1]
        elif depth==3:h3=text
        if not re.fullmatch(r'(?:chapter-\d+|quick-start)-h\d+',hid):continue
        parent=None if depth==2 else (h2 if depth==3 else h3)
        out[hid]={'chapter':hid.rsplit('-h',1)[0],'depth':depth,'tool':tool,'parent':None if tool and depth==3 else parent,'text':text,'source':commit}
    return out
anchors={}
for commit in VERSIONS:
    for hid,entry in inventory(commit).items():anchors.setdefault(hid,entry)
order=lambda k:(k.rsplit('-h',1)[0],int(k.rsplit('-h',1)[1]))
data={'note':__doc__.strip().splitlines()[0],'versions':VERSIONS,'anchors':{k:anchors[k] for k in sorted(anchors,key=order)}}
(ROOT/'research/legacy-anchors.json').write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n')
print(json.dumps({'legacy_anchors':len(anchors),'by_version':{v:sum(e['source']==v for e in anchors.values()) for v in VERSIONS}}))
