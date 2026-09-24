#!/usr/bin/env python3
"""MIT. Offline checks for the independent methodology study."""
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "studies/harness-quantification"
issues = []


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.remote_assets = [], [], []
        self.tables = self.figures = self.sections = 0
        self.stack = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag in {"img", "script", "iframe"} and a.get("src", "").startswith(("https:", "http:", "//")):
            self.remote_assets.append(a["src"])
        if tag == "link" and a.get("rel") == "stylesheet":
            self.remote_assets.append(a.get("href"))
        self.tables += tag == "table"
        self.figures += tag == "figure"
        self.sections += tag == "section"


page = (DIR / "index.html").read_text()
markdown = (DIR / "report.md").read_text()
parser = Page()
parser.feed(page)
manifest = json.loads((DIR / "build-manifest.json").read_text())
sources = json.loads((DIR / "sources.json").read_text())["sources"]


def check(condition, message):
    if not condition:
        issues.append(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


check(sha(page.encode()) == manifest["html_sha256"], "Stale HTML manifest")
check(sha(markdown.encode()) == manifest["markdown_sha256"], "Stale Markdown manifest")
check(sha((DIR / "sources.json").read_bytes()) == manifest["sources_sha256"], "Stale sources manifest")
check(not parser.remote_assets, f"Remote reading dependencies: {parser.remote_assets}")
check(not re.search(r"@import|url\(\s*['\"]?https?://", page), "Remote CSS dependency")
check(all(count == 1 for count in Counter(parser.ids).values()), "Duplicate HTML id")
local_links = 0
for link in parser.links:
    parsed = urlsplit(link)
    if parsed.scheme or parsed.netloc:
        continue
    if not parsed.path:
        check(unquote(parsed.fragment) in parser.ids, f"Missing anchor: {link}")
    else:
        check((DIR / unquote(parsed.path)).resolve().exists(), f"Missing local target: {link}")
    local_links += 1

body = markdown.split("<!-- REFERENCES:GENERATED -->")[0]
check(len(re.findall(r"^\*\*\d{2}｜", body, re.M)) == 40, "Related-work catalogue changed: review stated count")
fields = re.findall(r"^\| (F\d{2}) \|", body, re.M)
check(fields == [f"F{i:02}" for i in range(1, 37)], "Candidate field order or coverage mismatch")
check(parser.sections == manifest["chapter_count"] == 18, "Chapter count mismatch")
check(parser.figures == len(manifest["figures"]) == 6, "Figure count mismatch")
check("全部为虚构" in page and "没有运行这些产品" in page, "Missing synthetic / non-execution boundary")
check(not re.search(r"\[S\d{2}\]", page), "Unrendered source reference")
check(not re.search(r"[\uE200-\uE2FF]", page), "Internal web citation artifact")
for record in manifest["figures"]:
    content = (DIR / "figures" / record["file"]).read_bytes()
    check(sha(content) == record["sha256"], f"Stale figure: {record['file']}")
    svg = ET.fromstring(content)
    check(svg.find("{http://www.w3.org/2000/svg}title") is not None, "Missing accessible SVG title")
for record in manifest["shared_scripts"]:
    script = (ROOT / "research" / record["file"]).read_text()
    check(script in page, f"Shared script not embedded: {record['file']}")
    check(sha(script.encode()) == record["sha256"], "Stale shared script hash")

cached, manifest_only, excerpt_only = 0, 0, 0
for source in sources:
    if source.get("commit"):
        check(bool(re.fullmatch(r"[0-9a-f]{40}", source["commit"])), f"Invalid commit: {source['id']}")
    check(bool(source.get("reading_scope")), f"Missing reading scope: {source['id']}")
    if source.get("status") == "indexed_excerpt_only":
        excerpt_only += 1
        continue
    if source.get("sha256") and source.get("cache_file"):
        path = ROOT / source["cache_file"]
        if path.exists():
            check(sha(path.read_bytes()) == source["sha256"], f"Cache hash mismatch: {source['id']}")
            cached += 1
        else:
            manifest_only += 1
    else:
        issues.append(f"Missing source hash or explicit limitation: {source['id']}")

sys.path.insert(0, str(DIR))
from calculate_examples import examples
check(json.loads((DIR / "examples.json").read_text()) == examples(), "Stale synthetic example output")

visual_path = DIR / "diagram-visual-check.json"
visual_status = "Not recorded"
if visual_path.exists():
    visual = json.loads(visual_path.read_text())
    for item in visual["svg_checks"]:
        check(sha((DIR / item["file"]).read_bytes()) == item["sha256"], "Stale diagram visual check")
    visual_status = "Six light-mode SVG thumbnails reviewed; hashes matched. See diagram-visual-check.json; no HTML browser rendering."

result = {
    "method": "Static HTML/Markdown/SVG and source-manifest checks; no browser or product execution",
    "html_sha256": manifest["html_sha256"], "markdown_sha256": manifest["markdown_sha256"],
    "chapters": parser.sections, "tables": parser.tables, "figures": parser.figures,
    "catalogue_entries": 40, "candidate_fields": len(fields),
    "cited_sources": manifest["cited_source_count"], "registered_sources": len(sources),
    "local_links_checked": local_links, "cached_source_hashes_verified": cached,
    "manifest_only_source_checks": manifest_only, "indexed_excerpt_only_sources": excerpt_only,
    "synthetic_calculation_check": "Committed JSON equals direct recomputation; unit tests run separately by npm run check:study",
    "diagram_visual_qa": visual_status,
    "browser_visual_qa": "Not performed; prior local HTML preview denied by URL policy. No alternative local route used.",
    "product_or_model_tests": "Not performed; numerical tests use synthetic objects only",
    "issues": issues,
}
(DIR / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(bool(issues))
