"""Tests for the lower-level architecture diagrams and notes; render-only, nothing is written to disk."""
import pathlib, re, sys, unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import profile_architecture as pa
from profile_tiers import FOCUS, is_focus

NS = '{http://www.w3.org/2000/svg}'
SIZE, HALF = 16, 16 * .56

# Rule failures found on the real data, as (rule, diagram key). The generator and data
# stay untouched; each entry is reported instead of fixed.
KNOWN_FAILURES = set()


def diagrams():
    """Every diagram render_diagram produces in a build: (diagram key, profile key, spec)."""
    out = [(key, key, p) for key, p in pa.DETAIL.items()]
    out += [(f'{key}-{part["suffix"]}', key, part) for key, part in pa.SUPPLEMENTS.items()]
    return out


def parse(svg):
    root = ET.fromstring(svg)
    vb = tuple(float(v) for v in root.get('viewBox').split())
    boxes = {int(r.get('data-node')): tuple(float(r.get(k)) for k in ['x', 'y', 'width', 'height'])
             for r in root.iter(NS + 'rect') if r.get('data-node')}
    edges = []
    for n in root.iter(NS + 'path'):
        if n.get('data-edge'):
            numbers = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', n.get('d'))]
            a, b = (int(v) for v in n.get('data-edge').split('-'))
            edges.append((a, b, list(zip(numbers[::2], numbers[1::2]))))
    return root, vb, boxes, edges


def on_border(pt, box, tol=1):
    (px, py), (x, y, w, h) = pt, box
    vertical = (abs(px - x) <= tol or abs(px - (x + w)) <= tol) and y - tol <= py <= y + h + tol
    horizontal = (abs(py - y) <= tol or abs(py - (y + h)) <= tol) and x - tol <= px <= x + w + tol
    return vertical or horizontal


def crosses_interior(p, q, box):
    (x1, y1), (x2, y2), (x, y, w, h) = p, q, box
    if x1 == x2:
        return x < x1 < x + w and max(min(y1, y2), y) < min(max(y1, y2), y + h)
    return y < y1 < y + h and max(min(x1, x2), x) < min(max(x1, x2), x + w)


def walk(points, step=10):
    """Points every `step` px along an orthogonal polyline, with distance from the start."""
    out, travelled = [], 0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = abs(x2 - x1) + abs(y2 - y1)
        dx, dy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
        for i in range(0, int(length), step):
            out.append(((x1 + dx * i, y1 + dy * i), travelled + i))
        travelled += length
    out.append((points[-1], travelled))
    return out, travelled


class Wrap(unittest.TestCase):
    def labels(self):
        return [n for _, _, p in diagrams() for n in p['nodes']]

    def test_empty_string(self):
        self.assertEqual(pa.wrap(''), [])

    def test_full_width_counts_size_and_half_width_counts_056(self):
        # 3 × 16 = 48 fits, a fourth would not.
        self.assertEqual(pa.wrap('中' * 7, max_width=48), ['中中中', '中中中', '中'])
        self.assertEqual(pa.wrap('ア' * 4 + 'Ａ' * 2, max_width=48), ['アアア', 'アＡＡ'])
        # 5 × 8.96 = 44.8 fits under 45, 6 × 8.96 = 53.76 does not.
        self.assertEqual(pa.wrap('a' * 11, max_width=45), ['aaaaa', 'aaaaa', 'a'])
        # Half-width katakana is narrow.
        self.assertEqual(pa.wrap('ｱ' * 6, max_width=45), ['ｱ' * 5, 'ｱ'])
        # Mixed: 中 (16) + 3 × a (26.88) = 42.88 fits, the next 中 would not.
        self.assertEqual(pa.wrap('中aaa中', max_width=45), ['中aaa', '中'])
        self.assertEqual(pa.wrap('中' * 3, max_width=40, size=20), ['中中', '中'])
        self.assertEqual(pa.wrap('a' * 4, max_width=34, size=20), ['aaa', 'a'])  # 3 × 11.2 = 33.6
        # Half-width width scales with size: 3 × 11.2 = 33.6 > 30 at size 20, 5 × 5.6 = 28 ≤ 30 at size 10.
        self.assertEqual(pa.wrap('aaa', max_width=30, size=20), ['aa', 'a'])
        self.assertEqual(pa.wrap('abcde', max_width=30, size=10), ['abcde'])
        # Full-width width scales with size too: 3 × 20 = 60 > 50.
        self.assertEqual(pa.wrap('中文中文', max_width=50, size=20), ['中文', '中文'])

    def test_single_oversized_character_stays_on_its_own_line(self):
        self.assertEqual(pa.wrap('中', max_width=10), ['中'])
        self.assertEqual(pa.wrap('中中', max_width=10), ['中', '中'])

    def test_lines_fit_and_round_trip(self):
        samples = self.labels() + ['', '\n', 'a\n\nb', 'Claude Code／CLI 与 IDE\n多 agent workflow 编排 (beta)']
        for max_width in [40, 100, 228]:
            for text in samples:
                with self.subTest(text=text, max_width=max_width):
                    lines = pa.wrap(text, max_width=max_width)
                    self.assertEqual(''.join(lines), text.replace('\n', ''))
                    for line in lines:
                        if len(line) > 1:
                            self.assertLessEqual(self.measure(line), max_width + 1e-9, line)

    def test_explicit_newline_always_breaks(self):
        self.assertEqual(pa.wrap('ab\ncd'), ['ab', 'cd'])
        for text in self.labels() + ['短\n短', 'x' * 30 + '\n' + '长' * 20]:
            with self.subTest(text=text):
                expected = [line for part in text.split('\n') for line in pa.wrap(part)]
                self.assertEqual(pa.wrap(text), expected)

    @staticmethod
    def measure(line):
        import unicodedata
        return sum(SIZE if unicodedata.east_asian_width(c) in 'WF' else HALF for c in line)


