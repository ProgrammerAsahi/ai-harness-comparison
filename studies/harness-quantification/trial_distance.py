#!/usr/bin/env python3
"""MIT. Trial structural distance on the real pilot codings (report sections 5.5, 7 and 8).

Not a rating and not a result: the codings are unadjudicated first drafts by two coders,
made under codebooks fields-0.5 to fields-0.10. The trial asks how far distances computed
from them are stable across coders, gate costs and evidence coverage.

  python3 studies/harness-quantification/trial_distance.py            # summary tables
  python3 studies/harness-quantification/trial_distance.py --json F   # also write all pairs to F

Rules (fixed before looking at results):
- Each config uses its latest coding: recode rounds over batches, later batches over earlier.
- Nine groups weigh 1/9 each, four fields per group weigh equally inside it.
- Nominal: same 0, different 1. Set and conditional set: Jaccard distance, two known empty sets 0.
- known and known_absent are values; unknown removes the field from the observed part and keeps
  its weight for coverage and bounds (section 8.2). Facets are not used.
- Group G is a conditional subtree (section 5.5): F25 unknown on either side makes the whole group
  unknown; both absent makes the whole group known and equal; one present and one absent makes the
  whole group known with difference = gate cost; both present compares F25 (equal) and F26-F28.
- Three codings per config: each coder alone, and "agreed", which keeps a field only where both
  coders have the same status class and value and treats it as unknown otherwise.
"""
import argparse
import itertools
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
KNOWN = ("known", "known_absent")
GATE, DEPENDENTS = "F25", ("F26", "F27", "F28")
GATE_COSTS = (0.5, 0.75, 1.0)
BASE_GATE = 0.75
CODERS = ("opus", "gpt")
VARIANTS = CODERS + ("agreed",)
# relationships stated in the profiles; used only to see where such pairs fall, not as a target
RELATED = [("A09", "A17", "Step Code derives from Pi"), ("A09", "D05", "the omo engine senpi is a Pi fork"),
           ("A17", "D05", "both derive from Pi"), ("A08", "A11", "Kilo CLI is an OpenCode fork"),
           ("D03", "D04", "same maintainers, deliberately smaller")]


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def latest_codings(root=HERE):
    """config_id -> (round, {coder: record}); recode codings in data/codings win over batch archives."""
    out = {}
    for b in sorted((root / "batches").glob("batch-*/")):
        for p in (b / "opus").glob("*.json"):
            out[p.stem] = (b.name, {c: load_json(b / c / p.name) for c in CODERS})
    for p in (root / "data" / "codings" / "opus").glob("*.json"):
        rec = {c: load_json(root / "data" / "codings" / c / p.name) for c in CODERS}
        out[p.stem] = (rec["opus"]["round"], rec)
    return out


def agreed(a, b, schema):
    """Keep fields where both coders agree on status class and value; others become unknown."""
    out = {}
    for f in schema["fields"]:
        x, y = a[f["id"]], b[f["id"]]
        if x["status"] in KNOWN and y["status"] in KNOWN:
            vx, vy = x["value"], y["value"]
            same = sorted(vx) == sorted(vy) if isinstance(vx, list) and isinstance(vy, list) else vx == vy
            out[f["id"]] = {"status": "known", "value": vx} if same else {"status": "unknown"}
        elif x["status"] == y["status"] == "not_applicable":
            out[f["id"]] = {"status": "not_applicable"}
        else:
            out[f["id"]] = {"status": "unknown"}
    return out


