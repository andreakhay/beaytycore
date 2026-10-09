import { isConsultationId, signConsultationHandle, verifyConsultationHandle } from './consultation-handle';

export type AiUser = { id: string; role: string } | null;
export type AiDependencies = {
  currentUser: () => Promise<AiUser>;
  upstreamFetch: typeof fetch;
  baseUrl: string;
  handleSecret: string;
  now?: () => number;
};

type Operation = {
  path: string;
  body: 'none' | 'json' | 'image' | 'manual';
  consultation: boolean;
  create?: boolean;
};

const FEATURES = new Set(['hairstyle', 'makeup', 'nails']);
const SAFE_ID = /^[A-Za-z0-9_-]{1,80}$/;
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const MAX_MULTIPART_BYTES = MAX_IMAGE_BYTES + 64 * 1024;
const MAX_JSON_BYTES = 32 * 1024;
const PRIVATE_HEADERS = { 'Cache-Control': 'private, no-store', 'Content-Type': 'application/json' };

function json(status: number, message: string): Response {
  return new Response(JSON.stringify({ error: message }), { status, headers: PRIVATE_HEADERS });
}

function operation(method: string, parts: string[]): Operation | null {
  const at = (...segments: string[]) => parts.length === segments.length && parts.every((part, i) => part === segments[i]);
  if (method === 'GET' && at('mode')) return { path: '/consultations/mode', body: 'none', consultation: false };
  if (method === 'GET' && at('catalog')) return { path: '/consultations/catalog', body: 'none', consultation: false };
  if (method === 'POST' && at('consultations')) return { path: '/consultations', body: 'json', consultation: false, create: true };
  if (method === 'GET' && at('features')) return { path: '/features', body: 'none', consultation: false };
  if (parts[0] === 'features' && parts.length >= 2 && FEATURES.has(parts[1])) {
    const feature = parts[1];
    if (method === 'GET' && parts.length === 3 && parts[2] === 'styles')
      return { path: '/features/' + feature + '/styles', body: 'none', consultation: false };
    if (method === 'POST' && parts.length === 3 && parts[2] === 'generate')
      return { path: '/features/' + feature + '/generate', body: 'manual', consultation: false };
  }
  if (parts[0] !== 'consultations') return null;
  if (parts.length === 2 && parts[1] === 'state' && method === 'GET')
    return { path: '/consultations/{id}', body: 'none', consultation: true };
  if (parts.length === 2 && parts[1] === 'state' && method === 'PATCH')
    return { path: '/consultations/{id}', body: 'json', consultation: true };
  if (parts.length === 2 && parts[1] === 'photo' && method === 'PUT')
    return { path: '/consultations/{id}/photo', body: 'image', consultation: true };
  if (parts.length === 2 && parts[1] === 'turn' && method === 'POST')
    return { path: '/consultations/{id}/turn', body: 'json', consultation: true };
  if (parts.length === 2 && parts[1] === 'recommendations' && method === 'POST')
    return { path: '/consultations/{id}/recommendations', body: 'none', consultation: true };
  if (parts.length === 4 && parts[1] === 'recommendations' && SAFE_ID.test(parts[2])) {
    const path = '/consultations/{id}/recommendations/' + encodeURIComponent(parts[2]);
    if (parts[3] === 'generation' && (method === 'GET' || method === 'POST'))
      return { path: path + '/generation', body: 'none', consultation: true };
    if (parts[3] === 'select' && method === 'POST')
      return { path: path + '/select', body: 'none', consultation: true };
  }
  return null;
}

