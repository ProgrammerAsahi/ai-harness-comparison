"""MIT. Numerical contracts used in the report, including missing-data traps."""
import unittest
from calculate_examples import compare, examples, field_difference


class NumericalContracts(unittest.TestCase):
    def test_hand_calculation(self):
        result = examples()["four_fields"]["result"]
        self.assertAlmostEqual(result["observed_distance"], 1 / 3)
        self.assertEqual(result["coverage"], 0.75)
        self.assertEqual(result["distance_bounds"], [0.25, 0.5])
        self.assertEqual(result["similarity_bounds"], [0.5, 0.75])

    def test_unknown_is_not_equal(self):
        result = compare({}, {}, [{"id": "a", "kind": "nominal", "weight": 1}])
        self.assertIsNone(result["observed_distance"])
        self.assertEqual(result["coverage"], 0)
        self.assertEqual(result["distance_bounds"], [0, 1])

    def test_known_empty_sets_are_equal(self):
        self.assertEqual(field_difference([], [], "set"), 0)
        self.assertIsNone(field_difference([], None, "set"))
        self.assertEqual(field_difference([], ["a"], "set"), 1)

    def test_symmetry_and_weight_scale(self):
        sample = examples()["four_fields"]
        reverse = compare(sample["right"], sample["left"], sample["schema"])
        scaled = [{**f, "weight": f["weight"] * 100} for f in sample["schema"]]
        self.assertEqual(reverse, sample["result"])
        self.assertEqual(compare(sample["left"], sample["right"], scaled), sample["result"])

    def test_subdivision_does_not_increase_parent_budget(self):
        base = [{"id": "a", "kind": "nominal", "weight": 0.5}, {"id": "b", "kind": "nominal", "weight": 0.5}]
        split = [{"id": "a1", "kind": "nominal", "weight": 0.25}, {"id": "a2", "kind": "nominal", "weight": 0.25}, base[1]]
        first = compare({"a": 0, "b": 0}, {"a": 1, "b": 0}, base)
        second = compare({"a1": 0, "a2": 0, "b": 0}, {"a1": 1, "a2": 1, "b": 0}, split)
        self.assertEqual(first["observed_distance"], second["observed_distance"])

    def test_triangle_failure_is_reproducible(self):
        pairs = examples()["missing_triangle"]
        self.assertEqual([pairs[k]["observed_distance"] for k in ("AB", "BC", "AC")], [0, 0, 1])
        self.assertTrue(all(abs(v["coverage"] - 1 / 3) < 1e-12 for v in pairs.values()))

    def test_all_possible_missing_completions_respect_bounds(self):
        sample = examples()["four_fields"]
        low, high = sample["result"]["distance_bounds"]
        for value in ([], ["manual"], ["api"], ["manual", "api"]):
            result = compare(sample["left"], {**sample["right"], "trigger": value}, sample["schema"])
            self.assertLessEqual(low, result["observed_distance"])
            self.assertGreaterEqual(high, result["observed_distance"])
            self.assertEqual(result["coverage"], 1)

    def test_invalid_input(self):
        for weight in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                compare({}, {}, [{"id": "a", "kind": "nominal", "weight": weight}])
        with self.assertRaises(ValueError):
            field_difference(1, 2, "ordinal", 0)
        with self.assertRaises(ValueError):
            field_difference(float("nan"), 2, "numeric", 3)

    def test_complete_identity_and_fixed_range(self):
        sample = examples()["four_fields"]
        result = compare(sample["left"], sample["left"], sample["schema"])
        self.assertEqual(result["distance_bounds"], [0, 0])
        self.assertEqual(field_difference(0, 100, "numeric", 10), 1)


if __name__ == "__main__":
    unittest.main()
