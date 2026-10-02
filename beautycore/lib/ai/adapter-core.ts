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
    const url = new URL(value);
    if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) ||
        url.username || url.password || url.search || url.hash || url.pathname !== '/') return null;
    return url;
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
  let upstream: Response;
  try {
    upstream = await deps.upstreamFetch(new URL(upstreamPath, base), {
      method: request.method,
      headers,
      body,
      cache: 'no-store',
      redirect: 'error',
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') return json(504, 'AI service timed out. Check generation status before retrying.');
    return json(502, 'AI service is unavailable. Check generation status before retrying.');
  }
  if (!upstream.ok) {
    const allowed = new Set([400, 401, 403, 404, 409, 413, 415, 422, 429, 502, 503, 504]);
    const status = allowed.has(upstream.status) ? upstream.status : 502;
    return json(status, status < 500 ? 'AI request could not be completed.' : 'AI service could not complete the request.');
  }
  if (!upstream.headers.get('content-type')?.toLowerCase().includes('application/json'))
    return json(502, 'AI service returned an invalid response.');
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
