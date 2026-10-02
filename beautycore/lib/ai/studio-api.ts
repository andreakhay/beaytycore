/** The original AI studio's feature contract through BeautyCore's Client adapter. */
import {
  generateCustom,
  getStyles as getClientStyles,
  type AiStyle,
  type FeatureId,
  type GeneratedResult,
} from './browser-client';

export type { FeatureId };
export type Style = AiStyle;
export type GenerateResponse = GeneratedResult;

export const API_BASE_URL = '/api/ai';

export function getStyles(feature: FeatureId): Promise<Style[]> {
  return getClientStyles(feature);
}

export function generate(feature: FeatureId, photo: File, styleId: string): Promise<GenerateResponse> {
  return generateCustom(feature, photo, styleId);
}
