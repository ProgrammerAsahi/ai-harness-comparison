"""MIT. Offline regression tests for pilot/fetch_sources.py.

Covers the HTML-to-text reduction (article_text), the docs lookups (docs_url, doc_pages), the
commit placement of a config record (pinned, on synthetic records in a temporary directory) and
the joined docs-pages.txt (fetch_pages, with get() replaced so nothing touches the network).
Nothing reads tmp/ or the real config records.

  python3 -m unittest studies/harness-quantification/test_fetch_sources.py -v
"""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDY = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fetch_sources_under_test", STUDY / "pilot/fetch_sources.py")
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)

PRIMARY = "f" * 39 + "1"  # sorts after SECONDARY: order must come from the record, not from sorting
SECONDARY = "a" * 39 + "2"
THIRD = "c" * 39 + "3"


class ArticleText(unittest.TestCase):
    def test_only_article_text_is_kept(self):
        page = ("<html><head><title>T</title><style>p{color:red}</style></head><body>"
                "<header>Site header</header><article><p>Inside one.</p></article>"
                "<footer>Site footer</footer></body></html>")
        self.assertEqual(fs.article_text(page), "Inside one.")

    def test_non_content_tags_are_dropped(self):
        page = ("<article><nav><a>Home</a> <a>Docs</a></nav><p>Body text.</p>"
                "<script>var x = 1;</script><style>.a{}</style><svg><text>icon</text></svg>"
                "<button>Copy</button><p>After.</p></article>")
        text = fs.article_text(page)
        self.assertEqual(text, "Body text.\nAfter.")
        for gone in ("Home", "Docs", "var x", ".a{}", "icon", "Copy"):
            self.assertNotIn(gone, text)

    def test_nested_skip_tags_resume_after_close(self):
        page = "<article><nav><svg>a</svg>still nav</nav><p>Kept.</p></article>"
        self.assertEqual(fs.article_text(page), "Kept.")

    def test_headings_lists_and_cells_are_marked(self):
        page = ("<article><h1>Title</h1><p>Intro   text\n here.</p><h3>Sub</h3>"
                "<ul><li>one</li><li>two</li></ul>"
                "<table><tr><th>K</th><th>V</th></tr><tr><td>a</td><td>b</td></tr></table></article>")
        self.assertEqual(fs.article_text(page),
                         "# Title\nIntro text here.\n\n### Sub\n- one\n- two\n | K | V\n | a | b")

    def test_paragraph_breaks_and_blank_line_collapse(self):
        page = "<article><p>One.</p><p>Two.</p><div><div><div><p>Three.</p></div></div></div><br>Four.</article>"
        text = fs.article_text(page)
        self.assertEqual(text, "One.\nTwo.\n\nThree.\nFour.")
        self.assertNotIn("\n\n\n", text)

    def test_pre_keeps_whitespace(self):
        page = "<article><p>See:</p><pre>a  =  1\n  b = 2</pre><p>x   y</p></article>"
        self.assertEqual(fs.article_text(page), "See:\n```\na  =  1\n  b = 2\n```\n\nx y")

    def test_page_without_article_is_empty(self):
        self.assertEqual(fs.article_text("<html><body><div id=root></div><script>render()</script></body></html>"),
                         "")
        self.assertEqual(fs.article_text("<html><body><p>Not in an article.</p></body></html>"), "")


class DocsLookups(unittest.TestCase):
    def test_docs_url_by_prefix(self):
        self.assertEqual(fs.docs_url("A01__claude-code"), "https://code.claude.com/docs/llms-full.txt")
        self.assertEqual(fs.docs_url("A01__claude-code__anthropic-default"), "https://code.claude.com/docs/llms-full.txt")
        self.assertEqual(fs.docs_url("D02__n8n__self-hosted"), "https://docs.n8n.io/llms-full.txt")

    def test_docs_url_unknown_is_none(self):
        self.assertIsNone(fs.docs_url("Z99__unknown"))
        self.assertIsNone(fs.docs_url("B01__cursor"))
        self.assertIsNone(fs.docs_url("x-A01__claude-code"))

    def test_doc_pages_structure(self):
        pages = fs.doc_pages("B02__github-copilot__default")
        self.assertIs(pages, fs.DOC_PAGES["B02__github-copilot"])
        self.assertEqual(len(pages), 2)
        for entry in pages:
            self.assertEqual(len(entry), 4)
        self.assertEqual(pages[0][0], "https://code.visualstudio.com/llms.txt")
        self.assertEqual(pages[1][2], "https://docs.github.com/api/article/body?pathname={}")
        self.assertEqual(pages[1][3], "https://docs.github.com{}")
        amp = fs.doc_pages("B09__amp")
        self.assertEqual(amp, [("https://ampcode.com/llms.txt",
                                r"(?<=https://ampcode\.com/docs/markdown)(?:/[\w-]+)*(?![\w/-])",
                                "https://ampcode.com/docs/markdown{}", "https://ampcode.com/docs{}")])

    def test_doc_pages_unknown_is_none(self):
        self.assertIsNone(fs.doc_pages("Z99__unknown"))
        self.assertIsNone(fs.doc_pages("A01__claude-code"))

    def test_kiro_pattern_leaves_out_other_surfaces(self):
        _, pattern, _, _ = fs.doc_pages("B04__kiro")[0]
        self.assertTrue(fs.re.fullmatch(pattern, "https://kiro.dev/docs/specs/index.md"))
        self.assertIsNone(fs.re.fullmatch(pattern, "https://kiro.dev/docs/crew/setup.md"))
        self.assertIsNone(fs.re.fullmatch(pattern, "https://kiro.dev/docs/enterprise.md"))


