#!/usr/bin/env python3
"""MIT. Adjudicating the two coders' disagreements on each config's latest coding.

Only fields where compare_codings finds the two codings different (status or value; facets are
not adjudicated) are adjudicated, under the current codebook. Two readers judge each config blind:
the coders appear as 甲 and 乙 in a random order. Where the two readers settle on the same status
and value the field is settled; otherwise a third reader, or the research lead, decides. The
record in data/adjudications/<config_id>.json names the coder chosen (or "neither"), who settled
it and why. It is not a rating of any tool.

  python3 studies/harness-quantification/adjudicate.py prepare OUTDIR [--seed N]   # blinded inputs
  python3 studies/harness-quantification/adjudicate.py check                       # validate records
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare_codings as cc  # noqa: E402
import trial_distance as td  # noqa: E402
import validate_data as vd  # noqa: E402

ADJ = HERE / "data" / "adjudications"
SCHEMA_VERSION = "adjudication-0.1"
ROUND = "adjudication-1"
AGREE = ("agree_value", "agree_unknown", "agree_not_applicable")
CODERS = td.CODERS
CHOICES = CODERS + ("neither",)
SETTLED = ("readers_agree", "third_reader", "lead")
LABELS = ("甲", "乙")
TOP_KEYS = {"schema_version", "synthetic", "round", "config_id", "codebook_version", "codings",
            "adjudicated_at", "readers", "fields", "note"}
FIELD_KEYS = {"choice", "status", "value", "unknown_reason", "settled_by", "picks", "rationale", "evidence"}
ITEM_KEYS = {"field", "pick", "status", "value", "unknown_reason", "rationale", "evidence"}


def disagreements(schema, a, b):
    """Field ids where two coding records differ in status or value."""
    return [r["field"] for r in cc.compare_pair(schema, a, b)["rows"] if r["outcome"] not in AGREE]


def same(field, x, y):
    """Same status and value (sets compared as sets)."""
    if x.get("status") != y.get("status"):
        return False
    return vd._same(field, x.get("value"), y.get("value"))


def check_light(field, status, value, reason, ctx, where, errors):
    """Shape of a status/value pair without evidence cards (a reader's or lead's own reading)."""
    if status not in ctx.enums["status"]:
        errors.append(f"{where}: status {status!r} is not one of {sorted(ctx.enums['status'])}")
        return
    if status != "unknown" and reason is not None:
        errors.append(f"{where}: unknown_reason is only for status unknown")
    if status in ("known", "known_absent"):
        if value is None:
            errors.append(f"{where}: {status} needs a value")
            return
        n = len(errors)
        vd.check_value(field, value, where, errors)
        if len(errors) > n:
            return
        is_absent = "absent_value" in field and vd._same(field, value, field["absent_value"])
        if status == "known" and is_absent:
            errors.append(f"{where}: value means the mechanism is absent; use status known_absent")
        if status == "known_absent" and not is_absent:
            errors.append(f"{where}: known_absent needs the field's absent value")
    elif status == "unknown":
        if value is not None:
            errors.append(f"{where}: unknown must not carry a value")
        if reason not in ctx.enums["unknown_reason"]:
            errors.append(f"{where}: unknown needs unknown_reason {sorted(ctx.enums['unknown_reason'])}")
    elif status == "not_applicable":
        if value is not None:
            errors.append(f"{where}: not_applicable must not carry a value")
        if "condition" not in field:
            errors.append(f"{where}: {field['id']} has no precondition, so it cannot be not_applicable")


def blind_inputs(schema, codings, seed):
    """config_id -> ({label: coder}, {label: blinded record}); only configs with disagreements."""
    rng = random.Random(seed)
    out = {}
    for cid in sorted(codings):
        _, rec = codings[cid]
        diff = disagreements(schema, rec["opus"], rec["gpt"])
        if not diff:
            continue
        pair = list(CODERS)
        rng.shuffle(pair)
        labels = dict(zip(LABELS, pair))
        files = {lab: {"config_id": cid, "coder": f"编码者{lab}",
                       "codebook_version": rec[coder]["codebook_version"],
                       "fields": {f: rec[coder]["fields"][f] for f in diff}}
                 for lab, coder in labels.items()}
        out[cid] = (labels, files)
    return out


def check_reading(reading, cid, blinded, ctx):
    """Errors in one reader's blinded answer for one config."""
    errors, where = [], f"{cid} reading"
    if not isinstance(reading, dict) or reading.get("config_id") != cid or not isinstance(reading.get("items"), list):
        return [f"{where}: needs config_id {cid} and an items list"]
    want = set(blinded["甲"]["fields"])
    seen = set()
    for i, it in enumerate(reading["items"]):
        w = f"{where}.items[{i}]"
        if not isinstance(it, dict) or not {"field", "pick", "rationale"} <= set(it) or set(it) - ITEM_KEYS:
            errors.append(f"{w}: keys must be within {sorted(ITEM_KEYS)} and include field, pick, rationale")
            continue
        fid = it["field"]
        if fid not in want or fid in seen:
            errors.append(f"{w}: field {fid!r} is not one to adjudicate, or repeated")
            continue
        seen.add(fid)
        if not vd._is_str(it.get("rationale")):
            errors.append(f"{w}: rationale must be text")
        field = ctx.fields[fid]
        pick = it["pick"]
        if pick in LABELS:
            if it.get("status") is not None and not same(field, it, blinded[pick]["fields"][fid]):
                errors.append(f"{w}: status/value differ from 编码者{pick}'s; leave them null or pick neither")
        elif pick == "neither":
            check_light(field, it.get("status"), it.get("value"), it.get("unknown_reason"), ctx, w, errors)
            if any(same(field, it, blinded[lab]["fields"][fid]) for lab in LABELS):
                errors.append(f"{w}: neither, but the reading equals one coder's")
        else:
            errors.append(f"{w}: pick must be 甲, 乙 or neither")
    if want - seen:
        errors.append(f"{where}: no item for {sorted(want - seen)}")
    return errors


