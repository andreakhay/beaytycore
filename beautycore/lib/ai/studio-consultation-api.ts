/** Preserve the original Consultation page's contract using signed Client handles. */
import {
  createConsultation as create,
  generateRecommendation as generate,
  getGenerationStatus,
  getMode,
  getRecommendations,
  selectRecommendation as select,
  sendTurn,
  updatePreferences,
  uploadPhoto,
  type ConsultationView,
  type FeatureId,
  type GenerationDetail,
  type Preferences,
  type Recommendation,
} from './browser-client';

export type { GenerationDetail, Preferences, Recommendation };
type ConsultationState = ConsultationView & { id: string };
type RecommendationSet = { recommendations: Recommendation[] };

function withHandle(handle: string, state: ConsultationView): ConsultationState {
  // id is the signed, user bound handle, never FastAPI's consultation UUID.
  return { ...state, id: handle };
}

export async function getConsultationMode(): Promise<{ provider: 'gemini' | 'deterministic' }> {
  return { provider: await getMode() };
}

export async function createConsultation(feature: FeatureId): Promise<ConsultationState> {
  const created = await create(feature);
  return withHandle(created.handle, created.state);
}

export async function uploadConsultationPhoto(handle: string, photo: File): Promise<ConsultationState> {
  return withHandle(handle, await uploadPhoto(handle, photo));
}

export async function updateConsultation(handle: string, preferences: Preferences): Promise<ConsultationState> {
  return withHandle(handle, await updatePreferences(handle, preferences));
}

export async function sendConsultationTurn(handle: string, message?: string): Promise<{
  state: ConsultationState;
  status: 'more_information' | 'ready_for_recommendation';
  recommendations: RecommendationSet | null;
}> {
  const turn = await sendTurn(handle, message);
  return {
    state: withHandle(handle, turn.state),
    status: turn.status,
    recommendations: turn.recommendations ? { recommendations: turn.recommendations } : null,
  };
}

export async function recommendConsultation(handle: string): Promise<RecommendationSet> {
  return { recommendations: await getRecommendations(handle) };
}

export function generateRecommendation(handle: string, recommendationId: string): Promise<GenerationDetail> {
  return generate(handle, recommendationId);
}

export function getGenerationDetail(handle: string, recommendationId: string): Promise<GenerationDetail> {
  return getGenerationStatus(handle, recommendationId);
}

export async function selectRecommendation(handle: string, recommendationId: string): Promise<ConsultationState> {
  return withHandle(handle, await select(handle, recommendationId));
}
