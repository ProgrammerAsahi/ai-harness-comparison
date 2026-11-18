"""固定三分块契约的合成回归；不读取实际编码，不向实际成品目录写入。"""
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDY = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pilot_parts_under_test", STUDY / "pilot/parts.py")
parts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parts)


class SplitContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = "Z90__synthetic-a__local-default"
        self.coder = "coder-a"
        self.context = parts.vd.Context(bench_dir=self.root / "bench")
        fixtures = parts.vd.FIXTURES
        self.fields = json.loads(
            (fixtures / "codings" / self.coder / f"{self.config}.json").read_text()
        )["fields"]
        self.ids = {g: [f["id"] for f in parts.group_fields(self.context, g)] for g in parts.SPLIT}
        self.data = self.root / "data"
        for folder in ("templates", "configs"):
            (self.data / folder).mkdir(parents=True)
        (self.data / "templates/coding.template.json").write_bytes(
            (parts.vd.DATA / "templates/coding.template.json").read_bytes()
        )
        (self.data / "configs" / f"{self.config}.json").write_bytes(
            (fixtures / "configs" / f"{self.config}.json").read_bytes()
        )
        self.base = self.root / "parts"
        for target, name, value in (
            (parts, "PARTS", self.base),
            (parts, "REPO", self.root),
            (parts.vd, "DATA", self.data),
            (parts.vd, "Context", lambda: self.context),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for group in parts.SPLIT:
            self.write(group)

    def write(self, filename, declared=None, ids=None, **changes):
        declared = filename if declared is None else declared
        ids = self.ids[filename] if ids is None else ids
        record = {
            "coder": self.coder, "config_id": self.config, "groups": declared,
            "fields": {fid: copy.deepcopy(self.fields.get(fid, self.fields["F01"])) for fid in ids},
        }
        record.update(changes)
        path = self.base / self.coder / self.config / f"{filename}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record))
        return path

    def merge(self, dry="dry"):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = parts.merge(self.coder, self.config, "synthetic-model", "synthetic-p1", dry)
        return result, output.getvalue()

    def test_legal_parts_merge_and_write_only_to_temporary_data(self):
        for group in parts.SPLIT:
            path = self.base / self.coder / self.config / f"{group}.json"
            self.assertEqual(parts.check_part(path, self.context, quiet=True)[0], [])
        self.assertEqual(self.merge()[0], 0)
        self.assertEqual(self.merge(dry=None)[0], 0)
        result = json.loads((self.data / "codings" / self.coder / f"{self.config}.json").read_text())
        self.assertEqual(result["fields"], self.fields)

    def test_swapped_declarations_are_rejected_by_merge(self):
        self.write("ABC", "DEF", self.ids["DEF"])
        self.write("DEF", "ABC", self.ids["ABC"])
        result, output = self.merge()
        self.assertEqual(result, 1)
        self.assertIn("groups must match filename", output)

    def test_overlapping_group_declaration_is_rejected(self):
        self.write("ABC", "ABCDEF", self.ids["ABC"] + self.ids["DEF"])
        result, output = self.merge()
        self.assertEqual(result, 1)
        self.assertIn("repeated fields", output)

    def test_invalid_group_types_and_names_are_rejected(self):
        for group in ("XYZ", "", "ABCDEF", ["A", "B", "C"], 1):
            with self.subTest(group=group):
                path = self.write("ABC", group, [])
                errors, _ = parts.check_part(path, self.context, quiet=True)
                self.assertTrue(errors)
                self.assertIn("groups must be one of", errors[0])
                self.assertEqual(self.merge()[0], 1)

    def test_fields_must_be_an_object(self):
        for fields in ([], None, "F01"):
            with self.subTest(fields=fields):
                path = self.write("ABC", fields=fields)
                errors, _ = parts.check_part(path, self.context, quiet=True)
                self.assertIn("fields must be an object", errors[0])
                self.assertEqual(self.merge()[0], 1)

    def test_wrong_coder_and_config_are_rejected(self):
        for changes in ({"coder": "coder-b"}, {"config_id": "wrong-config"}):
            with self.subTest(changes=changes):
                self.write("DEF", **changes)
                result, output = self.merge()
                self.assertEqual(result, 1)
                self.assertIn("config_id or coder does not match", output)

    def test_missing_part_is_rejected(self):
        (self.base / self.coder / self.config / "GHI.json").unlink()
        result, output = self.merge()
        self.assertEqual(result, 1)
        self.assertIn("missing part", output)

    def test_extra_and_missing_fields_are_rejected(self):
        for ids in (self.ids["ABC"] + ["F13"], self.ids["ABC"] + ["F99"], self.ids["ABC"][:-1]):
            with self.subTest(ids=ids):
                path = self.write("ABC", ids=ids)
                errors, _ = parts.check_part(path, self.context, quiet=True)
                self.assertTrue(errors)
                self.assertEqual(self.merge()[0], 1)

    def test_failed_merge_never_overwrites_an_existing_result(self):
        self.assertEqual(self.merge(dry=None)[0], 0)
        result = self.data / "codings" / self.coder / f"{self.config}.json"
        before = result.read_bytes()
        self.write("ABC", "DEF", self.ids["DEF"])
        self.assertEqual(self.merge(dry=None)[0], 1)
        self.assertEqual(result.read_bytes(), before)

    def test_check_accepts_a_temporary_filename_for_a_valid_part(self):
        path = self.write("ABC")
        temporary = path.with_name("submission.json")
        path.rename(temporary)
        self.assertEqual(parts.check_part(temporary, self.context, quiet=True)[0], [])


if __name__ == "__main__":
    unittest.main()
