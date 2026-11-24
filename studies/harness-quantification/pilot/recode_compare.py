"""Compare a recode round with the batches its configs were first coded in.

  python3 studies/harness-quantification/pilot/recode_compare.py [round]      # default: recode-1

For each config the round lists with role "recode", three pairs are compared field by field with
compare_codings.compare_pair under the current codebook: the two original codings (archived in
batches/<original round>/), the two new codings (data/codings/), and each coder's new coding against
its own original. Fields are split into those whose definition the latest codebook revision touched
(REVISED) and the rest. Agreement counts the same outcomes as compare_codings.py and has no chance
correction. Run from the repository root.
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


def main(name="recode-1"):
    data = HERE / "data"
    schema = load(data / "schema" / "fields.json")
    rnd = load(data / "rounds" / f"{name}.json")
    rows, per_field = [], defaultdict(lambda: [0, 0])
    for t in rnd["tools"]:
        if t.get("role") != "recode":
            continue
        cid = t["config_id"]
        first = load(data / "configs" / f"{cid}.json")["round"]
        old = {c: load(HERE / "batches" / first / c / f"{cid}.json") for c in ("opus", "gpt")}
        new = {c: load(data / "codings" / c / f"{cid}.json") for c in ("opus", "gpt")}
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
        rows.append((cid, first, po["agreement_rate"], pn["agreement_rate"], selfs, split))

    pct = lambda x: f"{100 * x:.0f}"
    print("config | first round | original pair | new pair | change | opus new vs old | gpt new vs old | revised fields old->new | other fields old->new")
    for cid, first, o, n, s, sp in rows:
        r0, r1, u0, u1 = sp["old", True], sp["new", True], sp["old", False], sp["new", False]
        print(f"{cid} | {first} | {pct(o)} | {pct(n)} | {100 * (n - o):+.0f} | {pct(s['opus'])} | {pct(s['gpt'])} | "
              f"{r0[0]}/{r0[1]} -> {r1[0]}/{r1[1]} | {u0[0]}/{u0[1]} -> {u1[0]}/{u1[1]}")
    k = len(rows)
    mean = lambda i: sum(r[i] for r in rows) / k
    print(f"mean over {k}: original {100 * mean(2):.1f}, new {100 * mean(3):.1f}, "
          f"opus self {100 * sum(r[4]['opus'] for r in rows) / k:.1f}, gpt self {100 * sum(r[4]['gpt'] for r in rows) / k:.1f}")
    print("field | configs agreeing, original -> new")
    for fid in sorted(per_field, key=lambda f: (per_field[f][1] - per_field[f][0], f)):
        a, b = per_field[fid]
        if a != b:
            print(f"{fid}{'*' if fid in REVISED else ''} | {a} -> {b}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
