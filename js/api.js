// This is the only module that knows the backend URL and session transport.
// Demo and production use the same persistent API; there is no localStorage fallback.
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
