"""Tests for profile_models.py: the ROUTES model-route table build_profiles.py renders.

Each tool id maps to three rows (选择路线／候选组合／怎样决定), each row three non-empty
strings; build_profiles.py joins the cells with ' | ' into a Markdown table, so a cell
must never contain '|' or a newline. {{m:key}} placeholders in the cells are resolved
against the 'models' section of research/volatile-facts.json when the report is built.
The checks below are local functions so the same check can be pointed at synthetic
entries; only the relevant keys are asserted, never whole-table comparison.
"""
import json, pathlib, re, sys, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import profile_models
import profile_tiers

RESEARCH = pathlib.Path(__file__).resolve().parent
CATALOG_IDS = frozenset(e['id'] for e in json.loads((RESEARCH / 'catalog.json').read_text()))
MODEL_ROLES = frozenset(json.loads((RESEARCH / 'volatile-facts.json').read_text())['models'])
PLACEHOLDER = re.compile(r'\{\{m:([\w.\-]+)\}\}')

# Known data gaps in the current snapshot, reported instead of fixed (data stays as-is).
# If either list changes, update it here and note the change in the delivery report.
# {{m:role}} cells whose role is not defined in volatile-facts.json models; these rows
# belong to short profiles, whose model tables build_profiles.py does not render, so the
# build still passes:
KNOWN_UNRESOLVED_ROLES = {
    'google.flagship': ('A03', 'B12'),
    'qwen.cloud': ('A04',),
    'mistral.hosted': ('A14',),
    'mistral.self': ('A14',),
    'grok': ('A16',),
    'step.flash': ('A17',),
    'glm': ('B16',),
}
# ROUTES keys with no catalog.json entry: the four 03D maintenance-observation profiles
# (profile_expansions_d.py), which catalog.json intentionally does not list:
KNOWN_EXTRA_KEYS = ('H01', 'H02', 'H03', 'H04')


def model_roles(routes):
    """{role: sorted(profile keys)} for every {{m:role}} placeholder used in the rows."""
    used = {}
    for key, rows in routes.items():
        for row in rows:
            for cell in row:
                for role in PLACEHOLDER.findall(cell):
                    used.setdefault(role, set()).add(key)
    return {r: sorted(ks) for r, ks in used.items()}


def unresolved_roles(routes, known_roles=MODEL_ROLES):
    """{role: sorted(profile keys)} for placeholders missing from the model roles."""
    return {r: ks for r, ks in model_roles(routes).items() if r not in known_roles}


def table_problems(routes):
    """(key, problem) pairs for entries build_profiles.py would render as broken Markdown."""
    problems = []
    for key, rows in routes.items():
        if not isinstance(key, str) or not key.strip():
            problems.append((key, 'key is not a non-empty string'))
            continue
        if not isinstance(rows, (list, tuple)) or len(rows) != 3:
            problems.append((key, 'expected exactly 3 rows'))
            continue
        for i, row in enumerate(rows):
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                problems.append((key, f'row {i + 1} expected exactly 3 cells'))
                continue
            for j, cell in enumerate(row):
                if not isinstance(cell, str) or not cell.strip():
                    problems.append((key, f'row {i + 1} cell {j + 1} is not a non-empty string'))
                elif '|' in cell or '\n' in cell or '\r' in cell:
                    problems.append((key, f'row {i + 1} cell {j + 1} would break the Markdown table'))
    return problems


def extra_route_keys(routes, catalog_ids=CATALOG_IDS):
    """Sorted ROUTES keys that are not catalog ids, i.e. possible typos."""
    return sorted(k for k in routes if k not in catalog_ids)


