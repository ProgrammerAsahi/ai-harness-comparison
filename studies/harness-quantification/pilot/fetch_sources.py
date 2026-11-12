"""Fetch the source snapshot a pilot config record pins, for coders that work without network access.

  python3 studies/harness-quantification/pilot/fetch_sources.py <config_id> [...]   # or: all

For each config it reads the first 40-hex commit in `version_or_commit` (the primary evidence commit), finds the
repository from an evidence URL carrying that commit, downloads GitHub's source archive of that commit and writes

  <out>/<config_id>/src.tar.gz.00, .01, ...   pieces of at most 19 MB (cat them together to get the tar.gz)
  <out>/<config_id>/src-<repo>.tar.gz.00, ... the same for every further commit named in `version_or_commit` (a product
                                              split over several repositories). Its repository comes from an evidence
                                              URL carrying the commit or, failing that, from an `owner/repo` named
                                              before "提交 <sha>" in the same clause. A further 40-hex id that neither
                                              places (a tag object, say) is reported on stderr and in SOURCE.txt, so a
                                              missing snapshot is seen before coding starts.
  <out>/<config_id>/SOURCE.txt                repository, commit, archive size and SHA-256, how to unpack
  <out>/<config_id>/docs-llms-full.txt        only for tools whose official docs live outside the repository: the
                                              docs site's own full-text export, with URL, date and SHA-256 in SOURCE.txt
  <out>/<config_id>/docs-pages.txt            only for tools whose docs site has no full-text export: the pages its own
                                              index lists (a chosen part of them), fetched one by one as Markdown and
                                              joined, each under a "Source: <page URL>" line; SOURCE.txt lists the
                                              indexes, the selection, the page count and any page that failed

A closed-source product has no commit; its record is served by the docs export alone.

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
    "A14__mistral-vibe": "https://docs.mistral.ai/llms-full.txt",
    "A15__openhands": "https://docs.openhands.dev/llms-full.txt",
    "A16__grok-build": "https://docs.x.ai/llms-full.txt",
    "B10__factory-droid": "https://docs.factory.com/llms-full.txt",
    "C06__open-webui": "https://docs.openwebui.com/llms-full.txt",
    "C10__nanoclaw": "https://docs.nanoclaw.dev/llms-full.txt",
    "D01__dify": "https://docs.dify.ai/llms-full.txt",
}
# Docs sites with a page index but no full-text export. Per tool: (index URL, pattern a page must match, URL
# template that returns the page as Markdown, URL template to cite); "{}" is the matched text. Only the parts
# of a site that describe the coded entry point are taken; the selection is repeated in SOURCE.txt.
DOC_PAGES = {
    "B01__cursor": [
        ("https://cursor.com/llms.txt", r"https://cursor\.com/(?:docs|help)(?:/[\w.-]+)*\.md", "{}", "{}"),
    ],
    "B02__github-copilot": [
        ("https://code.visualstudio.com/llms.txt",
         r"https://code\.visualstudio\.com/docs/(?:agents|agent-customization|chat|setup|configure|editing|enterprise"
         r"|reference|getstarted)(?:/[\w.-]+)+\.md", "{}", "{}"),
        ("https://docs.github.com/api/pagelist/en/free-pro-team@latest",
         r"/en/copilot/(?:concepts|get-started|reference/(?:ai-models|copilot-cli-reference|copilot-billing)"
         r"|how-tos/(?:copilot-in-your-ide|use-copilot-agents|copilot-sdk|cloud-and-local-sandboxes"
         r"|manage-your-account|configure-content-exclusion|troubleshoot-copilot|provide-context|set-up))(?:/[\w.-]+)*",
         "https://docs.github.com/api/article/body?pathname={}", "https://docs.github.com{}"),
    ],
}
# Closed-source products whose version string carries a 40-hex build identifier that is not a public commit.
NO_PUBLIC_SOURCE = {"B01__cursor"}
AGENT = {"User-Agent": "harness-study-source-fetch"}


def docs_url(config_id):
    return next((u for key, u in DOCS.items() if config_id.startswith(key)), None)


def doc_pages(config_id):
    return next((v for key, v in DOC_PAGES.items() if config_id.startswith(key)), None)


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=120).read()


def fetch_pages(config_id, dest):
    """Join the selected pages of an index-only docs site into docs-pages.txt; describe them in SOURCE.txt."""
    parts, notes = [], []
    for index, pattern, page_url, cite_url in doc_pages(config_id):
        text = get(index).decode("utf-8", "replace")
        if text.lstrip().startswith("["):  # a JSON list of paths
            found = [x for x in json.loads(text) if re.fullmatch(pattern, x)]
        else:
            found = [m.group(0) for m in re.finditer(pattern, text)]
        found = list(dict.fromkeys(found))
        failed = []
        for item in found:
            try:
                body = get(page_url.format(item)).decode("utf-8", "replace")
            except Exception as error:  # a page the index lists but the site does not serve
                failed.append(f"{item} ({type(error).__name__})")
                continue
            parts.append(f"Source: {re.sub(r'[.]md$', '', cite_url.format(item))}\n\n{body.strip()}\n")
        missing = f", failed: {'; '.join(failed)}" if failed else ""
        notes.append(f"docs pages: index {index}, pages matching {pattern}: {len(found)} listed, "
                     f"{len(found) - len(failed)} fetched{missing}\n")
        print(f"{config_id}: {index}: {len(found) - len(failed)} of {len(found)} pages")
    data = ("\n\n" + "=" * 80 + "\n").join(parts).encode("utf-8")
    (dest / "docs-pages.txt").write_bytes(data)
    with (dest / "SOURCE.txt").open("a", encoding="utf-8") as f:
        f.write("".join(notes))
        f.write(f"docs: docs-pages.txt joins those pages as served on {datetime.date.today().isoformat()}, "
                f"{len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}; the site has no full-text export, "
                "and pages outside the selection were not fetched\n"
                "docs cite as: evidence kind official_doc; the URL on the Source: line above the passage\n")


def pinned(config_id):
    """((repository, commit) for every commit in version_or_commit that can be placed, primary first; ids left out)."""
    raw = (CONFIGS / f"{config_id}.json").read_text(encoding="utf-8")
    version = json.loads(raw)["version_or_commit"]
    shas = list(dict.fromkeys(re.findall(r"\b[0-9a-f]{40}\b", version)))
    if any(config_id.startswith(key) for key in NO_PUBLIC_SOURCE):
        return [], []
    if not shas:
        if docs_url(config_id) or doc_pages(config_id):
            return [], []
        raise SystemExit(f"{config_id}: no 40-hex commit in version_or_commit and no docs export listed")
    found, unplaced = [], []
    for sha in shas:
        m = (re.search(r"https://github\.com/([^/\s\"]+/[^/\s\"]+)/blob/" + sha, raw)
             or re.search(r"(?<![\w./@-])([A-Za-z0-9][\w.-]*/[\w.-]+)(?![\w/])[^；;。]*?提交 " + sha, version))
        if m:
            found.append((m.group(1), sha))
        elif sha == shas[0]:
            raise SystemExit(f"{config_id}: no evidence URL carries commit {sha}")
        else:
            unplaced.append(sha)
    return found, unplaced


def fetch(config_id):
    sources, unplaced = pinned(config_id)
    dest = OUT / config_id
    dest.mkdir(parents=True, exist_ok=True)
    for old in [*dest.glob("src*.tar.gz.*"), *dest.glob("docs-llms-full.txt"), *dest.glob("docs-pages.txt")]:
        old.unlink()
    lines = [f"config_id: {config_id}\n"]
    if not sources:
        lines.append("source: none (closed-source product; the official docs below are the only material)\n")
    for n, (repo, sha) in enumerate(sources):
        stem = "src" if n == 0 else "src-" + repo.split("/")[1]
        data = subprocess.run(["gh", "api", f"repos/{repo}/tarball/{sha}"], capture_output=True, check=True,
                              timeout=900).stdout
        if data[:2] != b"\x1f\x8b":
            raise SystemExit(f"{config_id}: download of {repo} is not a gzip archive")
        pieces = [data[i:i + PIECE] for i in range(0, len(data), PIECE)]
        for k, piece in enumerate(pieces):
            (dest / f"{stem}.tar.gz.{k:02d}").write_bytes(piece)
        lines.append(
            f"repository: https://github.com/{repo}\ncommit: {sha}\n"
            f"archive: GitHub source archive of that commit, {len(data)} bytes, "
            f"sha256 {hashlib.sha256(data).hexdigest()}\n"
            f"pieces: {len(pieces)} ({stem}.tar.gz.00 ...)\n"
            f"unpack: d=$(mktemp -d) && cat {stem}.tar.gz.* | tar -xzf - -C \"$d\" --strip-components=1\n"
            f"cite as: https://github.com/{repo}/blob/{sha}/<path inside the archive>\n")
        print(f"{config_id}: {repo}@{sha[:10]} {len(data) / 1e6:.1f} MB in {len(pieces)} piece(s)")
    for sha in unplaced:
        lines.append(f"not fetched: {sha} is named in version_or_commit but no repository could be found for it\n")
        print(f"{config_id}: NOT FETCHED {sha}: no evidence URL and no owner/repo before it in version_or_commit",
              file=sys.stderr)
    (dest / "SOURCE.txt").write_text("".join(lines), encoding="utf-8")
    url = docs_url(config_id)
    if url:
        docs = urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=300).read()
        (dest / "docs-llms-full.txt").write_bytes(docs)
        with (dest / "SOURCE.txt").open("a", encoding="utf-8") as f:
            f.write(f"docs: docs-llms-full.txt is {url} as served on {datetime.date.today().isoformat()}, "
                    f"{len(docs)} bytes, sha256 {hashlib.sha256(docs).hexdigest()}\n"
                    "docs cite as: evidence kind official_doc; the page URL where the file gives one (a Source: line), "
                    "otherwise the docs site address plus the section heading\n")
        print(f"{config_id}: docs export {len(docs) / 1e6:.1f} MB")
    if doc_pages(config_id):
        fetch_pages(config_id, dest)


if __name__ == "__main__":
    ids = sys.argv[1:]
    if not ids:
        sys.exit(__doc__)
    if ids == ["all"]:
        ids = sorted(p.stem for p in CONFIGS.glob("*.json"))
    for config_id in ids:
        fetch(config_id)
