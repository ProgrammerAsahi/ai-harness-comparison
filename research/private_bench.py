#!/usr/bin/env python3
"""Author's private-bench run records: export public aggregates, validate them, render tables.

The private ledger holds task IDs, task specs, logs and review notes; none of it leaves the
author's machine. `export` reads the ledger read-only and writes per-configuration
aggregates only, after merging every cell too small to hide single-task results.
`check` validates committed aggregate files. Report placeholders
{{bench:<campaign>.<table>}} are rendered by resolve_volatile.py through render().

Disclosure rules (see AGENTS.md):
- A configuration is published only when its judged runs cover at least min_cell tasks
  and runs; smaller ones are named without results.
- Per configuration, results are split by task category only. Categories whose cell is
  too small for any published configuration are merged with the next-smallest category
  until every cell passes, so no hidden remainder can be recovered by subtraction. If that
  would leave a single bucket, the split is dropped.
- Project types are reported as task counts for the whole campaign, never with results,
  so two published splits can never be intersected.
- Rows keep the fixed order of configs.json; nothing is sorted by result.

Commands:
  export --ledger <ledger.db> --campaign <name> --out research/private-bench/<name>.json [--task-groups <private.json>]
  check [files...]          validate committed aggregates (default: research/private-bench/*.json)
  preview <file>            print the rendered tables, synthetic data included
  synthetic-ledger <out>    write a synthetic ledger for tests and dry runs
"""
import argparse, collections, contextlib, datetime as dt, json, pathlib, random, sqlite3, statistics, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'research/private-bench'
META = json.loads((DATA / 'configs.json').read_text())
SCHEMA = 'private-bench-aggregate/1'


# ---------- export (runs on the author's machine) ----------

def _ts(s):
    return dt.datetime.fromisoformat(s) if s else None


def load_runs(ledger, campaign):
    """Read one campaign read-only, with the same verdict rules as the bench's own report tables."""
    with contextlib.closing(sqlite3.connect(f'file:{ledger}?mode=ro', uri=True)) as c:
        c.row_factory = sqlite3.Row
        return _read(c, campaign)


def _read(c, campaign):
    rows = c.execute(
        """select b.task_id, b.bench_task, b.config_id, b.status, t.category, t.acceptance_mode
           from bench_runs b join tasks t on t.id = b.task_id where b.campaign = ?""", (campaign,)).fetchall()
    if not rows:
        raise SystemExit(f'No runs for campaign {campaign}')
    out = []
    for r in rows:
        atts = c.execute('select * from attempts where task_id = ? order by started_at', (r['task_id'],)).fetchall()
        run = dict(task=r['bench_task'], config=r['config_id'], category=r['category'], timeout=False,
                   minutes=None, usd=None, version=None, start=None, end=None)
        if r['status'] == 'void':
            run['verdict'] = 'void'
        elif r['status'] != 'done' or not atts:
            run['verdict'] = 'unfinished'
        else:
            a = atts[-1]
            ev = c.execute('select passed from evaluations where attempt_id = ? order by id desc limit 1', (a['id'],)).fetchone()
            rv = c.execute('select verdict from reviews where task_id = ? order by ts desc limit 1', (r['task_id'],)).fetchone()
            passed, review, mode = bool(ev and ev['passed']), rv['verdict'] if rv else None, r['acceptance_mode']
            if mode == 'auto':
                verdict = 'ok' if passed else 'fail'
            elif mode == 'auto_human':
                verdict = 'fail' if not passed else ('pending' if review is None else ('ok' if review.startswith('accept') else 'fail'))
            else:
                verdict = 'pending' if review is None else ('ok' if review.startswith('accept') and passed else 'fail')
            start, end = _ts(a['started_at']), _ts(a['ended_at'])
            ids = [x['id'] for x in atts]
            usage = c.execute(f"select sum(api_equiv_usd) from calls where attempt_id in ({','.join('?' * len(ids))})", ids).fetchone()[0]
            run.update(verdict=verdict, timeout=a['status'] == 'timeout', version=a['harness_version'], start=start, end=end,
                       minutes=(end - start).total_seconds() / 60 if start and end else None,
                       usd=usage if all(x['usage_complete'] for x in atts) else None)
        out.append(run)
    return out