def unblind(reading, labels, blinded, ctx):
    """field -> {pick: coder|neither, status, value, unknown_reason, rationale, evidence}."""
    out = {}
    for it in reading["items"]:
        fid, pick = it["field"], it["pick"]
        if pick in LABELS:
            src = blinded[pick]["fields"][fid]
            row = {"pick": labels[pick], "status": src["status"], "value": src["value"],
                   "unknown_reason": src.get("unknown_reason")}
        else:
            row = {"pick": "neither", "status": it["status"], "value": it.get("value"),
                   "unknown_reason": it.get("unknown_reason")}
        row["rationale"], row["evidence"] = it["rationale"], it.get("evidence", "")
        out[fid] = row
    return out


def settle(first, second, ctx):
    """Fields both readers settled the same way, and fields left for a third reader."""
    agreed, open_ = {}, []
    for fid in sorted(first):
        if same(ctx.fields[fid], first[fid], second[fid]):
            agreed[fid] = first[fid]
        else:
            open_.append(fid)
    return agreed, open_


def merged_fields(rec_a, adj):
    """Status/value per field after adjudication; fields not adjudicated keep the coders' shared reading."""
    out = {fid: {"status": e["status"], "value": e.get("value")} for fid, e in rec_a["fields"].items()}
    for fid, e in adj["fields"].items():
        out[fid] = {"status": e["status"], "value": e.get("value")}
    return out