class RouteTableTests(unittest.TestCase):
    def test_every_focus_profile_has_a_route_entry(self):
        focus_in_catalog = sorted(k for k in CATALOG_IDS if profile_tiers.is_focus(k))
        self.assertEqual(focus_in_catalog, sorted(profile_tiers.FOCUS))
        missing = [k for k in profile_tiers.FOCUS if k not in profile_models.ROUTES]
        self.assertEqual(missing, [])

    def test_every_entry_is_three_rows_of_three_nonempty_cells(self):
        self.assertEqual(table_problems(profile_models.ROUTES), [])

    def test_table_problems_reports_broken_entries(self):
        row = ('路线', '候选', '决定')
        bad = {
            'T01': (row, row, row),
            'T02': (row, row),                        # two rows
            'T03': (row, row, ('a|b', 'c', 'd')),     # pipe in a cell
            'T04': (row, row, ('a\nb', 'c', 'd')),    # newline in a cell
            'T05': (row, row, ('  ', 'c', 'd')),      # blank cell
            'T06': (row, row, (1, 'c', 'd')),         # non-string cell
            'T07': (row, row, ('a', 'b')),            # two cells
        }
        problems = table_problems(bad)
        self.assertEqual([k for k, _ in problems], ['T02', 'T03', 'T04', 'T05', 'T06', 'T07'])
        self.assertNotIn('T01', {k for k, _ in problems})

    def test_unresolved_role_is_reported(self):
        routes = {'T01': (
            ('路线', '{{m:known.role}}', '决定'),
            ('路线', '{{m:unknown.role}}', '决定'),
            ('路线', '无型号占位符', '{{table:plans}} 与 {{date:facts}} 不属于型号键'),
        )}
        self.assertEqual(unresolved_roles(routes, known_roles={'known.role'}),
                         {'unknown.role': ['T01']})
        # only {{m:…}} counts as a model placeholder; other volatile kinds stay out of scope
        self.assertEqual(set(model_roles(routes)), {'known.role', 'unknown.role'})

    def test_unresolved_roles_match_the_known_list(self):
        self.assertEqual(unresolved_roles(profile_models.ROUTES),
                         {r: list(ks) for r, ks in KNOWN_UNRESOLVED_ROLES.items()})

    def test_route_gives_each_id_the_same_three_rows_without_touching_the_real_table(self):
        real = profile_models.ROUTES
        snapshot = dict(real)
        profile_models.ROUTES = {}
        try:
            rows = (('路线甲', '候选甲', '决定甲'), ('路线乙', '候选乙', '决定乙'), ('路线丙', '候选丙', '决定丙'))
            profile_models.route('X01 X02', *rows)
            self.assertEqual(sorted(profile_models.ROUTES), ['X01', 'X02'])
            self.assertEqual(profile_models.ROUTES['X01'], list(rows))
            self.assertEqual(profile_models.ROUTES['X02'], list(rows))
            profile_models.route('X03', *rows)
            self.assertEqual(sorted(profile_models.ROUTES), ['X01', 'X02', 'X03'])
        finally:
            profile_models.ROUTES = real
        self.assertIs(profile_models.ROUTES, real)
        self.assertEqual(profile_models.ROUTES, snapshot)
        self.assertFalse({'X01', 'X02', 'X03'} & set(real))

    def test_shared_route_ids_keep_identical_rows(self):
        # route('A08 A10 A11', …) assigned one set of rows to all three ids.
        self.assertEqual(profile_models.ROUTES['A08'], profile_models.ROUTES['A10'])
        self.assertEqual(profile_models.ROUTES['A10'], profile_models.ROUTES['A11'])

    def test_key_not_in_catalog_is_reported(self):
        rows = (('a', 'b', 'c'), ('d', 'e', 'f'), ('g', 'h', 'i'))
        self.assertEqual(extra_route_keys({'A01': rows, 'A8': rows}), ['A8'])
        self.assertEqual(extra_route_keys({'A01': rows}), [])

    def test_route_keys_match_catalog_plus_known_maintenance_keys(self):
        self.assertEqual(extra_route_keys(profile_models.ROUTES), list(KNOWN_EXTRA_KEYS))


if __name__ == '__main__':
    unittest.main()
