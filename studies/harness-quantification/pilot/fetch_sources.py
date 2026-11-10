"""Fetch the source snapshot a pilot config record pins, for coders that work without network access.

  python3 studies/harness-quantification/pilot/fetch_sources.py <config_id> [...]   # or: all

For each config it reads the first 40-hex commit in `version_or_commit` (the primary evidence commit), finds the
repository from an evidence URL carrying that commit, downloads GitHub's source archive of that commit and writes

  <out>/<config_id>/src.tar.gz.00, .01, ...   pieces of at most 19 MB (cat them together to get the tar.gz)
  <out>/<config_id>/SOURCE.txt                repository, commit, archive size and SHA-256, how to unpack
  <out>/<config_id>/docs-llms-full.txt        only for tools whose official docs live outside the repository: the
                                              docs site's own full-text export, with URL, date and SHA-256 in SOURCE.txt

<out> is the PILOT_SOURCES environment variable or, by default, tmp/quant-pilot/sources (not in Git: third-party
source is never committed). Nothing is installed or run; the archive is only unpacked by the coder for reading.
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
CONFIGS = STUDY / "data/configs"
OUT = Path(os.environ.get("PILOT_SOURCES") or REPO / "tmp/quant-pilot/sources").resolve()
PIECE = 19 * 1024 * 1024
# Official docs sites that are not part of the pinned repository, by tool; each publishes a full-text export.
DOCS = {
    "A01__claude-code": "https://code.claude.com/docs/llms-full.txt",
    "A02__codex": "https://developers.openai.com/codex/llms-full.txt",
}


def pinned(config_id):
    raw = (CONFIGS / f"{config_id}.json").read_text(encoding="utf-8")
    shas = re.findall(r"\b[0-9a-f]{40}\b", json.loads(raw)["version_or_commit"])
    if not shas:
        raise SystemExit(f"{config_id}: no 40-hex commit in version_or_commit")
    m = re.search(r"https://github\.com/([^/\s\"]+/[^/\s\"]+)/blob/" + shas[0], raw)
    if not m:
        raise SystemExit(f"{config_id}: no evidence URL carries commit {shas[0]}")
    return m.group(1), shas[0]


def fetch(config_id):
    repo, sha = pinned(config_id)
    dest = OUT / config_id
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("src.tar.gz.*"):
        old.unlink()
    data = subprocess.run(["gh", "api", f"repos/{repo}/tarball/{sha}"], capture_output=True, check=True,
                          timeout=900).stdout
    if data[:2] != b"\x1f\x8b":
        raise SystemExit(f"{config_id}: download is not a gzip archive")
    pieces = [data[i:i + PIECE] for i in range(0, len(data), PIECE)]
    for n, piece in enumerate(pieces):
        (dest / f"src.tar.gz.{n:02d}").write_bytes(piece)
    (dest / "SOURCE.txt").write_text(
        f"config_id: {config_id}\nrepository: https://github.com/{repo}\ncommit: {sha}\n"
        f"archive: GitHub source archive of that commit, {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}\n"
        f"pieces: {len(pieces)} (src.tar.gz.00 ...)\n"
        "unpack: d=$(mktemp -d) && cat src.tar.gz.* | tar -xzf - -C \"$d\" --strip-components=1\n"
        f"cite as: https://github.com/{repo}/blob/{sha}/<path inside the archive>\n", encoding="utf-8")
    print(f"{config_id}: {repo}@{sha[:10]} {len(data) / 1e6:.1f} MB in {len(pieces)} piece(s)")
    url = next((u for key, u in DOCS.items() if config_id.startswith(key)), None)
    if url:
        req = urllib.request.Request(url, headers={"User-Agent": "harness-study-source-fetch"})
        docs = urllib.request.urlopen(req, timeout=300).read()
        (dest / "docs-llms-full.txt").write_bytes(docs)
        with (dest / "SOURCE.txt").open("a", encoding="utf-8") as f:
            f.write(f"docs: docs-llms-full.txt is {url} as served on {datetime.date.today().isoformat()}, "
                    f"{len(docs)} bytes, sha256 {hashlib.sha256(docs).hexdigest()}\n"
                    "docs cite as: evidence kind official_doc; the page URL where the file gives one (a Source: line), "
                    "otherwise the docs site address plus the section heading\n")
        print(f"{config_id}: docs export {len(docs) / 1e6:.1f} MB")


if __name__ == "__main__":
    ids = sys.argv[1:]
    if not ids:
        sys.exit(__doc__)
    if ids == ["all"]:
        ids = sorted(p.stem for p in CONFIGS.glob("*.json"))
    for config_id in ids:
        fetch(config_id)