def check_adjudication(rec, codings, ctx):
    """Errors in one data/adjudications record against the latest codings."""
    cid = rec.get("config_id") if isinstance(rec, dict) else None
    where = f"adjudications/{cid}"
    errors = []
    if not isinstance(rec, dict) or set(rec) - TOP_KEYS or not TOP_KEYS - {"note"} <= set(rec):
        return [f"{where}: keys must be {sorted(TOP_KEYS)} (note optional)"]
    if cid not in codings:
        return [f"{where}: no latest coding for this config"]
    rnd, pair = codings[cid]
    if rec["schema_version"] != SCHEMA_VERSION or rec["round"] != ROUND or rec["synthetic"] is not False:
        errors.append(f"{where}: schema_version {SCHEMA_VERSION}, round {ROUND}, synthetic false")
    if rec["codebook_version"] != ctx.schema["schema_version"]:
        errors.append(f"{where}: adjudicated under {rec['codebook_version']}, current codebook is {ctx.schema['version']}")
    if rec["codings"] != {c: pair[c]["round"] for c in CODERS}:
        errors.append(f"{where}: codings must name the rounds of the latest codings {({c: pair[c]['round'] for c in CODERS})}")
    if vd._date(rec["adjudicated_at"]) is None:
        errors.append(f"{where}: adjudicated_at must be a date")
    readers = rec["readers"]
    if not isinstance(readers, dict) or not readers or not all(vd._is_str(k) and vd._is_str(v) for k, v in readers.items()):
        errors.append(f"{where}: readers maps reader ids to specific model names")
        readers = {}
    want = disagreements(ctx.schema, pair["opus"], pair["gpt"])
    fields = rec["fields"] if isinstance(rec["fields"], dict) else {}
    if sorted(fields) != sorted(want):
        errors.append(f"{where}: fields must be exactly the disagreements {sorted(want)}")
    for fid, e in sorted(fields.items()):
        w = f"{where}.{fid}"
        if fid not in ctx.fields or not isinstance(e, dict) or set(e) != FIELD_KEYS:
            errors.append(f"{w}: keys must be {sorted(FIELD_KEYS)}")
            continue
        field = ctx.fields[fid]
        choice, picks = e["choice"], e["picks"]
        if choice in CODERS:
            if not same(field, e, pair[choice]["fields"][fid]):
                errors.append(f"{w}: status/value must equal {choice}'s coding")
        elif choice == "neither":
            check_light(field, e["status"], e["value"], e["unknown_reason"], ctx, w, errors)
            if any(same(field, e, pair[c]["fields"][fid]) for c in CODERS):
                errors.append(f"{w}: neither, but the reading equals a coder's")
        else:
            errors.append(f"{w}: choice must be one of {CHOICES}")
        if not isinstance(picks, dict) or set(picks) - set(readers) or not all(p in CHOICES for p in picks.values()):
            errors.append(f"{w}: picks maps reader ids to {CHOICES}")
            picks = {}
        settled = e["settled_by"]
        if settled not in SETTLED:
            errors.append(f"{w}: settled_by must be one of {SETTLED}")
        elif settled == "readers_agree" and (len(picks) < 2 or set(picks.values()) != {choice}):
            errors.append(f"{w}: readers_agree needs two readers who both picked {choice}")
        elif settled == "third_reader" and (len(picks) < 3 or list(picks.values())[-1] != choice):
            errors.append(f"{w}: third_reader needs three picks, the last equal to the choice")
        if not vd._is_str(e["rationale"]) or not isinstance(e["evidence"], str):
            errors.append(f"{w}: rationale and evidence are text")
    if not errors:
        vd.check_conditions(merged_fields(pair["opus"], rec), where, ctx, errors)
    return errors


def check_all(root=HERE):
    ctx = vd.Context(td.load_json(root / "data" / "schema" / "fields.json"))
    codings = td.latest_codings(root)
    errors = []
    for p in sorted((root / "data" / "adjudications").glob("*.json")):
        rec = td.load_json(p)
        if rec.get("config_id") != p.stem:
            errors.append(f"adjudications/{p.name}: file name must equal config_id")
        errors += check_adjudication(rec, codings, ctx)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="write blinded 甲/乙 inputs per config and labels.json")
    p.add_argument("outdir", type=Path)
    p.add_argument("--seed", type=int, default=20261124)
    sub.add_parser("check", help="validate data/adjudications")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        errors = check_all()
        for e in errors:
            print(e)
        return 1 if errors else 0
    schema = td.load_json(HERE / "data" / "schema" / "fields.json")
    inputs = blind_inputs(schema, td.latest_codings(), args.seed)
    labels = {}
    for cid, (lab, files) in inputs.items():
        d = args.outdir / cid
        d.mkdir(parents=True, exist_ok=True)
        for name, body in files.items():
            (d / f"{name}.json").write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        labels[cid] = lab
    (args.outdir / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(inputs)} configs, {sum(len(f['甲']['fields']) for _, f in inputs.values())} fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
