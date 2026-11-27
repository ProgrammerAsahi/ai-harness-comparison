"""MIT. Unit tests for the trial structural distance rules (report sections 5.5, 7, 8)."""
import json
import unittest
from pathlib import Path

from trial_distance import adjudicated, agreed, distance, spearman

SCHEMA = json.loads((Path(__file__).parent / "data" / "schema" / "fields.json").read_text(encoding="utf-8"))
FIELDS = {f["id"]: f for f in SCHEMA["fields"]}


def coding(**over):
    """All fields known and equal-by-default; G group absent unless overridden."""
    out = {}
    for fid, f in FIELDS.items():
        first = f["vocabulary"][0]["id"]
        out[fid] = {"status": "known", "value": first if f["type"] == "nominal" else [first]}
    out["F25"] = {"status": "known", "value": "absent"}
    for fid in ("F26", "F27", "F28"):
        out[fid] = {"status": "not_applicable"}
    out.update(over)
    return out


class TrialDistance(unittest.TestCase):
    def test_identical_codings_are_zero_with_full_coverage(self):
        r = distance(coding(), coding(), SCHEMA)
        self.assertEqual(r["d_obs"], 0)
        self.assertAlmostEqual(r["coverage"], 1)

    def test_gate_mismatch_costs_the_whole_group_once(self):
        present = coding(F25={"status": "known", "value": "present"},
                         F26={"status": "known", "value": []}, F27={"status": "known", "value": []},
                         F28={"status": "known", "value": []})
        for g in (0.5, 0.75, 1.0):
            r = distance(coding(), present, SCHEMA, g)
            self.assertAlmostEqual(r["d_obs"], g / 9)
            self.assertAlmostEqual(r["coverage"], 1)

    def test_unknown_gate_makes_group_unknown_and_widens_bounds(self):
        r = distance(coding(), coding(F25={"status": "unknown"}), SCHEMA)
        self.assertAlmostEqual(r["coverage"], 8 / 9)
        self.assertEqual(r["groups"]["G"], 0)
        self.assertAlmostEqual(r["bounds"][1] - r["bounds"][0], 1 / 9)

    def test_sets_use_jaccard_and_empty_sets_agree(self):
        v = [x["id"] for x in FIELDS["F03"]["vocabulary"]][:2]
        r = distance(coding(F03={"status": "known", "value": v}), coding(F03={"status": "known", "value": v[:1]}), SCHEMA)
        self.assertAlmostEqual(r["d_obs"], 0.5 / 36)
        r = distance(coding(F03={"status": "known_absent", "value": []}), coding(F03={"status": "known_absent", "value": []}), SCHEMA)
        self.assertEqual(r["d_obs"], 0)

    def test_agreed_keeps_only_matching_fields(self):
        a, b = coding(), coding(F01={"status": "known", "value": FIELDS["F01"]["vocabulary"][1]["id"]}, F02={"status": "unknown"})
        c = agreed(a, b, SCHEMA)
        self.assertEqual(c["F01"]["status"], "unknown")
        self.assertEqual(c["F02"]["status"], "unknown")
        self.assertEqual(c["F03"], {"status": "known", "value": a["F03"]["value"]})
        self.assertEqual(c["F26"]["status"], "not_applicable")

    def test_adjudicated_takes_record_fields_and_keeps_the_rest(self):
        a = coding()
        v1 = FIELDS["F01"]["vocabulary"][1]["id"]
        rec = {"fields": {"F01": {"choice": "gpt", "status": "known", "value": v1, "settled_by": "lead"},
                          "F02": {"choice": "neither", "status": "unknown", "value": None, "unknown_reason": "not_found"}}}
        c = adjudicated(a, rec)
        self.assertEqual(c["F01"], {"status": "known", "value": v1})
        self.assertEqual(c["F02"], {"status": "unknown", "value": None})
        self.assertEqual(c["F03"], {"status": "known", "value": a["F03"]["value"]})
        self.assertEqual(adjudicated(a, None)["F01"], {"status": "known", "value": a["F01"]["value"]})

    def test_spearman_handles_ties(self):
        self.assertAlmostEqual(spearman([1, 2, 2, 3], [1, 2, 2, 3]), 1)
        self.assertAlmostEqual(spearman([1, 2, 3], [3, 2, 1]), -1)


if __name__ == "__main__":
    unittest.main()
