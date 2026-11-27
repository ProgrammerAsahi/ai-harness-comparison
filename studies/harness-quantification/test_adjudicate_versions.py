"""MIT. Unit tests for checking each adjudication under its own codebook version (synthetic tree only)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import adjudicate as adj
import validate_data as vd
from test_adjudicate import CID, SCHEMA, adjudication, pair

CURRENT = SCHEMA["schema_version"]
OLD = "fields-0.0"
LEGACY = "legacy_only_reading"


def old_schema():
    """The current codebook renamed to OLD, with one F04 value its successor dropped."""
    s = copy.deepcopy(SCHEMA)
    s["schema_version"] = OLD
    f04 = next(f for f in s["fields"] if f["id"] == "F04")
    f04["vocabulary"].append({**f04["vocabulary"][0], "id": LEGACY})
    return s


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def build_root(root, rec, archive_name=f"{OLD}.json"):
    """fields.json, an archived round with its codebook and both codings, and one adjudication."""
    write(root / "data" / "schema" / "fields.json", SCHEMA)
    write(root / "batches" / "recode-9" / archive_name, old_schema())
    _, p = pair()[CID]
    for coder in adj.CODERS:
        write(root / "batches" / "recode-9" / coder / f"{CID}.json", dict(p[coder], round="recode-9"))
    write(root / "data" / "adjudications" / f"{CID}.json", rec)


def record(version, f04=None):
    """An adjudication of the synthetic pair under `version`; f04 replaces the F04 entry with a 'neither' reading."""
    _, p = pair()[CID]
    codings = {CID: ("recode-9", {c: dict(p[c], round="recode-9") for c in adj.CODERS})}
    rec = adjudication(codings)
    rec["codings"] = {c: "recode-9" for c in adj.CODERS}
    rec["codebook_version"] = version
    if f04 is not None:
        rec["fields"]["F04"] = {"choice": "neither", "status": "known", "value": f04, "unknown_reason": None,
                                "settled_by": "lead", "picks": {}, "rationale": "依据旧版词表判。", "evidence": ""}
    return rec


class CheckUnderOwnCodebook(unittest.TestCase):
    def check(self, rec, **kw):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            build_root(root, rec, **kw)
            return adj.check_all(root)

    def test_current_version_is_clean(self):
        self.assertEqual(self.check(record(CURRENT)), [])

    def test_archived_version_accepts_its_own_vocabulary(self):
        errs = self.check(record(OLD, [LEGACY]))
        self.assertFalse([e for e in errs if "vocabulary" in e], errs)
        self.assertEqual(errs, [])
        errs = self.check(record(CURRENT, [LEGACY]))
        self.assertTrue(any("F04" in e and LEGACY in e and "vocabulary" in e for e in errs), errs)

    def test_unknown_version_is_reported_by_name(self):
        errs = self.check(record("fields-9.99"))
        self.assertTrue(any("fields-9.99" in e and "neither current nor archived" in e for e in errs), errs)

    def test_named_codebook_is_the_one_used(self):
        used, real = [], vd.Context

        def spy(schema, *a, **kw):
            used.append(schema["schema_version"])
            return real(schema, *a, **kw)

        for version in (OLD, CURRENT):
            used.clear()
            with mock.patch.object(adj.vd, "Context", side_effect=spy):
                errs = self.check(record(version))
            self.assertEqual(used, [version])
            self.assertFalse([e for e in errs if "checked against" in e], errs)
        # the archive's file name does not decide the version; the schema_version inside it does
        used.clear()
        with mock.patch.object(adj.vd, "Context", side_effect=spy):
            errs = self.check(record(OLD, [LEGACY]), archive_name="fields-renamed.json")
        self.assertEqual((used, errs), ([OLD], []))
        # a record checked against another codebook names both, the second being the one in use
        _, p = pair()[CID]
        codings = {CID: ("recode-9", {c: dict(p[c], round="recode-9") for c in adj.CODERS})}
        errs = adj.check_adjudication(record(CURRENT), codings, vd.Context(old_schema()))
        self.assertIn(f"{CID}: adjudicated under {CURRENT}, but checked against {OLD}",
                      [e.split("adjudications/", 1)[-1] for e in errs])

    def test_records_in_one_tree_each_use_their_own_codebook(self):
        other = CID.replace("Z01", "Z02")
        second = dict(record(CURRENT), config_id=other)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            build_root(root, record(OLD, [LEGACY]))
            _, p = pair()[CID]
            for coder in adj.CODERS:
                write(root / "batches" / "recode-9" / coder / f"{other}.json", dict(p[coder], round="recode-9"))
            write(root / "data" / "adjudications" / f"{other}.json", second)
            self.assertEqual(adj.check_all(root), [])


if __name__ == "__main__":
    unittest.main()