def _cell(runs):
    judged = [r for r in runs if r['verdict'] in ('ok', 'fail')]
    return {'tasks': len({r['task'] for r in judged}), 'judged': len(judged), 'success': sum(r['verdict'] == 'ok' for r in judged)}


def _passes(cell, minimum):
    return cell['tasks'] >= minimum['tasks'] and cell['judged'] >= minimum['judged']


def merge_categories(task_counts, minimum):
    """Merge categories with too few tasks in the campaign into the next-smallest one; None if one bucket would remain."""
    buckets = [(label,) for label in task_counts]
    size = lambda b: sum(task_counts[l] for l in b)
    while True:
        failing = [b for b in buckets if size(b) < minimum['tasks']]
        if not failing:
            return buckets if len(buckets) > 1 else None
        if len(buckets) <= 2:
            return None
        worst = min(failing, key=size)
        rest = [b for b in buckets if b != worst]
        partner = min(rest, key=size)
        merged = tuple(l for l in task_counts if l in worst + partner)
        buckets = [merged if b == partner else b for b in rest]


def split(runs, buckets, minimum):
    """One config's category cells, or None when any tested cell is still too small (the whole row is withheld)."""
    cells = [{'labels': list(b), **_cell([r for r in runs if r['category_label'] in b])} for b in buckets]
    return None if any(c['judged'] and not _passes(c, minimum) for c in cells) else cells


def export(ledger, campaign, task_groups=None, synthetic=False):
    runs = load_runs(ledger, campaign)
    unknown = sorted({r['config'] for r in runs} - set(META['configs']))
    if unknown:
        raise SystemExit('Add public descriptions to configs.json first: ' + ', '.join(unknown))
    cats = META['categories']
    missing = sorted({r['category'] for r in runs} - set(cats))
    if missing:
        raise SystemExit('Unknown task categories: ' + ', '.join(missing))
    for r in runs:
        r['category_label'] = cats[r['category']]
    minimum = META['min_cell']
    tasks = sorted({r['task'] for r in runs})
    by_config = collections.defaultdict(list)
    for r in runs:
        by_config[r['config']].append(r)
    published = {k: v for k, v in by_config.items() if _passes(_cell(v), minimum)}
    labels = [l for l in cats.values() if any(r['category_label'] == l for r in runs)]
    task_counts = {l: len({r['task'] for r in runs if r['category_label'] == l}) for l in labels}
    buckets = merge_categories(task_counts, minimum)
    per_task = collections.Counter((r['config'], r['task']) for r in runs)
    scope = {
        'tasks': len(tasks),
        'repeats': collections.Counter(per_task.values()).most_common(1)[0][0],
        'tasks_by_category': task_counts,
        'tasks_by_project_type': None,
        'period': None,
    }
    times = [t for r in runs for t in (r['start'], r['end']) if t]
    if times:
        scope['period'] = {'from': min(times).date().isoformat(), 'to': max(times).date().isoformat()}
    if task_groups:
        groups = json.loads(pathlib.Path(task_groups).read_text())['groups']
        bad = [g['label'] for g in groups if g['label'] not in META['project_types']]
        if bad:
            raise SystemExit('Project type labels must come from configs.json: ' + ', '.join(bad))
        counts = collections.Counter()
        for t in tasks:
            hit = [g['label'] for g in groups if any(t.startswith(p) for p in g['prefixes'])]
            if len(hit) != 1:
                raise SystemExit('Each task must match exactly one project type (check the private task-groups file)')
            counts[hit[0]] += 1
        scope['tasks_by_project_type'] = {l: counts[l] for l in META['project_types'] if counts[l]}
    configs = []
    for cid, spec in META['configs'].items():
        rs = by_config.get(cid)
        if not rs:
            continue
        entry = {'id': cid, **spec, 'harness_versions': sorted({r['version'] for r in rs if r['version']}),
                 'runs': {'registered': len(rs), 'void': sum(r['verdict'] == 'void' for r in rs),
                          'pending_review': sum(r['verdict'] == 'pending' for r in rs),
                          'unfinished': sum(r['verdict'] == 'unfinished' for r in rs),
                          'timeouts': sum(r['timeout'] for r in rs), 'judged': _cell(rs)['judged']}}
        if cid in published:
            entry['status'] = 'published'
            entry['total'] = _cell(rs)
            if buckets:
                entry['by_category'] = split(rs, buckets, minimum)
            costs = [r['usd'] for r in rs if r['verdict'] in ('ok', 'fail') and r['usd'] is not None]
            mins = [r['minutes'] for r in rs if r['verdict'] in ('ok', 'fail', 'pending') and r['minutes'] is not None]
            entry['api_usd_mean'] = round(statistics.mean(costs), 2) if costs else None
            entry['api_usd_coverage'] = [len(costs), entry['total']['judged']]
            entry['minutes_median'] = round(statistics.median(mins), 1) if mins else None
        else:
            entry['status'] = 'insufficient'
        configs.append(entry)
    data = {
        'schema': SCHEMA, 'synthetic': synthetic, 'campaign': campaign,
        'exported_at': dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'source': 'Author private ledger, read-only; task IDs, specs, logs and review notes are not exported',
        'stats_rules': META['stats_rules'], 'min_cell': minimum, 'scope': scope,
        'runs': {k: sum(c['runs'][k] for c in configs) for k in ('registered', 'void', 'pending_review', 'unfinished')},
        'category_buckets': [list(b) for b in buckets] if buckets else None,
        'configs': configs,
    }
    problems = validate(data)
    if problems:
        raise SystemExit('Export failed validation:\n' + '\n'.join(problems))
    return data


