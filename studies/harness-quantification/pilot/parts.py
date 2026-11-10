"""Helper for pilot coding cards: one coder codes one config in three parts (field groups ABC, DEF, GHI).

  python3 studies/harness-quantification/pilot/parts.py brief <groups>      # codebook slice for these groups, plus blank entries
  python3 studies/harness-quantification/pilot/parts.py check <part.json>   # validate the entries of one part; prints errors only
  python3 studies/harness-quantification/pilot/parts.py merge <coder> <config_id> <model> <prompt_version> [dry]
                                                                            # parts -> data/codings/<coder>/<config_id>.json

Run from the repository root. merge reads <parts>/<coder>/<config_id>/<groups>.json, where <parts> is the
PILOT_PARTS environment variable or, by default, tmp/quant-pilot/parts (not in Git).
"""
import datetime
import json
import os
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
sys.path.insert(0, str(STUDY))
import validate_data as vd  # noqa: E402

PARTS = Path(os.environ.get("PILOT_PARTS") or REPO / "tmp/quant-pilot/parts").resolve()
SPLIT = ("ABC", "DEF", "GHI")


def group_fields(ctx, groups):
    return [f for f in ctx.schema["fields"] if f["group"] in groups]


def brief(groups):
    ctx = vd.Context()
    s = ctx.schema
    print(f"码本 {s['schema_version']}，字段组 {groups}")
    print("\n状态：", json.dumps(s.get("statuses", s["enums"].get("status")), ensure_ascii=False))
    for key in ("unknown_reason", "confidence", "evidence_kind"):
        if key in s["enums"]:
            print(f"{key}：", json.dumps(s["enums"][key], ensure_ascii=False))
    print("子维度总则：", s["facet_rule"])
    for g in s["groups"]:
        if g["id"] not in groups:
            continue
        print(f"\n## {g['id']} {g.get('label', g.get('name', ''))}")
        for f in group_fields(ctx, g["id"]):
            print(f"\n### {f['id']} {f['question']}　类型：{f['answer_type_label']}（{f['type']}）")
            print("编码说明：", f["coding_hint"])
            if "absent_value" in f:
                print("已知不存在时：", "status=known_absent，value=" + json.dumps(f["absent_value"], ensure_ascii=False))
            elif f["type"] == "nominal":
                print("已知不存在时：本字段没有“无”这个取值，不能用 known_absent")
            else:
                print("已知不存在时：status=known_absent，value=[]")
            if "condition" in f:
                print("条件：", json.dumps(f["condition"], ensure_ascii=False))
            for k, v in (f.get("definition") or {}).items():
                print(f"{k}：{v}")
            print("词表：")
            for v in f["vocabulary"]:
                extra = f"｜判定：{v['criterion']}｜例：{v['example']}" if "criterion" in v else ""
                print(f"  - {v['id']}　{v['label']}{extra}")
            for fc in f.get("facets", []):
                vocab = "本字段词表" if fc.get("vocabulary_from") == "value" else "／".join(
                    f"{x['id']}（{x['label']}）" for x in fc["vocabulary"])
                ties = "；必须是 value 的子集" if fc.get("subset_of_value") else ""
                ties += "；不含主取值" if fc.get("excludes_value") else ""
                print(f"  子维度 {fc['id']}　{fc['label']}（{fc['type']}；取值：{vocab}{ties}）：{fc['rule']}")
    tpl = json.loads((vd.DATA / "templates/coding.template.json").read_text(encoding="utf-8"))
    ids = [f["id"] for f in group_fields(ctx, groups)]
    print("\n空白记录（每个字段一条，键名和顺序照此）：")
    print(json.dumps({ids[0]: tpl["fields"][ids[0]]}, ensure_ascii=False))
    with_facets = {i: tpl["fields"][i]["facets"] for i in ids if "facets" in tpl["fields"][i]}
    if with_facets:
        print("带子维度的字段，facets 键：", json.dumps(with_facets, ensure_ascii=False))
    print("证据小卡：", json.dumps(vd._blank_card(), ensure_ascii=False))
    print("本部分要交的字段：", " ".join(ids))


def check_part(path, ctx=None, quiet=False):
    ctx = ctx or vd.Context()
    errors = []
    part = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("config_id", "coder", "groups", "fields"):
        if key not in part:
            return [f"{path}: missing key {key!r}"], part
    want = [f["id"] for f in group_fields(ctx, part["groups"])]
    got = part["fields"]
    if sorted(got) != sorted(want):
        errors.append(f"{path}: fields must be exactly {want}; missing {sorted(set(want) - set(got))}, "
                      f"extra {sorted(set(got) - set(want))}")
    cutoff = datetime.date.today()
    for fid in sorted(set(got) & set(want)):
        vd.check_entry(ctx.fields[fid], got[fid], fid, ctx, errors, cutoff)
    if "G" in part["groups"] and all(i in got for i in ("F25", "F26", "F27", "F28")):
        vd.check_conditions(got, "G", ctx, errors)
    vd.check_no_local_paths(part, str(path), errors)
    if not quiet:
        print("\n".join(errors) if errors else f"OK {path}: {len(got)} fields")
    return errors, part


def merge(coder, config_id, model, prompt_version, dry=None):
    ctx = vd.Context()
    rec = json.loads((vd.DATA / "templates/coding.template.json").read_text(encoding="utf-8"))
    today = datetime.date.today().isoformat()
    rec.update(round="pilot-1", config_id=config_id, evidence_cutoff=today,
               coder={"id": coder, "model": model, "prompt_version": prompt_version, "coded_at": today})
    errors = []
    for groups in SPLIT:
        path = PARTS / coder / config_id / f"{groups}.json"
        if not path.exists():
            errors.append(f"missing part {path}")
            continue
        errs, part = check_part(path, ctx, quiet=True)
        errors += errs
        if part.get("config_id") != config_id or part.get("coder") != coder:
            errors.append(f"{path}: config_id or coder does not match")
        rec["fields"].update(part.get("fields", {}))
    if not errors:
        errors = vd.validate_coding(rec, f"{coder}/{config_id}", ctx)
    if errors:
        print("\n".join(errors))
        return 1
    if dry:
        print(f"dry run OK: {coder}/{config_id} would validate ({len(rec['fields'])} fields)")
        return 0
    out = vd.DATA / "codings" / coder / f"{config_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if cmd == "brief" and len(args) == 1:
        brief(args[0])
    elif cmd == "check" and len(args) == 1:
        sys.exit(1 if check_part(args[0])[0] else 0)
    elif cmd == "merge" and len(args) in (4, 5):
        sys.exit(merge(*args))
    else:
        sys.exit(__doc__)
