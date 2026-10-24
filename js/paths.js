// The Python app lives at /; a Pages project can live under /source-culture/.
export const appBase = globalThis.document?.querySelector('meta[name="app-base"]')?.content || '/';

export function appURL(path) {
  if (appBase === '/' || !path.startsWith('/') || path.startsWith('//')) return path;
  if (path.split(/[?#]/, 1)[0] === appBase.slice(0, -1) || path.startsWith(appBase)) return path;
  return appBase.slice(0, -1) + path;
}

export function routePath(pathname = location.pathname) {
  const path = appBase !== '/' && pathname.startsWith(appBase) ? pathname.slice(appBase.length - 1) : pathname;
  return path === appBase.slice(0, -1) ? '/' : path.replace(/\/$/, '') || '/';
}

export function scopeLinks(root) {
  root.querySelectorAll('a[href^="/"]').forEach(anchor => {
    anchor.setAttribute('href', appURL(anchor.getAttribute('href')));
  });
}
