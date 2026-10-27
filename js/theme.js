// Runs before styles paint; only the appearance preference is stored.
(() => {
  const key = 'source-culture-appearance';
  const themes = ['olive', 'charcoal'];
  const backgrounds = { olive: '#49512C', charcoal: '#120F05' };
  const normalise = value => themes.includes(value) ? value : null;
  const defaultTheme = 'olive';
  let preference;
  try { preference = localStorage.getItem(key); } catch { /* Device storage is optional. */ }
  preference = normalise(preference);

  const apply = theme => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', backgrounds[theme]);
    document.querySelectorAll('[data-theme-choice]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.themeChoice === theme));
    });
  };
  apply(preference || defaultTheme);
  document.addEventListener('DOMContentLoaded', () => {
    apply(document.documentElement.dataset.theme);
    document.querySelectorAll('[data-theme-choice]').forEach(button => {
      button.addEventListener('click', () => {
        preference = button.dataset.themeChoice;
        apply(preference);
        try { localStorage.setItem(key, preference); } catch { /* Keep working without persistence. */ }
      });
    });
  }, { once: true });
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    preference = normalise(event.newValue);
    apply(preference || defaultTheme);
  });
})();