# ---------- validation (runs in npm run check) ----------

TOP = {'schema', 'synthetic', 'campaign', 'exported_at', 'source', 'stats_rules', 'min_cell', 'scope', 'runs', 'category_buckets', 'configs'}
CONFIG_KEYS = {'id', 'tool', 'harness', 'model', 'effort', 'caps', 'harness_versions', 'runs', 'status', 'total', 'by_category',
               'api_usd_mean', 'api_usd_coverage', 'minutes_median'}
CELL = {'tasks', 'judged', 'success'}


def validate(data):
    p = []
    if set(data) != TOP:
        return [f'top-level keys {sorted(set(data) ^ TOP)}']
    if data['schema'] != SCHEMA or not isinstance(data['synthetic'], bool):
        p.append('schema or synthetic flag')
    minimum = data['min_cell']
    if minimum['tasks'] < META['min_cell']['tasks'] or minimum['judged'] < META['min_cell']['judged']:
        p.append('min_cell below the configured threshold')
    cats = list(META['categories'].values())
    scope = data['scope']
    if set(scope) != {'tasks', 'repeats', 'tasks_by_category', 'tasks_by_project_type', 'period'}:
        p.append('scope keys')
    if set(scope['tasks_by_category']) - set(cats) or sum(scope['tasks_by_category'].values()) != scope['tasks']:
        p.append('scope categories')
    projects = scope['tasks_by_project_type']
    if projects is not None and (set(projects) - set(META['project_types']) or sum(projects.values()) != scope['tasks']):
        p.append('scope project types')
    buckets = data['category_buckets']
    if buckets is not None:
        flat = [l for b in buckets for l in b]
        if sorted(flat) != sorted(scope['tasks_by_category']) or len(buckets) < 2:
            p.append('category buckets must cover each category once, in at least two buckets')
    order = list(META['configs'])
    ids = [c['id'] for c in data['configs']]
    if not set(ids) <= set(order) or ids != sorted(ids, key=order.index):
        p.append('configs must be known and keep the order of configs.json')
    for c in data['configs']:
        where = c.get('id')
        if set(c) - CONFIG_KEYS:
            p.append(f'{where}: unexpected keys {sorted(set(c) - CONFIG_KEYS)}')
        spec = META['configs'].get(where, {})
        if any(c.get(k) != spec.get(k) for k in ('tool', 'harness', 'model', 'effort', 'caps')):
            p.append(f'{where}: description differs from configs.json')
        runs = c['runs']
        if c['status'] == 'insufficient':
            if {'total', 'by_category', 'api_usd_mean', 'minutes_median'} & set(c):
                p.append(f'{where}: insufficient configs must not show results')
            continue
        if c['status'] != 'published':
            p.append(f'{where}: status')
            continue
        t = c['total']
        if set(t) != CELL or not _passes(t, minimum) or t['success'] > t['judged'] or t['judged'] != runs['judged']:
            p.append(f'{where}: total cell')
        if runs['judged'] + runs['void'] + runs['pending_review'] + runs['unfinished'] != runs['registered']:
            p.append(f'{where}: run counts do not add up')
        parts = c.get('by_category')
        if buckets is None and parts is not None or buckets is not None and 'by_category' not in c:
            p.append(f'{where}: category split must follow category_buckets (null when withheld)')
        if parts:
            if [x['labels'] for x in parts] != buckets:
                p.append(f'{where}: buckets differ from category_buckets')
            for x in parts:
                if set(x) != CELL | {'labels'} or x['success'] > x['judged'] or (x['judged'] and not _passes(x, minimum)):
                    p.append(f'{where}: category cell {x["labels"]} is too small or malformed')
            for k in CELL:
                if sum(x[k] for x in parts) != t[k]:
                    p.append(f'{where}: categories do not add up to the total ({k})')
    return p


