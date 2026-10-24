import { readResponse } from './api.js';

let snapshot;

export async function staticAPI(path, body) {
  if (body !== undefined) throw new Error('This site is read-only. Contributions and sign-in are unavailable.');
  if (!['/config', '/practices', '/sources'].includes(path) && !/^\/(practices|sources)\/[^/]+$/.test(path)) {
    throw new Error('This page is unavailable on the read-only site.');
  }
  snapshot ||= fetch(new URL('../data/public.json', import.meta.url), { headers: { Accept: 'application/json' } })
    .then(readResponse).catch(error => { snapshot = null; throw error; });
  const data = await snapshot;
  if (path === '/config') return data.config;
  const [, collection, slug] = path.split('/');
  const entries = data[collection];
  if (!slug) return entries;
  const entry = entries.find(entry => entry.slug === decodeURIComponent(slug) || entry.id === decodeURIComponent(slug));
  if (!entry) throw new Error('This entry is unavailable.');
  return entry;
}
