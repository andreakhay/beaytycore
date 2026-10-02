import test from 'node:test';
import assert from 'node:assert/strict';
import { handleAiRequest, type AiDependencies } from '../lib/ai/adapter-core';
import { signConsultationHandle } from '../lib/ai/consultation-handle';

const SECRET = 'phase-one-test-handle-secret-longer-than-thirty-two-bytes';
const ID = '4d321734-0990-4511-a119-0a45796a267b';
const USER = 'client-1';
const ORIGIN = 'http://localhost:3000';
const FUTURE = '2030-01-01T00:00:00.000Z';
const NOW = Date.parse('2026-10-02T10:00:00.000Z');
type Seen = { url: string; method: string; headers: Headers; body: BodyInit | null | undefined };
const seen: Seen[] = [];

function fakeResponse(path: string): Response {
  if (path === '/consultations') return Response.json({
    id: ID, primary_service: 'hairstyle', expires_at: FUTURE, photo: null, recommendations: null,
  }, { status: 201 });
  if (path === '/consultations/' + ID + '/turn')
    return Response.json({ state: { id: ID, primary_service: 'hairstyle' }, status: 'more_information' });
  if (path === '/consultations/' + ID || path.endsWith('/select') || path.endsWith('/photo'))
    return Response.json({ id: ID, primary_service: 'hairstyle', ok: true });
  if (path.endsWith('/recommendations')) return Response.json({
    recommendations: [1, 2, 3].map((n) => ({ id: 'look-' + n, primary: { feature: 'hairstyle', style_id: 'crew_cut' } })),
  });
  if (path.endsWith('/generation')) return Response.json({
    generation: { recommendation_id: 'look-1', status: 'completed' }, result: { image: 'private-result' },
  });
  return Response.json({ ok: true, path });
}

function deps(user: { id: string; role: string } | null = { id: USER, role: 'client' },
              respond: (path: string) => Response = fakeResponse): AiDependencies {
  return {
    baseUrl: 'http://127.0.0.1:8000/',
    handleSecret: SECRET,
    now: () => NOW,
    currentUser: async () => user,
    upstreamFetch: async (input, init) => {
      const url = String(input);
      seen.push({ url, method: init?.method ?? 'GET', headers: new Headers(init?.headers), body: init?.body });
      return respond(new URL(url).pathname);
    },
  };
}

function request(method: string, path: string, body?: BodyInit, handle?: string, origin = ORIGIN): Request {
  const headers = new Headers();
  if (method !== 'GET') headers.set('origin', origin);
  if (handle) headers.set('x-ai-consultation-handle', handle);
  if (typeof body === 'string') headers.set('content-type', 'application/json');
  return new Request(ORIGIN + '/api/ai/' + path, { method, headers, body });
}

async function handle(user = USER, expiry = FUTURE): Promise<string> {
  return signConsultationHandle(user, ID, expiry, SECRET, NOW);
}

function image(type: string, size = 4): FormData {
  const form = new FormData();
  form.append('image', new File([new Uint8Array(size)], 'private-image', { type }));
  return form;
}

test.beforeEach(() => { seen.length = 0; });

test('current database client reaches consultation create and gets a short-lived signed handle', async () => {
  const response = await handleAiRequest(request('POST', 'consultations', JSON.stringify({ primary_service: 'hairstyle' })),
    ['consultations'], deps());
  assert.equal(response.status, 201);
  const data = await response.json();
  assert.equal(data.id, undefined);
  assert.equal(typeof data.handle, 'string');
  assert.equal(response.headers.get('cache-control'), 'private, no-store');
  assert.equal(seen[0].url, 'http://127.0.0.1:8000/consultations');
  assert.equal(seen[0].method, 'POST');
  assert.equal(seen[0].headers.get('cookie'), null);
  assert.equal(seen[0].headers.get('authorization'), null);
  assert.equal(seen[0].headers.get('x-ai-consultation-handle'), null);
  assert.equal(data.handle.includes(ID), false);
});

