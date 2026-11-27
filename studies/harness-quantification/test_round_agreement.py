"""MIT. Unit tests for the per-round inter-coder agreement (trial_distance.round_rows / round_agreement)."""
import json
import tempfile
import unittest
from pathlib import Path

import trial_distance
from trial_distance import archived_rounds, compute, round_agreement

HERE = Path(__file__).parent
SCHEMA_TEXT = (HERE / "data" / "schema" / "fields.json").read_text(encoding="utf-8")
SCHEMA = json.loads(SCHEMA_TEXT)
FIELDS = {f["id"]: f for f in SCHEMA["fields"]}
N = len(FIELDS)
# nominal fields outside group G with a second value, used to make the coders disagree on a value
SWAPPABLE = [fid for fid, f in FIELDS.items()
             if f["type"] == "nominal" and fid not in ("F25", "F26", "F27", "F28") and len(f["vocabulary"]) > 1]


def fields(differ=0):
    """Every field known with its first value; G absent. The first `differ` swappable fields take the second value."""
    out = {}
    for fid, f in FIELDS.items():
        first = f["vocabulary"][0]["id"]
        out[fid] = {"status": "known", "value": first if f["type"] == "nominal" else [first]}
    out["F25"] = {"status": "known", "value": "absent"}
    for fid in ("F26", "F27", "F28"):
        out[fid] = {"status": "not_applicable"}
    for fid in SWAPPABLE[:differ]:
        out[fid] = {"status": "known", "value": FIELDS[fid]["vocabulary"][1]["id"]}
    return out


def round_rows(res, root):
    fn = getattr(trial_distance, "round_rows", None)
    if fn is None:
        raise AssertionError("trial_distance.round_rows(res, root) is missing")
    return fn(res, root)


def mean_and_count(v):
    """closed/open as (mean, n): accepts a pair or a dict with a mean and a count key."""
    if isinstance(v, dict):
        count = next(v[k] for k in ("n", "count", "configs") if k in v)
        return v["mean"], count
    mean, count = v
    return mean, count


class Fixture:
    def __init__(self, root):
        self.root = root
        (root / "data" / "schema").mkdir(parents=True)
        (root / "data" / "schema" / "fields.json").write_text(SCHEMA_TEXT, encoding="utf-8")
        (root / "data" / "configs").mkdir(parents=True)
        (root / "data" / "adjudications").mkdir(parents=True)
        for c in ("opus", "gpt"):
            (root / "data" / "codings" / c).mkdir(parents=True)

    def put(self, folder, cid, rnd, codebook="fields-0.11", differ=0, closed=False):
        """One config coded by both coders; gpt differs on `differ` values. Open configs cite a source path."""
        for c, n in (("opus", 0), ("gpt", differ)):
            (self.root / folder / c).mkdir(parents=True, exist_ok=True)
            rec = {"config_id": cid, "round": rnd, "codebook_version": codebook, "fields": fields(n)}
            (self.root / folder / c / f"{cid}.json").write_text(json.dumps(rec), encoding="utf-8")
        evidence = [] if closed else [{"evidence_kind": "source_path"}]
        (self.root / "data" / "configs" / f"{cid}.json").write_text(json.dumps({"evidence": evidence}), encoding="utf-8")

    def rows(self):
        res = compute(self.root)
        return round_rows(res, self.root), round_agreement(res, self.root)


