import assert from 'node:assert/strict';
import { test } from 'node:test';
import { api } from '../js/api.js';

test('project URLs stay inside the Pages project, including queries and deep links', async () => {
  const previousDocument = globalThis.document;
  try {
    globalThis.document = { querySelector: () => ({ content: '/source-culture/' }) };
    const { appURL, routePath } = await import('../js/paths.js?pages-test');
    for (const path of ['/', '/explore?q=rice&tag=poetry', '/practices/experiments-with-rice#account', '/sources/decolonising-computing']) {
      assert.equal(appURL(path), '/source-culture' + path);
      assert.equal(appURL(appURL(path)), appURL(path));
    }
    assert.equal(appURL('/source-culture?view=project'), '/source-culture?view=project');
    assert.equal(appURL('https://example.test/'), 'https://example.test/');
    assert.equal(appURL('//example.test/'), '//example.test/');
    assert.equal(appURL('#account'), '#account');
    assert.equal(routePath('/source-culture'), '/');
    assert.equal(routePath('/source-culture/'), '/');
    assert.equal(routePath('/source-culture/explore/'), '/explore');
    assert.equal(routePath('/source-culture/practices/experiments-with-rice/'), '/practices/experiments-with-rice');
  } finally {
    globalThis.document = previousDocument;
  }
});

test('the Pages adapter browses a single public snapshot and rejects writes and private reads', async () => {
  const previousDocument = globalThis.document, previousFetch = globalThis.fetch;
  const requests = [];
  try {
    globalThis.document = { querySelector: selector => selector.includes('app-mode') ? { content: 'static' } : { content: '/source-culture/' } };
    const entry = { id: 'editorial-rice', slug: 'experiments-with-rice', title: 'experiments with rice' };
    globalThis.fetch = async (url, options) => {
      requests.push({ url: String(url), options });
      return new Response(JSON.stringify({ config: { mode: 'static' }, practices: [entry], sources: [] }), { headers: { 'Content-Type': 'application/json' } });
    };
    // No POST, private request, or snapshot fetch should happen for these calls.
    await assert.rejects(api('/submissions', { title: 'Not submitted' }), /read-only/);
    await assert.rejects(api('/auth/request', { email: 'private@example.test' }), /read-only/);
    await assert.rejects(api('/mine'), /unavailable/);
    await assert.rejects(api('/session'), /unavailable/);
    assert.equal(requests.length, 0);
    assert.deepEqual(await api('/config'), { mode: 'static' });
    assert.deepEqual(await api('/practices'), [entry]);
    assert.deepEqual(await api('/practices/experiments-with-rice'), entry);
    assert.deepEqual(await api('/sources'), []);
    await assert.rejects(api('/sources/missing'), /unavailable/);
    assert.equal(requests.length, 1);
    assert.match(requests[0].url, /\/data\/public\.json$/);
  } finally {
    globalThis.document = previousDocument;
    globalThis.fetch = previousFetch;
  }
});
