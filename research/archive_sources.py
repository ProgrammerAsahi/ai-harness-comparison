#!/usr/bin/env python3
"""Archive official pages that support a dated fact refresh.

    python3 research/archive_sources.py <round.json>

<round.json> holds {"round": "...", "scope": "...", "sources": [{"key": ..., "url": ..., "supports": ...}]}.
Page bodies go to the ignored research/pages/ cache; URL, retrieval time and
hashes are appended to research/fact-refresh-sources.json, which is versioned.
A page that cannot be fetched is recorded with its error instead of a hash.
"""
import datetime, gzip, hashlib, html, json, pathlib, re, sys, urllib.request

R = pathlib.Path(__file__).resolve().parent
PAGES = R / 'pages'
LOG = R / 'fact-refresh-sources.json'


def text_of(body, ctype):
    if 'html' not in ctype:
        return body
    body = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', ' ', body)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', body))).strip()


def fetch(src):
    req = urllib.request.Request(src['url'], headers={'User-Agent': 'Mozilla/5.0 (ai-harness-comparison source archive)'})
    rec = {'key': src['key'], 'url': src['url'], 'supports': src.get('supports', '')}
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read()
            ctype = r.headers.get('Content-Type', '')
            rec['final_url'] = r.geturl()
        if r.headers.get('Content-Encoding') == 'gzip' or raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)  # some servers compress even without Accept-Encoding
    except Exception as e:  # recorded, not hidden
        rec.update(retrieved_at=now(), error=str(e)[:200])
        return rec
    body = raw.decode('utf-8', 'replace')
    text = text_of(body, ctype)
    PAGES.mkdir(exist_ok=True)
    (PAGES / f"{src['key']}.txt").write_text(text)
    rec.update(retrieved_at=now(), content_type=ctype, sha256=hashlib.sha256(raw).hexdigest(),
               chars=len(text), text_sha256=hashlib.sha256(text.encode()).hexdigest())
    (PAGES / f"{src['key']}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return rec


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
log = json.loads(LOG.read_text()) if LOG.exists() else {'rounds': []}
log['rounds'] = [r for r in log['rounds'] if r['round'] != spec['round']]
records = [fetch(s) for s in spec['sources']]
log['rounds'].append({'round': spec['round'], 'scope': spec['scope'], 'sources': records})
LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + '\n')
bad = [r['key'] for r in records if 'error' in r]
print('archived', len(records) - len(bad), 'failed', len(bad), *bad)