class RenderDiagram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svgs = {name: pa.render_diagram(name, p) for name, _, p in diagrams()}


def diagram_test(rule, name, profile, spec):
    def test(self):
        root, vb, boxes, edges = parse(self.svgs[name])
        getattr(self, 'check_' + rule)(name, spec, root, vb, boxes, edges)
    test.__doc__ = f'{name}: {rule}'
    return unittest.expectedFailure(test) if (rule, name) in KNOWN_FAILURES else test


def check_parses(self, name, spec, root, vb, boxes, edges):
    self.assertEqual(root.tag, NS + 'svg')
    self.assertEqual(sorted(boxes), list(range(1, len(spec['nodes']) + 1)))
    self.assertTrue(edges)


def check_labels(self, name, spec, root, vb, boxes, edges):
    texts = [(float(t.get('x')), float(t.get('y')), t.text or '') for t in root.iter(NS + 'text')]
    for i, label in enumerate(spec['nodes'], 1):
        x, y, w, h = boxes[i]
        inside = [s for tx, ty, s in texts if tx == x + w / 2 and y < ty < y + h]
        self.assertEqual(inside, pa.wrap(label), (name, i))
        self.assertEqual(''.join(inside), label.replace('\n', ''), (name, i))


def check_viewbox(self, name, spec, root, vb, boxes, edges):
    x0, y0, vw, vh = vb
    for r in root.iter(NS + 'rect'):
        x, y = float(r.get('x', 0)), float(r.get('y', 0))
        w, h = float(r.get('width')), float(r.get('height'))
        self.assertTrue(x0 <= x and y0 <= y and x + w <= x0 + vw and y + h <= y0 + vh, (name, r.attrib))
    for t in root.iter(NS + 'text'):
        x, y = float(t.get('x')), float(t.get('y'))
        self.assertTrue(x0 <= x <= x0 + vw and y0 <= y <= y0 + vh, (name, t.attrib, t.text))
    for a, b, pts in edges:
        for x, y in pts:
            self.assertTrue(x0 <= x <= x0 + vw and y0 <= y <= y0 + vh, (name, a, b, (x, y)))


def check_edge_endpoints(self, name, spec, root, vb, boxes, edges):
    for a, b, pts in edges:
        self.assertTrue(on_border(pts[0], boxes[a]), (name, f'{a}-{b}', 'start', pts[0], boxes[a]))
        self.assertTrue(on_border(pts[-1], boxes[b]), (name, f'{a}-{b}', 'end', pts[-1], boxes[b]))


def check_edges_avoid_boxes(self, name, spec, root, vb, boxes, edges):
    manual = pa.ROUTES.get(name, {})
    for a, b, pts in edges:
        for p, q in zip(pts, pts[1:]):
            self.assertTrue(p[0] == q[0] or p[1] == q[1], (name, f'{a}-{b}', 'diagonal', p, q))
            for i, box in boxes.items():
                if i not in (a, b):
                    self.assertFalse(crosses_interior(p, q, box), (name, f'{a}-{b}', 'crosses node', i))
        if (a - 1, b - 1) in manual:
            continue
        # The router steps 20 px straight out of a port, then walks only grid cells
        # outside every node box grown by 10 px; the last 20 px mirror the start.
        samples, total = walk(pts)
        for (x, y), dist in samples:
            if dist < 20 or dist > total - 20:
                continue
            for i, (bx, by, bw, bh) in boxes.items():
                self.assertFalse(bx - 10 <= x <= bx + bw + 10 and by - 10 <= y <= by + bh + 10,
                                 (name, f'{a}-{b}', 'within 10 px of node', i, (x, y)))


