#!/usr/bin/env python3
"""Resolve report citations against the captured public-source snapshot."""
import pathlib,json,re,csv
from source_records import REPOSITORIES,verify_source
ROOT=pathlib.Path(__file__).resolve().parent.parent
R=ROOT/'research'
# Locally captured page metadata (gitignored); each file may hold a newer final_url.
PAGES_DIR=R/'pages'
PLACEHOLDER=re.compile(r'\{\{((?:src|repo|doc):[^}]+)\}\}')
INLINE_SOURCE=re.compile(r'(https://github.com/([^/]+/[^/]+)/blob/([a-f0-9]{40})/([^\s)]+))')

def resolve_placeholder(text,refs,repositories,citations):
    """Replace one {{doc:…}}/{{repo:…}}/{{src:…}} token (text without the braces) with its URL.
    Appends the citation record to citations and returns the URL."""
    kind,key,*tail=text.split(':',2)
    if kind=='doc':
        meta=PAGES_DIR/f'{key}.json'
        url=json.loads(meta.read_text()).get('final_url',refs[key]) if meta.exists() else refs[key]
        citations.append({'kind':'official-document','key':key,'path':'','url':url})
        return url
    m=repositories[key]
    url='https://github.com/'+m['repository']
    if kind=='src':
        path=tail[0]
        verify_source(key,path)
        url+='/blob/'+m['sha']+'/'+path
        citations.append({'kind':'pinned-source','key':key,'path':path,'url':url})
    else:citations.append({'kind':'repository','key':key,'path':'','url':url})
    return url

def resolve_placeholders(text,refs,repositories,citations):
    """Replace every citation token in one document; return the updated text."""
    return PLACEHOLDER.sub(lambda m:resolve_placeholder(m.group(1),refs,repositories,citations),text)

def collect_inline_sources(text,repositories,citations):
    """Collect GitHub blob links pinned to a full commit SHA from one document body.
    Checks each link against the repository snapshot table (raising ValueError when the
    repository or commit does not match) and verifies the source record; appends the
    citation records to citations and returns them."""
    manifests={m['repository'].lower():(key,m) for key,m in repositories.items()}
    found=[]
    for url,repo,sha,path in INLINE_SOURCE.findall(text):
        item=manifests.get(repo.lower())
        if not item:raise ValueError('No pinned repository snapshot for '+url)
        key,m=item
        if sha!=m['sha']:raise ValueError('Mismatched snapshot for '+url)
        verify_source(key,path)
        found.append({'kind':'pinned-source','key':key,'path':path,'url':url})
    citations.extend(found)
    return found

def dedupe_citations(citations):
    """Keep a single record per (kind, url), in first-seen order."""
    return list({(x['kind'],x['url']):x for x in citations}.values())

def main():
    """Resolve citation tokens in report/*.md and refresh the citation records."""
    refs={}
    for p in R.glob('pages-*.json'):
        refs.update(json.loads(p.read_text()))
    citations=[]
    for p in sorted((ROOT/'report').glob('*.md')):
        p.write_text(resolve_placeholders(p.read_text(),refs,REPOSITORIES,citations))
    old=R/'citations.json'
    if old.exists():citations+=json.loads(old.read_text())
    for p in sorted((ROOT/'report').glob('*.md')):
        if p.name=='参考资料索引.md':continue
        collect_inline_sources(p.read_text(),REPOSITORIES,citations)
    citations=dedupe_citations(citations)
    old.write_text(json.dumps(citations,ensure_ascii=False,indent=2))
    with (R/'citations.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['kind','key','path','url']);w.writeheader();w.writerows(citations)
    print('Resolved citation records:',len(citations))

if __name__=='__main__':main()
