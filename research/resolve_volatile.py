#!/usr/bin/env python3
"""Resolve volatile facts (model names, prices, maintenance status) in report/*.md.

Generators write placeholders instead of hard-coded versions:
  {{m:<role>}}       current model name for a role, e.g. {{m:anthropic.daily}}
  {{date:facts}}     date the volatile facts were last checked
  {{table:<name>}}   a dated central table with its sources (model-families, api-prices, plans, maintenance, recent-changes)
All values live in volatile-facts.json, so a refresh edits one file.
"""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
FACTS = json.loads((ROOT / 'research/volatile-facts.json').read_text())
TOKEN = re.compile(r'\{\{(m|date|table):([\w.\-]+)\}\}')


def cell(text):
    return str(text).replace('|', '／').replace('\n', ' ')


def table(name):
    spec = FACTS['tables'][name]
    head = '| ' + ' | '.join(spec['columns']) + ' |\n|' + '|'.join(spec.get('align', ['---'] * len(spec['columns']))) + '|\n'
    body = ''.join('| ' + ' | '.join(cell(v) for v in row) + ' |\n' for row in spec['rows'])
    note = spec.get('note', '').replace('{{date:facts}}', FACTS['checked_at'])
    caption = f"*核实日期：{spec.get('checked_at', FACTS['checked_at'])}。{note}*\n\n" if note or spec.get('checked_at') else ''
    src = '、'.join(f'[{label}]({url})' for label, url in spec.get('sources', []))
    return caption + head + body.rstrip('\n') + (f'\n\n来源：{src}。' if src else '')


def resolve(text, where):
    def sub(m):
        kind, key = m.groups()
        if kind == 'm':
            if key not in FACTS['models']:
                raise SystemExit(f'{where}: unknown model role {key}')
            return FACTS['models'][key]
        if kind == 'date':
            if key != 'facts':
                raise SystemExit(f'{where}: unknown date {key}')
            return FACTS['checked_at']
        if key not in FACTS['tables']:
            raise SystemExit(f'{where}: unknown table {key}')
        return table(key)
    out = TOKEN.sub(sub, text)
    if '{{' in out and re.search(r'\{\{(m|date|table):', out):
        raise SystemExit(f'{where}: unresolved volatile placeholder')
    return out


if __name__ == '__main__':
    used = set()
    for p in sorted((ROOT / 'report').glob('*.md')):
        t = p.read_text()
        used |= {f'{k}:{v}' for k, v in TOKEN.findall(t)}
        r = resolve(t, p.name)
        if r != t:
            p.write_text(r)
    unused = {f'm:{k}' for k in FACTS['models']} | {f'table:{k}' for k in FACTS['tables']}
    unused -= used
    if unused:
        raise SystemExit('volatile-facts.json has unused entries: ' + ', '.join(sorted(unused)))
    print('volatile placeholders', len(used), 'checked_at', FACTS['checked_at'])
