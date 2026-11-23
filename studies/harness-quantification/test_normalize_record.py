"""配置记录草稿机械清理（pilot/normalize_record.py）的合成回归；只在临时目录里造记录，不联网。"""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parent
SCRIPT = STUDY / "pilot/normalize_record.py"
REPO = STUDY.parents[1]
CATALOG_PATH = REPO / "research/catalog.json"

ORDER = ["evidence_kind", "source_url", "locator", "lines", "version", "retrieved_at", "content_sha256",
         "configuration_scope", "note"]


def load_module():
    spec = importlib.util.spec_from_file_location("normalize_record_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def clean_evidence(**extra):
    item = {
        "evidence_kind": "official_docs",
        "source_url": "https://example.invalid/docs/setup",
        "locator": "合成文档 Setup 小节",
        "lines": "L10-L20",
        "version": "v1.2.3",
        "retrieved_at": "2026-11-01",
        "content_sha256": "0" * 64,
        "configuration_scope": "默认安装",
        "note": "合成说明",
    }
    item.update(extra)
    return item


def record(tool_id="Z90", product="合成产品", evidence=None, **extra):
    data = {
        "schema_version": "config-0.1",
        "synthetic": True,
        "config_id": f"{tool_id}__synthetic-a__local-default",
        "tool_id": tool_id,
        "product": product,
        "entrypoint": "CLI（合成）",
        "evidence": evidence if evidence is not None else [clean_evidence()],
    }
    data.update(extra)
    return data


class NormalizeRecordCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, data, name="Z90__synthetic-a__local-default.json", text=None):
        path = self.root / name
        path.write_text(dump(data) if text is None else text, encoding="utf-8")
        return path

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                              cwd=self.root, timeout=60)

    def normalize(self, data, *flags):
        path = self.write(data)
        result = self.run_script(path, *flags)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(path.read_text(encoding="utf-8")), result


class ModuleContract(unittest.TestCase):
    def test_script_exists_and_loads(self):
        self.assertTrue(SCRIPT.is_file(), f"{SCRIPT} missing")
        load_module()

    def test_docstring_starts_with_mit_and_documents_usage(self):
        doc = load_module().__doc__ or ""
        self.assertTrue(doc.startswith("MIT."), doc[:40])
        self.assertIn("normalize_record.py", doc)
        self.assertIn("--check", doc)
        self.assertIn("--product-from-catalog", doc)


class EmptyEvidenceKeys(NormalizeRecordCase):
    def test_empty_lines_sha_version_are_removed(self):
        item = clean_evidence(lines="", content_sha256="", version="")
        out, _ = self.normalize(record(evidence=[item]))
        got = out["evidence"][0]
        for key in ("lines", "content_sha256", "version"):
            self.assertNotIn(key, got)
        self.assertEqual(got["locator"], item["locator"])
        self.assertEqual(got["note"], item["note"])

    def test_only_empty_values_are_removed(self):
        items = [clean_evidence(lines=""), clean_evidence(version=""), clean_evidence(content_sha256="")]
        out, _ = self.normalize(record(evidence=items))
        self.assertNotIn("lines", out["evidence"][0])
        self.assertEqual(out["evidence"][0]["version"], "v1.2.3")
        self.assertEqual(out["evidence"][0]["content_sha256"], "0" * 64)
        self.assertNotIn("version", out["evidence"][1])
        self.assertEqual(out["evidence"][1]["lines"], "L10-L20")
        self.assertNotIn("content_sha256", out["evidence"][2])
        self.assertEqual(out["evidence"][2]["version"], "v1.2.3")

    def test_other_empty_keys_are_kept(self):
        item = clean_evidence(note="", configuration_scope="", lines="")
        out, _ = self.normalize(record(evidence=[item]))
        got = out["evidence"][0]
        self.assertEqual(got["note"], "")
        self.assertEqual(got["configuration_scope"], "")
        self.assertNotIn("lines", got)


