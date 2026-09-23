#!/usr/bin/env python3
"""Validate the generated local report without launching a browser or loading remote assets."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent

class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.remote_assets = []
        self.headings = []
        self.heading = None
        self.sections = 0
        self.diagrams = 0
        self.tables = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.append(a['id'])
        if tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        if tag == 'h2':
            self.heading = {'id': a.get('id'), 'text': ''}
        self.sections += tag == 'section' and a.get('class') == 'chapter'
        self.diagrams += tag == 'figure' and a.get('class') == 'diagram'
        self.tables += tag == 'table'
        if tag in ('img', 'script', 'iframe', 'source', 'video', 'audio'):
            url = a.get('src', '')
        elif tag == 'link' and a.get('rel') == 'stylesheet':
            url = a.get('href', '')
        else:
            url = ''
        if url.startswith(('https:', 'http:')):
            self.remote_assets.append(url)

    def handle_data(self, data):
        if self.heading is not None:
            self.heading['text'] += data

    def handle_endtag(self, tag):
        if tag == 'h2' and self.heading is not None:
            self.headings.append(self.heading)
            self.heading = None

html = (ROOT / 'AI-Harness调研报告.html').read_text()
p = ReportParser()
p.feed(html)
issues = []
missing = sorted(set(u for u in p.links if u.startswith('#') and unquote(u[1:]) not in p.ids))
duplicate = [k for k, v in Counter(p.ids).items() if v > 1]
for url in p.links:
    if url.startswith(('https:', 'http:', '#', 'mailto:')):
        continue
    if not (ROOT / unquote(url.split('#')[0])).exists():
        issues.append('Missing local file: ' + url)

step_headings = [h for h in p.headings if 'Step' in h['text']]
if len(step_headings) != 5:
    issues.append(f'Expected five Step sections, got {len(step_headings)}')
if p.sections != 12 or p.diagrams != 6:
    issues.append('Incorrect chapter/diagram count')
if missing or duplicate or p.remote_assets:
    issues.append('Broken anchors, duplicate IDs, or remote asset dependencies')
if re.search(r'\{\{(?:doc|repo|src):', html):
    issues.append('Unresolved citation token')
svg_checks = []
for file in sorted((ROOT / 'report/figures').glob('*.svg')):
    root = ET.parse(file).getroot()
    svg_checks.append({'file': file.name, 'viewBox': root.attrib.get('viewBox'), 'accessible_title': bool(root.find('{http://www.w3.org/2000/svg}title') is not None)})
if not all(x['accessible_title'] for x in svg_checks):
    issues.append('Diagram without accessible title')

result = {
    'date': '2026-09-23',
    'method': 'Static HTML/Markdown/SVG inspection; no browser execution',
    'chapters': p.sections, 'diagrams': p.diagrams, 'tables': p.tables,
    'step_section_targets': step_headings,
    'missing_anchors': missing, 'duplicate_ids': duplicate,
    'remote_asset_dependencies': p.remote_assets,
    'svg_checks': svg_checks,
    'browser_visual_qa': 'Not completed: browser URL policy blocked local file preview; no workaround attempted.',
    'issues': issues,
}
(ROOT / 'research/qa/step-addition-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(bool(issues))
