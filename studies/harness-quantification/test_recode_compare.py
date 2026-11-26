"""MIT. Unit tests for pilot/recode_compare.py, the recode-round comparison.

Part 1 builds a minimal synthetic tree under tempfile: data/schema/fields.json copied from the
real codebook, one round listing two "recode" configs (in two different original batches) plus a
non-recode config that must be skipped, and codings that differ in only two or three fields so
the expectations are hand-computable. Part 2 runs compare_round over the repository's real
recode-1 (read-only) and checks the published numbers from the "一致率" table in
batches/recode-1.md to one decimal place. The tests only read the in-repo schema and data,
write only to tempfile, and need no network access.

  python3 -m unittest discover -s studies/harness-quantification -p 'test_*.py' -v
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parent
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

spec = importlib.util.spec_from_file_location("recode_compare_under_test", STUDY / "pilot" / "recode_compare.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

SCHEMA = json.loads((STUDY / "data" / "schema" / "fields.json").read_text(encoding="utf-8"))
FIELD_IDS = [f["id"] for f in SCHEMA["fields"]]
N_FIELDS = len(FIELD_IDS)  # 36

CFG_A = "Z90__synthetic-a__local-default"
CFG_B = "Z91__synthetic-b__local-default"
CFG_C = "Z92__synthetic-c__local-default"
BATCH_A, BATCH_B = "batch-s", "batch-t"
ROUND = "syn-recode"


def base_field(field):
    if field["type"] in ("set", "conditional_set"):
        return {"status": "known", "value": []}
    return {"status": "known", "value": "base"}


def coding(config_id, round_name, coder, overrides):
    """A synthetic coding: every field at a shared base value, plus a few differing ones."""
    fields = {f["id"]: base_field(f) for f in SCHEMA["fields"]}
    for fid, value in overrides.items():
        fields[fid] = {"status": "known", "value": value}
    return {
        "schema_version": "coding-0.1",
        "codebook_version": "fields-0.10",
        "synthetic": True,
        "round": round_name,
        "config_id": config_id,
        "coder": {"id": coder},
        "independent": True,
        "evidence_cutoff": "2026-01-01",
        "fields": fields,
    }


class SyntheticTree(unittest.TestCase):
    """compare_round over a hand-computed synthetic tree (write-only to tempfile)."""

    # Per-config differences (field: value) for the four Z90/Z91 codings.
    # Z90: old pair differs on F01 (other) and F04 (revised); the new pair on F01, F04, F05;
    #     each coder changed F01, F04 and F05 between rounds.
    # Z91: the old pair agrees on all 36 fields; the new pair differs only on F10 (revised);
    #     each coder changed F10 and F20 (other) between rounds.
    OVERRIDES = {
        (CFG_A, BATCH_A, "opus"): {"F01": "a"},
        (CFG_A, BATCH_A, "gpt"): {"F01": "b", "F04": ["g"]},
        (CFG_A, ROUND, "opus"): {"F01": "a2", "F04": ["o2"], "F05": "p"},
        (CFG_A, ROUND, "gpt"): {"F01": "b2", "F04": ["o3"], "F05": "q"},
        (CFG_B, BATCH_B, "opus"): {},
        (CFG_B, BATCH_B, "gpt"): {},
        (CFG_B, ROUND, "opus"): {"F10": ["m"], "F20": ["u"]},
        (CFG_B, ROUND, "gpt"): {"F10": ["n"], "F20": ["u"]},
    }

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        (root / "data" / "schema").mkdir(parents=True)
        (root / "data" / "schema" / "fields.json").write_bytes(
            (STUDY / "data" / "schema" / "fields.json").read_bytes())
        for folder in ("data/rounds", "data/configs", "data/codings/opus", "data/codings/gpt",
                       f"batches/{BATCH_A}/opus", f"batches/{BATCH_A}/gpt",
                       f"batches/{BATCH_B}/opus", f"batches/{BATCH_B}/gpt"):
            (root / folder).mkdir(parents=True)
        tools = [
            {"tool_id": "Z90", "role": "recode", "config_id": CFG_A},
            {"tool_id": "Z91", "role": "recode", "config_id": CFG_B},
            # a non-recode config: compare_round must skip it; it has no batch codings, so a
            # processing mistake would raise FileNotFoundError
            {"tool_id": "Z92", "role": "holdout", "config_id": CFG_C},
        ]
        (root / "data" / "rounds" / f"{ROUND}.json").write_text(
            json.dumps({"round": ROUND, "synthetic": True, "codebook_version": "fields-0.10",
                        "tools": tools}, ensure_ascii=False), encoding="utf-8")
        batch_of = {CFG_A: BATCH_A, CFG_B: BATCH_B, CFG_C: BATCH_A}
        for cfg in (CFG_A, CFG_B, CFG_C):
            (root / "data" / "configs" / f"{cfg}.json").write_text(
                json.dumps({"schema_version": "config-0.1", "synthetic": True, "config_id": cfg,
                            "round": batch_of[cfg]}, ensure_ascii=False), encoding="utf-8")
        for (cfg, batch, coder), overrides in cls.OVERRIDES.items():
            dest = root / "batches" / batch / coder if batch != ROUND else root / "data" / "codings" / coder
            dest.mkdir(parents=True, exist_ok=True)
            (dest / f"{cfg}.json").write_text(
                json.dumps(coding(cfg, batch, coder, overrides), ensure_ascii=False), encoding="utf-8")
        # the skipped config gets its own new codings, which the comparison must never read
        (root / "data" / "codings" / "opus" / f"{CFG_C}.json").write_text(
            json.dumps(coding(CFG_C, ROUND, "opus", {}), ensure_ascii=False), encoding="utf-8")
        (root / "data" / "codings" / "gpt" / f"{CFG_C}.json").write_text(
            json.dumps(coding(CFG_C, ROUND, "gpt", {}), ensure_ascii=False), encoding="utf-8")
        cls.root = root
        cls.result = rc.compare_round(ROUND, root=root)
        cls.rows = {r["config_id"]: r for r in cls.result["rows"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_non_recode_config_is_skipped(self):
        self.assertEqual([r["config_id"] for r in self.result["rows"]], [CFG_A, CFG_B])
        self.assertNotIn(CFG_C, self.rows)

    def test_z90_row_matches_hand_computation(self):
        r = self.rows[CFG_A]
        self.assertEqual(r["first_round"], BATCH_A)
        # old pair: 34/36 agree (F01, F04 differ); new pair: 33/36 (F01, F04, F05 differ)
        self.assertEqual(r["original"], round(34 / N_FIELDS, 4))
        self.assertEqual(r["new"], round(33 / N_FIELDS, 4))
        # each coder changed F01, F04 and F05 between rounds: 33/36 against its own original
        self.assertEqual(r["opus_self"], round(33 / N_FIELDS, 4))
        self.assertEqual(r["gpt_self"], round(33 / N_FIELDS, 4))
        # 22 revised fields, 14 others
        self.assertEqual(r["revised_old"], (21, 22))
        self.assertEqual(r["revised_new"], (20, 22))
        self.assertEqual(r["other_old"], (13, 14))
        self.assertEqual(r["other_new"], (13, 14))

    def test_z91_row_matches_hand_computation(self):
        r = self.rows[CFG_B]
        self.assertEqual(r["first_round"], BATCH_B)
        self.assertEqual(r["original"], 1.0)
        self.assertEqual(r["new"], round(35 / N_FIELDS, 4))
        self.assertEqual(r["opus_self"], round(34 / N_FIELDS, 4))
        self.assertEqual(r["gpt_self"], round(34 / N_FIELDS, 4))
        self.assertEqual(r["revised_old"], (22, 22))
        self.assertEqual(r["revised_new"], (21, 22))
        self.assertEqual(r["other_old"], (14, 14))
        self.assertEqual(r["other_new"], (14, 14))

    def test_per_field_counts(self):
        per_field = self.result["per_field"]
        self.assertEqual(sorted(per_field), FIELD_IDS)
        # F01, F04: one of the two configs agrees in each round; F05, F10: the rounds flip
        self.assertEqual(per_field["F01"], [1, 1])
        self.assertEqual(per_field["F04"], [1, 1])
        self.assertEqual(per_field["F05"], [2, 1])
        self.assertEqual(per_field["F10"], [2, 1])
        # F20 differs in neither pair (both codings say ["u"] in the new round)
        self.assertEqual(per_field["F20"], [2, 2])
        for fid in FIELD_IDS:
            if fid not in ("F01", "F04", "F05", "F10", "F20"):
                with self.subTest(field=fid):
                    self.assertEqual(per_field[fid], [2, 2])

    def test_default_root_is_the_repository_study(self):
        result = rc.compare_round("recode-1")
        self.assertEqual(len(result["rows"]), 10)


class RealRecodeOne(unittest.TestCase):
    """compare_round over the real recode-1 (read-only), checked against batches/recode-1.md.

    The published numbers below are from the "一致率" table of batches/recode-1.md, compared to
    one decimal place; the per-field spot values are from the "逐字段看" paragraph.
    """

    @classmethod
    def setUpClass(cls):
        cls.result = rc.compare_round("recode-1")
        cls.rows = {r["config_id"]: r for r in cls.result["rows"]}

    def test_ten_configs_and_all_fields(self):
        self.assertEqual(len(self.result["rows"]), 10)
        self.assertEqual(sorted(self.result["per_field"]), FIELD_IDS)
        for cfg in ("B19__tabnine-agent__ide-default", "C04__chatbox__desktop-default",
                    "A03__gemini-cli__cli-default"):
            self.assertEqual(self.rows[cfg]["first_round"],
                             "batch-3" if cfg.startswith("A03") else "batch-5")

    def test_published_config_numbers(self):
        b19, c04 = self.rows["B19__tabnine-agent__ide-default"], self.rows["C04__chatbox__desktop-default"]
        self.assertEqual(round(100 * b19["original"], 1), 50.0)
        self.assertEqual(round(100 * b19["new"], 1), 72.2)
        self.assertEqual(round(100 * c04["original"], 1), 97.2)
        self.assertEqual(round(100 * c04["new"], 1), 91.7)

    def test_published_mean(self):
        k = len(self.result["rows"])
        original = 100 * sum(r["original"] for r in self.result["rows"]) / k
        new = 100 * sum(r["new"] for r in self.result["rows"]) / k
        self.assertEqual(round(original, 1), 65.3)
        self.assertEqual(round(new, 1), 74.2)

    def test_published_per_field_spots(self):
        per_field = self.result["per_field"]
        self.assertEqual(per_field["F20"], [4, 8])
        self.assertEqual(per_field["F15"], [3, 7])
        self.assertEqual(per_field["F35"], [7, 4])
        self.assertEqual(per_field["F23"], [10, 8])


if __name__ == "__main__":
    unittest.main()