def field_diff(field, x, y):
    if x["status"] not in KNOWN or y["status"] not in KNOWN:
        return None
    a, b = x["value"], y["value"]
    if field["type"] == "nominal":
        return float(a != b)
    sa, sb = set(a), set(b)
    return 1 - len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def distance(left, right, schema, gate_cost=BASE_GATE):
    """Return observed distance, coverage, bounds and per-group coverage for two field dicts."""
    fields = {f["id"]: f for f in schema["fields"]}
    known = contribution = 0.0
    groups = {}
    for g in schema["groups"]:
        gw, fw = 1 / len(schema["groups"]), 1 / len(schema["groups"]) / len(g["fields"])
        gk = gc = 0.0
        if GATE in g["fields"]:
            x, y = left[GATE], right[GATE]
            if x["status"] in KNOWN and y["status"] in KNOWN:
                px, py = x["value"] == "present", y["value"] == "present"
                if px != py:
                    gk, gc = gw, gw * gate_cost
                elif not px:
                    gk = gw
                else:
                    gk = fw
                    for fid in DEPENDENTS:
                        d = field_diff(fields[fid], left[fid], right[fid])
                        if d is not None:
                            gk += fw
                            gc += fw * d
        else:
            for fid in g["fields"]:
                d = field_diff(fields[fid], left[fid], right[fid])
                if d is not None:
                    gk += fw
                    gc += fw * d
        groups[g["id"]] = round(gk / gw, 4)
        known += gk
        contribution += gc
    d_obs = contribution / known if known else None
    return {"d_obs": d_obs, "coverage": known, "bounds": [contribution, contribution + 1 - known], "groups": groups}


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(xs, ys):
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def compute(root=HERE):
    schema = load_json(root / "data" / "schema" / "fields.json")
    codings = latest_codings(root)
    configs = {p.stem: load_json(p) for p in (root / "data" / "configs").glob("*.json")}
    closed = {c for c, r in configs.items() if not any(e.get("evidence_kind") == "source_path" for e in r.get("evidence", []))}
    fields = {}
    for cid, (_, rec) in codings.items():
        fields[cid, "opus"] = rec["opus"]["fields"]
        fields[cid, "gpt"] = rec["gpt"]["fields"]
        fields[cid, "agreed"] = agreed(rec["opus"]["fields"], rec["gpt"]["fields"], schema)
    ids = sorted(codings)
    pairs = []
    for a, b in itertools.combinations(ids, 2):
        row = {"a": a, "b": b, "kind": {0: "open-open", 1: "mixed", 2: "closed-closed"}[(a in closed) + (b in closed)]}
        for v in VARIANTS:
            for g in GATE_COSTS:
                row[v, g] = distance(fields[a, v], fields[b, v], schema, g)
        pairs.append(row)
    return {"schema": schema, "codings": codings, "configs": configs, "closed": closed, "ids": ids, "pairs": pairs}


def round_agreement(res, root=HERE):
    """Inter-coder agreement per round, recomputed with compare_codings.compare_pair under the current codebook."""
    from compare_codings import compare_pair
    schema, closed = res["schema"], res["closed"]
    rounds = [(b.name, b) for b in sorted((root / "batches").glob("batch-*/"))]
    rounds.append(("recode-1", root / "data" / "codings"))
    out = ["round | codebook | configs | mean agreement | closed (n) | open (n) | agree-value among both-known"]
    for name, base in rounds:
        rates, cl, op, av, bk, cb = [], [], [], 0, 0, set()
        for p in sorted((base / "opus").glob("*.json")):
            a, b = load_json(p), load_json(base / "gpt" / p.name)
            if a["round"] != name:
                continue
            r = compare_pair(schema, a, b)
            rates.append(r["agreement_rate"])
            (cl if p.stem in closed else op).append(r["agreement_rate"])
            av += r["outcomes"].get("agree_value", 0)
            bk += r["both_known"]
            cb.add(a["codebook_version"])
        m = lambda xs: f"{100 * statistics.fmean(xs):.1f}% ({len(xs)})" if xs else "- (0)"
        out.append(f"{name} | {', '.join(sorted(cb))} | {len(rates)} | {100 * statistics.fmean(rates):.1f}% | {m(cl)} | {m(op)} | {100 * av / bk:.1f}%")
    return "\n".join(out)