class EvidenceKeyOrder(NormalizeRecordCase):
    def test_known_keys_follow_fixed_order(self):
        item = clean_evidence()
        shuffled = {key: item[key] for key in reversed(ORDER)}
        out, _ = self.normalize(record(evidence=[shuffled]))
        self.assertEqual(list(out["evidence"][0]), ORDER)
        self.assertEqual(out["evidence"][0], item)

    def test_unknown_keys_go_last_in_original_relative_order(self):
        item = {
            "zeta_extra": "z",
            "note": "合成说明",
            "environment": "合成环境",
            "source_url": "https://example.invalid/a",
            "alpha_extra": "a",
            "evidence_kind": "official_docs",
            "locator": "合成定位",
        }
        out, _ = self.normalize(record(evidence=[item]))
        self.assertEqual(list(out["evidence"][0]),
                         ["evidence_kind", "source_url", "locator", "note", "zeta_extra", "environment", "alpha_extra"])

    def test_top_level_key_order_is_untouched(self):
        data = record(evidence=[{key: clean_evidence()[key] for key in reversed(ORDER)}])
        out, _ = self.normalize(data)
        self.assertEqual(list(out), list(data))


class HomePathBackticks(NormalizeRecordCase):
    def test_bare_home_path_is_backticked_everywhere_except_source_url(self):
        url = "https://example.invalid/home/alice/x /home/alice/y"
        data = record(
            evidence=[clean_evidence(source_url=url, note="写入 /home/alice/.config/tool/settings.json 之后生效")],
            entrypoint="/home/bob/bin/tool",
            environment_premises={"workspace": "仓库位于 /home/carol/src/repo 根目录"},
            enabled_extensions=["插件目录 /home/dave/.tool/plugins 下的全部插件"],
        )
        out, _ = self.normalize(data)
        self.assertEqual(out["evidence"][0]["source_url"], url)
        self.assertEqual(out["evidence"][0]["note"], "写入 `/home/alice/.config/tool/settings.json` 之后生效")
        self.assertEqual(out["entrypoint"], "`/home/bob/bin/tool`")
        self.assertEqual(out["environment_premises"]["workspace"], "仓库位于 `/home/carol/src/repo` 根目录")
        self.assertEqual(out["enabled_extensions"], ["插件目录 `/home/dave/.tool/plugins` 下的全部插件"])

    def test_source_url_with_bare_home_path_is_never_touched(self):
        data = record(evidence=[clean_evidence(source_url="/home/alice/mirror/page.html")])
        out, _ = self.normalize(data)
        self.assertEqual(out["evidence"][0]["source_url"], "/home/alice/mirror/page.html")

    def test_already_backticked_paths_are_left_alone(self):
        texts = [
            "见 `/home/alice/.config/x.json` 文件",
            "运行 `cat /home/alice/.config/x.json` 查看",
        ]
        data = record(evidence=[clean_evidence(note=t) for t in texts])
        out, _ = self.normalize(data)
        self.assertEqual([e["note"] for e in out["evidence"]], texts)

    def test_path_preceded_by_excluded_characters_is_left_alone(self):
        texts = [
            "~/home/alice/x 不动",
            "a/home/alice/x 不动",
            "9/home/alice/x 不动",
            "./home/alice/x 不动",
            "-/home/alice/x 不动",
            "//home/alice/x 不动",
            "/srv/home/alice/x 不动",
            "~/.claude/projects/<project>/memory/ 不动",
        ]
        data = record(evidence=[clean_evidence(note=t) for t in texts])
        out, _ = self.normalize(data)
        self.assertEqual([e["note"] for e in out["evidence"]], texts)

    def test_path_at_string_start_and_after_space(self):
        data = record(evidence=[clean_evidence(note="/home/alice/a 和 /home/bob/b")])
        out, _ = self.normalize(data)
        self.assertEqual(out["evidence"][0]["note"], "`/home/alice/a` 和 `/home/bob/b`")

    def test_other_values_are_not_rewritten(self):
        data = record(
            evidence=[clean_evidence()],
            synthetic=True,
            subagents_enabled=False,
            enabled_extensions=["合成扩展 A", "合成扩展 B"],
            environment_premises={"host_os": "macOS 或 Linux", "other": "无"},
        )
        out, _ = self.normalize(data)
        self.assertEqual(out, data)


