"""Tests for source-record verification and editorial baseline reading, on synthetic data (no local source cache needed)."""
import hashlib, pathlib, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import editorial
import source_records

KEY = 'demo-repo'
REPOSITORY = 'demo-org/demo-repo'
SHA = 'a' * 40
OTHER_SHA = 'b' * 40
PATH = 'README.md'
CONTENT = b'demo source file\n'


def make_record(key, path, sha, repository, content):
    """Build a manifest row consistent with the snapshot, then corrupt fields per test."""
    return {
        'key': key,
        'repository': repository,
        'commit': sha,
        'path': path,
        'url': f'https://github.com/{repository}/blob/{sha}/{path}',
        'bytes': len(content),
        'sha256': hashlib.sha256(content).hexdigest(),
    }


class VerifySource(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.research = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def repos(self):
        return {KEY: {'id': KEY, 'repository': REPOSITORY, 'sha': SHA}}

    def write_cache(self, content, key=KEY, path=PATH):
        d = self.research / 'repos' / key / 'files'
        d.mkdir(parents=True)
        (d / path).write_bytes(content)

    def verify(self, key, path, require_cache, records, repos=None):
        with mock.patch.object(source_records, 'REPOSITORIES', repos if repos is not None else self.repos()), \
                mock.patch.object(source_records, 'SOURCE_RECORDS', records), \
                mock.patch.object(source_records, 'RESEARCH', self.research):
            return source_records.verify_source(key, path, require_cache=require_cache)

    def test_all_correct_returns_true(self):
        self.write_cache(CONTENT)
        records = {(KEY, PATH): make_record(KEY, PATH, SHA, REPOSITORY, CONTENT)}
        self.assertTrue(self.verify(KEY, PATH, False, records))
        self.assertTrue(self.verify(KEY, PATH, True, records))

    def test_unregistered_source_raises(self):
        self.write_cache(CONTENT)
        records = {(KEY, 'other-file.md'): make_record(KEY, 'other-file.md', SHA, REPOSITORY, CONTENT)}
        with self.assertRaises(ValueError) as ctx:
            self.verify(KEY, PATH, False, records)
        message = str(ctx.exception)
        self.assertIn('Unregistered source', message)
        self.assertIn(f'{KEY}/{PATH}', message)

    def test_commit_mismatch_raises(self):
        self.write_cache(CONTENT)
        record = make_record(KEY, PATH, SHA, REPOSITORY, CONTENT)
        record['commit'] = 'c' * 40
        with self.assertRaises(ValueError) as ctx:
            self.verify(KEY, PATH, False, {(KEY, PATH): record})
        self.assertIn('does not match repository snapshot', str(ctx.exception))

    def test_repository_mismatch_raises(self):
        self.write_cache(CONTENT)
        record = make_record(KEY, PATH, SHA, REPOSITORY, CONTENT)
        record['repository'] = 'other-org/demo-repo'
        with self.assertRaises(ValueError) as ctx:
            self.verify(KEY, PATH, False, {(KEY, PATH): record})
        self.assertIn('does not match repository snapshot', str(ctx.exception))

    def test_url_mismatch_raises(self):
        self.write_cache(CONTENT)
        record = make_record(KEY, PATH, SHA, REPOSITORY, CONTENT)
        record['url'] = record['url'].replace(SHA, OTHER_SHA)
        with self.assertRaises(ValueError) as ctx:
            self.verify(KEY, PATH, False, {(KEY, PATH): record})
        self.assertIn('does not match repository snapshot', str(ctx.exception))

    def test_missing_cache_returns_false_when_not_required(self):
        records = {(KEY, PATH): make_record(KEY, PATH, SHA, REPOSITORY, CONTENT)}
        self.assertFalse(self.verify(KEY, PATH, False, records))

    def test_missing_cache_raises_when_required(self):
        records = {(KEY, PATH): make_record(KEY, PATH, SHA, REPOSITORY, CONTENT)}
        with self.assertRaises(ValueError) as ctx:
            self.verify(KEY, PATH, True, records)
        self.assertIn('Missing local source cache', str(ctx.exception))

    def test_byte_count_mismatch_raises(self):
        self.write_cache(CONTENT)
        record = make_record(KEY, PATH, SHA, REPOSITORY, CONTENT)
        record['bytes'] = len(CONTENT) - 1  # sha256 仍正确，仅长度不符
        with self.assertRaises(ValueError) as ctx:
            self.verify(KEY, PATH, False, {(KEY, PATH): record})
        self.assertIn('Local source hash mismatch', str(ctx.exception))

    def test_sha256_mismatch_raises(self):
        self.write_cache(CONTENT)
        record = make_record(KEY, PATH, SHA, REPOSITORY, CONTENT)
        record['sha256'] = hashlib.sha256(b'x' + CONTENT[1:]).hexdigest()  # 同长度、不同内容
        with self.assertRaises(ValueError) as ctx:
            self.verify(KEY, PATH, False, {(KEY, PATH): record})
        self.assertIn('Local source hash mismatch', str(ctx.exception))


class ReadBaseline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / '03A-demo.md'

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, text, revisions):
        self.path.write_text(text, encoding='utf-8')
        with mock.patch.object(editorial, 'REVISIONS', revisions):
            return editorial.read_baseline(self.path)

    def test_replacement_applies(self):
        revisions = {self.path.name: [{'before': '旧措辞', 'after': '新措辞'}]}
        self.assertEqual(self.read('开头旧措辞结尾', revisions), '开头新措辞结尾')

    def test_multiple_edits_apply_in_list_order(self):
        # 第二条修订改写第一条的产物，只有按列表顺序逐条替换才能成立。
        revisions = {self.path.name: [
            {'before': '第一句', 'after': '改写甲'},
            {'before': '改写甲', 'after': '最终措辞'},
        ]}
        self.assertEqual(self.read('第一句。其余内容。', revisions), '最终措辞。其余内容。')

    def test_no_revisions_for_name_returns_text_unchanged(self):
        revisions = {'another-file.md': [{'before': '甲', 'after': '乙'}]}
        self.assertEqual(self.read('有甲保持不变', revisions), '有甲保持不变')

    def test_stale_before_raises(self):
        revisions = {self.path.name: [{'before': '不存在的句子', 'after': '新措辞'}]}
        with self.assertRaises(ValueError) as ctx:
            self.read('现有内容。', revisions)
        message = str(ctx.exception)
        self.assertIn('Stale editorial revision', message)
        self.assertIn(self.path.name, message)


if __name__ == '__main__':
    unittest.main()
