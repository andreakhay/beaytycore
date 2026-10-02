import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ClientAiConsultationPage from '../app/client/ai-consultation/page';
import {
  AiClientError, createConsultation, generateCustom, generateRecommendation, getGenerationStatus,
  getMode, getRecommendations, getStyles, selectRecommendation, sendTurn, uploadPhoto,
  type GenerationDetail, type Recommendation,
} from '../lib/ai/browser-client';
import { applyGenerationDetail, generateOne, generateSequential, initialCards } from '../lib/ai/consultation-flow';

const ID = '4d321734-0990-4511-a119-0a45796a267b';
const HANDLE = 'signed-browser-handle';
const image = { data_url: 'data:image/png;base64,AA==', content_type: 'image/png', width: 256, height: 256 };
const service = { name: 'Hair', estimated_price: 100, estimated_duration_minutes: 30, currency: 'PHP', estimate_kind: 'demo_only' };
const rows: Recommendation[] = [1, 2, 3].map((n) => ({
  id: 'look-' + n, primary: { feature: 'hairstyle', style_id: 'crew_cut', style_name: 'Crew Cut', service, nail_path: null },
  reason: 'Matches your simple direction.', complements: [],
}));
const state = {
  id: ID, primary_service: 'hairstyle', stage: 'collecting', conversation_status: 'not_started',
  photo: null, messages: [], recommendations: null,
  generations: rows.map((row) => ({ recommendation_id: row.id, status: 'pending', error: null, attempts: 0, result_available: false })),
  selected_recommendation_id: null,
};
const completed = (id: string): GenerationDetail => ({
  generation: { recommendation_id: id, status: 'completed', attempts: 1, error: null, result_available: true },
  result: { status: 'completed', style: { id: 'crew_cut', name: 'Crew Cut', status: 'available', description: '' }, image },
});
const failed = (id: string): GenerationDetail => ({
  generation: { recommendation_id: id, status: 'failed', attempts: 1, error: 'Could not generate.', result_available: false },
  result: null,
});

test('initial Client page shows service step only, with all three choices', () => {
  const html = renderToStaticMarkup(React.createElement(ClientAiConsultationPage));
  for (const name of ['Hairstyle', 'Makeup', 'Nails', 'CHOOSE A SERVICE', 'Continue']) assert.ok(html.includes(name));
  assert.ok(!html.includes('Upload a photo'));
  assert.ok(!html.includes('Generate My Looks'));
});

test('same-origin client keeps only signed handle, never uses raw upstream ID as a route', async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init: init || {} });
    if (url === '/api/ai/consultations') return Response.json({ ...state, handle: HANDLE }, { status: 201 });
    if (url === '/api/ai/consultations/photo') return Response.json({ ...state, photo: { content_type: 'image/png', width: 256, height: 256 } });
    if (url === '/api/ai/consultations/turn') return Response.json({ state, status: 'ready_for_recommendation', assistant_message: 'Ready', recommendations: { recommendations: rows } });
    if (url === '/api/ai/consultations/recommendations') return Response.json({ recommendations: rows });
    if (String(url).endsWith('/generation')) return Response.json(completed('look-1'));
    if (String(url).endsWith('/select')) return Response.json({ ...state, selected_recommendation_id: 'look-1' });
    return Response.json({ provider: 'gemini', model: 'configured-server-side' });
  };
  try {
    assert.equal(await getMode(), 'gemini');
    const created = await createConsultation('hairstyle');
    assert.deepEqual(Object.keys(created), ['handle', 'state']);
    assert.equal('id' in created.state, false);
    assert.equal(created.handle, HANDLE);
    const file = new File([new Uint8Array([1, 2])], 'portrait.png', { type: 'image/png' });
    await uploadPhoto(HANDLE, file);
    const turn = await sendTurn(HANDLE, 'Clean graduation look');
    assert.equal(turn.recommendations?.length, 3);
    assert.equal((await getRecommendations(HANDLE)).length, 3);
    assert.equal((await generateRecommendation(HANDLE, 'look-1')).generation.status, 'completed');
    assert.equal((await getGenerationStatus(HANDLE, 'look-1')).generation.status, 'completed');
    assert.equal((await selectRecommendation(HANDLE, 'look-1')).selected_recommendation_id, 'look-1');
    assert.ok(calls.every((call) => call.url.startsWith('/api/ai/') && !call.url.includes(ID)));
    assert.ok(calls.filter((call) => call.url.includes('/consultations/') && call.url !== '/api/ai/consultations')
      .every((call) => new Headers(call.init.headers).get('x-ai-consultation-handle') === HANDLE));
  } finally { globalThis.fetch = original; }
});

