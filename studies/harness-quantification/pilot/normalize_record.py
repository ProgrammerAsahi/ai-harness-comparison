#!/usr/bin/env python3
"""MIT. Mechanical clean-up of a configuration-record draft before it goes into data/configs/.

Only formatting is touched, never facts:
  1. evidence items: keys lines, content_sha256 and version are dropped when their value is "";
  2. evidence item keys are put in the fixed order evidence_kind, source_url, locator, lines,
     version, retrieved_at, content_sha256, configuration_scope, note (other keys follow, in
     their original relative order);
  3. product paths like /home/<name>/... in every string except source_url values are wrapped in
     backticks so validate_data.py's machine-path check does not flag them; a path counts only
     when it is not preceded by a letter, digit, backtick, slash, dot, tilde or hyphen, and
     anything already inside a backtick code span is left alone;
  4. with --product-from-catalog, the top-level product becomes the catalog name of its tool_id
     (research/catalog.json, the same file as validate_data.CATALOG_PATH).
Output is JSON with ensure_ascii=False, indent=2 and a trailing newline. One line per record
reports what changed; --check writes nothing and exits 1 when something would change.

  python3 studies/harness-quantification/pilot/normalize_record.py IN.json [OUT.json]   # OUT omitted: in place
  python3 studies/harness-quantification/pilot/normalize_record.py --check IN.json
  python3 studies/harness-quantification/pilot/normalize_record.py --product-from-catalog IN.json [OUT.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
import validate_data as vd  # noqa: E402

CATALOG_PATH = vd.CATALOG_PATH
EVIDENCE_ORDER = (
    "evidence_kind", "source_url", "locator", "lines", "version",
    "retrieved_at", "content_sha256", "configuration_scope", "note",
)
DROP_IF_EMPTY = ("lines", "content_sha256", "version")
# A product path: /home/<name>[/...], ASCII non-space characters up to a quote, bracket or backtick.
HOME_PATH = re.compile(r"(?<![A-Za-z0-9`/.~-])/home/[^/\s`'\"()<>]+(?:/[^\s`'\"()<>]*)?")
TRAILING = ".,;:!?"
CODE_RUN = re.compile(r"`+")


def _segments(text):
    """Split text into (is_code, piece); a code span is a backtick run closed by a run of equal length."""
    out, pos, i = [], 0, 0
    runs = list(CODE_RUN.finditer(text))
    while i < len(runs):
        opener = runs[i]
        close = next((j for j in range(i + 1, len(runs)) if len(runs[j].group()) == len(opener.group())), None)
        if close is None:
            i += 1
            continue
        if opener.start() > pos:
            out.append((False, text[pos:opener.start()]))
        out.append((True, text[opener.start():runs[close].end()]))
        pos = runs[close].end()
        i = close + 1
    if pos < len(text):
        out.append((False, text[pos:]))
    return out


def backtick_paths(text):
    """Return (new_text, count) with bare /home/<name>/... paths outside code spans wrapped in backticks."""
    count = 0

    def wrap(m):
        nonlocal count
        path = m.group().rstrip(TRAILING)
        count += 1
        return f"`{path}`{m.group()[len(path):]}"

    pieces = [p if code else HOME_PATH.sub(wrap, p) for code, p in _segments(text)]
    return "".join(pieces), count


def _backtick_tree(obj, key=None):
    if isinstance(obj, str):
        return (obj, 0) if key == "source_url" else backtick_paths(obj)
    if isinstance(obj, dict):
        total, out = 0, {}
        for k, v in obj.items():
            out[k], n = _backtick_tree(v, k)
            total += n
        return out, total
    if isinstance(obj, list):
        total, out = 0, []
        for v in obj:
            v, n = _backtick_tree(v)
            out.append(v)
            total += n
        return out, total
    return obj, 0


def load_catalog(path=None):
    return {t["id"]: t["name"] for t in json.loads(Path(path or CATALOG_PATH).read_text(encoding="utf-8"))}


def normalize(rec, catalog=None):
    """Return (new_record, changes); changes is a list of short descriptions, empty when nothing changed."""
    changes = []
    rec = dict(rec)
    evidence = rec.get("evidence")
    if isinstance(evidence, list):
        dropped = reordered = 0
        items = []
        for item in evidence:
            if not isinstance(item, dict):
                items.append(item)
                continue
            kept = {k: v for k, v in item.items() if not (k in DROP_IF_EMPTY and v == "")}
            dropped += len(item) - len(kept)
            known = [k for k in EVIDENCE_ORDER if k in kept]
            ordered = {k: kept[k] for k in known + [k for k in kept if k not in EVIDENCE_ORDER]}
            if list(ordered) != list(kept):
                reordered += 1
            items.append(ordered)
        rec["evidence"] = items
        if dropped:
            changes.append(f"dropped {dropped} empty evidence key(s)")
        if reordered:
            changes.append(f"reordered keys in {reordered} evidence item(s)")
    rec, wrapped = _backtick_tree(rec)
    if wrapped:
        changes.append(f"backticked {wrapped} /home/ path(s)")
    if catalog is not None:
        tool_id = rec.get("tool_id")
        if tool_id not in catalog:
            raise KeyError(f"tool_id {tool_id!r} is not in the catalog")
        if rec.get("product") != catalog[tool_id]:
            changes.append(f"product {rec.get('product')!r} -> {catalog[tool_id]!r}")
            rec["product"] = catalog[tool_id]
    return rec, changes


def dump(rec):
    return json.dumps(rec, ensure_ascii=False, indent=2) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mechanical clean-up of a configuration-record draft.")
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path, nargs="?")
    ap.add_argument("--check", action="store_true", help="report what would change; write nothing; exit 1 on changes")
    ap.add_argument("--product-from-catalog", action="store_true", help="set product to the catalog name of tool_id")
    ap.add_argument("--catalog", type=Path, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        rec = json.loads(args.input.read_text(encoding="utf-8"))
        catalog = load_catalog(args.catalog) if args.product_from_catalog else None
        new, changes = normalize(rec, catalog)
    except (OSError, ValueError, KeyError) as e:
        print(f"{args.input}: error: {e}", file=sys.stderr)
        return 2
    print(f"{args.input}: {'; '.join(changes) if changes else 'no changes'}")
    if args.check:
        return 1 if changes else 0
    (args.output or args.input).write_text(dump(new), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