class Pinned(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.configs = Path(tmp.name) / "configs"
        self.configs.mkdir()
        patcher = patch.object(fs, "CONFIGS", self.configs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, config_id, version, urls=()):
        record = {"config_id": config_id, "version_or_commit": version,
                  "evidence": [{"kind": "source", "url": u} for u in urls]}
        (self.configs / f"{config_id}.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    def test_single_commit_from_evidence_url(self):
        self.write("Z90__synthetic", f"v1.0 提交 {PRIMARY}",
                   [f"https://github.com/acme/tool/blob/{PRIMARY}/README.md"])
        self.assertEqual(fs.pinned("Z90__synthetic"), ([("acme/tool", PRIMARY)], []))

    def test_primary_first_even_when_it_sorts_last(self):
        self.write("Z90__synthetic", f"主仓库提交 {PRIMARY}；插件仓库提交 {SECONDARY}；再次 {PRIMARY}",
                   [f"https://github.com/acme/plugin/blob/{SECONDARY}/a.py",
                    f"https://github.com/acme/core/blob/{PRIMARY}/b.py"])
        self.assertEqual(fs.pinned("Z90__synthetic"),
                         ([("acme/core", PRIMARY), ("acme/plugin", SECONDARY)], []))

    def test_three_commits_keep_record_order(self):
        self.write("Z90__synthetic", f"{PRIMARY}，{THIRD}，{SECONDARY}",
                   [f"https://github.com/o/a/blob/{SECONDARY}/x", f"https://github.com/o/c/blob/{THIRD}/x",
                    f"https://github.com/o/f/blob/{PRIMARY}/x"])
        found, unplaced = fs.pinned("Z90__synthetic")
        self.assertEqual([sha for _, sha in found], [PRIMARY, THIRD, SECONDARY])
        self.assertEqual(unplaced, [])

    def test_unplaced_secondary_that_sorts_first_does_not_stop(self):
        self.write("Z90__synthetic", f"提交 {PRIMARY}；tag 对象 {SECONDARY}",
                   [f"https://github.com/acme/core/blob/{PRIMARY}/b.py"])
        self.assertEqual(fs.pinned("Z90__synthetic"), ([("acme/core", PRIMARY)], [SECONDARY]))

    def test_secondary_placed_by_owner_repo_in_version(self):
        self.write("Z90__synthetic", f"acme/core 提交 {PRIMARY}；acme/extra 提交 {SECONDARY}",
                   [f"https://github.com/acme/core/blob/{PRIMARY}/b.py"])
        self.assertEqual(fs.pinned("Z90__synthetic"),
                         ([("acme/core", PRIMARY), ("acme/extra", SECONDARY)], []))

    def test_unplaced_primary_stops(self):
        self.write("Z90__synthetic", f"提交 {PRIMARY}；{SECONDARY}",
                   [f"https://github.com/acme/plugin/blob/{SECONDARY}/a.py"])
        with self.assertRaises(SystemExit) as caught:
            fs.pinned("Z90__synthetic")
        self.assertIn(PRIMARY, str(caught.exception))

    def test_no_commit_with_docs_is_empty(self):
        self.write("A01__claude-code__synthetic", "2.1.0 (npm)")
        self.assertEqual(fs.pinned("A01__claude-code__synthetic"), ([], []))
        self.write("B02__github-copilot__synthetic", "1.100")
        self.assertEqual(fs.pinned("B02__github-copilot__synthetic"), ([], []))

    def test_no_commit_without_docs_stops(self):
        self.write("Z90__synthetic", "1.0.0")
        with self.assertRaises(SystemExit):
            fs.pinned("Z90__synthetic")

    def test_closed_source_ignores_its_hex_id(self):
        self.write("B01__cursor__synthetic", f"build {PRIMARY}",
                   [f"https://github.com/acme/installer/blob/{PRIMARY}/x"])
        self.assertEqual(fs.pinned("B01__cursor__synthetic"), ([], []))


class FetchPages(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dest = Path(tmp.name)

    def run_pages(self, config_id, pages, responses):
        def fake_get(url):
            if url not in responses:
                raise AssertionError(f"unexpected fetch {url}")
            value = responses[url]
            if isinstance(value, Exception):
                raise value
            return value.encode("utf-8")

        with patch.dict(fs.DOC_PAGES, {config_id: pages}), patch.object(fs, "get", side_effect=fake_get) as get, \
                patch.object(fs.urllib.request, "urlopen", side_effect=AssertionError("network")), \
                contextlib.redirect_stdout(io.StringIO()):
            fs.fetch_pages(config_id, self.dest)
        return get, (self.dest / "docs-pages.txt").read_text(encoding="utf-8"), \
            (self.dest / "SOURCE.txt").read_text(encoding="utf-8")

    def test_markdown_pages_joined_with_source_lines(self):
        index = "https://ex.test/llms.txt"
        pages = [(index, r"https://ex\.test/docs/[\w-]+\.md", "{}", "{}")]
        responses = {
            index: "- https://ex.test/docs/one.md\n- https://ex.test/docs/two.md\n- https://ex.test/docs/one.md\n",
            "https://ex.test/docs/one.md": "\n# One\nFirst body.\n\n",
            "https://ex.test/docs/two.md": "# Two\nSecond body.",
        }
        get, text, source = self.run_pages("Z91__synthetic", pages, responses)
        self.assertEqual(get.call_count, 3)  # the repeated link is fetched once
        self.assertEqual(text, "Source: https://ex.test/docs/one\n\n# One\nFirst body.\n"
                               "\n\n" + "=" * 80 + "\n"
                               "Source: https://ex.test/docs/two\n\n# Two\nSecond body.\n")
        self.assertIn(f"docs pages: index {index}, pages matching {pages[0][1]}: 2 listed, 2 fetched\n", source)
        self.assertNotIn("served as HTML only", source)
        self.assertIn(f"{len(text.encode('utf-8'))} bytes", source)

    def test_html_pages_reduced_and_failures_noted(self):
        index = "https://ex.test/sitemap.xml"
        pages = [(index, r"(?<=<loc>https://ex\.test/)[\w-]+\.html", "https://ex.test/docs/{}", "https://ex.test/d/{}")]
        responses = {
            index: "<loc>https://ex.test/a.html</loc><loc>https://ex.test/b.html</loc><loc>https://ex.test/c.html</loc>",
            "https://ex.test/docs/a.html": "<!DOCTYPE html><html><body><nav>menu</nav>"
                                           "<article><h2>A</h2><p>Alpha text.</p></article></body></html>",
            "https://ex.test/docs/b.html": "<html><body><div id=app></div></body></html>",
            "https://ex.test/docs/c.html": OSError("gone"),
        }
        _, text, source = self.run_pages("Z92__synthetic", pages, responses)
        self.assertEqual(text, "Source: https://ex.test/d/a.html\n\n## A\nAlpha text.\n")
        self.assertIn("3 listed, 1 fetched, failed: b.html (no text in the served HTML); c.html (OSError)\n", source)
        self.assertIn("served as HTML only", source)

    def test_json_index_and_cite_template(self):
        index = "https://ex.test/pagelist"
        pages = [(index, r"/en/keep(?:/[\w-]+)*", "https://ex.test/body?p={}", "https://ex.test{}")]
        responses = {
            index: json.dumps(["/en/keep/x", "/en/drop/y", "/en/keep/x/more-z"]),
            "https://ex.test/body?p=/en/keep/x": "X body",
            "https://ex.test/body?p=/en/keep/x/more-z": "Z body",
        }
        _, text, _ = self.run_pages("Z93__synthetic", pages, responses)
        sep = "\n\n" + "=" * 80 + "\n"
        self.assertEqual(text.split(sep), ["Source: https://ex.test/en/keep/x\n\nX body\n",
                                           "Source: https://ex.test/en/keep/x/more-z\n\nZ body\n"])

    def test_source_txt_is_appended(self):
        (self.dest / "SOURCE.txt").write_text("config_id: Z94__synthetic\n", encoding="utf-8")
        index = "https://ex.test/llms.txt"
        pages = [(index, r"https://ex\.test/p\.md", "{}", "{}")]
        _, _, source = self.run_pages("Z94__synthetic", pages, {index: "https://ex.test/p.md",
                                                               "https://ex.test/p.md": "P"})
        self.assertTrue(source.startswith("config_id: Z94__synthetic\ndocs pages: "))


if __name__ == "__main__":
    unittest.main()
