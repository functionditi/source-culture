import { readResponse } from './api.js';

// Public project URL/key only. Secrets and editor authorization stay in the
// Edge Function. Access tokens live in sessionStorage, never localStorage.
export function createSupabaseAPI({ url, publishableKey }, { request = fetch, storage, clock = () => Date.now() } = {}) {
  if (storage === undefined) { try { storage = globalThis.sessionStorage; } catch {} }
  const project = new URL(url);
  if (project.protocol !== 'https:' || !/^[a-z0-9-]+\.supabase\.co$/.test(project.hostname)) throw new Error('The Supabase project URL is invalid.');
  if (typeof publishableKey !== 'string' || (!publishableKey.startsWith('sb_publishable_') && !publishableKey.startsWith('eyJ'))) throw new Error('The Supabase public key is invalid.');
  const endpoint = new URL('/functions/v1/source-culture', project).href;
  const sessionKey = 'source-culture-session:' + project.hostname;
  let credentials = null;
  const objectURLs = new Set();
  function clear() {
    credentials = null;
    try { storage?.removeItem(sessionKey); } catch {}
    for (const url of objectURLs) URL.revokeObjectURL(url);
    objectURLs.clear();
  }
  try {
    const saved = JSON.parse(storage?.getItem(sessionKey) || 'null');
    if (saved && typeof saved.access_token === 'string' && typeof saved.expires_at === 'number' && saved.expires_at * 1000 > clock()) credentials = saved;
    else clear();
  } catch { clear(); }
  function mediaURL(id) { return endpoint + '?path=' + encodeURIComponent('/media/' + id); }
  function options(body, publicAuth = false) {
    if (credentials && credentials.expires_at * 1000 <= clock()) clear();
    return {
      method: body === undefined ? 'GET' : 'POST', credentials: 'omit', cache: 'no-store',
      headers: { Accept: 'application/json', apikey: publishableKey,
        ...(credentials && !publicAuth ? { Authorization: 'Bearer ' + credentials.access_token } : {}),
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    };
  }
  async function decorate(record, privateRead) {
    if (!record?.media) return record;
    const media = await Promise.all(record.media.map(async image => {
      const remote = mediaURL(image.id);
      if (!privateRead) return { ...image, url: remote };
      // <img> cannot attach a bearer header. Fetch private previews explicitly;
      // no access token is placed in a URL, markup, or the browser history.
      const response = await request(remote, options());
      if (!response.ok) {
        if (response.status === 401) clear();
        await readResponse(response);
      }
      const blobURL = URL.createObjectURL(await response.blob());
      objectURLs.add(blobURL);
      return { ...image, url: blobURL };
    }));
    return { ...record, media };
  }
  const send = async function supabaseAPI(path, body) {
    const response = await request(endpoint + '?path=' + encodeURIComponent(path), options(body, ['/auth/request', '/auth/verify'].includes(path)));
    if (response.status === 401) {
      clear();
      if (path === '/session') return { user: null, csrf: null };
    }
    const data = await readResponse(response);
    if (path === '/auth/verify') {
      if (typeof data.access_token !== 'string' || typeof data.expires_at !== 'number') throw new Error('The sign-in response was incomplete. Please request a new link.');
      clear();
      credentials = { access_token: data.access_token, expires_at: data.expires_at };
      try { storage?.setItem(sessionKey, JSON.stringify(credentials)); } catch {}
      return { message: data.message };
    }
    if (path === '/auth/logout') clear();
    const privateRead = ['/mine', '/admin'].includes(path) || /^\/submissions\/[^/]+$/.test(path);
    if (privateRead) {
      for (const url of objectURLs) URL.revokeObjectURL(url);
      objectURLs.clear();
    }
    // Queue cards need only image IDs/counts. Private blobs are fetched later,
    // for the selected review, instead of downloading the entire image archive.
    if (privateRead) {
      const hide = record => record?.media ? { ...record, media: record.media.map(image => ({ ...image, url: '' })) } : record;
      return Array.isArray(data) ? data.map(hide) : hide(data);
    }
    if (Array.isArray(data)) return Promise.all(data.map(record => decorate(record, false)));
    return decorate(data, false);
  };
  send.loadPrivateMedia = record => decorate(record, true);
  return send;
}

let adapter;
async function getAdapter() {
  adapter ||= fetch(new URL('../data/supabase.json', import.meta.url), { headers: { Accept: 'application/json' }, cache: 'no-store' })
    .then(readResponse).then(config => createSupabaseAPI(config)).catch(error => { adapter = null; throw error; });
  return adapter;
}
export async function loadPrivateMedia(record) {
  return (await getAdapter()).loadPrivateMedia(record);
}
export async function supabaseAPI(path, body) {
  const request = await getAdapter();
  const data = await request(path, body);
  // Curated project photography is built with the site, while all publication
  // state comes from Supabase. Never fall back to stale published entries.
  const decorate = record => {
    const names = { 'rice-grid': 'experiments-with-rice.webp', prasa: 'prasa-example.webp' };
    return record?.editorial && names[record.placeholder] ? { ...record, project_image: '/project-images/' + names[record.placeholder] } : record;
  };
  return Array.isArray(data) ? data.map(decorate) : decorate(data);
}
