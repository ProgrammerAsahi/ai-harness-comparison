#!/usr/bin/env python3
"""MIT. Compare independent codings of the same configuration, field by field.

For every configuration coded by two or more coders, each coder pair is compared on all
codebook fields. Output: per-pair agreement rates and a per-field disagreement summary,
ordered by field so the codebook can be revised where coders part ways (report §14.1).
Codings are validated first; invalid data stops the comparison.

  python3 studies/harness-quantification/compare_codings.py [--config ID ...] [--coders a,b] [--json]
  python3 studies/harness-quantification/compare_codings.py --fixtures     synthetic fixtures
"""
import argparse
import itertools
import json
import sys
from collections import defaultdict

from validate_data import DATA, FIXTURES, Context, validate_tree

KNOWN = ("known", "known_absent")


def _norm(field, value):
    return sorted(value) if field["type"] in ("set", "conditional_set") and isinstance(value, list) else value


def compare_entry(field, a, b):
    """Classify one field for one coder pair."""
    sa, sb = a["status"], b["status"]
    out = {"field": field["id"]}
    if sa in KNOWN and sb in KNOWN:
        va, vb = _norm(field, a["value"]), _norm(field, b["value"])
        if va == vb:
            out["outcome"] = "agree_value"
        else:
            out["outcome"] = "value_differs"
            if isinstance(va, list):
                union = set(va) | set(vb)
                out["jaccard_distance"] = round(1 - len(set(va) & set(vb)) / len(union), 4) if union else 0.0
    elif sa == sb == "unknown":
        out["outcome"] = "agree_unknown"
        if a.get("unknown_reason") != b.get("unknown_reason"):
            out["reason_differs"] = True
    elif sa == sb == "not_applicable":
        out["outcome"] = "agree_not_applicable"
    else:
        out["outcome"] = "status_differs"
    return out


def compare_pair(schema, rec_a, rec_b):
    fields = {f["id"]: f for f in schema["fields"]}
    rows = [compare_entry(fields[fid], rec_a["fields"][fid], rec_b["fields"][fid]) for fid in fields]
    n = len(rows)
    count = defaultdict(int)
    for r in rows:
        count[r["outcome"]] += 1
    agree = count["agree_value"] + count["agree_unknown"] + count["agree_not_applicable"]
    both_known = count["agree_value"] + count["value_differs"]
    return {
        "fields": n,
        "outcomes": {k: v for k, v in sorted(count.items()) if v},
        "agreement_rate": round(agree / n, 4),
        "known_agreement_rate": round(count["agree_value"] / both_known, 4) if both_known else None,
        "both_known": both_known,
        "rows": rows,
    }


def _show(entry):
    if entry["status"] in KNOWN:
        return json.dumps(entry["value"], ensure_ascii=False)
    if entry["status"] == "unknown":
        return f"unknown({entry.get('unknown_reason')})"
    return entry["status"]


