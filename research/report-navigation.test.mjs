/* Behavioral checks with synthetic geometry, not browser rendering or visual QA. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { test } from 'node:test';

const source = fs.readFileSync(new URL('./report-navigation.js', import.meta.url), 'utf8');
class Element {
  listeners = new Map();
  attributes = new Map();
  hidden = false;
  style = {};
  addEventListener(type, callback) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(callback);
  }
  emit(type) { for (const callback of this.listeners.get(type) || []) callback({ target: this }); }
  setAttribute(key, value) { this.attributes.set(key, value); }
  removeAttribute(key) { this.attributes.delete(key); }
  getAttribute(key) { return this.attributes.get(key) ?? null; }
}

function fixture({ scrollY = 0, mobile = false } = {}) {
  const window = new Element();
  Object.assign(window, { scrollY, innerHeight: 900, innerWidth: mobile ? 430 : 1280 });
  const pending = new Map();
  let frame = 0;
  window.requestAnimationFrame = callback => { pending.set(++frame, callback); return frame; };
  const observerCallbacks = [];
  window.ResizeObserver = class {
    constructor(callback) { observerCallbacks.push(callback); }
    observe() {}
  };
  const sidebar = new Element();
  const classes = new Set();
  sidebar.classList = {
    toggle(name) { if (classes.has(name)) { classes.delete(name); return false; } classes.add(name); return true; },
    remove(name) { classes.delete(name); },
  };
  const nav = new Element();
  Object.assign(nav, { clientTop: 0, scrollTop: 0 });
  Object.defineProperty(nav, 'clientHeight', { get: () => mobile && !classes.has('expanded') ? 0 : 220 });
  nav.getBoundingClientRect = () => ({ top: 100, bottom: 320 });
  const search = Object.assign(new Element(), { value: '' });
  const toggle = new Element();
  const empty = new Element();
  const main = new Element();
  const document = { documentElement: { scrollHeight: 14500 } };
  const groups = [];
  const headings = new Map();
  const links = [];

  for (let index = 0; index < 4; index++) {
    const key = 'abcd'[index];
    const start = [1000, 4200, 8000, 11600][index];
    const chapter = { end: [3600, 7400, 11000, 14300][index] };
    chapter.getBoundingClientRect = () => ({ bottom: chapter.end - window.scrollY });
    const group = new Element();
    group.summary = { textContent: `Chapter ${key}` };
    group.children = [];
    let open = index === 0 || index === 2;
    Object.defineProperty(group, 'open', {
      get: () => open,
      set(value) { if (open !== value) { open = value; group.emit('toggle'); } },
    });
    group.querySelector = () => group.summary;
    group.querySelectorAll = () => group.children;
    groups.push(group);
    for (let child = 0; child < 3; child++) {
      const id = child ? `${key}${child}` : key;
      const heading = { id, top: start + [0, 200, 1200][child], chapter };
      heading.getBoundingClientRect = () => ({ top: heading.top - window.scrollY });
      heading.closest = () => chapter;
      headings.set(id, heading);
      const link = Object.assign(new Element(), { hash: '#' + id, textContent: id, id, height: child ? 28 : 30 });
      if (!child) group.parentLink = link;
      link.closest = selector => selector === '.nav-group' ? group : child ? group.children : null;
      link.getClientRects = () => link.hidden || group.hidden || (child && !group.open) || !nav.clientHeight ? [] : [{}];
      link.getBoundingClientRect = () => {
        let offset = 0;
        for (const other of groups) {
          if (other === group) break;
          if (!other.hidden) offset += groupHeight(other);
        }
        if (child) offset += group.parentLink.height + group.children.slice(0, child - 1).filter(item => !item.hidden).reduce((sum, item) => sum + item.height, 0);
        const top = 100 + nav.clientTop + offset - nav.scrollTop;
        const height = link.height;
        return { top, bottom: top + height, height };
      };
      links.push(link);
      if (child) group.children.push(link);
    }
  }
  function groupHeight(group) {
    return group.parentLink.height + (group.open ? group.children.filter(item => !item.hidden).reduce((sum, item) => sum + item.height, 0) : 0);
  }
  Object.defineProperty(nav, 'scrollHeight', {
    get: () => Math.max(nav.clientHeight, groups.filter(group => !group.hidden).reduce((sum, group) => sum + groupHeight(group), 0)),
  });
  nav.querySelectorAll = selector => selector === '.nav-group' ? groups : links;
  sidebar.querySelector = () => nav;
  document.getElementById = id => headings.get(id);
  document.querySelector = selector => ({ '.sidebar': sidebar, '#toc-search': search, '#toggle-nav': toggle, '.empty': empty, main })[selector];
  vm.runInNewContext(source, { window, document });
  const flush = () => {
    for (let limit = 0; pending.size; limit++) {
      assert.ok(limit < 20, 'navigation should settle without a toggle/scroll loop');
      const callbacks = [...pending.values()]; pending.clear();
      for (const callback of callbacks) callback();
    }
  };
  const current = () => links.filter(link => link.getAttribute('aria-current') === 'location').map(link => link.id);
  const scroll = y => { window.scrollY = y; window.emit('scroll'); flush(); };
  flush();
  return { window, document, groups, headings, links, nav, search, toggle, classes, observerCallbacks, pending, flush, current, scroll };
}

test('cover has no active entry; long content stays assigned after its heading leaves view', () => {
  const f = fixture();
  assert.deepEqual(f.current(), []);
  f.scroll(2600);
  assert.deepEqual(f.current(), ['a2']);
  assert.deepEqual(f.groups.map(group => group.open), [true, false, true, false]);
  f.scroll(0);
  assert.deepEqual(f.current(), []);
});

test('only a hidden current child opens its own parent; reverse scrolling preserves all other choices', () => {
  const f = fixture();
  f.scroll(4210);
  assert.deepEqual(f.current(), ['b']);
  assert.equal(f.groups[1].open, false, 'a visible parent needs no auto-expansion');
  f.scroll(4450);
  assert.deepEqual(f.current(), ['b1']);
  assert.deepEqual(f.groups.map(group => group.open), [true, true, true, false]);
  f.groups[1].open = false; f.flush();
  assert.equal(f.groups[1].open, true, 'a hidden current child is made visible again');
  f.groups[2].open = false;
  f.groups[3].open = true;
  f.flush();
  f.scroll(6800);
  assert.deepEqual(f.current(), ['b2']);
  f.scroll(1230);
  assert.deepEqual(f.current(), ['a1']);
  assert.deepEqual(f.groups.map(group => group.open), [true, true, false, true]);
});

test('a fully departed chapter gives way to the next visible parent even across a gap', () => {
  const f = fixture();
  f.scroll(3650);
  assert.deepEqual(f.current(), ['b']);
  assert.equal(f.groups[1].open, false);
});

test('deep-link load and page restoration follow the current content, with only one active entry', () => {
  const f = fixture({ scrollY: 4500 });
  assert.deepEqual(f.current(), ['b1']);
  f.window.scrollY = 9300;
  f.window.emit('pageshow'); f.flush();
  assert.deepEqual(f.current(), ['c2']);
  assert.equal(f.groups[3].open, false);
  f.window.scrollY = 1250;
  f.window.emit('hashchange'); f.flush();
  assert.deepEqual(f.current(), ['a1']);
});

test('the last short section is selectable at the page bottom', () => {
  const f = fixture();
  f.headings.get('d2').top = 14430;
  f.headings.get('d2').chapter.end = 14480;
  f.window.emit('resize'); f.flush();
  f.scroll(13600);
  assert.deepEqual(f.current(), ['d2']);
});

test('following the sidebar never moves the article; manual sidebar scrolling lasts until article scrolling resumes', () => {
  const f = fixture();
  f.scroll(11850);
  assert.deepEqual(f.current(), ['d1']);
  assert.equal(f.window.scrollY, 11850);
  assert.ok(f.nav.scrollTop > 0);
  f.nav.scrollTop = 0;
  f.nav.emit('scroll'); f.flush();
  assert.equal(f.nav.scrollTop, 0);
  f.scroll(11900);
  assert.ok(f.nav.scrollTop > 0);
  f.scroll(12900);
  assert.deepEqual(f.current(), ['d2']);
  assert.ok(f.nav.scrollTop > 0);
  assert.equal(f.window.scrollY, 12900);
});

function assertCentered(f, id) {
  const item = f.links.find(link => link.id === id).getBoundingClientRect();
  const midpoint = f.nav.getBoundingClientRect().top + f.nav.clientTop + f.nav.clientHeight / 2;
  assert.equal(item.top + item.height / 2, midpoint, `${id} should be centered in the scrollable navigation`);
}

test('active titles center in both reading directions, even when already visible', () => {
  const f = fixture();
  f.scroll(4450); assertCentered(f, 'b1');
  f.scroll(5500); assertCentered(f, 'b2');
  f.scroll(4450); assertCentered(f, 'b1');
  assert.equal(f.window.scrollY, 4450);
});

test('multiline titles and changed navigation layout remain centered', () => {
  const f = fixture({ scrollY: 4450 });
  f.links.find(link => link.id === 'b1').height = 112;
  f.nav.clientTop = 2;
  f.window.emit('resize'); f.flush();
  assertCentered(f, 'b1');
  f.groups[0].open = false; f.flush();
  assertCentered(f, 'b1');
  assert.deepEqual(f.groups.map(group => group.open), [false, true, true, false]);
});

test('centering stops at the first and last navigation boundaries', () => {
  const f = fixture();
  f.scroll(1000);
  assert.equal(f.nav.scrollTop, 0);
  f.scroll(12900);
  assert.equal(f.nav.scrollTop, f.nav.scrollHeight - f.nav.clientHeight);
  assert.ok(f.nav.scrollTop > 0);
  f.scroll(1000);
  assert.equal(f.nav.scrollTop, 0);
});

test('search results are not overridden by scroll tracking; clearing search reveals the current child', () => {
  const f = fixture();
  f.search.value = 'c1'; f.search.emit('input'); f.flush();
  f.scroll(4500);
  assert.deepEqual(f.current(), ['b1']);
  assert.equal(f.groups[1].hidden, true);
  assert.equal(f.groups[1].open, false);
  assert.equal(f.groups[3].open, false);
  f.search.value = ''; f.search.emit('input'); f.flush();
  assert.equal(f.groups[1].hidden, false);
  assert.equal(f.groups[1].open, true);
  assert.equal(f.groups[3].open, false);
});

test('layout changes refresh heading positions and scroll events share a single animation frame', () => {
  const f = fixture({ scrollY: 4450 });
  assert.deepEqual(f.current(), ['b1']);
  f.headings.get('b1').top = 5100;
  f.observerCallbacks.forEach(callback => callback()); f.flush();
  assert.deepEqual(f.current(), ['b']);
  for (let i = 0; i < 100; i++) f.window.emit('scroll');
  assert.equal(f.pending.size, 1);
  f.flush();
});

test('mobile menu still opens and closes without forcing unrelated parent states', () => {
  const f = fixture({ scrollY: 4500, mobile: true });
  assert.deepEqual(f.current(), ['b1']);
  assert.equal(f.nav.scrollTop, 0, 'hidden mobile navigation is not scrolled');
  f.toggle.emit('click'); f.flush();
  assert.equal(f.toggle.getAttribute('aria-expanded'), 'true');
  f.links.find(link => link.id === 'b1').emit('click'); f.flush();
  assert.equal(f.toggle.getAttribute('aria-expanded'), 'false');
  assert.deepEqual(f.groups.map(group => group.open), [true, true, true, false]);
});

test('generated HTML embeds this exact controller and current-title styling without an external script', () => {
  const html = fs.readFileSync(new URL('../AI-Harness调研报告.html', import.meta.url), 'utf8');
  assert.ok(html.includes(`<script>\n${source}\n</script>`));
  assert.match(html, /a\[aria-current="location"\]\{[^}]*color:#123d34;[^}]*font-weight:750/);
  assert.match(html, /a\[aria-current="location"\]::before\{content:'→'/);
  assert.doesNotMatch(html, /<script[^>]+src=/);
});
