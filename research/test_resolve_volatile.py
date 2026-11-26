"""Tests for resolve_volatile.py: volatile placeholders in report Markdown.

{{m:role}}, {{date:facts}}, {{table:name}} and {{bench:campaign.table}} are resolved against
research/volatile-facts.json. FACTS is patched with synthetic data here, so nothing depends
on the real volatile-facts.json content (it changes on every fact refresh).
"""
import pathlib, sys, unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import resolve_volatile as rv


def facts_with(tables, checked_at='2026-01-01', models=None):
    return {'checked_at': checked_at, 'models': models or {}, 'tables': tables}


class CellTests(unittest.TestCase):
    def test_pipe_becomes_fullwidth(self):
        self.assertEqual(rv.cell('a|b'), 'a／b')

    def test_newline_becomes_space(self):
        self.assertEqual(rv.cell('a\nb'), 'a b')

    def test_non_string_values_are_stringified(self):
        self.assertEqual(rv.cell(123), '123')
        self.assertEqual(rv.cell(None), 'None')

    def test_multiple_replacements_in_one_cell(self):
        self.assertEqual(rv.cell('a|b\nc'), 'a／b c')


class TableTests(unittest.TestCase):
    def run_table(self, spec, name='t', checked_at='2026-01-01'):
        with mock.patch.object(rv, 'FACTS', facts_with({name: spec}, checked_at=checked_at)):
            return rv.table(name)

    def test_header_default_alignment_and_rows(self):
        spec = {'columns': ['项目', '状态'], 'rows': [['Alpha', '维护中'], ['Beta', '已归档']]}
        self.assertEqual(self.run_table(spec), '| 项目 | 状态 |\n|---|---|\n| Alpha | 维护中 |\n| Beta | 已归档 |')

    def test_explicit_alignment(self):
        spec = {'columns': ['名称', '价格'], 'align': ['---', '---:'], 'rows': [['X', '¥1']]}
        self.assertEqual(self.run_table(spec), '| 名称 | 价格 |\n|---|---:|\n| X | ¥1 |')

    def test_rows_go_through_cell(self):
        spec = {'columns': ['甲', '乙'], 'rows': [['a|b', 'c\nd'], [7, None]]}
        self.assertEqual(self.run_table(spec), '| 甲 | 乙 |\n|---|---|\n| a／b | c d |\n| 7 | None |')

    def test_note_placeholder_uses_global_checked_at(self):
        spec = {'columns': ['甲'], 'rows': [['x']], 'note': '截至 {{date:facts}} 的官方目录'}
        self.assertEqual(self.run_table(spec), '*核实日期：2026-01-01。截至 2026-01-01 的官方目录*\n\n| 甲 |\n|---|\n| x |')

    def test_table_checked_at_overrides_global(self):
        spec = {'columns': ['甲'], 'rows': [['x']], 'note': '注', 'checked_at': '2026-02-02'}
        self.assertEqual(self.run_table(spec), '*核实日期：2026-02-02。注*\n\n| 甲 |\n|---|\n| x |')

    def test_no_note_no_checked_at_no_caption(self):
        spec = {'columns': ['甲'], 'rows': [['x']]}
        self.assertNotIn('核实日期', self.run_table(spec))

    def test_checked_at_without_note_still_shows_caption(self):
        # note empty: the format's period simply closes the line, e.g. *核实日期：2026-02-02。*
        spec = {'columns': ['甲'], 'rows': [['x']], 'checked_at': '2026-02-02'}
        self.assertEqual(self.run_table(spec), '*核实日期：2026-02-02。*\n\n| 甲 |\n|---|\n| x |')

    def test_sources_line_and_its_omission(self):
        spec = {'columns': ['甲'], 'rows': [['x']], 'sources': [['文档A', 'https://a.example/doc'], ['文档B', 'https://b.example/doc']]}
        self.assertEqual(self.run_table(spec), '| 甲 |\n|---|\n| x |\n\n来源：[文档A](https://a.example/doc)、[文档B](https://b.example/doc)。')
        self.assertNotIn('来源', self.run_table({'columns': ['甲'], 'rows': [['x']], 'sources': []}))
        self.assertNotIn('来源', self.run_table({'columns': ['甲'], 'rows': [['x']]}))

    def test_full_table(self):
        spec = {'note': '截至 {{date:facts}} 的目录', 'checked_at': '2026-02-02',
                'columns': ['名称', '价格'], 'align': ['---', '---:'],
                'rows': [['X', '¥1']], 'sources': [['来源A', 'https://a.example/']]}
        self.assertEqual(self.run_table(spec),
                         '*核实日期：2026-02-02。截至 2026-01-01 的目录*\n\n'
                         '| 名称 | 价格 |\n|---|---:|\n| X | ¥1 |\n\n'
                         '来源：[来源A](https://a.example/)。')


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.facts = {
            'checked_at': '2026-01-01',
            'models': {'daily': 'Daily-9', 'flagship': 'Flag-9'},
            'tables': {'plain': {'columns': ['甲'], 'rows': [['x']]}},
        }
        self.patcher = mock.patch.object(rv, 'FACTS', self.facts)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_model_placeholder(self):
        self.assertEqual(rv.resolve('前 {{m:daily}} 后', 'w.md'), '前 Daily-9 后')

    def test_date_placeholder(self):
        self.assertEqual(rv.resolve('核实于 {{date:facts}}', 'w.md'), '核实于 2026-01-01')

    def test_table_placeholder(self):
        self.assertEqual(rv.resolve('{{table:plain}}', 'w.md'), '| 甲 |\n|---|\n| x |')

    def test_mixed_placeholders(self):
        self.assertEqual(rv.resolve('{{m:daily}}，{{date:facts}}，{{table:plain}}', 'w.md'),
                         'Daily-9，2026-01-01，| 甲 |\n|---|\n| x |')

    def test_unknown_model_role_exits_with_where(self):
        with self.assertRaises(SystemExit) as cm:
            rv.resolve('{{m:nope}}', 'w.md')
        self.assertEqual(str(cm.exception), 'w.md: unknown model role nope')

    def test_unknown_date_key_exits_with_where(self):
        with self.assertRaises(SystemExit) as cm:
            rv.resolve('{{date:other}}', 'w.md')
        self.assertEqual(str(cm.exception), 'w.md: unknown date other')

    def test_unknown_table_exits_with_where(self):
        with self.assertRaises(SystemExit) as cm:
            rv.resolve('{{table:nope}}', 'w.md')
        self.assertEqual(str(cm.exception), 'w.md: unknown table nope')

    def test_unrecognized_placeholder_kind_is_kept(self):
        self.assertEqual(rv.resolve('保留 {{x:y}} 原样', 'w.md'), '保留 {{x:y}} 原样')

    def test_bench_splits_campaign_and_table_at_last_dot(self):
        with mock.patch.object(rv.private_bench, 'render', return_value='BENCH') as fake:
            self.assertEqual(rv.resolve('{{bench:2026-10.model.totals}}', 'w.md'), 'BENCH')
            fake.assert_called_once_with('2026-10.model', 'totals')

    def test_bench_two_part_key(self):
        with mock.patch.object(rv.private_bench, 'render', return_value='BENCH') as fake:
            self.assertEqual(rv.resolve('{{bench:2026-10.totals}}', 'w.md'), 'BENCH')
            fake.assert_called_once_with('2026-10', 'totals')


if __name__ == '__main__':
    unittest.main()