def compare_tree(root, ctx, configs=None, coders=None):
    errors = validate_tree(root, ctx)
    if errors:
        return None, errors
    by_config = defaultdict(dict)
    for p in sorted((root / "codings").glob("*/*.json")):
        rec = json.loads(p.read_text())
        if configs and rec["config_id"] not in configs:
            continue
        if coders and rec["coder"]["id"] not in coders:
            continue
        by_config[rec["config_id"]][rec["coder"]["id"]] = rec
    pairs, per_field = [], defaultdict(lambda: {"compared": 0, "agree": 0, "status_differs": 0, "value_differs": 0,
                                                 "reason_differs": 0, "cases": [], "proposals": []})
    for cid, recs in sorted(by_config.items()):
        for ca, cb in itertools.combinations(sorted(recs), 2):
            result = compare_pair(ctx.schema, recs[ca], recs[cb])
            pairs.append({"config_id": cid, "coders": [ca, cb],
                          **{k: v for k, v in result.items() if k != "rows"}})
            for row in result["rows"]:
                fid, s = row["field"], per_field[row["field"]]
                s["compared"] += 1
                if row["outcome"].startswith("agree"):
                    s["agree"] += 1
                else:
                    s[row["outcome"]] += 1
                    case = {"config_id": cid, ca: _show(recs[ca]["fields"][fid]), cb: _show(recs[cb]["fields"][fid]),
                            "outcome": row["outcome"]}
                    if "jaccard_distance" in row:
                        case["jaccard_distance"] = row["jaccard_distance"]
                    s["cases"].append(case)
                if row.get("reason_differs"):
                    s["reason_differs"] += 1
                    s["cases"].append({"config_id": cid, ca: _show(recs[ca]["fields"][fid]),
                                       cb: _show(recs[cb]["fields"][fid]), "outcome": "unknown_reason_differs"})
        for coder, rec in sorted(recs.items()):
            for fid, entry in rec["fields"].items():
                for prop in entry.get("vocabulary_proposals", []):
                    per_field[fid]["proposals"].append({"config_id": cid, "coder": coder, **prop})
    fields_out = []
    for f in ctx.schema["fields"]:
        s = per_field.get(f["id"])
        if not s:
            continue
        fields_out.append({"field": f["id"], "question": f["question"],
                           "needs_definition": bool(f.get("needs_definition")),
                           "agreement_rate": round(s["agree"] / s["compared"], 4) if s["compared"] else None, **s})
    return {"pairs": pairs, "fields": fields_out,
            "note": "Agreement counts equal statuses and equal values; both-unknown is counted as agreement on status "
                    "but reported separately, because it carries no shared evidence (report §8.1)."}, []


def render_text(result):
    out = ["# Pair agreement"]
    for p in result["pairs"]:
        o = p["outcomes"]
        known = "n/a" if p["known_agreement_rate"] is None else f"{p['known_agreement_rate']:.0%}"
        out.append(f"{p['config_id']}  {p['coders'][0]} vs {p['coders'][1]}: agreement {p['agreement_rate']:.0%} "
                   f"({p['fields']} fields); both known {p['both_known']}, agreeing {known}; "
                   f"both unknown {o.get('agree_unknown', 0)}; status differs {o.get('status_differs', 0)}; "
                   f"value differs {o.get('value_differs', 0)}")
    out += ["", "# Fields with disagreements or proposals (codebook revision list)"]
    shown = 0
    for f in result["fields"]:
        if not f["cases"] and not f["proposals"] and not f["reason_differs"]:
            continue
        shown += 1
        flag = " [needs_definition]" if f["needs_definition"] else ""
        out.append(f"{f['field']} {f['question']}{flag}: agreement {f['agreement_rate']:.0%} over {f['compared']}; "
                   f"status differs {f['status_differs']}, value differs {f['value_differs']}, "
                   f"unknown reasons differ {f['reason_differs']}")
        for c in f["cases"]:
            detail = ", ".join(f"{k}={v}" for k, v in c.items() if k not in ("config_id", "outcome"))
            out.append(f"  - {c['config_id']} {c['outcome']}: {detail}")
        for p in f["proposals"]:
            out.append(f"  + proposal by {p['coder']} on {p['config_id']}: {p['value']} — {p['definition']}")
    if not shown:
        out.append("(none)")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", action="append", help="limit to these config ids")
    ap.add_argument("--coders", help="comma-separated coder ids to compare")
    ap.add_argument("--fixtures", action="store_true", help="compare the synthetic fixtures instead of real data")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)
    root = FIXTURES if args.fixtures else DATA
    ctx = Context(synthetic=args.fixtures)
    result, errors = compare_tree(root, ctx, args.config, args.coders.split(",") if args.coders else None)
    if errors:
        print("Validation failed; fix these before comparing:", *errors, sep="\n")
        return 1
    if not result["pairs"]:
        print("No configuration has two codings yet.")
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
