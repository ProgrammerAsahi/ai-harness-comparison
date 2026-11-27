"""MIT. Unit tests for adjudicating the coders' disagreements (synthetic records only, plus the real tree)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import adjudicate as adj
import validate_data as vd

SCHEMA = json.loads((Path(__file__).parent / "data" / "schema" / "fields.json").read_text(encoding="utf-8"))
CTX = vd.Context(SCHEMA)
CID = "Z01__synthetic__cli-default"


def record(coder, **over):
    fields = {}
    for fid, f in CTX.fields.items():
        first = f["vocabulary"][0]["id"]
        fields[fid] = {"status": "known", "value": first if f["type"] == "nominal" else [first], "facets": {}}
    fields["F25"] = {"status": "known", "value": "absent", "facets": {}}
    for fid in ("F26", "F27", "F28"):
        fields[fid] = {"status": "not_applicable", "value": None, "facets": {}}
    for fid, e in over.items():
        fields[fid] = {"facets": {}, **e}
    return {"round": "batch-9", "codebook_version": SCHEMA["schema_version"], "fields": fields}


def second_value(fid):
    f = CTX.fields[fid]
    v = f["vocabulary"][1]["id"]
    return v if f["type"] == "nominal" else [v]


def pair():
    a = record("opus")
    b = record("gpt", F01={"status": "known", "value": second_value("F01")},
               F04={"status": "unknown", "value": None, "unknown_reason": "closed_source"})
    return {CID: ("batch-9", {"opus": a, "gpt": b})}


def adjudication(codings, **over):
    _, p = codings[CID]
    rec = {"schema_version": adj.SCHEMA_VERSION, "synthetic": False, "round": adj.ROUND, "config_id": CID,
           "codebook_version": SCHEMA["schema_version"], "codings": {"opus": "batch-9", "gpt": "batch-9"},
           "adjudicated_at": "2026-11-24", "readers": {"r1": "Model A 1.0", "r2": "Model B 2.0"}, "fields": {}}
    for fid, coder in (("F01", "gpt"), ("F04", "opus")):
        e = p[coder]["fields"][fid]
        rec["fields"][fid] = {"choice": coder, "status": e["status"], "value": e["value"],
                              "unknown_reason": e.get("unknown_reason"), "settled_by": "readers_agree",
                              "picks": {"r1": coder, "r2": coder}, "rationale": "依据配置记录的入口判。", "evidence": ""}
    rec["fields"].update(over)
    return rec


class Adjudicate(unittest.TestCase):
    def test_disagreements_and_blinding(self):
        codings = pair()
        _, p = codings[CID]
        self.assertEqual(adj.disagreements(SCHEMA, p["opus"], p["gpt"]), ["F01", "F04"])
        inputs = adj.blind_inputs(SCHEMA, codings, seed=1)
        labels, files = inputs[CID]
        self.assertEqual(sorted(labels.values()), ["gpt", "opus"])
        self.assertEqual(sorted(files["甲"]["fields"]), ["F01", "F04"])
        self.assertNotIn("opus", json.dumps(files, ensure_ascii=False))
        same = {CID: ("batch-9", {"opus": p["opus"], "gpt": copy.deepcopy(p["opus"])})}
        self.assertEqual(adj.blind_inputs(SCHEMA, same, seed=1), {})

    def test_reading_checks(self):
        labels, files = adj.blind_inputs(SCHEMA, pair(), seed=1)[CID]
        ok = {"config_id": CID, "items": [
            {"field": "F01", "pick": "甲", "status": None, "value": None, "rationale": "x", "evidence": ""},
            {"field": "F04", "pick": "neither", "status": "known", "value": second_value("F04"),
             "unknown_reason": None, "rationale": "y", "evidence": ""}]}
        self.assertEqual(adj.check_reading(ok, CID, files, CTX), [])
        bad = copy.deepcopy(ok)
        bad["items"][0].update(status="known_absent", value=[])
        bad["items"][1].update(unknown_reason=files["乙"]["fields"]["F04"].get("unknown_reason"),
                               status=files["乙"]["fields"]["F04"]["status"], value=files["乙"]["fields"]["F04"]["value"])
        errs = adj.check_reading(bad, CID, files, CTX)
        self.assertTrue(any("differ from" in e for e in errs), errs)
        self.assertTrue(any("equals one coder" in e for e in errs), errs)
        short = {"config_id": CID, "items": ok["items"][:1]}
        self.assertTrue(any("no item for" in e for e in adj.check_reading(short, CID, files, CTX)))
        wrong = copy.deepcopy(ok)
        wrong["items"][1].update(status="known", value=["no_such_value"], unknown_reason=None)
        self.assertTrue(any("vocabulary" in e for e in adj.check_reading(wrong, CID, files, CTX)))

    def test_unblind_and_settle(self):
        labels, files = adj.blind_inputs(SCHEMA, pair(), seed=1)[CID]
        r1 = {"config_id": CID, "items": [{"field": "F01", "pick": "甲", "rationale": "x"},
                                          {"field": "F04", "pick": "乙", "rationale": "x"}]}
        r2 = {"config_id": CID, "items": [{"field": "F01", "pick": "甲", "rationale": "y"},
                                          {"field": "F04", "pick": "甲", "rationale": "y"}]}
        u1, u2 = (adj.unblind(r, labels, files, CTX) for r in (r1, r2))
        self.assertEqual(u1["F01"]["pick"], labels["甲"])
        agreed, open_ = adj.settle(u1, u2, CTX)
        self.assertEqual(list(agreed), ["F01"])
        self.assertEqual(open_, ["F04"])

    def test_adjudication_record_checks(self):
        codings = pair()
        self.assertEqual(adj.check_adjudication(adjudication(codings), codings, CTX), [])
        rec = adjudication(codings)
        del rec["fields"]["F04"]
        self.assertTrue(any("exactly the disagreements" in e for e in adj.check_adjudication(rec, codings, CTX)))
        rec = adjudication(codings)
        rec["fields"]["F01"]["choice"] = "opus"
        self.assertTrue(any("must equal opus" in e for e in adj.check_adjudication(rec, codings, CTX)))
        rec = adjudication(codings)
        rec["fields"]["F01"]["picks"] = {"r1": "gpt", "r2": "opus"}
        self.assertTrue(any("readers_agree" in e for e in adj.check_adjudication(rec, codings, CTX)))
        rec = adjudication(codings)
        rec["fields"]["F01"].update(settled_by="third_reader", picks={"r1": "gpt", "r2": "opus", "r3": "gpt"})
        rec["readers"]["r3"] = "Model C 3.0"
        self.assertEqual(adj.check_adjudication(rec, codings, CTX), [])
        rec = adjudication(codings)
        rec["codings"]["gpt"] = "batch-1"
        self.assertTrue(any("rounds of the latest" in e for e in adj.check_adjudication(rec, codings, CTX)))

    def test_merged_record_keeps_conditions(self):
        _, p = pair()[CID]
        present = {"status": "known", "value": "present"}
        b = copy.deepcopy(p["gpt"])
        b["fields"]["F25"] = {**present, "facets": {}}
        for fid in ("F26", "F27", "F28"):
            b["fields"][fid] = {"status": "unknown", "value": None, "unknown_reason": "not_found", "facets": {}}
        codings = {CID: ("batch-9", {"opus": p["opus"], "gpt": b})}
        rec = adjudication(codings)
        rec["fields"]["F25"] = {"choice": "gpt", **present, "unknown_reason": None, "settled_by": "lead",
                                "picks": {}, "rationale": "x", "evidence": ""}
        for fid in ("F26", "F27", "F28"):
            rec["fields"][fid] = {"choice": "opus", "status": "not_applicable", "value": None, "unknown_reason": None,
                                  "settled_by": "lead", "picks": {}, "rationale": "x", "evidence": ""}
        errs = adj.check_adjudication(rec, codings, CTX)
        self.assertTrue(any("must be coded" in e for e in errs), errs)
        merged = adj.merged_fields(p["opus"], adjudication(pair()))
        self.assertEqual(merged["F01"]["value"], second_value("F01"))

    def test_codebooks_include_archived_copies(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data" / "schema").mkdir(parents=True)
            (root / "batches" / "recode-9").mkdir(parents=True)
            old = dict(SCHEMA, schema_version="fields-0.1")
            (root / "batches" / "recode-9" / "fields-0.1.json").write_text(json.dumps(old), encoding="utf-8")
            (root / "data" / "schema" / "fields.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
            self.assertEqual(sorted(adj.codebooks(root)), sorted({"fields-0.1", SCHEMA["schema_version"]}))

    def test_real_adjudications_are_valid(self):
        self.assertEqual(adj.check_all(), [])


if __name__ == "__main__":
    unittest.main()
