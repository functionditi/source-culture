// This is the only module that knows the backend URL and session transport.
// The Pages export explicitly selects a public, read-only snapshot.
// The full app never falls back to static data after an API failure.
let csrf = null;

export class BackendUnavailableError extends Error {
  constructor() {
    super('This preview is not connected to the Source Culture server. Start the app with npm run dev, then open http://127.0.0.1:8000.');
    this.name = 'BackendUnavailableError';
  }
}

export async function readResponse(response) {
  const contentType = response.headers.get('Content-Type') || '';
  if (!/^application\/(?:[\w.-]+\+)?json(?:\s*;|$)/i.test(contentType)) {
    throw new BackendUnavailableError();
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error('The server returned an unreadable response. Please try again.');
  }
  if (!response.ok) {
    throw new Error(typeof data?.error === 'string' ? data.error : 'The server could not complete this request. Please try again.');
  }
  return data;
}

export async function api(path, body) {
  const mode = globalThis.document?.querySelector('meta[name="app-mode"]')?.content;
  if (mode === 'supabase') {
    const { supabaseAPI } = await import('./supabase-api.js');
    return supabaseAPI(path, body);
  }
  if (mode === 'static') {
    const { staticAPI } = await import('./static-api.js');
    return staticAPI(path, body);
  }
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) }) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return readResponse(response);
}
export async function session() {
  const data = await api('/session');
  csrf = data.csrf;
  return data.user;
}
export async function signOut() {
  await api('/auth/logout', {});
  csrf = null;
}
export async function loadPrivateMedia(record) {
  if (globalThis.document?.querySelector('meta[name="app-mode"]')?.content !== 'supabase') return record;
  const { loadPrivateMedia } = await import('./supabase-api.js');
  return loadPrivateMedia(record);
}