test('anonymous, deleted, role-changed, admin and stylist identities fail closed', async () => {
  for (const user of [null, { id: USER, role: 'admin' }, { id: USER, role: 'stylist' }, { id: USER, role: 'staff' }]) {
    const response = await handleAiRequest(request('GET', 'features'), ['features'], deps(user));
    assert.equal(response.status, user ? 403 : 401);
  }
  assert.equal(seen.length, 0);
});

test('database/auth lookup errors fail closed', async () => {
  const config = deps();
  config.currentUser = async () => { throw new Error('database unavailable'); };
  assert.equal((await handleAiRequest(request('GET', 'features'), ['features'], config)).status, 503);
  assert.equal(seen.length, 0);
});

test('tampered, expired and cross-user consultation handles cannot reach upstream', async () => {
  const valid = await handle();
  const expired = await handle(USER, '2026-10-02T09:59:59.000Z').catch(() => null);
  assert.equal(expired, null);
  const old = await handle(USER, '2026-10-02T10:00:10.000Z');
  for (const [token, user] of [[valid.slice(0, -2) + 'xx', USER], [valid, 'client-2'], [old, USER]] as const) {
    const config = deps({ id: user, role: 'client' });
    if (token === old) config.now = () => NOW + 11_000;
    const response = await handleAiRequest(request('GET', 'consultations/state', undefined, token),
      ['consultations', 'state'], config);
    assert.equal(response.status, 403);
  }
  assert.equal(seen.length, 0);
});

test('missing handle and raw upstream IDs or arbitrary proxy routes cannot be supplied', async () => {
  assert.equal((await handleAiRequest(request('GET', 'consultations/state'), ['consultations', 'state'], deps())).status, 403);
  for (const parts of [
    ['consultations', ID], ['consultations', ID, 'photo'], ['proxy', 'http://evil'],
    ['features', 'hairstyle', 'delete'], ['features', 'unknown', 'generate'],
  ]) {
    const response = await handleAiRequest(request('GET', parts.join('/')), parts, deps());
    assert.equal(response.status, 404);
  }
  assert.equal(seen.length, 0);
});

test('only allowlisted methods and routes forward and mutations require same origin', async () => {
  assert.equal((await handleAiRequest(request('POST', 'mode'), ['mode'], deps())).status, 404);
  assert.equal((await handleAiRequest(request('DELETE', 'features'), ['features'], deps())).status, 404);
  assert.equal((await handleAiRequest(request('POST', 'consultations', '{}', undefined, 'https://evil.example'),
    ['consultations'], deps())).status, 403);
  assert.equal(seen.length, 0);
});

test('consultation state, photo, preferences, turn and recommendations preserve fixed paths', async () => {
  const token = await handle();
  const calls: [string, string[], BodyInit | undefined, string][] = [
    ['GET', ['consultations', 'state'], undefined, '/consultations/' + ID],
    ['PATCH', ['consultations', 'state'], JSON.stringify({ preferences: { occasion: 'graduation' } }), '/consultations/' + ID],
    ['PUT', ['consultations', 'photo'], image('image/jpeg'), '/consultations/' + ID + '/photo'],
    ['POST', ['consultations', 'turn'], JSON.stringify({ message: 'I want a clean look' }), '/consultations/' + ID + '/turn'],
    ['POST', ['consultations', 'recommendations'], undefined, '/consultations/' + ID + '/recommendations'],
  ];
  for (const [method, parts, body, expected] of calls) {
    const response = await handleAiRequest(request(method, parts.join('/'), body, token), parts, deps());
    assert.equal(response.status, 200);
    assert.equal(new URL(seen.at(-1)!.url).pathname, expected);
    const payload = await response.json();
    assert.equal(payload.id, undefined);
    if (parts.at(-1) === 'turn') assert.equal(payload.state.id, undefined);
  }
  const recommendations = await (await handleAiRequest(request('POST', 'consultations/recommendations', undefined, token),
    ['consultations', 'recommendations'], deps())).json();
  assert.equal(recommendations.recommendations.length, 3);
});

