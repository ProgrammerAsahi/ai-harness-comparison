"""Tests for the citation resolver, run on synthetic data in temporary directories (never the real report files)."""
import json, pathlib, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render_references as rr

REPOS = {'synth-repo': {'id': 'synth-repo', 'repository': 'octo/widget', 'sha': 'a' * 40},
         'other-repo': {'id': 'other-repo', 'repository': 'octo/other', 'sha': 'b' * 40}}
REFS = {'synth-doc': 'https://docs.example.com/synth',
        'synth-doc-2': 'https://docs.example.com/synth-2',
        'synth-doc-3': 'https://docs.example.com/synth-3'}
PIN_A = 'a' * 40
PIN_B = 'b' * 40


class RenderReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pages = pathlib.Path(cls.tmp.name) / 'pages'
        cls.pages.mkdir()
        (cls.pages / 'synth-doc.json').write_text(json.dumps({'final_url': 'https://final.example.com/synth'}))
        (cls.pages / 'synth-doc-3.json').write_text(json.dumps({'title': 'no final_url field'}))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_doc_uses_page_metadata_final_url_when_present(self):
        with mock.patch.object(rr, 'PAGES_DIR', self.pages):
            citations = []
            url = rr.resolve_placeholder('doc:synth-doc', REFS, REPOS, citations)
        self.assertEqual(url, 'https://final.example.com/synth')
        self.assertEqual(citations, [{'kind': 'official-document', 'key': 'synth-doc', 'path': '', 'url': url}])

    def test_doc_falls_back_to_registry_without_page_metadata(self):
        with mock.patch.object(rr, 'PAGES_DIR', self.pages):
            citations = []
            url = rr.resolve_placeholder('doc:synth-doc-2', REFS, REPOS, citations)
        self.assertEqual(url, REFS['synth-doc-2'])
        self.assertEqual(citations, [{'kind': 'official-document', 'key': 'synth-doc-2', 'path': '', 'url': url}])

    def test_doc_page_metadata_without_final_url_falls_back_to_registry(self):
        with mock.patch.object(rr, 'PAGES_DIR', self.pages):
            url = rr.resolve_placeholder('doc:synth-doc-3', REFS, REPOS, [])
        self.assertEqual(url, REFS['synth-doc-3'])

    def test_repo_generates_repository_homepage(self):
        citations = []
        url = rr.resolve_placeholder('repo:synth-repo', REFS, REPOS, citations)
        self.assertEqual(url, 'https://github.com/octo/widget')
        self.assertEqual(citations, [{'kind': 'repository', 'key': 'synth-repo', 'path': '', 'url': url}])

    def test_src_generates_pinned_blob_link_and_calls_verify_source(self):
        citations = []
        with mock.patch.object(rr, 'verify_source', return_value=True) as verify:
            url = rr.resolve_placeholder('src:synth-repo:README.md', REFS, REPOS, citations)
        self.assertEqual(url, 'https://github.com/octo/widget/blob/' + PIN_A + '/README.md')
        verify.assert_called_once_with('synth-repo', 'README.md')
        self.assertEqual(citations, [{'kind': 'pinned-source', 'key': 'synth-repo', 'path': 'README.md', 'url': url}])

    def test_resolve_placeholders_replaces_every_token_in_one_document(self):
        with mock.patch.object(rr, 'PAGES_DIR', self.pages), \
                mock.patch.object(rr, 'verify_source', return_value=True):
            citations = []
            text = rr.resolve_placeholders(
                'a {{doc:synth-doc}} b {{repo:synth-repo}} c {{src:synth-repo:src/app.py}}', REFS, REPOS, citations)
        self.assertEqual(text, 'a https://final.example.com/synth b https://github.com/octo/widget '
                                'c https://github.com/octo/widget/blob/' + PIN_A + '/src/app.py')
        self.assertEqual(len(citations), 3)

    def test_collect_inline_sources_records_pinned_links_and_verifies(self):
        url = 'https://github.com/octo/other/blob/' + PIN_B + '/docs/notes.md'
        citations = []
        with mock.patch.object(rr, 'verify_source', return_value=True) as verify:
            found = rr.collect_inline_sources('inline [pin](' + url + ') here', REPOS, citations)
        self.assertEqual(found, [{'kind': 'pinned-source', 'key': 'other-repo', 'path': 'docs/notes.md', 'url': url}])
        self.assertEqual(citations, found)
        verify.assert_called_once_with('other-repo', 'docs/notes.md')

    def test_collect_inline_sources_rejects_unpinned_repository(self):
        url = 'https://github.com/nobody/unknown/blob/' + 'c' * 40 + '/README.md'
        with mock.patch.object(rr, 'verify_source') as verify:
            with self.assertRaises(ValueError):
                rr.collect_inline_sources('[' + url + '](x)', REPOS, [])
        verify.assert_not_called()

    def test_collect_inline_sources_rejects_mismatched_sha(self):
        url = 'https://github.com/octo/widget/blob/' + 'c' * 40 + '/README.md'
        with mock.patch.object(rr, 'verify_source') as verify:
            with self.assertRaises(ValueError):
                rr.collect_inline_sources('[' + url + '](x)', REPOS, [])
        verify.assert_not_called()

    def test_dedupe_keeps_one_record_per_kind_and_url(self):
        a = {'kind': 'pinned-source', 'key': 'synth-repo', 'path': 'README.md', 'url': 'https://example.com/a'}
        b = {'kind': 'official-document', 'key': 'synth-doc', 'path': '', 'url': 'https://example.com/a'}
        dup = {'kind': 'pinned-source', 'key': 'synth-repo', 'path': 'README.md', 'url': 'https://example.com/a'}
        out = rr.dedupe_citations([a, b, dup])
        self.assertEqual(out, [a, b])
        self.assertEqual(rr.dedupe_citations([]), [])

    def test_main_resolves_placeholders_and_refreshes_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'research' / 'pages').mkdir(parents=True)
            (root / 'report').mkdir()
            (root / 'research' / 'pages-seed.json').write_text(json.dumps({'synth-doc': REFS['synth-doc']}))
            (root / 'research' / 'pages' / 'synth-doc.json').write_text(
                json.dumps({'final_url': 'https://final.example.com/synth'}))
            inline = 'https://github.com/octo/widget/blob/' + PIN_A + '/docs/notes.md'
            # src tokens resolve to bare GitHub URLs; the inline scan re-reads them, so the
            # token sits inside a markdown link and the resolved URL stays paren-terminated.
            body = ('# 示例\n\n依据 {{doc:synth-doc}} 与 {{repo:synth-repo}}，'
                    '源码见 [README.md]({{src:synth-repo:README.md}})。\n\n'
                    '内联[固定链接](' + inline + ')再次出现（[同上](' + inline + ')）。\n')
            (root / 'report' / 'demo.md').write_text(body)
            with mock.patch.object(rr, 'ROOT', root), \
                    mock.patch.object(rr, 'R', root / 'research'), \
                    mock.patch.object(rr, 'PAGES_DIR', root / 'research' / 'pages'), \
                    mock.patch.object(rr, 'REPOSITORIES', REPOS), \
                    mock.patch.object(rr, 'verify_source', return_value=True) as verify:
                rr.main()
                text = (root / 'report' / 'demo.md').read_text()
                self.assertNotIn('{{', text)
                self.assertIn('https://final.example.com/synth', text)
                self.assertIn('https://github.com/octo/widget', text)
                citations = json.loads((root / 'research' / 'citations.json').read_text())
                self.assertEqual(citations, [
                    {'kind': 'official-document', 'key': 'synth-doc', 'path': '',
                     'url': 'https://final.example.com/synth'},
                    {'kind': 'repository', 'key': 'synth-repo', 'path': '',
                     'url': 'https://github.com/octo/widget'},
                    {'kind': 'pinned-source', 'key': 'synth-repo', 'path': 'README.md',
                     'url': 'https://github.com/octo/widget/blob/' + PIN_A + '/README.md'},
                    {'kind': 'pinned-source', 'key': 'synth-repo', 'path': 'docs/notes.md', 'url': inline},
                ])
                # verify_source: once for the src placeholder, once per inline URL (3, incl. the duplicate).
                self.assertEqual(len(verify.call_args_list), 4)
                rows = (root / 'research' / 'citations.csv').read_text().splitlines()
                self.assertEqual(rows[0], 'kind,key,path,url')
                self.assertEqual(len(rows), 5)
                # A second run over already-resolved text keeps the same deduplicated records.
                rr.main()
                self.assertEqual(json.loads((root / 'research' / 'citations.json').read_text()), citations)


if __name__ == '__main__':
    unittest.main()
