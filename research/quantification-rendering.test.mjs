// MIT. Regression coverage for visible markup and self-contained mathematics.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createStudyParser, embeddedMathAssets } from './quantification-markdown.mjs';

const dir = new URL('../studies/harness-quantification/', import.meta.url);
const markdown = fs.readFileSync(new URL('report.md', dir), 'utf8');
const html = fs.readFileSync(new URL('index.html', dir), 'utf8');

test('catalogue and visualization leads render as actual strong text, without literal delimiters', () => {
  const catalogue = [...html.matchAll(/<p class="entry-title"><strong>\d{2} · [\s\S]*?<\/strong><\/p>/g)];
  assert.equal(catalogue.length, 40);
  const views = [...html.matchAll(/<p class="entry-title"><strong>[一二三四五六七八]，[\s\S]*?<\/strong><\/p>/g)];
  assert.equal(views.length, 8);
  const content = html.split('<main id="content">')[1].split('</main>')[0];
  assert.ok(!content.includes('**'), 'literal Markdown emphasis reached the article');
  assert.ok(!content.includes('｜Architectural'), 'old catalogue separator');
});

test('all 36 questions have a separate, fully named answer type', () => {
  const tables = [...html.matchAll(/<table class="field-codebook">([\s\S]*?)<\/table>/g)];
  assert.equal(tables.length, 9);
  let fields = 0;
  for (const [, table] of tables) {
    assert.match(table, /<th>答案类型<\/th>/);
    const rows = [...table.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].slice(1);
    for (const [, row] of rows) {
      const cells = [...row.matchAll(/<td>([\s\S]*?)<\/td>/g)].map(m => m[1]);
      assert.equal(cells.length, 4);
      assert.match(cells[0], /^F\d{2}$/);
      assert.match(cells[2], /^(类别（无顺序）|集合（可多选）|条件集合)$/);
      assert.ok(!/[？?](类|集|条件)/.test(cells[1]));
      fields++;
    }
  }
  assert.equal(fields, 36);
});

test('display and inline TeX produce math layout and accessible MathML', () => {
  const parser = createStudyParser();
  const result = parser.parse('行内 $w_k$。\n\n$$\nd=\\frac{\\sum_k w_k\\delta_k}{\\sum_k w_k}\n$$\n');
  assert.match(result, /class="math-display"/);
  assert.match(result, /<mfrac>/);
  assert.match(result, /<msub>/);
  assert.match(result, /class="katex-html" aria-hidden="true"/);
  assert.match(result, /encoding="application\/x-tex"/);
});

test('code fences, code spans and escaped dollar signs retain their literal meaning', () => {
  const result = createStudyParser().parse('`$x$` 与 \\$5\n\n```text\n$x$\n```');
  assert.match(result, /<code>\$x\$<\/code>/);
  assert.match(result, /<pre><code class="language-text">\$x\$/);
  assert.ok(!result.includes('class="katex"'));
});

test('invalid TeX fails the build rather than leaving source or a red fallback', () => {
  assert.throws(() => createStudyParser().parse('$$\n\\notARealMacro{x}\n$$\n'), /Undefined control sequence/);
});

test('generated article contains every display equation and no raw dollar delimiters', () => {
  const blocks = [...markdown.matchAll(/^\$\$\n([\s\S]*?)\n\$\$/gm)];
  assert.ok(blocks.length >= 10);
  assert.equal((html.match(/class="math-display"/g) || []).length, blocks.length);
  const content = html.split('<main id="content">')[1].split('</main>')[0];
  assert.ok(!content.includes('$$'));
  assert.ok(!content.includes('katex-error'));
  assert.match(content, /d_\{\\mathrm\{obs\}\}/);
});

test('font bytes, styles and copyright remain embedded in the downloadable HTML', () => {
  const assets = embeddedMathAssets();
  assert.ok(assets.manifest.fonts.length > 0);
  assert.equal((assets.css.match(/data:font\/woff2;base64,/g) || []).length, assets.manifest.fonts.length);
  assert.ok(!/url\((?!["']?data:)/.test(assets.css));
  assert.ok(html.includes(assets.css));
  assert.ok(html.includes(assets.license));
  assert.ok(!html.includes('<script src='));
});
