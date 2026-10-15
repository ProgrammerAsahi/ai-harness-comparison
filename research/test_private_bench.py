"""Tests for the private-bench aggregate pipeline, run on a synthetic ledger (no measured data)."""
import copy, json, pathlib, sys, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import private_bench as pb

GROUPS = {'groups': [{'label': 'JavaScript／TypeScript 应用', 'prefixes': ['secret-alpha']},
                     {'label': 'Python 数据与文档校验项目', 'prefixes': ['secret-beta', 'secret-delta']},
                     {'label': 'Python 后端与 iOS 应用', 'prefixes': ['secret-gamma']}]}


class PrivateBench(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = pathlib.Path(cls.tmp.name)
        cls.ledger = d / 'ledger.db'
        pb.synthetic_ledger(cls.ledger)
        cls.groups = d / 'groups.json'
        cls.groups.write_text(json.dumps(GROUPS, ensure_ascii=False))
        cls.data = pb.export(cls.ledger, 'synthetic-example', cls.groups, synthetic=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def config(self, data, cid):
        return next(c for c in data['configs'] if c['id'] == cid)

    def test_export_keeps_task_identities_private(self):
        text = json.dumps(self.data, ensure_ascii=False)
        self.assertNotIn('secret', text)
        self.assertNotIn('run-', text)
        self.assertEqual(pb.validate(self.data), [])

    def test_small_categories_merge_and_partial_configs_withhold_their_split(self):
        self.assertEqual(self.data['category_buckets'], [['修复缺陷'], ['新增功能', '更新文档']])
        self.assertIsNone(self.config(self.data, 'gpt-6-luna')['by_category'])
        cells = self.config(self.data, 'astra')['by_category']
        self.assertTrue(all(pb._passes(c, self.data['min_cell']) for c in cells))

    def test_small_configs_are_named_without_results(self):
        mimo = self.config(self.data, 'mimo-flash-free')
        self.assertEqual(mimo['status'], 'insufficient')
        self.assertFalse({'total', 'by_category', 'api_usd_mean'} & set(mimo))

    def test_project_types_are_counts_only(self):
        self.assertEqual(sum(self.data['scope']['tasks_by_project_type'].values()), self.data['scope']['tasks'])
        self.assertFalse(any('project' in k for c in self.data['configs'] for k in c))

    def test_merge_rule(self):
        m = {'tasks': 5, 'judged': 15}
        self.assertEqual(pb.merge_categories({'a': 12, 'b': 9, 'c': 1}, m), [('a',), ('b', 'c')])
        self.assertIsNone(pb.merge_categories({'a': 12, 'b': 3, 'c': 1}, m))
        self.assertIsNone(pb.merge_categories({'a': 20}, m))

    def test_validation_rejects_leaky_or_inconsistent_files(self):
        def broken(change):
            d = copy.deepcopy(self.data)
            change(d)
            return pb.validate(d)
        astra = lambda d: self.config(d, 'astra')
        self.assertTrue(broken(lambda d: astra(d)['by_category'][1].update(tasks=2)))
        self.assertTrue(broken(lambda d: astra(d)['total'].update(success=astra(d)['total']['success'] + 1)))
        self.assertTrue(broken(lambda d: astra(d).update(task_ids=['x'])))
        self.assertTrue(broken(lambda d: self.config(d, 'mimo-flash-free').update(total={'tasks': 2, 'judged': 6, 'success': 3})))
        self.assertTrue(broken(lambda d: astra(d).update(model='Other')))
        self.assertTrue(broken(lambda d: d['configs'].reverse()))
        self.assertTrue(broken(lambda d: d['min_cell'].update(tasks=1)))
        self.assertTrue(broken(lambda d: d['scope']['tasks_by_project_type'].update({'某私有仓库': 1})))

    def test_export_refuses_unknown_inputs(self):
        bad = pathlib.Path(self.tmp.name) / 'bad-groups.json'
        bad.write_text(json.dumps({'groups': GROUPS['groups'][:2]}, ensure_ascii=False))
        with self.assertRaises(SystemExit):
            pb.export(self.ledger, 'synthetic-example', bad, synthetic=True)
        bad.write_text(json.dumps({'groups': [{'label': '私有仓库名', 'prefixes': ['secret']}]}, ensure_ascii=False))
        with self.assertRaises(SystemExit):
            pb.export(self.ledger, 'synthetic-example', bad, synthetic=True)
        with self.assertRaises(SystemExit):
            pb.export(self.ledger, 'no-such-campaign')

    def test_render_refuses_synthetic_data_in_the_report(self):
        with self.assertRaises(SystemExit):
            pb.render('synthetic-example', 'totals', self.data)
        totals = pb.render('synthetic-example', 'totals', self.data, allow_synthetic=True)
        rows = [l for l in totals.splitlines() if l.startswith('| [')]
        self.assertEqual([r.split('＋')[1].split(' |')[0] for r in rows], ['GPT-6 Astra', 'GPT-6 Luna', 'Claude Opus 5.5'])
        self.assertIn('样本不足', totals)
        self.assertIn('不拆分', pb.render('synthetic-example', 'by-category', self.data, allow_synthetic=True))
        self.assertIn('不是现金', pb.render('synthetic-example', 'resources', self.data, allow_synthetic=True))

    def test_committed_aggregates_validate(self):
        files = sorted(f for f in pb.DATA.glob('*.json') if f.name != 'configs.json')
        self.assertEqual(pb.check(files), [])


if __name__ == '__main__':
    unittest.main()