def summarize(res):
    pairs, ids, closed, configs = res["pairs"], res["ids"], res["closed"], res["configs"]
    name = lambda c: f"{c[:3]} {configs[c]['product']}"
    pct = lambda x: f"{100 * x:.1f}%"
    out = ["## inter-coder agreement by round", round_agreement(res), ""]
    out.append(f"configs {len(ids)} (closed {len(closed & set(ids))}), pairs {len(pairs)}")
    rounds = {}
    for cid, (rnd, rec) in res["codings"].items():
        rounds.setdefault(rnd, []).append(rec["opus"]["codebook_version"])
    out.append("codings used by round: " + ", ".join(f"{r} {len(v)} ({sorted(set(v))[0]})" for r, v in sorted(rounds.items())))

    out.append("\n## coverage (agreed, gate 0.75): median [min, max] by pair kind")
    for kind in ("open-open", "mixed", "closed-closed", None):
        sel = [p["agreed", BASE_GATE]["coverage"] for p in pairs if kind in (None, p["kind"])]
        out.append(f"{kind or 'all'}: n={len(sel)} median {pct(statistics.median(sel))} [{pct(min(sel))}, {pct(max(sel))}]")
    for v in CODERS:
        sel = [p[v, BASE_GATE]["coverage"] for p in pairs]
        out.append(f"{v} alone: median coverage {pct(statistics.median(sel))}")

    out.append("\n## rank agreement of observed distances across pairs (Spearman)")
    def col(v, g, kind=None):
        return [p[v, g]["d_obs"] for p in pairs if kind in (None, p["kind"])]
    for kind in (None, "open-open", "mixed", "closed-closed"):
        o, g_, a = col("opus", BASE_GATE, kind), col("gpt", BASE_GATE, kind), col("agreed", BASE_GATE, kind)
        out.append(f"{kind or 'all'}: opus~gpt {spearman(o, g_):.3f}, opus~agreed {spearman(o, a):.3f}, gpt~agreed {spearman(g_, a):.3f}")
    for v in VARIANTS:
        out.append(f"gate cost, {v}: 0.5~0.75 {spearman(col(v, 0.5), col(v, 0.75)):.3f}, 0.75~1 {spearman(col(v, 0.75), col(v, 1.0)):.3f}, 0.5~1 {spearman(col(v, 0.5), col(v, 1.0)):.3f}")
    gap = [abs(p["opus", BASE_GATE]["d_obs"] - p["gpt", BASE_GATE]["d_obs"]) for p in pairs]
    out.append(f"|d_opus - d_gpt|: median {statistics.median(gap):.3f}, 90th pct {sorted(gap)[int(0.9 * len(gap))]:.3f}, max {max(gap):.3f}")

    def neighbours(v, cid, k=3):
        rows = [(p[v, BASE_GATE]["d_obs"], p["b"] if p["a"] == cid else p["a"], p[v, BASE_GATE]["coverage"])
                for p in pairs if cid in (p["a"], p["b"])]
        return sorted(rows)[:k]
    overlap = [len({n for _, n, _ in neighbours("opus", c)} & {n for _, n, _ in neighbours("gpt", c)}) for c in ids]
    out.append(f"top-3 neighbours shared by opus and gpt: mean {statistics.fmean(overlap):.2f} of 3; "
               f"0 shared {overlap.count(0)}, 1 {overlap.count(1)}, 2 {overlap.count(2)}, 3 {overlap.count(3)}")

    out.append("\n## nearest neighbours (agreed, gate 0.75): d_obs / coverage; [opus top-1, gpt top-1]")
    for c in ids:
        nb = neighbours("agreed", c)
        o1, g1 = neighbours("opus", c, 1)[0][1], neighbours("gpt", c, 1)[0][1]
        out.append(f"{name(c)}{' (closed)' if c in closed else ''}: " + "; ".join(f"{n[:3]} {d:.2f}/{pct(cv)}" for d, n, cv in nb)
                   + f"  [{o1[:3]}, {g1[:3]}]")

    out.append("\n## related pairs: rank of the partner among the others (1 = nearest), per coding")
    for a, b, why in RELATED:
        ca, cb = next(c for c in ids if c.startswith(a)), next(c for c in ids if c.startswith(b))
        cells = []
        for v in VARIANTS:
            ds = sorted((p[v, BASE_GATE]["d_obs"], p["b"] if p["a"] == ca else p["a"]) for p in pairs if ca in (p["a"], p["b"]))
            r = 1 + sum(d < next(x for x, n in ds if n == cb) for d, _ in ds)
            row = next(p for p in pairs if {p["a"], p["b"]} == {ca, cb})[v, BASE_GATE]
            cells.append(f"{v} #{r} d={row['d_obs']:.2f} cov={pct(row['coverage'])}")
        out.append(f"{a}-{b} ({why}): " + "; ".join(cells))

    out.append("\n## diagnostics (gate 0.75)")
    for kind in ("open-open", "mixed", "closed-closed"):
        out.append(f"mean d_obs {kind}: " + ", ".join(f"{v} {statistics.fmean(col(v, BASE_GATE, kind)):.3f}" for v in VARIANTS))
    for v in VARIANTS:
        out.append(f"{v}: Spearman(coverage, d_obs) {spearman([p[v, BASE_GATE]['coverage'] for p in pairs], col(v, BASE_GATE)):.3f}")
    gids = [g["id"] for g in res["schema"]["groups"]]
    for label, sel in (("open", [c for c in ids if c not in closed]), ("closed", [c for c in ids if c in closed])):
        cov = {g: [] for g in gids}
        for c in sel:
            for p in pairs:
                if c in (p["a"], p["b"]):
                    for g in gids:
                        cov[g].append(p["agreed", BASE_GATE]["groups"][g])
        out.append(f"agreed group coverage, pairs touching a {label} config: " + " ".join(f"{g} {100 * statistics.fmean(cov[g]):.0f}" for g in gids))
    rnd = {c: res["codings"][c][0] for c in ids}
    for v in VARIANTS:
        same = [p[v, BASE_GATE]["d_obs"] for p in pairs if rnd[p["a"]] == rnd[p["b"]]]
        cross = [p[v, BASE_GATE]["d_obs"] for p in pairs if rnd[p["a"]] != rnd[p["b"]]]
        out.append(f"{v}: same-round pairs n={len(same)} mean d {statistics.fmean(same):.3f}; cross-round n={len(cross)} mean d {statistics.fmean(cross):.3f}")
    oo = [p for p in pairs if p["kind"] == "open-open"]
    for v in VARIANTS:
        same = [p[v, BASE_GATE]["d_obs"] for p in oo if rnd[p["a"]] == rnd[p["b"]]]
        cross = [p[v, BASE_GATE]["d_obs"] for p in oo if rnd[p["a"]] != rnd[p["b"]]]
        out.append(f"{v}, open-open only: same-round mean d {statistics.fmean(same):.3f} (n={len(same)}); cross-round {statistics.fmean(cross):.3f} (n={len(cross)})")

    d_all = [p["agreed", BASE_GATE]["d_obs"] for p in pairs]
    w = [p["agreed", BASE_GATE]["bounds"][1] - p["agreed", BASE_GATE]["bounds"][0] for p in pairs]
    out.append(f"\nagreed d_obs: median {statistics.median(d_all):.3f} [{min(d_all):.3f}, {max(d_all):.3f}]; bound width median {statistics.median(w):.3f}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    res = compute()
    print(summarize(res))
    if args.json:
        rows = [{"a": p["a"], "b": p["b"], "kind": p["kind"],
                 **{f"{v}@{g}": {k: (round(x, 4) if isinstance(x, float) else [round(y, 4) for y in x] if isinstance(x, list) else x)
                                 for k, x in p[v, g].items()} for v in VARIANTS for g in GATE_COSTS}} for p in res["pairs"]]
        Path(args.json).write_text(json.dumps({"note": "trial only; unadjudicated codings; see batches/cross-batch.md", "pairs": rows},
                                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