def check(files):
    problems = []
    for f in files:
        problems += [f'{f.name}: {x}' for x in validate(json.loads(f.read_text()))]
    return problems


# ---------- rendering (report placeholders) ----------

def _profile_link(key):
    letter = key[0]
    page = next((p.name for p in sorted((ROOT / 'report').glob(f'03{letter}-*.md'))), None)
    return f'#{key.lower()}' if page is None else f'{page}#{key.lower()}'


def _rate(c):
    return f"{c['success']}/{c['judged']}（{round(100 * c['success'] / c['judged'])}%）"


def _combo(c):
    return f"[{c['harness']}]({_profile_link(c['tool'])})＋{c['model']}"


def render(campaign, table, data=None, allow_synthetic=False):
    if data is None:
        path = DATA / f'{campaign}.json'
        if not path.exists():
            raise SystemExit(f'No private-bench aggregate for {campaign}')
        data = json.loads(path.read_text())
    problems = validate(data)
    if problems:
        raise SystemExit(f'{campaign}: ' + '; '.join(problems))
    if data['synthetic'] and not allow_synthetic:
        raise SystemExit(f'{campaign}: synthetic data cannot be rendered into the report')
    pub = [c for c in data['configs'] if c['status'] == 'published']
    note = (f"*作者私有题库运行记录（{data['campaign']}，导出于 {data['exported_at'][:10]}）。题目、日志与评分细则不公开，外部无法复核；"
            f"每个模型只在一个外壳里测过，数字描述的是组合，不代表外壳或模型各自的高下，也不构成排名。*\n\n")
    if table == 'scope':
        s = data['scope']
        cats = '、'.join(f'{k} {v} 题' for k, v in s['tasks_by_category'].items())
        lines = [f"- 题集：{s['tasks']} 题（{cats}），每个组合每题跑 {s['repeats']} 次，每次独立冷启动。"]
        if s['tasks_by_project_type']:
            lines.append('- 项目类型：' + '、'.join(f'{k} {v} 题' for k, v in s['tasks_by_project_type'].items()) + '；按项目类型只给题数，不给结果。')
        if s['period']:
            lines.append(f"- 运行时间：{s['period']['from']} 至 {s['period']['to']}。")
        r = data['runs']
        lines.append(f"- 登记 {r['registered']} 次；作废 {r['void']} 次（越界读取或环境故障，不进分母）；待人工评审 {r['pending_review']} 次、未跑完 {r['unfinished']} 次，都不计入“判过”。")
        lines.append('- 判定：自动验收通过算做对；文档类还要通过盲评；超时、超步数、超预算都算没做对。')
        lines.append(f"- 公开粒度：某组合判过的运行覆盖不足 {data['min_cell']['tasks']} 题或 {data['min_cell']['judged']} 次时，只列名称不给结果；"
                     '按任务类型拆分时，过小的类别并入相邻类别。')
        lines.append('- 资源上限各组合不同，“一步”在不同外壳里含义也不同，所以数字是各自默认上限下的结果，不是等资源比较。')
        return note + '\n'.join(lines)
    if table == 'totals':
        head = '| 组合 | 思考强度 | 题数 | 做对／判过 | 作废 | 待评 | 超时 |\n|---|---|---:|---:|---:|---:|---:|\n'
        body = ''.join(f"| {_combo(c)} | {c['effort']} | {c['total']['tasks']} | {_rate(c['total'])} | {c['runs']['void']} | {c['runs']['pending_review']} | {c['runs']['timeouts']} |\n" for c in pub)
        rest = [c for c in data['configs'] if c['status'] == 'insufficient']
        tail = ('\n\n样本不足、未列结果的组合：' + '、'.join(f"{_combo(c)}（判过 {c['runs']['judged']} 次）" for c in rest) + '。') if rest else ''
        return note + head + body.rstrip('\n') + tail
    if table == 'by-category':
        if not data['category_buckets']:
            return note + '本轮数据按任务类型拆分后格子过小，只公布各组合的总数。'
        labels = ['＋'.join(b) for b in data['category_buckets']]
        head = '| 组合 | ' + ' | '.join(labels) + ' |\n|---|' + '---:|' * len(labels) + '\n'
        row = lambda c: ' | '.join(_rate(x) if x['judged'] else '未测' for x in c['by_category']) if c['by_category'] else ' | '.join(['不拆分'] * len(labels))
        body = ''.join(f"| {_combo(c)} | {row(c)} |\n" for c in pub)
        withheld = '\n\n“不拆分”表示该组合有类别格子过小（多因部分题目未测），只看上表的总数。' if any(not c['by_category'] for c in pub) else ''
        return note + head + body.rstrip('\n') + withheld
    if table == 'resources':
        head = '| 组合 | 上限（步／分钟／API 等价） | 每次平均 API 等价 | 用时中位数 | 外壳版本 |\n|---|---|---:|---:|---|\n'
        def cap(c):
            k = c['caps']
            return f"{k['steps']}／{k['minutes']}／{'无' if k['api_usd'] is None else 'US$' + format(k['api_usd'], 'g')}"
        def usd(c):
            n, total = c['api_usd_coverage']
            return '—' if c['api_usd_mean'] is None else f"US${c['api_usd_mean']:.2f}（{n}/{total} 次有完整用量）"
        body = ''.join(f"| {_combo(c)} | {cap(c)} | {usd(c)} | {'—' if c['minutes_median'] is None else str(c['minutes_median']) + ' 分钟'} | {'、'.join(c['harness_versions']) or '—'} |\n" for c in pub)
        return note + head + body.rstrip('\n') + '\n\nAPI 等价按牌价折算，不是现金支出；订阅额度扣减另计。用量没有记全的运行不计入平均值。'
    raise SystemExit(f'Unknown private-bench table {table}')