test('generation, status and Select relay individually; no automatic generation retry', async () => {
  const token = await handle();
  const base = ['consultations', 'recommendations', 'look-1'];
  for (const [method, leaf] of [['POST', 'generation'], ['GET', 'generation'], ['POST', 'select']] as const) {
    const parts = [...base, leaf];
    const response = await handleAiRequest(request(method, parts.join('/'), undefined, token), parts, deps());
    assert.equal(response.status, 200);
    assert.equal(new URL(seen.at(-1)!.url).pathname, '/consultations/' + ID + '/recommendations/look-1/' + leaf);
  }
  assert.equal(seen.length, 3);
});

test('manual feature list/styles/generation use same client authorization', async () => {
  assert.equal((await handleAiRequest(request('GET', 'features'), ['features'], deps())).status, 200);
  for (const feature of ['hairstyle', 'makeup', 'nails']) {
    assert.equal((await handleAiRequest(request('GET', 'features/' + feature + '/styles'),
      ['features', feature, 'styles'], deps())).status, 200);
    const form = image('image/png');
    form.append('style_id', 'supported_style');
    assert.equal((await handleAiRequest(request('POST', 'features/' + feature + '/generate', form),
      ['features', feature, 'generate'], deps())).status, 200);
  }
  assert.equal(seen.length, 7);
  const response = await handleAiRequest(request('GET', 'features'), ['features'], deps({ id: 'admin', role: 'admin' }));
  assert.equal(response.status, 403);
  assert.equal(seen.length, 7);
});

test('JPEG and PNG uploads forward raw File multipart without database persistence or data URLs', async () => {
  const token = await handle();
  for (const mime of ['image/jpeg', 'image/png']) {
    const form = image(mime);
    const response = await handleAiRequest(request('PUT', 'consultations/photo', form, token),
      ['consultations', 'photo'], deps());
    assert.equal(response.status, 200);
    assert.ok(seen.at(-1)!.body instanceof FormData);
    const forwarded = (seen.at(-1)!.body as FormData).get('image');
    assert.ok(forwarded instanceof File);
    assert.equal(forwarded.type, mime);
    assert.equal(forwarded.size, 4);
  }
});

test('WebP, empty and oversized uploads are rejected before FastAPI', async () => {
  const token = await handle();
  for (const [form, status] of [
    [image('image/webp'), 415], [image('image/jpeg', 0), 400], [image('image/png', 8 * 1024 * 1024 + 1), 413],
  ] as const) {
    assert.equal((await handleAiRequest(request('PUT', 'consultations/photo', form, token),
      ['consultations', 'photo'], deps())).status, status);
  }
  assert.equal(seen.length, 0);
});

test('upstream status and invalid responses are controlled without exposing upstream body', async () => {
  for (const [upstream, expected] of [
    [new Response('private model path', { status: 422 }), 422],
    [new Response('private stack trace', { status: 500 }), 502],
    [new Response('<html>bad gateway</html>', { status: 200, headers: { 'content-type': 'text/html' } }), 502],
  ] as const) {
    const response = await handleAiRequest(request('GET', 'features'), ['features'], deps(undefined, () => upstream));
    assert.equal(response.status, expected);
    assert.equal((await response.text()).includes('private'), false);
  }
});

test('ambiguous transport disconnect and timeout do not retry', async () => {
  for (const [error, status] of [[new TypeError('secret transport URL'), 502], [Object.assign(new Error('timeout'), { name: 'AbortError' }), 504]] as const) {
    let attempts = 0;
    const config = deps();
    config.upstreamFetch = async () => { attempts++; throw error; };
    const response = await handleAiRequest(request('GET', 'features'), ['features'], config);
    assert.equal(response.status, status);
    assert.equal(attempts, 1);
    assert.equal((await response.text()).includes('secret'), false);
  }
});

test('invalid local configuration cannot reach arbitrary host or disclose secrets', async () => {
  for (const url of ['https://evil.example/', 'http://user:pass@127.0.0.1:8000/', 'http://127.0.0.1:8000/private']) {
    const config = deps();
    config.baseUrl = url;
    assert.equal((await handleAiRequest(request('GET', 'features'), ['features'], config)).status, 503);
  }
  assert.equal(seen.length, 0);
});
