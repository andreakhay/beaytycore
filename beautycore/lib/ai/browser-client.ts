/** Same-origin browser contract. Upstream consultation IDs are deliberately discarded. */
export type FeatureId = 'hairstyle' | 'makeup' | 'nails';
export type AiStyle = { id: string; name: string; description: string; status: string };
export type Choice = {
  feature: FeatureId; style_id: string; style_name: string;
  service: { name: string; estimated_price: number; estimated_duration_minutes: number; currency: string; estimate_kind: string };
  nail_path: 'model' | 'renderer' | null;
};
export type Recommendation = { id: string; primary: Choice; reason: string; complements: Choice[] };
export type GenerationStatus = { recommendation_id: string; status: 'pending' | 'generating' | 'completed' | 'failed'; error: string | null; attempts: number; result_available: boolean };
export type GeneratedResult = { image: { data_url: string; content_type: string; width: number; height: number }; style: AiStyle; status: string };
export type GenerationDetail = { generation: GenerationStatus; result: GeneratedResult | null };
export type ConsultationView = {
  primary_service: FeatureId; stage: 'collecting' | 'recommended';
  conversation_status: 'not_started' | 'more_information' | 'ready_for_recommendation';
  photo: { content_type: string; width: number; height: number } | null;
  messages: { role: 'user' | 'assistant'; content: string }[];
  recommendations: { recommendations: Recommendation[] } | null;
  generations: GenerationStatus[];
  selected_recommendation_id: string | null;
};
export type Preferences = {
  occasion?: string; vibe?: string; avoids?: string[]; notes?: string;
  hair_maintenance?: 'low' | 'medium' | 'high';
  makeup_intensity?: 'natural' | 'soft' | 'bold';
  nail_finish?: 'glossy' | 'matte' | 'ombre' | 'french';
};

export class AiClientError extends Error {
  constructor(message: string, public readonly status: number, public readonly ambiguous = false) {
    super(message);
    this.name = 'AiClientError';
  }
}

