// MIT. Build-time Markdown/math rendering with self-contained font assets.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';

const require = createRequire(import.meta.url);
const location = name => process.env.HARNESS_NODE_MODULES ? path.join(process.env.HARNESS_NODE_MODULES, name) : name;
const { Marked } = require(location('marked'));
const katex = require(location('katex'));
const katexDist = path.dirname(require.resolve(location('katex')));

function math(tex, displayMode) {
  const rendered = katex.renderToString(tex, {
    displayMode, output: 'htmlAndMathml', throwOnError: true, strict: 'error',
    trust: false, maxExpand: 1000, maxSize: 20,
  });
  return displayMode ? `<div class="math-display" tabindex="0">${rendered}</div>\n` : rendered;
}

export function createStudyParser() {
  const parser = new Marked({ gfm: true });
  parser.use({ extensions: [
    {
      name: 'displayMath', level: 'block',
      start(source) { const i = source.indexOf('$$\n'); return i < 0 ? undefined : i; },
      tokenizer(source) {
        const match = /^\$\$\n([\s\S]+?)\n\$\$(?:\n|$)/.exec(source);
        if (match) return { type: 'displayMath', raw: match[0], text: match[1].trim() };
      },
      renderer(token) { return math(token.text, true); },
    },
    {
      name: 'inlineMath', level: 'inline',
      start(source) { const i = source.indexOf('$'); return i < 0 ? undefined : i; },
      tokenizer(source) {
        const match = /^\$(?!\$)((?:\\.|[^\\$\n])+?)\$(?!\$)/.exec(source);
        if (match) return { type: 'inlineMath', raw: match[0], text: match[1] };
      },
      renderer(token) { return math(token.text, false); },
    },
  ] });
  return parser;
}

export function embeddedMathAssets() {
  const fonts = [];
  const sha = data => createHash('sha256').update(data).digest('hex');
  let css = fs.readFileSync(path.join(katexDist, 'katex.min.css'), 'utf8');
  // Modern browser WOFF2 faces suffice; embed bytes, never request a CDN.
  css = css.replace(/src:[^;}]+/g, declaration => {
    const file = /url\(["']?(fonts\/[\w-]+\.woff2)["']?\)/.exec(declaration)?.[1];
    if (!file) throw Error(`Missing WOFF2 face in ${declaration}`);
    const data = fs.readFileSync(path.join(katexDist, file));
    fonts.push({ file, sha256: sha(data), bytes: data.length });
    return `src:url("data:font/woff2;base64,${data.toString('base64')}") format("woff2")`;
  });
  if (/url\((?!["']?data:)/.test(css)) throw Error('Math CSS contains an external resource');
  const license = fs.readFileSync(path.join(katexDist, '..', 'LICENSE'), 'utf8');
  return { css, license, manifest: { renderer: 'KaTeX', version: katex.version, output: 'htmlAndMathml', fonts, license_sha256: sha(license) } };
}