# ---------- synthetic ledger (tests and dry runs only) ----------

def synthetic_ledger(path, seed=7):
    """Write a small ledger with the real schema subset and made-up tasks; nothing here is measured."""
    rnd = random.Random(seed)
    c = sqlite3.connect(path)
    c.executescript("""
      create table tasks(id text primary key, category text, acceptance_mode text);
      create table bench_runs(task_id text, campaign text, bench_task text, config_id text, repeat int, status text, void_reason text);
      create table attempts(id text primary key, task_id text, started_at text, ended_at text, steps int, status text, harness_version text, usage_complete int);
      create table evaluations(id integer primary key, attempt_id text, passed int);
      create table reviews(id integer primary key, task_id text, ts text, verdict text);
      create table calls(id integer primary key, attempt_id text, api_equiv_usd real);""")
    tasks = [(f'secret-alpha-{i:02d}', 'code.bugfix') for i in range(8)] + [(f'secret-beta-{i:02d}', 'code.bugfix') for i in range(4)] \
        + [(f'secret-alpha-f{i:02d}', 'code.feature') for i in range(3)] + [(f'secret-gamma-f{i:02d}', 'code.feature') for i in range(6)] \
        + [('secret-delta-doc', 'docs.metadata')]
    plan = {'astra': (0.9, tasks), 'gpt-6-luna': (0.7, [t for t in tasks if not t[0].startswith('secret-gamma')]),
            'opus': (0.85, tasks), 'mimo-flash-free': (0.5, tasks[:2])}
    n = 0
    t0 = dt.datetime(2026, 10, 14, 12, 0)
    for cfg, (p, ts) in plan.items():
        for name, cat in ts:
            for rep in range(3):
                n += 1
                tid, aid = f'run-{n}', f'att-{n}'
                mode = 'auto_human' if cat == 'docs.metadata' else 'auto'
                status = 'void' if rnd.random() < 0.03 else 'done'
                c.execute('insert into tasks values (?,?,?)', (tid, cat, mode))
                c.execute('insert into bench_runs values (?,?,?,?,?,?,?)', (tid, 'synthetic-example', name, cfg, rep + 1, status, 'synthetic void' if status == 'void' else None))
                start = t0 + dt.timedelta(minutes=7 * n)
                timeout = rnd.random() < 0.05
                c.execute('insert into attempts values (?,?,?,?,?,?,?,?)', (aid, tid, start.isoformat(), (start + dt.timedelta(minutes=rnd.uniform(2, 25))).isoformat(),
                                                                           rnd.randint(5, 50), 'timeout' if timeout else 'completed', '0.0.0-synthetic', 1))
                c.execute('insert into evaluations(attempt_id, passed) values (?,?)', (aid, int(not timeout and rnd.random() < p)))
                c.execute('insert into calls(attempt_id, api_equiv_usd) values (?,?)', (aid, round(rnd.uniform(0.05, 1.5), 3)))
                if mode == 'auto_human' and rep == 0:
                    c.execute('insert into reviews(task_id, ts, verdict) values (?,?,?)', (tid, start.isoformat(), 'accept'))
    c.commit()
    c.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export'); e.add_argument('--ledger', required=True); e.add_argument('--campaign', required=True)
    e.add_argument('--out', required=True); e.add_argument('--task-groups'); e.add_argument('--synthetic', action='store_true')
    k = sub.add_parser('check'); k.add_argument('files', nargs='*')
    v = sub.add_parser('preview'); v.add_argument('file')
    s = sub.add_parser('synthetic-ledger'); s.add_argument('out')
    a = ap.parse_args(argv)
    if a.cmd == 'export':
        data = export(a.ledger, a.campaign, a.task_groups, a.synthetic)
        pathlib.Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
        print(json.dumps({'campaign': a.campaign, 'configs': len(data['configs']),
                          'published': sum(c['status'] == 'published' for c in data['configs']), 'category_buckets': data['category_buckets']}, ensure_ascii=False))
    elif a.cmd == 'check':
        files = [pathlib.Path(f) for f in a.files] or sorted(f for f in DATA.glob('*.json') if f.name != 'configs.json')
        problems = check(files)
        print(json.dumps({'files': [f.name for f in files], 'issues': problems}, ensure_ascii=False))
        return 1 if problems else 0
    elif a.cmd == 'preview':
        data = json.loads(pathlib.Path(a.file).read_text())
        for t in ('scope', 'totals', 'by-category', 'resources'):
            print(f'<!-- {t} -->\n' + render(data['campaign'], t, data, allow_synthetic=True) + '\n')
    elif a.cmd == 'synthetic-ledger':
        synthetic_ledger(a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