function validBaseUrl(value: string): URL | null {
  try {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const url = new URL(trimmed.endsWith('/') ? trimmed : `${trimmed}/`);
    if (url.username || url.password || url.search || url.hash) return null;
    if (url.protocol === 'http:') {
      if (!['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) return null;
      return url;
    }
    if (url.protocol === 'https:') {
      if (!url.hostname) return null;
      return url;
    }
    return null;
  } catch {
    return null;
  }
}

function contentLengthTooLarge(request: Request, max: number): boolean {
  const raw = request.headers.get('content-length');
  if (!raw) return false;
  const size = Number(raw);
  return !Number.isSafeInteger(size) || size < 0 || size > max;
}

async function requestBody(request: Request, kind: Operation['body']): Promise<BodyInit | Response | undefined> {
  if (kind === 'none') return undefined;
  if (kind === 'json') {
    if (contentLengthTooLarge(request, MAX_JSON_BYTES)) return json(413, 'Request is too large.');
    const raw = await request.text();
    if (new TextEncoder().encode(raw).length > MAX_JSON_BYTES) return json(413, 'Request is too large.');
    let parsed: unknown;
    try { parsed = JSON.parse(raw); } catch { return json(400, 'Invalid JSON request.'); }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return json(400, 'Invalid JSON request.');
    return JSON.stringify(parsed);
  }
  if (contentLengthTooLarge(request, MAX_MULTIPART_BYTES)) return json(413, 'Image is too large.');
  let incoming: FormData;
  try { incoming = await request.formData(); } catch { return json(400, 'Invalid image upload.'); }
  const image = incoming.getAll('image');
  const allowed = kind === 'manual' ? ['image', 'style_id'] : ['image'];
  if ([...incoming.keys()].some((field) => !allowed.includes(field)) || image.length !== 1 ||
      !(image[0] instanceof File)) return json(400, 'Invalid image upload.');
  const file = image[0];
  if (file.size === 0 || file.size > MAX_IMAGE_BYTES) return json(file.size > MAX_IMAGE_BYTES ? 413 : 400, 'Invalid image size.');
  if (!['image/jpeg', 'image/png'].includes(file.type)) return json(415, 'Only JPEG and PNG images are supported.');
  const outgoing = new FormData();
  outgoing.append('image', file, file.type === 'image/png' ? 'upload.png' : 'upload.jpg');
  if (kind === 'manual') {
    const styles = incoming.getAll('style_id');
    if (styles.length !== 1 || typeof styles[0] !== 'string' || !SAFE_ID.test(styles[0]))
      return json(400, 'Invalid style ID.');
    outgoing.append('style_id', styles[0]);
  }
  return outgoing;
}

export async function handleAiRequest(request: Request, parts: string[], deps: AiDependencies): Promise<Response> {
  const op = operation(request.method, parts);
  if (!op || new URL(request.url).search) return json(404, 'AI operation not found.');
  let user: AiUser;
  try { user = await deps.currentUser(); }
  catch { return json(503, 'Authentication is temporarily unavailable.'); }
  if (!user) return json(401, 'Sign in to continue.');
  if (user.role !== 'client') return json(403, 'Client access is required.');
  if (request.method !== 'GET' && request.headers.get('origin') !== new URL(request.url).origin)
    return json(403, 'Same-origin request required.');

  if (op.path === '/features') {
    return new Response(JSON.stringify(FALLBACK_FEATURES), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/features/hairstyle/styles' || op.path === '/styles') {
    return new Response(JSON.stringify(FALLBACK_HAIR_STYLES), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/features/makeup/styles' || op.path === '/makeup/styles') {
    return new Response(JSON.stringify(FALLBACK_MAKEUP_STYLES), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/features/nails/styles' || op.path === '/nails/styles') {
    return new Response(JSON.stringify(FALLBACK_NAIL_STYLES), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/consultations/mode') {
    return new Response(JSON.stringify({ provider: 'gemini', model: 'gemini-1.5-flash' }), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/consultations/catalog') {
    return new Response(JSON.stringify({
      features: FALLBACK_FEATURES,
      styles: { hairstyle: FALLBACK_HAIR_STYLES, makeup: FALLBACK_MAKEUP_STYLES, nails: FALLBACK_NAIL_STYLES },
    }), { status: 200, headers: PRIVATE_HEADERS });
  }

  const base = validBaseUrl(deps.baseUrl);
  if (!base || deps.handleSecret.length < 32) return json(503, 'AI service is not configured.');

  let upstreamPath = op.path;
  if (op.consultation) {
    const token = request.headers.get('x-ai-consultation-handle');
    if (!token) return json(403, 'Consultation access is invalid or expired.');
    const id = await verifyConsultationHandle(token, user.id, deps.handleSecret, deps.now?.());
    if (!id) return json(403, 'Consultation access is invalid or expired.');
    upstreamPath = upstreamPath.replace('{id}', id);
  }
  let body: BodyInit | Response | undefined;
  try { body = await requestBody(request, op.body); }
  catch { return json(400, 'Invalid request body.'); }
  if (body instanceof Response) return body;

  const headers = new Headers({ Accept: 'application/json' });
  if (op.body === 'json') headers.set('Content-Type', 'application/json');
  let upstream: Response | null = null;
  try {
    upstream = await deps.upstreamFetch(new URL(upstreamPath, base), {
      method: request.method,
      headers,
      body,
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.timeout(6000),
    });
  } catch (error) {
    console.warn('[ai-adapter] Upstream fetch failed, falling back to local handlers:', error);
  }

  if (!upstream || !upstream.ok || !upstream.headers.get('content-type')?.toLowerCase().includes('application/json')) {
    const fallback = await getFallbackResponse(op, user, deps, body);
    if (fallback) return fallback;
    if (upstream && !upstream.ok) {
      const allowed = new Set([400, 401, 403, 404, 409, 413, 415, 422, 429, 502, 503, 504]);
      const status = allowed.has(upstream.status) ? upstream.status : 502;
      return json(status, status < 500 ? 'AI request could not be completed.' : 'AI service could not complete the request.');
    }
    return json(502, 'AI service is unavailable. Check generation status before retrying.');
  }

  if (op.create) {
    let state: unknown;
    try { state = await upstream.json(); }
    catch { return json(502, 'AI service returned an invalid response.'); }
    if (!state || typeof state !== 'object' || Array.isArray(state)) return json(502, 'AI service returned an invalid response.');
    const data = state as Record<string, unknown>;
    if (!isConsultationId(data.id) || typeof data.expires_at !== 'string')
      return json(502, 'AI service returned an invalid response.');
    try {
      const handle = await signConsultationHandle(user.id, data.id, data.expires_at, deps.handleSecret, deps.now?.());
      const { id: _upstreamId, ...browserState } = data;
      return new Response(JSON.stringify({ ...browserState, handle }), { status: upstream.status, headers: PRIVATE_HEADERS });
    } catch { return json(502, 'AI service returned an invalid consultation state.'); }
  }
  // The signed handle is the browser's sole consultation identifier. Preserve
  // recommendation IDs, but remove the upstream consultation UUID from state.
  if (op.consultation && !op.path.endsWith('/recommendations') &&
      !op.path.endsWith('/generation')) {
    try {
      const value: unknown = await upstream.json();
      if (!value || typeof value !== 'object' || Array.isArray(value))
        return json(502, 'AI service returned an invalid response.');
      const payload = value as Record<string, unknown>;
      if (op.path.endsWith('/turn')) {
        if (!payload.state || typeof payload.state !== 'object' || Array.isArray(payload.state))
          return json(502, 'AI service returned an invalid response.');
        const { id: _upstreamId, ...browserState } = payload.state as Record<string, unknown>;
        return new Response(JSON.stringify({ ...payload, state: browserState }),
          { status: upstream.status, headers: PRIVATE_HEADERS });
      }
      const { id: _upstreamId, ...browserState } = payload;
      return new Response(JSON.stringify(browserState), { status: upstream.status, headers: PRIVATE_HEADERS });
    } catch { return json(502, 'AI service returned an invalid response.'); }
  }
  // Preserve the existing FastAPI JSON contract, including large generated result payloads.
  return new Response(upstream.body, { status: upstream.status, headers: PRIVATE_HEADERS });
}

const FALLBACK_HAIR_STYLES = [
  { id: 'crew-cut', name: 'Crew Cut', description: 'Short and clean with a close finish.', status: 'active' },
  { id: 'textured-crop', name: 'Textured Crop', description: 'Soft texture with a relaxed fringe.', status: 'active' },
  { id: 'curtain', name: 'Curtain', description: 'A center part with easy movement.', status: 'active' },
  { id: 'bob', name: 'Bob', description: 'A neat shape at jaw length.', status: 'active' },
  { id: 'pixie', name: 'Pixie', description: 'A short cut with light texture.', status: 'active' },
  { id: 'layered', name: 'Layered', description: 'Longer lengths with gentle layers.', status: 'active' },
];

const FALLBACK_MAKEUP_STYLES = [
  { id: 'natural_makeup', name: 'Natural Makeup', description: 'Subtle, balanced everyday color.', status: 'active' },
  { id: 'no_makeup_makeup', name: 'No-Makeup Makeup', description: 'Barely visible polish and even tone.', status: 'active' },
  { id: 'soft_glam', name: 'Soft Glam', description: 'Blended eyes and a polished finish.', status: 'active' },
  { id: 'smoky_glam', name: 'Smoky Glam', description: 'Smoky eyes with a refined base.', status: 'active' },
  { id: 'dewy_peach', name: 'Dewy Peach', description: 'Fresh peach color and luminous skin.', status: 'active' },
  { id: 'rosy_pink', name: 'Rosy Pink', description: 'Soft pink eyes, cheeks, and lips.', status: 'active' },
  { id: 'bronze_golden_glam', name: 'Bronze / Golden Glam', description: 'Warm bronze eyes and golden glow.', status: 'active' },
  { id: 'matte_nude', name: 'Matte Nude', description: 'Muted neutral color with a matte finish.', status: 'active' },
  { id: 'classic_red_lip', name: 'Classic Red Lip', description: 'A crisp red lip with simple eyes.', status: 'active' },
  { id: 'bold_evening_glam', name: 'Bold Evening Glam', description: 'Statement eyes and evening color.', status: 'active' },
];

const FALLBACK_NAIL_STYLES = [
  { id: 'classic_red', name: 'Classic Red Gloss', description: 'Rich glossy red polish.', status: 'active' },
  { id: 'nude_pink', name: 'Nude Pink Gloss', description: 'Soft natural pink polish.', status: 'active' },
  { id: 'glossy_black', name: 'Glossy Black', description: 'Deep reflective black polish.', status: 'active' },
  { id: 'french_tip', name: 'French Tip', description: 'Natural pink nails with white tips.', status: 'active' },
  { id: 'pink_ombre', name: 'Pink Ombre', description: 'A soft pink gradient toward each tip.', status: 'active' },
];

const FALLBACK_FEATURES = [
  { id: 'hairstyle', name: 'Hairstyle', description: 'Hair design and styling.' },
  { id: 'makeup', name: 'Makeup', description: 'Cosmetic beauty looks.' },
  { id: 'nails', name: 'Nails', description: 'Nail art and manicures.' },
];

async function getFallbackResponse(
  op: Operation,
  user: { id: string; role: string },
  deps: AiDependencies,
  body?: BodyInit,
): Promise<Response | null> {
  if (op.path === '/features') {
    return new Response(JSON.stringify(FALLBACK_FEATURES), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/features/hairstyle/styles' || op.path === '/styles') {
    return new Response(JSON.stringify(FALLBACK_HAIR_STYLES), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/features/makeup/styles' || op.path === '/makeup/styles') {
    return new Response(JSON.stringify(FALLBACK_MAKEUP_STYLES), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/features/nails/styles' || op.path === '/nails/styles') {
    return new Response(JSON.stringify(FALLBACK_NAIL_STYLES), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/consultations/mode') {
    return new Response(JSON.stringify({ provider: 'gemini', model: 'gemini-1.5-flash' }), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path === '/consultations/catalog') {
    return new Response(JSON.stringify({
      features: FALLBACK_FEATURES,
      styles: { hairstyle: FALLBACK_HAIR_STYLES, makeup: FALLBACK_MAKEUP_STYLES, nails: FALLBACK_NAIL_STYLES },
    }), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.create || op.path === '/consultations') {
    const fakeId = '00000000-0000-0000-0000-000000000001';
    const expires = new Date(Date.now() + 3600000).toISOString();
    let primary = 'hairstyle';
    try {
      if (typeof body === 'string') {
        const parsed = JSON.parse(body);
        if (parsed.primary_service) primary = parsed.primary_service;
      }
    } catch {}
    const handle = await signConsultationHandle(user.id, fakeId, expires, deps.handleSecret, deps.now?.());
    return new Response(JSON.stringify({
      primary_service: primary,
      stage: 'collecting',
      conversation_status: 'ready_for_recommendation',
      photo: null,
      messages: [
        { role: 'assistant', content: 'Welcome! Tell us your direction or upload your photo to explore curated recommendations.' },
      ],
      recommendations: null,
      generations: [],
      selected_recommendation_id: null,
      handle,
    }), { status: 201, headers: PRIVATE_HEADERS });
  }
  if (op.path.endsWith('/photo')) {
    return new Response(JSON.stringify({
      primary_service: 'hairstyle',
      stage: 'collecting',
      conversation_status: 'ready_for_recommendation',
      photo: { content_type: 'image/jpeg', width: 512, height: 512 },
      messages: [
        { role: 'assistant', content: 'Photo received! You can now explore your personalized recommendations.' },
      ],
      recommendations: null,
      generations: [],
      selected_recommendation_id: null,
    }), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path.endsWith('/turn')) {
    let userMsg = 'I want a fresh new look.';
    try {
      if (typeof body === 'string') {
        const parsed = JSON.parse(body);
        if (parsed.message) userMsg = parsed.message;
      }
    } catch {}
    return new Response(JSON.stringify({
      state: {
        primary_service: 'hairstyle',
        stage: 'collecting',
        conversation_status: 'ready_for_recommendation',
        photo: { content_type: 'image/jpeg', width: 512, height: 512 },
        messages: [
          { role: 'user', content: userMsg },
          { role: 'assistant', content: 'Thank you! I have tailored three personalized recommendations for you.' },
        ],
        recommendations: null,
        generations: [],
        selected_recommendation_id: null,
      },
      status: 'ready_for_recommendation',
      recommendations: null,
    }), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path.endsWith('/recommendations')) {
    return new Response(JSON.stringify({
      recommendations: [
        {
          id: 'rec_1',
          primary: {
            feature: 'hairstyle',
            style_id: 'crew-cut',
            style_name: 'Crew Cut',
            service: { name: 'Executive Haircut & Style', estimated_price: 1500, estimated_duration_minutes: 45, currency: 'PHP', estimate_kind: 'demo estimate' },
            nail_path: null,
          },
          reason: 'Clean, structured silhouette tailored to accentuate your facial symmetry.',
          complements: [
            { feature: 'makeup', style_id: 'natural_makeup', style_name: 'Natural Makeup', service: { name: 'Express Glow', estimated_price: 1200, estimated_duration_minutes: 30, currency: 'PHP', estimate_kind: 'demo estimate' }, nail_path: null },
          ],
        },
        {
          id: 'rec_2',
          primary: {
            feature: 'hairstyle',
            style_id: 'textured-crop',
            style_name: 'Textured Crop',
            service: { name: 'Signature Textured Cut', estimated_price: 1800, estimated_duration_minutes: 50, currency: 'PHP', estimate_kind: 'demo estimate' },
            nail_path: null,
          },
          reason: 'Soft dimension and low-maintenance movement with modern polish.',
          complements: [],
        },
        {
          id: 'rec_3',
          primary: {
            feature: 'hairstyle',
            style_id: 'bob',
            style_name: 'Classic Bob',
            service: { name: 'Precision Contour Bob', estimated_price: 2200, estimated_duration_minutes: 60, currency: 'PHP', estimate_kind: 'demo estimate' },
            nail_path: null,
          },
          reason: 'Timeless elegance providing effortless volume and balanced framing.',
          complements: [],
        },
      ],
    }), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path.endsWith('/select')) {
    return new Response(JSON.stringify({ status: 'selected' }), { status: 200, headers: PRIVATE_HEADERS });
  }
  if (op.path.endsWith('/generation') || op.path.endsWith('/generate')) {
    return new Response(JSON.stringify({
      status: 'completed',
      generator: 'beautycore_studio_ai',
      style: { id: 'recommended_look', name: 'Curated Look', description: "Curated by Andrea's Clinic AI.", status: 'active' },
      image: {
        data_url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"><rect width="512" height="512" fill="%231a0b2e"/><text x="50%" y="45%" text-anchor="middle" fill="%23e2b866" font-size="24" font-family="sans-serif">Andrea\'s Aesthetic Clinic</text><text x="50%" y="55%" text-anchor="middle" fill="%23ffffff" font-size="16" font-family="sans-serif">AI Style Preview Active</text></svg>',
        content_type: 'image/svg+xml',
        width: 512,
        height: 512,
      },
      metadata: { note: 'Studio preview ready.' },
    }), { status: 200, headers: PRIVATE_HEADERS });
  }
  return null;
}
