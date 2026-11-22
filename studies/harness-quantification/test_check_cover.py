"""MIT. Synthetic acceptance tests for pilot/check_cover.py.

Every case builds a config record, SOURCE.txt, a docs export and a small split tar.gz archive in a
temporary directory; nothing is fetched, nothing under tmp/ or data/ is read.

  python3 -m unittest studies/harness-quantification/test_check_cover.py -v
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDY = Path(__file__).resolve().parent
SCRIPT = STUDY / "pilot/check_cover.py"

REPO = "example-org/example-tool"
PINNED = "a" * 40
OTHER = "b" * 40
CID = "Z91__synthetic-cover__cli-default"
DOCS = "https://docs.example.test"
# src/app.py has 5 text lines; the reader counts newlines + 1, so anything past line 6 is out of range.
FILES = {
    "src/app.py": "".join(f"line {n}\n" for n in range(1, 6)),
    "README.md": "# Example\n",
    "run_me.py": "import pathlib\npathlib.Path('EXECUTED').write_text('archive content ran')\n",
}


def blob(path, sha=PINNED, repo=REPO, anchor=""):
    return f"https://github.com/{repo}/blob/{sha}/{path}{anchor}"


def run_main(argv, cwd):
    """Load the script with importlib as __main__ under argv; return (exit code, stdout)."""
    if not SCRIPT.exists():
        raise AssertionError(f"{SCRIPT.relative_to(STUDY)} does not exist")
    out = io.StringIO()
    code = 0
    old = Path.cwd()
    os.chdir(cwd)
    try:
        with patch.object(sys, "argv", [str(SCRIPT), *argv]), contextlib.redirect_stdout(out):
            spec = importlib.util.spec_from_file_location("__main__", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except SystemExit as stop:
                code = stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
    finally:
        os.chdir(old)
    return code, out.getvalue()


class Snapshot:
    """A synthetic records dir and sources dir for one or more config ids."""

    def __init__(self, root):
        self.root = Path(root)
        self.records = self.root / "records"
        self.sources = self.root / "sources"
        self.records.mkdir()
        self.sources.mkdir()

    def add(self, cid, evidence, docs_name="docs-llms-full.txt", pages=None, pieces=2):
        folder = self.sources / cid
        folder.mkdir()
        (self.records / f"{cid}.json").write_text(
            json.dumps({"config_id": cid, "evidence": evidence}, indent=2), encoding="utf-8")
        (folder / "SOURCE.txt").write_text(
            f"config_id: {cid}\n"
            f"repository: https://github.com/{REPO}\ncommit: {PINNED}\n"
            f"archive: GitHub source archive of that commit\n"
            f"pieces: {pieces} (src.tar.gz.00 ...)\n"
            f"cite as: https://github.com/{REPO}/blob/{PINNED}/<path inside the archive>\n"
            f"docs: {docs_name}\n", encoding="utf-8")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            top = tarfile.TarInfo("example-org-example-tool-aaaaaaa")
            top.type = tarfile.DIRTYPE
            tar.addfile(top)
            for path, text in FILES.items():
                data = text.encode()
                info = tarfile.TarInfo(f"example-org-example-tool-aaaaaaa/{path}")
                info.size = len(data)
                info.mode = 0o755
                tar.addfile(info, io.BytesIO(data))
        data = buf.getvalue()
        size = -(-len(data) // pieces)
        for k in range(pieces):
            (folder / f"src.tar.gz.{k:02d}").write_bytes(data[k * size:(k + 1) * size])
        lines = docs_export(pages or PAGES)
        (folder / docs_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return lines


# Three pages; page "beta" sits well past its own relative length in the export.
PAGES = [("alpha", 30), ("beta", 10), ("gamma", 10)]


def docs_export(pages):
    lines = ["# Example docs", ""]
    for name, count in pages:
        lines.append(f"Source: {DOCS}/{name}")
        lines.extend(f"{name} text {n}" for n in range(1, count + 1))
    return lines


def body_range(lines, name):
    """1-based absolute (first, last) line of a page's body in the export."""
    start = lines.index(f"Source: {DOCS}/{name}") + 2
    end = start
    while end < len(lines) and not lines[end].startswith("Source: "):
        end += 1
    return start, end


