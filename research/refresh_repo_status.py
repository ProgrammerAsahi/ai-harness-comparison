#!/usr/bin/env python3
"""Record current GitHub status for the snapshot repositories.

The fixed-commit source snapshot (repository-snapshot.json) stays unchanged;
this writes a separate, dated status record used for the inventory's activity
column. Requires the GitHub CLI (`gh`) with network access.

    python3 research/refresh_repo_status.py
"""
import datetime, json, pathlib, subprocess

R = pathlib.Path(__file__).resolve().parent
OUT = R / 'repository-status.json'


def gh(path, jq):
    p = subprocess.run(['gh', 'api', path, '--jq', jq], capture_output=True, text=True)
    return json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else None


snapshot = json.loads((R / 'repository-snapshot.json').read_text())
rows = []
for r in snapshot:
    cur = gh(f"repos/{r['repository']}", '{full_name,archived,pushed_at,stargazers_count,html_url}')
    if cur is None:
        raise SystemExit(f"GitHub lookup failed: {r['repository']}")
    rel = gh(f"repos/{r['repository']}/releases/latest", '{tag_name,published_at}')
    rows.append({
        'id': r['id'],
        'snapshot_repository': r['repository'],
        'repository': cur['full_name'],
        'url': cur['html_url'],
        'stars': cur['stargazers_count'],
        'pushed_at': cur['pushed_at'],
        'archived': cur['archived'],
        'latest_release': rel,
    })
now = datetime.datetime.now(datetime.timezone.utc)
OUT.write_text(json.dumps({
    'retrieved_at': now.isoformat(timespec='seconds'),
    'scope': 'GitHub API 元数据（星数、最近推送、归档、最新 Release）。不改变固定提交快照，也不代表重新阅读源码。',
    'repositories': rows,
}, ensure_ascii=False, indent=2) + '\n')
print('repositories', len(rows), 'retrieved_at', now.date())
