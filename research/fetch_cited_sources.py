#!/usr/bin/env python3
"""Restore only pinned, hashed citation files; never execute downloaded code."""
from pathlib import PurePosixPath
from urllib.request import Request,urlopen
from urllib.parse import quote
import argparse,hashlib
from source_records import RESEARCH,SOURCE_RECORDS,verify_source

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('keys',nargs='*',help='Optional repository keys; omit to restore all registered citations.')
args=parser.parse_args()
known={key for key,path in SOURCE_RECORDS}
if set(args.keys)-known:parser.error('Unknown repository keys: '+', '.join(sorted(set(args.keys)-known)))
restored=0
for (key,path),record in SOURCE_RECORDS.items():
    if args.keys and key not in args.keys:continue
    rel=PurePosixPath(path)
    if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe source path')
    if verify_source(key,path):continue
    url=f"https://raw.githubusercontent.com/{record['repository']}/{record['commit']}/{quote(path,safe='/')}"
    with urlopen(Request(url,headers={'User-Agent':'ai-harness-comparison-source-restore'}),timeout=60) as response:
        data=response.read(record['bytes']+1)
    if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:
        raise ValueError('Downloaded source does not match saved evidence: '+record['url'])
    target=RESEARCH/'repos'/key/'files'/path;target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.tmp');temporary.write_bytes(data);temporary.replace(target)
    restored+=1
print(f'Restored {restored} pinned source files; no downloaded code executed.')
