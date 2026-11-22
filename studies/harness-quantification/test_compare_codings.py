"""MIT. Unit tests for compare_codings.py, the field-by-field comparison of two codings.

Covers compare_entry's five outcomes, set and conditional_set order-insensitivity with
jaccard_distance, the facet comparison rules (optional left-out, one/both missing,
list order), and compare_tree run once over the synthetic fixtures in
data/fixtures/synthetic. Entries are small synthetic dicts; the tests only read the
in-repo fixtures and schema, write nothing, and need no network access.

  python3 -m unittest discover -s studies/harness-quantification -p 'test_*.py' -v
"""
import importlib.util
import sys
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parent
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))
import validate_data as vd  # noqa: E402

spec = importlib.util.spec_from_file_location("compare_codings_under_test", STUDY / "compare_codings.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

CFG_A = "Z90__synthetic-a__local-default"
CFG_B = "Z91__synthetic-b__local-default"


def entry(status, value=None, **extra):
    e = {"status": status, "value": value}
    e.update(extra)
    return e


class CompareEntryOutcomes(unittest.TestCase):
    """The five outcomes of compare_entry for one field, one coder pair."""

    @classmethod
    def setUpClass(cls):
        fields = {f["id"]: f for f in vd.Context().schema["fields"]}
        cls.f01 = fields["F01"]
        cls.f25 = fields["F25"]
        cls.f26 = fields["F26"]

    def test_agree_value(self):
        out = cc.compare_entry(self.f01, entry("known", "model_loop"), entry("known", "model_loop"))
        self.assertEqual(out["field"], "F01")
        self.assertEqual(out["outcome"], "agree_value")
        self.assertNotIn("jaccard_distance", out)

    def test_equal_known_absent_counts_as_agree_value(self):
        out = cc.compare_entry(self.f25, entry("known_absent", "absent"), entry("known_absent", "absent"))
        self.assertEqual(out["outcome"], "agree_value")

    def test_value_differs(self):
        out = cc.compare_entry(self.f01, entry("known", "model_loop"), entry("known", "user_stepwise"))
        self.assertEqual(out["outcome"], "value_differs")

    def test_agree_unknown_same_reason_has_no_reason_differs(self):
        a = entry("unknown", None, unknown_reason="closed_source")
        b = entry("unknown", None, unknown_reason="closed_source")
        out = cc.compare_entry(self.f26, a, b)
        self.assertEqual(out["outcome"], "agree_unknown")
        self.assertNotIn("reason_differs", out)

    def test_agree_unknown_without_reasons_has_no_reason_differs(self):
        out = cc.compare_entry(self.f26, entry("unknown", None), entry("unknown", None))
        self.assertEqual(out["outcome"], "agree_unknown")
        self.assertNotIn("reason_differs", out)

    def test_agree_unknown_differing_reasons_flagged(self):
        for a, b in (
            (entry("unknown", None, unknown_reason="closed_source"), entry("unknown", None, unknown_reason="not_found")),
            (entry("unknown", None, unknown_reason="not_found"), entry("unknown", None, unknown_reason="closed_source")),
        ):
            with self.subTest(a=a["unknown_reason"], b=b["unknown_reason"]):
                out = cc.compare_entry(self.f26, a, b)
                self.assertEqual(out["outcome"], "agree_unknown")
                self.assertTrue(out.get("reason_differs"))

    def test_agree_not_applicable(self):
        out = cc.compare_entry(self.f26, entry("not_applicable", None), entry("not_applicable", None))
        self.assertEqual(out["outcome"], "agree_not_applicable")

    def test_status_differs(self):
        for a, b in (
            (entry("known", "model_loop"), entry("unknown", None, unknown_reason="not_found")),
            (entry("known", "model_loop"), entry("not_applicable", None)),
            (entry("unknown", None, unknown_reason="not_found"), entry("not_applicable", None)),
        ):
            with self.subTest(a=a["status"], b=b["status"]):
                self.assertEqual(cc.compare_entry(self.f01, a, b)["outcome"], "status_differs")


class SetAndConditionalSet(unittest.TestCase):
    """set / conditional_set: order-insensitive equality, jaccard_distance on difference."""

    @classmethod
    def setUpClass(cls):
        fields = {f["id"]: f for f in vd.Context().schema["fields"]}
        cls.f03 = fields["F03"]
        cls.f06 = fields["F06"]
        cls.f26 = fields["F26"]

    def test_set_order_does_not_matter(self):
        a = entry("known", ["budget", "user_interrupt"])
        b = entry("known", ["user_interrupt", "budget"])
        out = cc.compare_entry(self.f03, a, b)
        self.assertEqual(out["outcome"], "agree_value")
        self.assertNotIn("jaccard_distance", out)

    def test_conditional_set_order_does_not_matter(self):
        a = entry("known", ["main_agent", "user"])
        b = entry("known", ["user", "main_agent"])
        out = cc.compare_entry(self.f26, a, b)
        self.assertEqual(out["outcome"], "agree_value")
        self.assertNotIn("jaccard_distance", out)

    def test_empty_sets_agree(self):
        out = cc.compare_entry(self.f03, entry("known", []), entry("known", []))
        self.assertEqual(out["outcome"], "agree_value")
        self.assertNotIn("jaccard_distance", out)

    def test_value_differs_reports_jaccard_distance(self):
        for field, a, b, expected in (
            # disjoint sets: distance 1
            (self.f03, entry("known", ["budget"]), entry("known", ["user_interrupt"]), 1.0),
            # one shared member of two: 1 - 1/2
            (self.f06, entry("known", ["subprocess"]), entry("known", ["subprocess", "container"]), 0.5),
            # one shared member of three: 1 - 1/3
            (self.f03, entry("known", ["budget", "user_interrupt"]),
             entry("known", ["user_interrupt", "model_end_signal"]), 0.6667),
        ):
            with self.subTest(a=a["value"], b=b["value"]):
                out = cc.compare_entry(field, a, b)
                self.assertEqual(out["outcome"], "value_differs")
                self.assertEqual(out.get("jaccard_distance"), expected)

    def test_empty_union_distance_is_zero(self):
        # Defensive branch of the distance: when both sides contribute no members at
        # all the union is empty and the distance is 0.0, not a division by zero.
        out = cc.compare_entry(self.f03, entry("known", []), entry("known", ""))
        self.assertEqual(out["outcome"], "value_differs")
        self.assertEqual(out.get("jaccard_distance"), 0.0)


class FacetComparison(unittest.TestCase):
    """Facet rules: optional left-out is not compared; missing is one/both_unknown; list order ignored."""

    @classmethod
    def setUpClass(cls):
        fields = {f["id"]: f for f in vd.Context().schema["fields"]}
        cls.f03 = fields["F03"]  # set field whose only facet is the optional "unresolved"
        cls.f12 = fields["F12"]  # set field with non-optional set facets hard_stop / soft_notice / mode_unknown

    def test_optional_facet_left_out_on_both_sides_is_not_compared(self):
        out = cc.compare_entry(self.f03, entry("known", ["budget"]), entry("known", ["budget"]))
        self.assertEqual(out["outcome"], "agree_value")
        self.assertNotIn("facets", out)
        # Same when the facets object is present but the optional key is absent.
        out = cc.compare_entry(self.f03, entry("known", ["budget"], facets={}),
                               entry("known", ["budget"], facets={}))
        self.assertNotIn("facets", out)

    def test_optional_facet_one_side_missing_is_compared_against_empty(self):
        out = cc.compare_entry(self.f03, entry("known", ["budget"]),
                               entry("known", ["budget"], facets={"unresolved": ["user_interrupt"]}))
        self.assertEqual(out["outcome"], "agree_value")
        self.assertEqual(out["facets"]["unresolved"], "differs")

    def test_optional_facet_list_order_ignored(self):
        a = entry("known", ["budget"], facets={"unresolved": ["model_end_signal", "user_interrupt"]})
        b = entry("known", ["budget"], facets={"unresolved": ["user_interrupt", "model_end_signal"]})
        self.assertEqual(cc.compare_entry(self.f03, a, b)["facets"]["unresolved"], "agree")

    def test_non_optional_facet_one_side_missing_is_one_unknown(self):
        a = entry("known", ["output_limit", "total_tokens", "call_count"],
                  facets={"hard_stop": ["output_limit"], "soft_notice": ["call_count"], "mode_unknown": []})
        b = entry("known", ["output_limit", "total_tokens", "call_count"],
                  facets={"hard_stop": ["output_limit"], "soft_notice": ["call_count"]})
        out = cc.compare_entry(self.f12, a, b)
        self.assertEqual(out["facets"]["hard_stop"], "agree")
        self.assertEqual(out["facets"]["soft_notice"], "agree")
        self.assertEqual(out["facets"]["mode_unknown"], "one_unknown")
        self.assertNotIn("unresolved", out["facets"])  # optional, both empty: not compared

    def test_non_optional_facet_both_missing_is_both_unknown(self):
        a = entry("known", ["output_limit", "total_tokens", "call_count"],
                  facets={"hard_stop": ["output_limit"], "soft_notice": ["call_count"]})
        b = entry("known", ["output_limit", "total_tokens", "call_count"],
                  facets={"hard_stop": ["output_limit"], "soft_notice": ["call_count"]})
        self.assertEqual(cc.compare_entry(self.f12, a, b)["facets"]["mode_unknown"], "both_unknown")

    def test_set_facet_list_order_ignored(self):
        a = entry("known", ["output_limit", "total_tokens", "call_count"],
                  facets={"hard_stop": ["output_limit", "total_tokens"], "soft_notice": ["call_count"],
                          "mode_unknown": []})
        b = entry("known", ["output_limit", "total_tokens", "call_count"],
                  facets={"hard_stop": ["total_tokens", "output_limit"], "soft_notice": ["call_count"],
                          "mode_unknown": []})
        self.assertEqual(cc.compare_entry(self.f12, a, b)["facets"]["hard_stop"], "agree")

    def test_set_facet_content_differs(self):
        a = entry("known", ["output_limit", "total_tokens", "call_count"],
                  facets={"hard_stop": ["output_limit"], "soft_notice": ["call_count"], "mode_unknown": []})
        b = entry("known", ["output_limit", "total_tokens", "call_count"],
                  facets={"hard_stop": ["call_count"], "soft_notice": ["output_limit"], "mode_unknown": []})
        out = cc.compare_entry(self.f12, a, b)
        self.assertEqual(out["facets"]["hard_stop"], "differs")
        self.assertEqual(out["facets"]["soft_notice"], "differs")


class CompareTreeOnFixtures(unittest.TestCase):
    """compare_tree over the in-repo synthetic fixtures (read-only)."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.errors = cc.compare_tree(vd.FIXTURES, vd.Context(synthetic=True))
        cls.schema_fields = [f["id"] for f in vd.Context().schema["fields"]]

    def test_fixtures_validate_and_produce_one_pair_per_config(self):
        self.assertEqual(self.errors, [])
        self.assertIsNotNone(self.result)
        self.assertEqual(sorted(p["config_id"] for p in self.result["pairs"]), [CFG_A, CFG_B])

    def test_per_field_compared_is_partition_of_agree_and_disagrees(self):
        self.assertEqual(sorted(f["field"] for f in self.result["fields"]), sorted(self.schema_fields))
        for f in self.result["fields"]:
            with self.subTest(field=f["field"]):
                self.assertGreaterEqual(f["compared"], 1)
                self.assertEqual(f["compared"], f["agree"] + f["status_differs"] + f["value_differs"])

    def test_both_unknown_and_both_not_applicable_count_as_agree(self):
        totals = {}
        for p in self.result["pairs"]:
            with self.subTest(config=p["config_id"]):
                agree = (p["outcomes"].get("agree_value", 0) + p["outcomes"].get("agree_unknown", 0)
                         + p["outcomes"].get("agree_not_applicable", 0))
                self.assertEqual(p["fields"], sum(p["outcomes"].values()))
                self.assertEqual(p["agreement_rate"], round(agree / p["fields"], 4))
            for k, v in p["outcomes"].items():
                totals[k] = totals.get(k, 0) + v
        # The fixtures contain a both-unknown field (F20 on Z90) and both-not_applicable
        # fields (F26-F28 on Z91); both families occur and the recomputed rates above
        # show they are inside agreement_rate.
        self.assertGreaterEqual(totals.get("agree_unknown", 0), 1)
        self.assertGreaterEqual(totals.get("agree_not_applicable", 0), 1)
        by_field = {f["field"]: f for f in self.result["fields"]}
        for fid in ("F20", "F26"):
            with self.subTest(field=fid):
                f = by_field[fid]
                self.assertEqual(f["status_differs"], 0)
                self.assertEqual(f["value_differs"], 0)
                self.assertEqual(f["agree"], f["compared"])


if __name__ == "__main__":
    unittest.main()