class RoundRows(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_batches_sort_by_number_not_by_name(self):
        for b in ("batch-10", "batch-2", "batch-9"):
            self.fx.put(f"batches/{b}", f"C{b}", b)
        rows, _ = self.fx.rows()
        self.assertEqual([r["round"] for r in rows], ["batch-2", "batch-9", "batch-10"])

    def test_recode_rounds_follow_batches_by_number(self):
        for b in ("recode-10", "batch-3", "recode-2", "batch-1"):
            self.fx.put(f"batches/{b}", f"C{b}", b)
        rows, _ = self.fx.rows()
        self.assertEqual([r["round"] for r in rows], ["batch-1", "batch-3", "recode-2", "recode-10"])

    def test_empty_data_codings_adds_no_round(self):
        self.fx.put("batches/batch-1", "C1", "batch-1")
        rows, table = self.fx.rows()
        self.assertEqual([r["round"] for r in rows], ["batch-1"])
        self.assertEqual(len(table.splitlines()), 2)

    def test_data_codings_come_last_named_by_their_round_field(self):
        self.fx.put("batches/recode-1", "C1", "recode-1")
        self.fx.put("data/codings", "C2", "recode-2")
        rows, table = self.fx.rows()
        self.assertEqual([r["round"] for r in rows], ["recode-1", "recode-2"])
        self.assertEqual(rows[-1]["configs"], 1)
        self.assertTrue(table.splitlines()[-1].startswith("recode-2 | "))

    def test_codings_whose_round_field_differs_are_skipped(self):
        self.fx.put("batches/batch-1", "C1", "batch-1", codebook="fields-0.5")
        self.fx.put("batches/batch-1", "C2", "recode-1", codebook="fields-0.9", differ=3)
        self.fx.put("batches/recode-1", "C2", "recode-1", codebook="fields-0.9", differ=3)
        rows, _ = self.fx.rows()
        by = {r["round"]: r for r in rows}
        self.assertEqual(by["batch-1"]["configs"], 1)
        self.assertEqual(by["batch-1"]["codebooks"], ["fields-0.5"])
        self.assertAlmostEqual(by["batch-1"]["mean"], 1.0)
        self.assertEqual(by["recode-1"]["configs"], 1)

    def test_codebooks_are_a_sorted_list_without_repeats(self):
        self.fx.put("batches/batch-1", "C1", "batch-1", codebook="fields-0.9")
        self.fx.put("batches/batch-1", "C2", "batch-1", codebook="fields-0.10")
        self.fx.put("batches/batch-1", "C3", "batch-1", codebook="fields-0.9")
        rows, _ = self.fx.rows()
        self.assertEqual(rows[0]["codebooks"], ["fields-0.10", "fields-0.9"])
        self.assertEqual(rows[0]["configs"], 3)

    def test_closed_and_open_groups_and_agree_value(self):
        k = 4
        self.fx.put("batches/batch-1", "C1", "batch-1", closed=True)
        self.fx.put("batches/batch-1", "C2", "batch-1", differ=k)
        rows, table = self.fx.rows()
        r = rows[0]
        cm, cn = mean_and_count(r["closed"])
        om, on = mean_and_count(r["open"])
        self.assertEqual((cn, on), (1, 1))
        self.assertAlmostEqual(cm, 1.0)
        self.assertAlmostEqual(om, round((N - k) / N, 4))
        self.assertAlmostEqual(r["mean"], (1.0 + round((N - k) / N, 4)) / 2)
        # F26–F28 are not_applicable on both sides, so each config has N - 3 both-known fields.
        bk = N - 3
        self.assertAlmostEqual(r["agree_value_among_both_known"], (2 * bk - k) / (2 * bk))
        line = table.splitlines()[1]
        self.assertIn(f" | 100.0% (1) | {100 * round((N - k) / N, 4):.1f}% (1) | ", line)

    def test_empty_group_has_no_mean_and_shows_a_dash(self):
        self.fx.put("batches/batch-1", "C1", "batch-1", closed=True)
        self.fx.put("batches/batch-1", "C2", "batch-1", closed=True)
        rows, table = self.fx.rows()
        om, on = mean_and_count(rows[0]["open"])
        self.assertEqual(on, 0)
        self.assertIsNone(om)
        self.assertEqual(mean_and_count(rows[0]["closed"])[1], 2)
        self.assertEqual(table.splitlines()[1], "batch-1 | fields-0.11 | 2 | 100.0% | 100.0% (2) | - (0) | 100.0%")

    def test_table_header_and_one_line_per_row(self):
        self.fx.put("batches/batch-2", "C1", "batch-2", codebook="fields-0.10", differ=2)
        self.fx.put("batches/batch-1", "C2", "batch-1", codebook="fields-0.9", closed=True)
        rows, table = self.fx.rows()
        lines = table.splitlines()
        self.assertEqual(lines[0], "round | codebook | configs | mean agreement | closed (n) | open (n) | agree-value among both-known")
        self.assertEqual(len(lines), len(rows) + 1)
        for r, line in zip(rows, lines[1:]):
            self.assertTrue(line.startswith(f"{r['round']} | {', '.join(r['codebooks'])} | {r['configs']} | "))


class RepositoryRounds(unittest.TestCase):
    def test_rows_follow_the_repository_round_folders(self):
        res = compute()
        rows = round_rows(res, HERE)
        names = [b.name for b in archived_rounds()]
        current = sorted((HERE / "data" / "codings" / "opus").glob("*.json"))
        if current:
            names.append(json.loads(current[0].read_text(encoding="utf-8"))["round"])
        self.assertEqual([r["round"] for r in rows], names)
        lines = round_agreement(res).splitlines()
        self.assertEqual(len(lines), len(rows) + 1)
        for r, line in zip(rows, lines[1:]):
            self.assertTrue(line.startswith(f"{r['round']} | "))
            self.assertEqual(line.count(" | "), 6)


if __name__ == "__main__":
    unittest.main()
