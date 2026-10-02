import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import ConsultationPage from '../app/client/ai-consultation/page';
import HairPage from '../app/client/hair-studio/page';
import MakeupPage from '../app/client/makeup-studio/page';
import NailsPage from '../app/client/nail-studio/page';
import { createConsultation, uploadConsultationPhoto } from '../lib/ai/studio-consultation-api';
import { generate, getStyles } from '../lib/ai/studio-api';
import { rememberCustomPhoto, takeCustomPhoto } from '../lib/ai/studio-photo-handoff';

test('the imported AI studio presents all four real Client destinations', () => {
  const pages = [
    { Page: ConsultationPage, current: '/client/ai-consultation' },
    { Page: HairPage, current: '/client/hair-studio' },
    { Page: MakeupPage, current: '/client/makeup-studio' },
    { Page: NailsPage, current: '/client/nail-studio' },
  ];
  for (const { Page, current } of pages) {
    const html = renderToStaticMarkup(React.createElement(Page));
    for (const route of ['/client/ai-consultation', '/client/hair-studio',
      '/client/makeup-studio', '/client/nail-studio'].filter((route) => route !== current))
      assert.ok(html.includes(route));
    assert.ok(html.includes('studio-page'));
    assert.equal(html.includes('/client/ai-advisor'), false);
  }
});

test('manual Hair, Makeup and Nails generation uses only the secure Client adapter', async () => {
  const calls: { url: string; method: string }[] = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    calls.push({ url: String(input), method: init?.method || 'GET' });
    if (String(input).endsWith('/styles'))
      return Response.json([{ id: 'approved', name: 'Approved', description: '', status: 'available' }]);
    return Response.json({ status: 'completed', style: { id: 'approved', name: 'Approved',
      description: '', status: 'available' }, image: { data_url: 'data:image/png;base64,AA==',
      content_type: 'image/png', width: 2, height: 2 } });
  };
  try {
    const photo = new File([new Uint8Array([1])], 'photo.png', { type: 'image/png' });
    for (const feature of ['hairstyle', 'makeup', 'nails'] as const) {
      assert.equal((await getStyles(feature))[0].id, 'approved');
      assert.equal((await generate(feature, photo, 'approved')).status, 'completed');
    }
    assert.deepEqual(calls.map((call) => call.method), ['GET', 'POST', 'GET', 'POST', 'GET', 'POST']);
    assert.ok(calls.every(({ url }) => url.startsWith('/api/ai/features/')));
  } finally { globalThis.fetch = before; }
});

test('the original consultation UI receives only a signed handle and reuses one photo for Custom', async () => {
  const calls: { url: string; handle: string | null }[] = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    calls.push({ url: String(input), handle: new Headers(init?.headers).get('x-ai-consultation-handle') });
    return Response.json({ primary_service: 'nails', stage: 'collecting', conversation_status: 'not_started',
      photo: null, messages: [], recommendations: null, generations: [],
      selected_recommendation_id: null, handle: 'signed-client-handle' });
  };
  try {
    const created = await createConsultation('nails');
    assert.equal(created.id, 'signed-client-handle');
    const photo = new File([new Uint8Array([1])], 'hand.jpg', { type: 'image/jpeg' });
    await uploadConsultationPhoto(created.id, photo);
    rememberCustomPhoto('nails', photo);
    assert.equal(takeCustomPhoto('nails'), photo);
    assert.equal(takeCustomPhoto('nails'), null);
    assert.deepEqual(calls.map(({ url }) => url), ['/api/ai/consultations', '/api/ai/consultations/photo']);
    assert.deepEqual(calls.map(({ handle }) => handle), [null, created.id]);
    assert.equal(calls.some(({ url }) => url.includes('127.0.0.1:8000')), false);
  } finally { globalThis.fetch = before; }
});
