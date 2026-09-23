"""Validate pinned references without requiring third-party downloads in Git."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parent.parent
RESEARCH=ROOT/'research'
REPOSITORIES={row['id']:row for row in json.loads((RESEARCH/'repository-snapshot.json').read_text())}
MANIFEST_PATH=RESEARCH/'source-manifest.json'
SOURCE_RECORDS={(row['key'],row['path']):row for row in json.loads(MANIFEST_PATH.read_text())['files']}

def verify_source(key,path,require_cache=False):
    """Return True for verified cached bytes, False for manifest-only validation."""
    repo=REPOSITORIES[key];record=SOURCE_RECORDS.get((key,path))
    if record is None:
        raise ValueError(f'Unregistered source: {key}/{path}; record its pinned version and verified hash first.')
    expected=f"https://github.com/{repo['repository']}/blob/{repo['sha']}/{path}"
    if record['commit']!=repo['sha'] or record['repository']!=repo['repository'] or record['url']!=expected:
        raise ValueError('Source record does not match repository snapshot: '+expected)
    file=RESEARCH/'repos'/key/'files'/path
    if not file.exists():
        if require_cache:raise ValueError('Missing local source cache: '+expected)
        return False
    content=file.read_bytes()
    if len(content)!=record['bytes'] or hashlib.sha256(content).hexdigest()!=record['sha256']:
        raise ValueError('Local source hash mismatch: '+expected)
    return True