function object(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}
function feature(value: unknown): value is FeatureId {
  return value === 'hairstyle' || value === 'makeup' || value === 'nails';
}
function recommendations(value: unknown): Recommendation[] {
  if (!object(value) || !Array.isArray(value.recommendations) || value.recommendations.length !== 3)
    throw new AiClientError('The recommendation response is incomplete.', 502);
  const rows = value.recommendations as Recommendation[];
  if (new Set(rows.map((row) => row.id)).size !== 3 ||
      rows.some((row) => !object(row) || typeof row.id !== 'string' || !object(row.primary) ||
        !feature(row.primary.feature) || typeof row.primary.style_id !== 'string' ||
        typeof row.primary.style_name !== 'string' || typeof row.reason !== 'string' ||
        !Array.isArray(row.complements) || !object(row.primary.service)))
    throw new AiClientError('The recommendation response is incomplete.', 502);
  return rows;
}
function state(value: unknown): ConsultationView {
  if (!object(value) || !feature(value.primary_service) ||
      !['collecting', 'recommended'].includes(String(value.stage)) ||
      !Array.isArray(value.messages) || !Array.isArray(value.generations))
    throw new AiClientError('The consultation response is incomplete.', 502);
  const selection = value.selected_recommendation_id;
  return {
    primary_service: value.primary_service,
    stage: value.stage as ConsultationView['stage'],
    conversation_status: value.conversation_status as ConsultationView['conversation_status'],
    photo: object(value.photo) ? {
      content_type: String(value.photo.content_type), width: Number(value.photo.width), height: Number(value.photo.height),
    } : null,
    messages: value.messages.filter(object).map((item) => ({
      role: item.role === 'assistant' ? 'assistant' as const : 'user' as const,
      content: String(item.content),
    })),
    recommendations: value.recommendations ? { recommendations: recommendations(value.recommendations) } : null,
    generations: value.generations as GenerationStatus[],
    selected_recommendation_id: typeof selection === 'string' ? selection : null,
  };
}
function detail(value: unknown): GenerationDetail {
  if (!object(value) || !object(value.generation) ||
      !['pending', 'generating', 'completed', 'failed'].includes(String(value.generation.status)))
    throw new AiClientError('The generation response is incomplete.', 502, true);
  if (value.result !== null && (!object(value.result) || !object(value.result.image) ||
      typeof value.result.image.data_url !== 'string' ||
      !/^data:image\/(png|jpeg);base64,/.test(value.result.image.data_url)))
    throw new AiClientError('The generated image response is invalid.', 502, true);
  return value as GenerationDetail;
}
async function request(path: string, init: RequestInit = {}, handle?: string): Promise<unknown> {
  const headers = new Headers(init.headers);
  if (handle) headers.set('x-ai-consultation-handle', handle);
  let response: Response;
  try {
    response = await fetch('/api/ai/' + path, { ...init, headers, cache: 'no-store' });
  } catch {
    throw new AiClientError('Connection interrupted. Check generation status before retrying.', 502, true);
  }
  if (!response.ok) {
    let message = 'The AI request could not be completed.';
    try {
      const error: unknown = await response.json();
      if (object(error) && typeof error.error === 'string') message = error.error;
    } catch { /* Never show upstream HTML or internal errors. */ }
    throw new AiClientError(message, response.status, response.status >= 500 || response.status === 429);
  }
  try { return await response.json(); }
  catch { throw new AiClientError('The AI response could not be read.', 502, true); }
}
function jsonBody(value: unknown): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) };
}
export async function getMode(): Promise<'gemini' | 'deterministic'> {
  const value = await request('mode');
  if (!object(value) || (value.provider !== 'gemini' && value.provider !== 'deterministic'))
    throw new AiClientError('Consultation mode is unavailable.', 502);
  return value.provider;
}
export async function createConsultation(service: FeatureId): Promise<{ handle: string; state: ConsultationView }> {
  const value = await request('consultations', jsonBody({ primary_service: service }));
  if (!object(value) || typeof value.handle !== 'string' || !value.handle)
    throw new AiClientError('Consultation could not be created.', 502);
  return { handle: value.handle, state: state(value) };
}
export async function uploadPhoto(handle: string, file: File): Promise<ConsultationView> {
  const body = new FormData(); body.append('image', file);
  return state(await request('consultations/photo', { method: 'PUT', body }, handle));
}
export async function updatePreferences(handle: string, preferences: Preferences): Promise<ConsultationView> {
  return state(await request('consultations/state', {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ preferences }),
  }, handle));
}
export async function sendTurn(handle: string, message?: string): Promise<{
  state: ConsultationView; status: 'more_information' | 'ready_for_recommendation'; recommendations: Recommendation[] | null;
}> {
  const value = await request('consultations/turn', jsonBody(message === undefined ? {} : { message }), handle);
  if (!object(value) || (value.status !== 'more_information' && value.status !== 'ready_for_recommendation'))
    throw new AiClientError('The consultant response is incomplete.', 502);
  return { state: state(value.state), status: value.status,
    recommendations: value.recommendations ? recommendations(value.recommendations) : null };
}
export async function getRecommendations(handle: string): Promise<Recommendation[]> {
  return recommendations(await request('consultations/recommendations', { method: 'POST' }, handle));
}
export async function generateRecommendation(handle: string, recommendationId: string): Promise<GenerationDetail> {
  return detail(await request('consultations/recommendations/' + encodeURIComponent(recommendationId) + '/generation',
    { method: 'POST' }, handle));
}
export async function getGenerationStatus(handle: string, recommendationId: string): Promise<GenerationDetail> {
  return detail(await request('consultations/recommendations/' + encodeURIComponent(recommendationId) + '/generation',
    {}, handle));
}
export async function selectRecommendation(handle: string, recommendationId: string): Promise<ConsultationView> {
  return state(await request('consultations/recommendations/' + encodeURIComponent(recommendationId) + '/select',
    { method: 'POST' }, handle));
}
export async function getStyles(service: FeatureId): Promise<AiStyle[]> {
  const value = await request('features/' + service + '/styles');
  if (!Array.isArray(value) || value.some((row) => !object(row) || typeof row.id !== 'string' ||
      typeof row.name !== 'string' || typeof row.status !== 'string'))
    throw new AiClientError('Styles are unavailable.', 502);
  return value as AiStyle[];
}
export async function generateCustom(service: FeatureId, file: File, styleId: string): Promise<GeneratedResult> {
  const body = new FormData(); body.append('image', file); body.append('style_id', styleId);
  const value = await request('features/' + service + '/generate', { method: 'POST', body });
  if (!object(value) || !object(value.image) || typeof value.image.data_url !== 'string' ||
      !/^data:image\/(png|jpeg);base64,/.test(value.image.data_url))
    throw new AiClientError('The generated image response is invalid.', 502);
  return value as GeneratedResult;
}
