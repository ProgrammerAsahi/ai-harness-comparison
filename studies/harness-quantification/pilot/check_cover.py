#!/usr/bin/env python3
"""MIT. Check that the evidence a config record cites is present in its pinned source snapshot.

For each config, reads the record's evidence list (data/configs/<config_id>.json) and verifies
against the snapshot under <sources>/<config_id>/ (SOURCE.txt with the pinned repository and
commit, the docs export docs-llms-full.txt or docs-pages.txt, and the source archive split into
src*.tar.gz.* pieces) that: every cited GitHub commit is the one the snapshot pins, every cited
file exists in the archive, and every cited line number stays inside the file, or inside the
page it cites. Official-doc line numbers are written either relative to the page or absolute to
the whole export file; both count as covered. Archives are read in memory; nothing is unpacked
to disk and nothing from an archive is executed. Prints one summary line per record, then the
items that are not covered (at most 12 per record). Exit status 1 when any item is WRONG, 0
otherwise.

  python3 studies/harness-quantification/pilot/check_cover.py [--records DIR] [--sources DIR] CONFIG_ID...
"""
import argparse
import io
import json
import re
import sys
import tarfile
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]


def norm(url):
    url = url.split("#")[0].split("?")[0]
    url = re.sub(r"[.]md$", "", url)
    return url.rstrip("/")


def span(lines):
    m = re.search(r"(\d+)(?:\s*[-–]\s*(\d+))?", lines or "")
    return (int(m.group(1)), int(m.group(2) or m.group(1))) if m else None


def load_pages(folder):
    """{normalised page url: (line count of the page, first export line, last export line)}.

    The line numbers are 1-based positions in the export file itself (docs-pages.txt or
    docs-llms-full.txt); the page runs from its "Source:" line to the line before the next one.
    """
    pages = {}
    for name in ("docs-pages.txt", "docs-llms-full.txt"):
        f = folder / name
        if not f.exists():
            continue
        current, count, start, last = None, 0, 0, 0
        for n, line in enumerate(f.read_text("utf-8", "replace").splitlines(), 1):
            m = re.match(r"Source: (\S+)\s*$", line)
            if m:
                if current:
                    pages[current] = (count, start, last)
                current, count, start, last = norm(m.group(1)), 0, n, n
            else:
                count += 1
                last = n
        if current:
            pages[current] = (count, start, last)
    return pages


def load_tree(folder):
    """{(stem): (combined archive bytes, {path: tar member})} for each archive in the folder.

    Pieces are joined and read from memory; nothing is written to disk.
    """
    trees = {}
    stems = sorted({p.name.split(".tar.gz.")[0] for p in folder.glob("src*.tar.gz.*")})
    for stem in stems:
        data = b"".join(p.read_bytes() for p in sorted(folder.glob(stem + ".tar.gz.*")))
        files = {}
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for m in tar:
                if m.isfile() and "/" in m.name:
                    files[m.name.split("/", 1)[1]] = m
        trees[stem] = (data, files)
    return trees


def check_record(records, sources, cid):
    """Check one record; return (summary line, wrong items, outside items)."""
    rec = json.loads((records / f"{cid}.json").read_text("utf-8"))
    folder = sources / cid
    pages = load_pages(folder)
    source_txt = (folder / "SOURCE.txt").read_text("utf-8")
    pins = dict(re.findall(r"repository: https://github.com/(\S+)\ncommit: ([0-9a-f]{40})", source_txt))
    trees = load_tree(folder)
    tar_cache = {}
    ok, bad, outside = 0, [], []
    for n, ev in enumerate(rec["evidence"]):
        url, kind, lines = ev["source_url"], ev["evidence_kind"], ev.get("lines") or ""
        m = re.match(r"https://github.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)", url.split("#")[0])
        if m:
            repo, sha, path = m.groups()
            if pins.get(repo) != sha:
                bad.append(f"[{n}] {kind}: commit not the pinned one: {repo}@{sha[:10]}")
                continue
            found = None
            for stem, (data, files) in trees.items():
                if path in files:
                    found = (stem, data, files[path])
            if not found:
                bad.append(f"[{n}] {kind}: path not in archive: {path}")
                continue
            s = span(lines)
            if s:
                stem, data, member = found
                key = (stem, path)
                if key not in tar_cache:
                    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                        tar_cache[key] = tar.extractfile(member).read().count(b"\n") + 1
                if s[1] > tar_cache[key]:
                    bad.append(f"[{n}] {kind}: lines {lines} past end of {path} ({tar_cache[key]} lines)")
                    continue
            ok += 1
        elif norm(url) in pages:
            count, start, end = pages[norm(url)]
            s = span(lines)
            # Relative to the page (a little slack) or absolute to the export file: both are covered.
            if s and s[1] > count + 2 and not (start <= s[0] and s[1] <= end):
                bad.append(f"[{n}] {kind}: lines {lines} past end of page {url} ({count} lines)")
            else:
                ok += 1
        else:
            outside.append(f"[{n}] {kind}: {url}" + (f" lines={lines}" if lines else ""))
    summary = f"{cid}: evidence {len(rec['evidence'])} | in snapshot {ok} | wrong {len(bad)} | outside {len(outside)}"
    return summary, bad, outside


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check config-record evidence against its pinned source snapshot.")
    parser.add_argument("config_ids", metavar="CONFIG_ID", nargs="+",
                        help="config ids to check (record <records>/<CONFIG_ID>.json)")
    parser.add_argument("--records", type=Path, default=STUDY / "data/configs",
                        help="directory of config records (default: %(default)s)")
    parser.add_argument("--sources", type=Path, default=REPO / "tmp/quant-pilot/sources",
                        help="directory of source snapshots (default: %(default)s)")
    args = parser.parse_args(argv)
    wrong = 0
    for cid in args.config_ids:
        summary, bad, outside = check_record(args.records, args.sources, cid)
        wrong += len(bad)
        print(summary)
        for line in bad[:12]:
            print("  WRONG " + line)
        for line in outside[:12]:
            print("  OUT   " + line)
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