class ProductFromCatalog(NormalizeRecordCase):
    def catalog_entry(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        return catalog[0]["id"], catalog[0]["name"]

    def test_flag_sets_product_from_catalog_name(self):
        tool_id, name = self.catalog_entry()
        out, _ = self.normalize(record(tool_id=tool_id, product=name + "（草稿名）"), "--product-from-catalog")
        self.assertEqual(out["product"], name)
        self.assertEqual(out["tool_id"], tool_id)

    def test_without_flag_product_is_unchanged(self):
        tool_id, name = self.catalog_entry()
        draft = name + "（草稿名）"
        out, _ = self.normalize(record(tool_id=tool_id, product=draft))
        self.assertEqual(out["product"], draft)


class CommandLine(NormalizeRecordCase):
    def dirty(self):
        return record(evidence=[{"note": "写入 /home/alice/x 后", "lines": "", "evidence_kind": "official_docs",
                                 "source_url": "https://example.invalid/a", "locator": "合成定位"}])

    def test_in_place_without_out(self):
        path = self.write(self.dirty())
        result = self.run_script(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        got = json.loads(path.read_text(encoding="utf-8"))["evidence"][0]
        self.assertEqual(list(got), ["evidence_kind", "source_url", "locator", "note"])
        self.assertEqual(got["note"], "写入 `/home/alice/x` 后")

    def test_out_path_leaves_input_untouched(self):
        path = self.write(self.dirty())
        before = path.read_bytes()
        out_path = self.root / "out.json"
        result = self.run_script(path, out_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_bytes(), before)
        got = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertNotIn("lines", got["evidence"][0])

    def test_output_format(self):
        data = record(product="合成产品", evidence=[clean_evidence(lines="")])
        compact = json.dumps(data, ensure_ascii=True)
        path = self.write(data, text=compact)
        result = self.run_script(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = copy.deepcopy(data)
        del expected["evidence"][0]["lines"]
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text, dump(expected))
        self.assertIn("合成产品", text)
        self.assertTrue(text.endswith("}\n"))
        self.assertFalse(text.endswith("\n\n"))

    def test_prints_one_line_per_record(self):
        path = self.write(self.dirty())
        result = self.run_script(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, result.stdout)

    def test_check_reports_without_writing_and_exits_1(self):
        path = self.write(self.dirty())
        before = path.read_bytes()
        result = self.run_script(path, "--check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(result.stdout.strip(), "--check should report what would change")

    def test_check_with_out_path_writes_nothing(self):
        path = self.write(self.dirty())
        out_path = self.root / "out.json"
        result = self.run_script(path, out_path, "--check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(out_path.exists())

    def test_check_on_clean_record_exits_0(self):
        path = self.write(record())
        before = path.read_bytes()
        result = self.run_script(path, "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(path.read_bytes(), before)

    def test_check_counts_catalog_product_as_change_only_with_flag(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        tool_id, name = catalog[0]["id"], catalog[0]["name"]
        path = self.write(record(tool_id=tool_id, product=name + "（草稿名）"))
        self.assertEqual(self.run_script(path, "--check").returncode, 0)
        self.assertEqual(self.run_script(path, "--check", "--product-from-catalog").returncode, 1)

    def test_normalized_output_is_idempotent(self):
        path = self.write(self.dirty())
        self.assertEqual(self.run_script(path).returncode, 0)
        once = path.read_bytes()
        result = self.run_script(path, "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.run_script(path).returncode, 0)
        self.assertEqual(path.read_bytes(), once)


if __name__ == "__main__":
    unittest.main()
