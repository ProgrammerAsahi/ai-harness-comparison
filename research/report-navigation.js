/* Inlined by build_report.mjs so the reading artifact remains self-contained. */
(() => {
  const sidebar = document.querySelector('.sidebar');
  const nav = sidebar.querySelector('nav');
  const groups = [...nav.querySelectorAll('.nav-group')];
  const search = document.querySelector('#toc-search');
  const toggle = document.querySelector('#toggle-nav');
  const entries = [...nav.querySelectorAll('a[href^="#"]')].map(link => {
    const heading = document.getElementById(link.hash.slice(1));
    return {
      link,
      heading,
      chapter: heading?.closest('.chapter'),
      group: link.closest('.nav-group'),
      child: Boolean(link.closest('.nav-children')),
    };
  }).filter(entry => entry.heading && entry.chapter);

  let active = null;
  let geometry = [];
  let layoutDirty = true;
  let frame = 0;
  let revealRequested = false;

  function measure() {
    const chapterEnds = new Map();
    geometry = entries.map(entry => {
      if (!chapterEnds.has(entry.chapter)) {
        chapterEnds.set(entry.chapter, entry.chapter.getBoundingClientRect().bottom + window.scrollY);
      }
      return {
        entry,
        top: entry.heading.getBoundingClientRect().top + window.scrollY,
        end: chapterEnds.get(entry.chapter),
      };
    });
    layoutDirty = false;
  }

  function currentEntry() {
    if (!geometry.length) return null;
    const top = window.scrollY;
    const bottom = top + window.innerHeight;
    // Follow a reading line near the top, rather than only visible heading text.
    const readingLine = top + Math.min(120, window.innerHeight * 0.2);
    const atBottom = bottom >= document.documentElement.scrollHeight - 2;
    const limit = atBottom ? bottom - 1 : readingLine;
    let low = 0;
    let high = geometry.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (geometry[middle].top <= limit) low = middle + 1;
      else high = middle;
    }
    // Entering the first chapter from the cover can precede the reading line.
    let item = geometry[Math.max(0, low - 1)];
    // In a chapter gap, the old chapter may have left while the next is visible.
    if (item.end <= top) item = geometry[low];
    return item && item.top < bottom && item.end > top ? item.entry : null;
  }

  function revealInNav(link) {
    if (!nav.clientHeight || !link.getClientRects().length) return;
    const container = nav.getBoundingClientRect();
    const item = link.getBoundingClientRect();
    const top = container.top + nav.clientTop + 8;
    const bottom = container.top + nav.clientTop + nav.clientHeight - 8;
    // Never use scrollIntoView: it can also move the document being read.
    if (item.top < top || item.height > bottom - top) nav.scrollTop += item.top - top;
    else if (item.bottom > bottom) nav.scrollTop += item.bottom - bottom;
  }

  function update() {
    frame = 0;
    if (layoutDirty) measure();
    const next = currentEntry();
    const changed = next !== active;
    if (changed) {
      active?.link.removeAttribute('aria-current');
      active = next;
      active?.link.setAttribute('aria-current', 'location');
    }
    // Searching is an explicit request to inspect other entries. Do not fight it.
    if (active && !search.value.trim() && !active.group.hidden && !active.link.hidden) {
      let opened = false;
      if (active.child && !active.group.open) {
        active.group.open = true;
        opened = true;
      }
      // Other groups are never opened or closed by scroll tracking.
      if (changed || opened || revealRequested) revealInNav(active.link);
    }
    revealRequested = false;
  }

  function schedule({ layout = false, reveal = false } = {}) {
    layoutDirty ||= layout;
    revealRequested ||= reveal;
    if (!frame) frame = window.requestAnimationFrame(update);
  }

  search.addEventListener('input', () => {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    for (const group of groups) {
      const title = group.querySelector('summary').textContent.toLowerCase();
      let matches = 0;
      for (const link of group.querySelectorAll('.nav-children a')) {
        const hit = !query || title.includes(query) || link.textContent.toLowerCase().includes(query);
        link.hidden = !hit;
        if (hit) matches++;
      }
      const hit = !query || title.includes(query) || matches > 0;
      group.hidden = !hit;
      if (hit) visible++;
      if (query && hit) group.open = true;
    }
    document.querySelector('.empty').style.display = visible ? 'none' : 'block';
    schedule({ layout: true, reveal: !query });
  });

  toggle.addEventListener('click', () => {
    const open = sidebar.classList.toggle('expanded');
    toggle.setAttribute('aria-expanded', String(open));
    schedule({ layout: true, reveal: open });
  });
  for (const entry of entries) {
    entry.link.addEventListener('click', () => {
      if (window.innerWidth <= 740) {
        sidebar.classList.remove('expanded');
        toggle.setAttribute('aria-expanded', 'false');
        schedule({ layout: true });
      }
    });
  }
  // A details toggle can move the document on mobile, but does not reset siblings.
  for (const group of groups) group.addEventListener('toggle', () => schedule({ layout: true }));
  window.addEventListener('scroll', () => schedule(), { passive: true });
  window.addEventListener('resize', () => schedule({ layout: true, reveal: true }));
  window.addEventListener('hashchange', () => schedule({ layout: true, reveal: true }));
  window.addEventListener('pageshow', () => schedule({ layout: true, reveal: true }));
  window.addEventListener('load', () => schedule({ layout: true }));
  document.fonts?.ready.then(() => schedule({ layout: true }));
  if (window.ResizeObserver) {
    const observer = new window.ResizeObserver(() => schedule({ layout: true }));
    observer.observe(document.querySelector('main'));
    observer.observe(sidebar);
  }
  schedule({ layout: true, reveal: true });
})();