RULES = {'parses': check_parses, 'labels': check_labels, 'viewbox': check_viewbox,
         'edge_endpoints': check_edge_endpoints, 'edges_avoid_boxes': check_edges_avoid_boxes}
for _rule, _check in RULES.items():
    setattr(RenderDiagram, 'check_' + _rule, _check)
    for _name, _profile, _spec in diagrams():
        setattr(RenderDiagram, f'test_{_rule}_{_name.replace("-", "_")}', diagram_test(_rule, _name, _profile, _spec))


class DetailMarkdown(unittest.TestCase):
    IMAGE = re.compile(r'!\[[^\]]*\]\(([^)\s]+)\)')

    def test_heading_table_and_detail_image(self):
        for key, p in pa.DETAIL.items():
            with self.subTest(key=key):
                text = pa.detail_markdown(key)
                self.assertTrue(text.startswith('#### 深入一层：' + p['focus'] + '\n'))
                lines = text.split('\n')
                self.assertEqual(lines.count('| 模块／交接点 | 怎样工作 | 状态与边界 |'), 1)
                separators = [i for i, line in enumerate(lines) if re.fullmatch(r'\|(\s*:?-+:?\s*\|)+', line)]
                self.assertEqual(len(separators), 1)
                start = separators[0]
                self.assertEqual(lines[start - 1].count('|'), 4)
                body = []
                for line in lines[start + 1:]:
                    if not line.startswith('|'):
                        break
                    body.append(line)
                self.assertEqual(len(body), len(p['rows']))
                for line in body:
                    self.assertEqual(len(line.strip().strip('|').split('|')), 3, line)
                images = self.IMAGE.findall(text)
                self.assertEqual(images[0], f'figures/profiles/{key}-detail.svg')

    def test_images_match_expected_figures_for_focus_profiles(self):
        # build_profiles only emits detail_markdown for focus profiles.
        for key in pa.DETAIL:
            if not is_focus(key):
                continue
            with self.subTest(key=key):
                images = self.IMAGE.findall(pa.detail_markdown(key))
                self.assertEqual(images, pa.expected_figures(key)[1:])
                self.assertEqual(images[0], pa.expected_figures(key)[1])

    def test_supplement_section(self):
        for key in pa.DETAIL:
            with self.subTest(key=key):
                text = pa.detail_markdown(key)
                if key not in pa.SUPPLEMENTS:
                    self.assertNotIn('局部放大', text)
                    self.assertEqual(len(self.IMAGE.findall(text)), 1)
                    continue
                part = pa.SUPPLEMENTS[key]
                head, _, tail = text.partition('\n\n#### 局部放大：' + part['focus'] + '\n\n')
                self.assertTrue(tail)
                self.assertEqual(self.IMAGE.findall(tail), [f'figures/profiles/{key}-{part["suffix"]}.svg'])
                if is_focus(key):
                    self.assertIn(self.IMAGE.findall(tail)[0], pa.expected_figures(key))


class ExpectedFigures(unittest.TestCase):
    def keys(self):
        return sorted(set(pa.DETAIL) | set(pa.SUPPLEMENTS) | set(FOCUS) | {'A13', 'Z99'})

    def test_short_profiles_have_only_the_overview(self):
        for key in self.keys():
            if not is_focus(key):
                with self.subTest(key=key):
                    self.assertEqual(pa.expected_figures(key), [f'figures/profiles/{key}.svg'])

    def test_focus_profiles_add_detail_and_supplement(self):
        for key in self.keys():
            if is_focus(key):
                with self.subTest(key=key):
                    expected = [f'figures/profiles/{key}.svg', f'figures/profiles/{key}-detail.svg']
                    if key in pa.SUPPLEMENTS:
                        expected.append(f'figures/profiles/{key}-{pa.SUPPLEMENTS[key]["suffix"]}.svg')
                    self.assertEqual(pa.expected_figures(key), expected)

    def test_focus_tier_drives_detail(self):
        self.assertTrue(any(is_focus(k) and k in pa.SUPPLEMENTS for k in pa.DETAIL))
        self.assertTrue(any(not is_focus(k) and k in pa.SUPPLEMENTS for k in pa.DETAIL))
        for key in FOCUS:
            self.assertIn(key, pa.DETAIL)


if __name__ == '__main__':
    unittest.main()
