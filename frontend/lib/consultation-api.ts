import { isGeneration, request, type FeatureId, type GenerateResponse } from "@/lib/api";

export type Preferences = {
  occasion?: string; vibe?: string; avoids?: string[]; notes?: string;
  hair_length?: "short" | "medium" | "long";
  hair_maintenance?: "low" | "medium" | "high";
  makeup_intensity?: "natural" | "soft" | "bold";
  makeup_finish?: "dewy" | "matte" | "glossy";
  nail_color?: string;
  nail_finish?: "glossy" | "matte" | "ombre" | "french";
};

export type ServiceEstimate = { feature: FeatureId; name: string; estimated_price: number;
  currency: "PHP"; estimated_duration_minutes: number; estimate_kind: "demo_only" };
export type Choice = { feature: FeatureId; style_id: string; style_name: string;
  service: ServiceEstimate; nail_path: "model" | "renderer" | null };
export type Recommendation = { id: string; primary: Choice; reason: string; complements: Choice[] };
export type RecommendationSet = { recommendations: [Recommendation, Recommendation, Recommendation] };
export type GenerationStatus = { recommendation_id: string; status: "pending" | "generating" | "completed" | "failed";
  attempts: number; error: string | null; result_available: boolean };
export type ConsultationState = { id: string; primary_service: FeatureId; stage: "collecting" | "recommended";
  photo: { id: string; content_type: string; width: number; height: number } | null;
  recommendations: RecommendationSet | null; generations: GenerationStatus[];
  selected_recommendation_id: string | null };
export type GenerationDetail = { generation: GenerationStatus; result: GenerateResponse | null };

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function feature(value: unknown): value is FeatureId {
  return value === "hairstyle" || value === "makeup" || value === "nails";
}
function estimate(value: unknown): value is ServiceEstimate {
  return record(value) && feature(value.feature) && typeof value.name === "string"
    && Number.isFinite(value.estimated_price) && value.currency === "PHP"
    && Number.isFinite(value.estimated_duration_minutes) && value.estimate_kind === "demo_only";
}
function choice(value: unknown): value is Choice {
  return record(value) && feature(value.feature) && typeof value.style_id === "string"
    && typeof value.style_name === "string" && estimate(value.service)
    && (value.nail_path === null || value.nail_path === "model" || value.nail_path === "renderer");
}
function recommendation(value: unknown): value is Recommendation {
  return record(value) && typeof value.id === "string" && choice(value.primary)
    && typeof value.reason === "string" && Array.isArray(value.complements)
    && value.complements.every(choice);
}
function recommendationSet(value: unknown): value is RecommendationSet {
  if (!record(value) || !Array.isArray(value.recommendations)
      || value.recommendations.length !== 3 || !value.recommendations.every(recommendation)) return false;
  return new Set(value.recommendations.map((row: Recommendation) => row.id)).size === 3;
}
function generationStatus(value: unknown): value is GenerationStatus {
  return record(value) && typeof value.recommendation_id === "string"
    && ["pending", "generating", "completed", "failed"].includes(value.status as string)
    && Number.isInteger(value.attempts) && (value.error === null || typeof value.error === "string")
    && typeof value.result_available === "boolean";
}
function consultationState(value: unknown): value is ConsultationState {
  return record(value) && typeof value.id === "string" && feature(value.primary_service)
    && (value.stage === "collecting" || value.stage === "recommended")
    && (value.photo === null || (record(value.photo) && typeof value.photo.id === "string"
      && typeof value.photo.content_type === "string" && Number.isInteger(value.photo.width)
      && Number.isInteger(value.photo.height)))
    && (value.recommendations === null || recommendationSet(value.recommendations))
    && Array.isArray(value.generations) && value.generations.every(generationStatus)
    && (value.selected_recommendation_id === null || typeof value.selected_recommendation_id === "string");
}
function generationDetail(value: unknown): value is GenerationDetail {
  return record(value) && generationStatus(value.generation)
    && (value.result === null || isGeneration(value.result));
}

export function createConsultation(primaryService: FeatureId): Promise<ConsultationState> {
  return request("/consultations", consultationState, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ primary_service: primaryService }) });
}
export function uploadConsultationPhoto(id: string, file: File): Promise<ConsultationState> {
  const body = new FormData(); body.append("image", file);
  return request(`/consultations/${encodeURIComponent(id)}/photo`, consultationState,
    { method: "PUT", body });
}
export function updateConsultation(id: string, preferences: Preferences): Promise<ConsultationState> {
  return request(`/consultations/${encodeURIComponent(id)}`, consultationState, { method: "PATCH",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ preferences }) });
}
export function recommendConsultation(id: string): Promise<RecommendationSet> {
  return request(`/consultations/${encodeURIComponent(id)}/recommendations`, recommendationSet,
    { method: "POST" });
}
export function generateRecommendation(id: string, recommendationId: string): Promise<GenerationDetail> {
  return request(`/consultations/${encodeURIComponent(id)}/recommendations/${encodeURIComponent(recommendationId)}/generation`,
    generationDetail, { method: "POST" });
}
export function getGenerationDetail(id: string, recommendationId: string): Promise<GenerationDetail> {
  return request(`/consultations/${encodeURIComponent(id)}/recommendations/${encodeURIComponent(recommendationId)}/generation`,
    generationDetail, { cache: "no-store" });
}
export function selectRecommendation(id: string, recommendationId: string): Promise<ConsultationState> {
  return request(`/consultations/${encodeURIComponent(id)}/recommendations/${encodeURIComponent(recommendationId)}/select`,
    consultationState, { method: "POST" });
}
