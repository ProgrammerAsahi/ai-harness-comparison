/* Runs in <head> before paint; optional storage failures must not break reading. */
(() => {
  const root = document.documentElement;
  const preference = window.matchMedia('(prefers-color-scheme: dark)');
  let saved;
  try { saved = localStorage.getItem('harness-report-theme'); } catch {}
  if (saved !== 'dark' && saved !== 'light') saved = null;
  let button;
  function apply(theme) {
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    if (button) {
      button.textContent = theme === 'dark' ? '☀ 浅色模式' : '☾ 深色模式';
      button.setAttribute('aria-pressed', String(theme === 'dark'));
      button.setAttribute('aria-label', theme === 'dark' ? '切换到浅色模式' : '切换到深色模式');
    }
  }
  apply(saved || (preference.matches ? 'dark' : 'light'));
  preference.addEventListener('change', event => {
    if (!saved) apply(event.matches ? 'dark' : 'light');
  });
  document.addEventListener('DOMContentLoaded', () => {
    button = document.getElementById('theme-toggle');
    apply(root.dataset.theme);
    button.addEventListener('click', () => {
      saved = root.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem('harness-report-theme', saved); } catch {}
      apply(saved);
    });
  });
})();