def parse(output, cid=CID):
    summary = re.search(
        rf"^{re.escape(cid)}: evidence (\d+) \| in snapshot (\d+) \| wrong (\d+) \| outside (\d+)$",
        output, re.M)
    if not summary:
        raise AssertionError(f"no summary line for {cid} in:\n{output}")
    wrong = re.findall(r"^\s+WRONG \[(\d+)\] (.*)$", output, re.M)
    out = re.findall(r"^\s+OUT\s+\[(\d+)\] (.*)$", output, re.M)
    return tuple(int(x) for x in summary.groups()), {int(n): t for n, t in wrong}, {int(n): t for n, t in out}


class CheckCover(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.cwd = self.root / "cwd"
        self.cwd.mkdir()
        self.snap = Snapshot(self.root)

    def check(self, evidence, snap=None, **kw):
        snap = snap or self.snap
        lines = snap.add(CID, evidence, **kw)
        code, output = run_main(["--records", str(snap.records), "--sources", str(snap.sources), CID], self.cwd)
        return code, output, lines

    def test_commit_not_pinned(self):
        code, output, _ = self.check([
            {"evidence_kind": "source_path", "source_url": blob("src/app.py", sha=OTHER), "lines": "L1"},
            {"evidence_kind": "source_path", "source_url": blob("src/app.py"), "lines": "L1"},
        ])
        (total, ok, wrong, outside), bad, _ = parse(output)
        self.assertEqual((total, ok, wrong, outside), (2, 1, 1, 0), output)
        self.assertIn("commit not the pinned one", bad[0])
        self.assertEqual(code, 1)

    def test_path_not_in_archive(self):
        code, output, _ = self.check([
            {"evidence_kind": "source_path", "source_url": blob("src/missing.py"), "lines": "L1"},
            {"evidence_kind": "source_path", "source_url": blob("README.md")},
        ])
        (total, ok, wrong, outside), bad, _ = parse(output)
        self.assertEqual((total, ok, wrong, outside), (2, 1, 1, 0), output)
        self.assertIn("path not in archive", bad[0])
        self.assertIn("src/missing.py", bad[0])
        self.assertEqual(code, 1)

    def test_source_lines_past_end(self):
        code, output, _ = self.check([
            {"evidence_kind": "source_path", "source_url": blob("src/app.py", anchor="#L20-L22"),
             "lines": "L20-L22"},
            {"evidence_kind": "source_path", "source_url": blob("src/app.py", anchor="#L2-L4"),
             "lines": "L2-L4"},
        ])
        (total, ok, wrong, outside), bad, _ = parse(output)
        self.assertEqual((total, ok, wrong, outside), (2, 1, 1, 0), output)
        self.assertIn("past end of src/app.py", bad[0])
        self.assertEqual(code, 1)

    def test_doc_relative_lines_pass(self):
        code, output, _ = self.check([
            {"evidence_kind": "official_doc", "source_url": f"{DOCS}/beta", "lines": "L2-L5"},
            {"evidence_kind": "official_doc", "source_url": f"{DOCS}/alpha/", "lines": "L25-L30"},
        ])
        self.assertEqual(parse(output)[0], (2, 2, 0, 0), output)
        self.assertEqual(code, 0)

    def test_doc_absolute_lines_pass(self):
        for docs_name in ("docs-llms-full.txt", "docs-pages.txt"):
            with self.subTest(docs_name=docs_name):
                folder = self.root / docs_name
                folder.mkdir()
                lines = docs_export(PAGES)
                first, last = body_range(lines, "beta")
                self.assertGreater(first, 10 + 2, "fixture must put beta past its relative length")
                code, output, _ = self.check([
                    {"evidence_kind": "official_doc", "source_url": f"{DOCS}/beta",
                     "lines": f"L{first + 1}-L{last - 1}"},
                    {"evidence_kind": "official_doc", "source_url": f"{DOCS}/beta#section",
                     "lines": f"L{last}"},
                ], snap=Snapshot(folder), docs_name=docs_name)
                self.assertEqual(parse(output)[0], (2, 2, 0, 0), output)
                self.assertNotIn("past end of page", output)
                self.assertEqual(code, 0)

    def test_doc_lines_outside_both_ranges_are_wrong(self):
        lines = docs_export(PAGES)
        first, last = body_range(lines, "gamma")
        code, output, _ = self.check([
            {"evidence_kind": "official_doc", "source_url": f"{DOCS}/beta", "lines": f"L{first + 1}-L{last}"},
        ])
        (total, ok, wrong, outside), bad, _ = parse(output)
        self.assertEqual((total, ok, wrong, outside), (1, 0, 1, 0), output)
        self.assertIn("past end of page", bad[0])
        self.assertEqual(code, 1)

    def test_url_not_in_snapshot(self):
        code, output, _ = self.check([
            {"evidence_kind": "official_doc", "source_url": f"{DOCS}/not-exported", "lines": "L1-L3"},
            {"evidence_kind": "default_release",
             "source_url": f"https://github.com/{REPO}/releases/tag/v1.0.0"},
            {"evidence_kind": "source_path", "source_url": blob("README.md")},
        ])
        (total, ok, wrong, outside), bad, out = parse(output)
        self.assertEqual((total, ok, wrong, outside), (3, 1, 0, 2), output)
        self.assertEqual(sorted(out), [0, 1])
        self.assertIn(f"{DOCS}/not-exported", out[0])
        self.assertEqual(bad, {})
        self.assertEqual(code, 0)

    def test_one_summary_per_config(self):
        other = "Z92__synthetic-cover__other"
        self.snap.add(other, [{"evidence_kind": "source_path", "source_url": blob("README.md")}])
        self.snap.add(CID, [{"evidence_kind": "source_path", "source_url": blob("README.md")}])
        code, output = run_main(
            ["--records", str(self.snap.records), "--sources", str(self.snap.sources), CID, other], self.cwd)
        self.assertEqual(parse(output, CID)[0], (1, 1, 0, 0), output)
        self.assertEqual(parse(output, other)[0], (1, 1, 0, 0), output)
        self.assertEqual(code, 0)

    def test_archive_not_extracted_or_executed(self):
        before = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        evidence = [
            {"evidence_kind": "source_path", "source_url": blob("run_me.py"), "lines": "L1-L2"},
            {"evidence_kind": "source_path", "source_url": blob("src/app.py"), "lines": "L1"},
        ]
        fail = AssertionError("archive members must not be extracted to disk")
        ran = AssertionError("nothing may be executed")
        with patch.object(tarfile.TarFile, "extract", side_effect=fail), \
                patch.object(tarfile.TarFile, "extractall", side_effect=fail), \
                patch.object(subprocess, "Popen", side_effect=ran), \
                patch.object(os, "system", side_effect=ran):
            code, output, _ = self.check(evidence)
        self.assertEqual(parse(output)[0], (2, 2, 0, 0), output)
        self.assertEqual(code, 0)
        after = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        added = sorted(set(after) - set(before))
        expected = {Path("records") / f"{CID}.json", Path("sources") / CID}
        unexpected = [p for p in added if p not in expected and Path("sources") / CID not in p.parents]
        self.assertEqual(unexpected, [])
        self.assertEqual(sorted(p.name for p in (self.snap.sources / CID).iterdir()),
                         ["SOURCE.txt", "docs-llms-full.txt", "src.tar.gz.00", "src.tar.gz.01"])
        self.assertEqual(list(self.cwd.iterdir()), [])


class CommandLine(unittest.TestCase):
    """The script as a process: argparse usage and exit codes."""

    def run_cli(self, *args, cwd):
        if not SCRIPT.exists():
            self.fail(f"{SCRIPT.relative_to(STUDY)} does not exist")
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], cwd=cwd,
                              capture_output=True, text=True, timeout=60)

    def test_help_lists_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = self.run_cli("--help", cwd=tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        for option in ("--records", "--sources", "CONFIG_ID"):
            self.assertIn(option, done.stdout)

    def test_config_id_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = self.run_cli("--records", tmp, "--sources", tmp, cwd=tmp)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap = Snapshot(tmp)
            snap.add(CID, [{"evidence_kind": "source_path", "source_url": blob("README.md")}])
            bad = "Z93__synthetic-cover__bad"
            snap.add(bad, [{"evidence_kind": "source_path", "source_url": blob("README.md", sha=OTHER)}])
            common = ["--records", str(snap.records), "--sources", str(snap.sources)]
            good_run = self.run_cli(*common, CID, cwd=tmp)
            bad_run = self.run_cli(*common, CID, bad, cwd=tmp)
        self.assertEqual(good_run.returncode, 0, good_run.stdout + good_run.stderr)
        self.assertEqual(bad_run.returncode, 1, bad_run.stdout + bad_run.stderr)
        self.assertEqual(parse(bad_run.stdout, bad)[0], (1, 0, 1, 0))


if __name__ == "__main__":
    unittest.main()