test('three primary looks generate serially and reveal each completed result', async () => {
  const events: string[] = [];
  let active = 0;
  const cards = initialCards(rows);
  const updates: string[] = [];
  const outcome = await generateSequential(cards, {
    generate: async (id) => { assert.equal(active, 0); active++; events.push(id); active--; return completed(id); },
    status: async () => { throw new Error('Unexpected status call'); },
    wait: async () => {},
  }, (card) => { updates.push(card.recommendation.id + ':' + card.status); });
  assert.equal(outcome, 'settled');
  assert.deepEqual(events, ['look-1', 'look-2', 'look-3']);
  assert.deepEqual(updates.filter((row) => row.endsWith('completed')), events.map((id) => id + ':completed'));
});

test('one failed look does not erase successful siblings or trigger automatic retry', async () => {
  const events: string[] = [];
  const cards = initialCards(rows);
  const current = new Map(cards.map((card) => [card.recommendation.id, card]));
  await generateSequential(cards, {
    generate: async (id) => { events.push(id); return id === 'look-2' ? failed(id) : completed(id); },
    status: async () => { throw new Error('Unexpected status call'); }, wait: async () => {},
  }, (card) => current.set(card.recommendation.id, card));
  assert.deepEqual(events, ['look-1', 'look-2', 'look-3']);
  assert.equal(current.get('look-1')?.status, 'completed');
  assert.equal(current.get('look-2')?.status, 'failed');
  assert.equal(current.get('look-2')?.canRetry, true);
  assert.equal(current.get('look-3')?.status, 'completed');
});

test('ambiguous disconnect performs status GET before permitting a manual retry', async () => {
  const events: string[] = [];
  let last = initialCards(rows)[0];
  const outcome = await generateOne(last, {
    generate: async () => { events.push('POST'); throw new AiClientError('connection lost', 502, true); },
    status: async (id) => { events.push('GET'); return {
      generation: { recommendation_id: id, status: 'pending', attempts: 0, error: null, result_available: false }, result: null,
    }; },
    wait: async () => {},
  }, (card) => { last = card; });
  assert.equal(outcome, 'settled');
  assert.deepEqual(events, ['POST', 'GET']);
  assert.equal(last.status, 'failed');
  assert.equal(last.canRetry, true);
});

test('uncertain in-flight work blocks the next look and cannot automatically retry', async () => {
  const events: string[] = [];
  const result = await generateSequential(initialCards(rows), {
    generate: async (id) => { events.push('POST ' + id); throw new AiClientError('disconnected', 502, true); },
    status: async (id) => { events.push('GET ' + id); return {
      generation: { recommendation_id: id, status: 'generating', attempts: 1, error: null, result_available: false }, result: null,
    }; },
    wait: async () => {},
  }, () => {});
  assert.equal(result, 'unknown');
  assert.deepEqual(events[0], 'POST look-1');
  assert.equal(events.some((event) => event.startsWith('POST look-2')), false);
});

test('manual retry is one user-requested POST and result promotion does not generate', async () => {
  const card = { ...initialCards(rows)[1], status: 'failed' as const, canRetry: true };
  let posts = 0;
  let current: ReturnType<typeof initialCards>[number] = card;
  await generateOne(card, { generate: async (id) => { posts++; return completed(id); },
    status: async () => { throw new Error('No status needed'); }, wait: async () => {} },
  (updated) => { current = updated; });
  assert.equal(posts, 1);
  assert.equal(current.status, 'completed');
  assert.equal(applyGenerationDetail(current, completed('look-2')).status, 'completed');
  assert.equal(posts, 1);
});

test('Hair, Makeup and Nails Custom use the same BeautyCore adapter', async () => {
  const calls: string[] = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url) => {
    calls.push(String(url));
    if (String(url).endsWith('/styles')) return Response.json([{ id: 'style_1', name: 'Style', description: '', status: 'available' }]);
    return Response.json({ status: 'completed', style: { id: 'style_1', name: 'Style', description: '', status: 'available' }, image });
  };
  try {
    const file = new File([new Uint8Array([1])], 'photo.jpg', { type: 'image/jpeg' });
    for (const feature of ['hairstyle', 'makeup', 'nails'] as const) {
      assert.equal((await getStyles(feature)).length, 1);
      assert.equal((await generateCustom(feature, file, 'style_1')).status, 'completed');
    }
    assert.ok(calls.every((path) => path.startsWith('/api/ai/features/')));
  } finally { globalThis.fetch = original; }
});

test('malformed recommendations fail safely', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ recommendations: null });
  try { await assert.rejects(getRecommendations(HANDLE), AiClientError); }
  finally { globalThis.fetch = original; }
});
