import { api, session, BackendUnavailableError } from './api.js';
import { e, heading } from './ui.js';
import { home, explore } from './views/collection.js?v=prasa-background-grid-1';
import { practice, sources, source } from './views/detail.js?v=prasa-background-grid-1';
import { about } from './views/about.js';
import { contribute } from './forms.js';
import { account } from './views/account.js';
import { mountWordmarkGrids } from './sketches/column-grids.js?v=prasa-background-grid-1';
import { appBase, appURL, routePath, scopeLinks } from './paths.js';

mountWordmarkGrids(document);

const main = document.querySelector('#main');
let cleanup = () => {}, navigation = 0, config;

export function navigate(url, options = {}) {
  if (options.replace) history.replaceState(options.state || {}, '', appURL(url)); else history.pushState(options.state || {}, '', appURL(url));
  render(options);
}
async function render({ scroll = true, focus = null } = {}) {
  const ticket = ++navigation;
  const path = routePath();
  cleanup?.(); cleanup = () => {};
  document.body.dataset.view = path === '/' ? 'notebook' : ['/explore', '/sources', '/about'].includes(path) ? 'browse' : 'page';
  document.title = 'source culture — everyday ways of knowing';
  document.querySelector('meta[name=description]').content = 'A growing collection of everyday instructions, patterns, and ways of knowing.';
  const isPrivate = ['/admin', '/manage', '/contribute'].includes(path);
  document.querySelector('meta[name=robots]')?.remove();
  if (isPrivate) { const meta = document.createElement('meta'); meta.name = 'robots'; meta.content = 'noindex, nofollow'; document.head.append(meta); }
  document.querySelectorAll('[data-nav]').forEach(a => { if (path.startsWith('/' + a.dataset.nav)) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  main.innerHTML = '<p class="loading" role="status">opening the notebook…</p>';
  try {
    config ||= await api('/config');
    document.querySelector('#mode-notice').hidden = config.mode !== 'demo';
    if (config.mode === 'static') {
      const invitation = document.querySelector('.nav-contribute');
      invitation.textContent = 'about this notebook ↗';
      invitation.href = appURL('/about#participate');
      document.querySelector('.footer-top > .text-link').textContent = 'explore the notebook ↗';
      document.querySelector('.footer-top > .text-link').href = appURL('/explore');
      document.querySelectorAll('.footer-bottom a').forEach(anchor => {
        if (['/contribute', '/manage', '/admin'].some(path => new URL(anchor.href).pathname === appURL(path))) anchor.remove();
      });
    }
    const stage = document.createElement('div');
    let dispose;
    // Views are rendered into a detached element so a slow request cannot overwrite a newer route.
    if (config.mode === 'static' && isPrivate) stage.innerHTML = `${heading('a notebook to explore.', 'This version of Source Culture is read-only. Contributions, corrections, sign-in, and editor access are not available here. Browse the projects and follow their sources.', 'source culture')}<p class="page-section"><a class="button primary" href="/explore">explore the collection ↗</a></p>`;
    else if (path === '/') dispose = await home(stage, config, navigate);
    else if (path === '/explore') dispose = await explore(stage, config, navigate);
    else if (path.startsWith('/practices/')) dispose = await practice(stage, decodeURIComponent(path.slice(11)), navigate);
    else if (path === '/sources') dispose = await sources(stage, config, navigate);
    else if (path.startsWith('/sources/')) dispose = await source(stage, decodeURIComponent(path.slice(9)), navigate);
    else if (path === '/about') dispose = about(stage, config);
    else if (path === '/contribute') dispose = await contribute(stage, config, navigate, await session());
    else if (path === '/manage' || path === '/admin') dispose = await account(stage, path === '/admin', navigate, config);
    else stage.innerHTML = `${heading('a page out of place.', 'This page may have moved, or the entry may have been withdrawn.')}<p class="page-section"><a class="button primary" href="/explore">back to the collection ↗</a></p>`;
    if (ticket !== navigation) { dispose?.(); return; }
    scopeLinks(stage);
    main.replaceChildren(stage);
    cleanup = dispose || (() => {});
    if (scroll) { window.scrollTo(0, 0); main.focus({ preventScroll: true }); }
    else if (focus) main.querySelector(focus)?.focus({ preventScroll: true });
    if (location.hash && !location.hash.startsWith('#token=')) {
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      target?.scrollIntoView();
    }
  } catch (error) {
    if (ticket !== navigation) return;
    const missingBackend = error instanceof BackendUnavailableError;
    const localPreview = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
    const recoveryLink = missingBackend && localPreview
      ? '<a class="button primary" href="http://127.0.0.1:8000/">open the local app ↗</a>'
      : missingBackend ? '' : '<a class="button primary" href="/explore">explore the collection ↗</a>';
    main.innerHTML = `${heading(missingBackend ? 'the app server is needed.' : 'a thread we couldn’t follow.', missingBackend && !localPreview ? 'The application server is unavailable. Please try again shortly.' : error.message, 'something needs another look')}<div class="button-row page-section">${recoveryLink}<button class="button" id="retry-page">try again ↗</button></div>`;
    scopeLinks(main);
    main.querySelector('#retry-page').addEventListener('click', () => render());
  }
}
document.addEventListener('click', event => {
  const anchor = event.target.closest('a[href]');
  if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || anchor.target || anchor.hasAttribute('download')) return;
  const url = new URL(anchor.href);
  if (url.origin !== location.origin) return;
  if (appBase !== '/' && !url.pathname.startsWith(appBase) && url.pathname !== appBase.slice(0, -1)) return;
  if (url.pathname === location.pathname && url.search === location.search && url.hash) return;
  event.preventDefault(); navigate(url.pathname + url.search + url.hash);
});
window.addEventListener('popstate', () => { if (!location.hash.startsWith('#token=')) render(); });
window.addEventListener('hashchange', () => { if (location.hash.startsWith('#token=')) render(); });
render();
