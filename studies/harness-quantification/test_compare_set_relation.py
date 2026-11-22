"""MIT. Acceptance tests for the set_relation output of compare_codings.py.

When two coders both know a set-valued field and their lists differ, the comparison says which way they
differ (a_subset, b_subset, overlap, disjoint); each pair counts the four kinds and the text report prints them.
Only synthetic records built in a temporary directory are compared; validation is stubbed for those trees.

  python3 -m unittest studies/harness-quantification/test_compare_set_relation.py -v
"""
import contextlib
import importlib.util
import io
import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

STUDY = Path(__file__).resolve().parent
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))
spec = importlib.util.spec_from_file_location("compare_codings_set_relation", STUDY / "compare_codings.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

RELATIONS = ("a_subset", "b_subset", "overlap", "disjoint")
SET = {"id": "S1", "type": "set", "question": "synthetic set"}
NOMINAL = {"id": "N1", "type": "nominal", "question": "synthetic nominal"}


def known(value):
    return {"status": "known", "value": value}


class CompareEntry(unittest.TestCase):
    def relation(self, a, b, field=SET):
        out = cc.compare_entry(field, known(a), known(b))
        self.assertEqual(out["outcome"], "value_differs")
        return out.get("set_relation")

    def test_a_proper_subset(self):
        self.assertEqual(self.relation(["x"], ["x", "y"]), "a_subset")

    def test_b_proper_subset(self):
        self.assertEqual(self.relation(["x", "y"], ["y"]), "b_subset")

    def test_overlap(self):
        self.assertEqual(self.relation(["x", "y"], ["y", "z"]), "overlap")

    def test_disjoint(self):
        self.assertEqual(self.relation(["x"], ["y", "z"]), "disjoint")

    def test_empty_side_counts_as_subset(self):
        self.assertEqual(self.relation([], ["x"]), "a_subset")
        self.assertEqual(self.relation(["x", "y"], []), "b_subset")

    def test_order_does_not_matter(self):
        self.assertEqual(self.relation(["z", "y", "x"], ["x", "z"]), "b_subset")

    def test_conditional_set_field(self):
        field = {"id": "S9", "type": "conditional_set", "question": "synthetic conditional"}
        self.assertEqual(self.relation(["x"], ["x", "y"], field), "a_subset")

    def test_existing_keys_kept(self):
        out = cc.compare_entry(SET, known(["x"]), known(["x", "y"]))
        self.assertEqual(out["field"], "S1")
        self.assertEqual(out["jaccard_distance"], 0.5)

    def test_absent_unless_lists_differ(self):
        self.assertNotIn("set_relation", cc.compare_entry(SET, known(["x", "y"]), known(["y", "x"])))
        self.assertNotIn("set_relation", cc.compare_entry(NOMINAL, known("p"), known("q")))
        unknown = {"status": "unknown", "value": None, "unknown_reason": "closed_source"}
        self.assertNotIn("set_relation", cc.compare_entry(SET, known(["x"]), unknown))
        self.assertNotIn("set_relation", cc.compare_entry(SET, unknown, unknown))


class CompareTree(unittest.TestCase):
    """Two synthetic configurations, each coded by coder-a and coder-b."""

    FIELDS = [dict(SET, id=f"S{i}") for i in range(1, 6)] + [NOMINAL]
    CODINGS = {
        "C1": {
            "coder-a": {"S1": ["x"], "S2": ["x", "y"], "S3": ["x", "y"], "S4": ["x"], "S5": ["x"], "N1": "p"},
            "coder-b": {"S1": ["x", "y"], "S2": ["y"], "S3": ["y", "z"], "S4": ["x"], "S5": None, "N1": "q"},
        },
        "C2": {
            "coder-a": {"S1": ["x"], "S2": [], "S3": ["x"], "S4": ["x"], "S5": ["x"], "N1": "p"},
            "coder-b": {"S1": ["y"], "S2": ["z"], "S3": ["x"], "S4": ["x"], "S5": ["x"], "N1": "p"},
        },
    }
    EXPECTED = {
        "C1": {"a_subset": 1, "b_subset": 1, "overlap": 1, "disjoint": 0},
        "C2": {"a_subset": 1, "b_subset": 0, "overlap": 0, "disjoint": 1},
    }
    CASES = {("C1", "S1"): "a_subset", ("C1", "S2"): "b_subset", ("C1", "S3"): "overlap",
             ("C2", "S1"): "disjoint", ("C2", "S2"): "a_subset"}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for cid, coders in self.CODINGS.items():
            for coder, values in coders.items():
                fields = {fid: ({"status": "unknown", "value": None, "unknown_reason": "closed_source"}
                                if v is None else known(v)) for fid, v in values.items()}
                p = self.root / "codings" / coder / f"{cid}.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps({"config_id": cid, "coder": {"id": coder}, "fields": fields}))
        self.ctx = types.SimpleNamespace(schema={"fields": self.FIELDS})
        with patch.object(cc, "validate_tree", return_value=[]):
            self.result, errors = cc.compare_tree(self.root, self.ctx)
        self.assertEqual(errors, [])

    def test_pair_counts_have_all_four_keys(self):
        pairs = {p["config_id"]: p for p in self.result["pairs"]}
        self.assertEqual(sorted(pairs), ["C1", "C2"])
        for cid, expected in self.EXPECTED.items():
            self.assertEqual(pairs[cid]["set_relations"], expected)

    def test_existing_pair_keys_unchanged(self):
        c1 = next(p for p in self.result["pairs"] if p["config_id"] == "C1")
        self.assertEqual(set(c1) - {"set_relations"},
                         {"config_id", "coders", "fields", "outcomes", "agreement_rate", "known_agreement_rate",
                          "both_known"})
        self.assertEqual(c1["coders"], ["coder-a", "coder-b"])
        self.assertEqual(c1["outcomes"], {"agree_value": 1, "status_differs": 1, "value_differs": 4})

    def test_cases_carry_set_relation(self):
        seen = {}
        for f in self.result["fields"]:
            for case in f["cases"]:
                if case["outcome"] == "value_differs" and f["field"].startswith("S"):
                    seen[(case["config_id"], f["field"])] = case["set_relation"]
                    self.assertIn("jaccard_distance", case)
                else:
                    self.assertNotIn("set_relation", case)
        self.assertEqual(seen, self.CASES)

    def test_text_prints_counts_after_each_pair_line(self):
        lines = cc.render_text(self.result).splitlines()
        for p in self.result["pairs"]:
            i = next(n for n, line in enumerate(lines)
                     if line.startswith(f"{p['config_id']}  coder-a vs coder-b: agreement"))
            follow = lines[i + 1]
            for name in RELATIONS:
                m = re.search(rf"{name}\D{{0,3}}(\d+)", follow)
                self.assertTrue(m, f"{name} count missing in {follow!r}")
                self.assertEqual(int(m.group(1)), self.EXPECTED[p["config_id"]][name])

    def test_json_output_only_adds_keys(self):
        old = {"pairs", "fields", "note"}
        with patch.object(cc, "validate_tree", return_value=[]), \
                patch.object(cc, "FIXTURES", self.root), patch.object(cc, "Context", lambda **_: self.ctx):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(cc.main(["--fixtures", "--json"]), 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(set(data), old)
        self.assertEqual(data["pairs"], self.result["pairs"])
        for f in data["fields"]:
            self.assertTrue({"field", "question", "agreement_rate", "compared", "agree", "status_differs",
                             "value_differs", "reason_differs", "cases", "proposals"} <= set(f))


class FixtureConsistency(unittest.TestCase):
    """On the shipped synthetic fixtures, only check that counts and cases agree with each other."""

    def test_counts_match_cases(self):
        ctx = cc.Context(synthetic=True)
        result, errors = cc.compare_tree(cc.FIXTURES, ctx)
        self.assertEqual(errors, [])
        total = dict.fromkeys(RELATIONS, 0)
        for p in result["pairs"]:
            self.assertEqual(sorted(p["set_relations"]), sorted(RELATIONS))
            for k, v in p["set_relations"].items():
                total[k] += v
        from_cases = dict.fromkeys(RELATIONS, 0)
        for f in result["fields"]:
            for case in f["cases"]:
                if "set_relation" in case:
                    self.assertIn("jaccard_distance", case)
                    from_cases[case["set_relation"]] += 1
                elif case["outcome"] == "value_differs":
                    self.assertNotIn("jaccard_distance", case)
        self.assertEqual(total, from_cases)


if __name__ == "__main__":
    unittest.main()
