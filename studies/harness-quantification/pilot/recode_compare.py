"""Compare a recode round with the batches its configs were first coded in.

  python3 studies/harness-quantification/pilot/recode_compare.py [round]      # default: recode-1

For each config the round lists with role "recode", three pairs are compared field by field with
compare_codings.compare_pair under the current codebook: the two original codings (archived in
batches/<original round>/), the two new codings (data/codings/ while the round is current,
batches/<round>/ once a codebook revision has archived it), and each coder's new coding against
its own original. Fields are split into those whose definition the latest codebook revision touched
(REVISED) and the rest. Agreement counts the same outcomes as compare_codings.py and has no chance
correction. compare_round computes and returns the numbers; main only prints them. Run from the
repository root.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from compare_codings import compare_pair  # noqa: E402

# fields whose definitions or values the fields-0.10 revision touched (definition-decisions-0.10.md)
REVISED = set("F04 F05 F06 F09 F10 F11 F12 F13 F16 F19 F21 F22 F23 F25 F26 F27 F28 F30 F33 F34 F35 F36".split())
AGREE = ("agree_value", "agree_unknown", "agree_not_applicable")


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def compare_round(name="recode-1", root=None):
    """Compare one recode round with the batches its configs were first coded in.

    root is the study directory (studies/harness-quantification), read only; it defaults to the
    repository's own study directory, so tests can pass a temporary one. Returns
    {"rows": [...], "per_field": {fid: [configs agreeing in the original batch,
    configs agreeing in this round]}}. Each row is one config: config_id, first_round (the
    original batch name), the original pair's and the new pair's agreement rates, each coder's
    new-vs-own-original agreement rate, and the (agreements, fields) split between the revised and
    the other fields in both rounds.
    """
    root = HERE if root is None else Path(root)
    data = root / "data"
    schema = load(data / "schema" / "fields.json")
    rnd = load(data / "rounds" / f"{name}.json")
    archived = root / "batches" / name
    newbase = archived if (archived / "opus").is_dir() else data / "codings"
    rows, per_field = [], defaultdict(lambda: [0, 0])
    for t in rnd["tools"]:
        if t.get("role") != "recode":
            continue
        cid = t["config_id"]
        first = load(data / "configs" / f"{cid}.json")["round"]
        old = {c: load(root / "batches" / first / c / f"{cid}.json") for c in ("opus", "gpt")}
        new = {c: load(newbase / c / f"{cid}.json") for c in ("opus", "gpt")}
        po, pn = compare_pair(schema, old["opus"], old["gpt"]), compare_pair(schema, new["opus"], new["gpt"])
        selfs = {c: compare_pair(schema, new[c], old[c])["agreement_rate"] for c in ("opus", "gpt")}
        split = {}
        for tag, pair in (("old", po), ("new", pn)):
            for rev in (True, False):
                part = [r for r in pair["rows"] if (r["field"] in REVISED) == rev]
                split[tag, rev] = (sum(r["outcome"] in AGREE for r in part), len(part))
        for a, b in zip(po["rows"], pn["rows"]):
            per_field[a["field"]][0] += a["outcome"] in AGREE
            per_field[a["field"]][1] += b["outcome"] in AGREE
        rows.append({
            "config_id": cid,
            "first_round": first,
            "original": po["agreement_rate"],
            "new": pn["agreement_rate"],
            "opus_self": selfs["opus"],
            "gpt_self": selfs["gpt"],
            "revised_old": split["old", True],
            "revised_new": split["new", True],
            "other_old": split["old", False],
            "other_new": split["new", False],
        })
    return {"rows": rows, "per_field": dict(per_field)}


def main(name="recode-1"):
    result = compare_round(name)
    rows, per_field = result["rows"], result["per_field"]
    pct = lambda x: f"{100 * x:.0f}"
    print("config | first round | original pair | new pair | change | opus new vs old | gpt new vs old | revised fields old->new | other fields old->new")
    for r in rows:
        print(f"{r['config_id']} | {r['first_round']} | {pct(r['original'])} | {pct(r['new'])} | "
              f"{100 * (r['new'] - r['original']):+.0f} | {pct(r['opus_self'])} | {pct(r['gpt_self'])} | "
              f"{r['revised_old'][0]}/{r['revised_old'][1]} -> {r['revised_new'][0]}/{r['revised_new'][1]} | "
              f"{r['other_old'][0]}/{r['other_old'][1]} -> {r['other_new'][0]}/{r['other_new'][1]}")
    k = len(rows)
    print(f"mean over {k}: original {100 * sum(r['original'] for r in rows) / k:.1f}, "
          f"new {100 * sum(r['new'] for r in rows) / k:.1f}, "
          f"opus self {100 * sum(r['opus_self'] for r in rows) / k:.1f}, "
          f"gpt self {100 * sum(r['gpt_self'] for r in rows) / k:.1f}")
    print("field | configs agreeing, original -> new")
    for fid in sorted(per_field, key=lambda f: (per_field[f][1] - per_field[f][0], f)):
        a, b = per_field[fid]
        if a != b:
            print(f"{fid}{'*' if fid in REVISED else ''} | {a} -> {b}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
