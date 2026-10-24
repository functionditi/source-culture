import assert from 'node:assert/strict';
import { test } from 'node:test';
import { api, BackendUnavailableError, readResponse } from '../js/api.js';

test('HTML 404 and HTML fallback responses explain how to open the app', async () => {
  for (const status of [200, 404]) {
    const response = new Response('<!DOCTYPE html><title>Not an API</title>', {
      status, headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
    await assert.rejects(readResponse(response), error => {
      assert.ok(error instanceof BackendUnavailableError);
      assert.match(error.message, /npm run dev/);
      assert.match(error.message, /127\.0\.0\.1:8000/);
      assert.doesNotMatch(error.message, /Unexpected token|DOCTYPE/);
      return true;
    });
  }
});

test('JSON success and server validation errors keep their API behavior', async () => {
  assert.deepEqual(await readResponse(new Response('[{"id":"published"}]', {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  })), [{ id: 'published' }]);
  await assert.rejects(readResponse(new Response('{"error":"Please add a title."}', {
    status: 422, headers: { 'Content-Type': 'application/json' },
  })), /Please add a title\./);
});

test('malformed JSON gets a readable error without leaking the raw parser message', async () => {
  await assert.rejects(readResponse(new Response('not json', {
    headers: { 'Content-Type': 'application/json' },
  })), /unreadable response/);
});

test('a failed submission does not retry or switch to browser storage', async () => {
  const previousFetch = globalThis.fetch;
  const requests = [];
  try {
    globalThis.fetch = async (url, options) => {
      requests.push({ url, options });
      return new Response('<!DOCTYPE html>', { headers: { 'Content-Type': 'text/html' } });
    };
    const contribution = { title: 'My preserved contribution' };
    await assert.rejects(api('/submissions', contribution), BackendUnavailableError);
    assert.equal(requests.length, 1);
    assert.equal(requests[0].options.headers.Accept, 'application/json');
    assert.deepEqual(JSON.parse(requests[0].options.body), contribution);
    assert.deepEqual(contribution, { title: 'My preserved contribution' });
  } finally {
    globalThis.fetch = previousFetch;
  }
});
