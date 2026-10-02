import { AiClientError, type GenerationDetail, type GeneratedResult, type Recommendation } from './browser-client';

export type LookStatus = 'pending' | 'generating' | 'completed' | 'failed' | 'unknown';
export type LookCard = {
  recommendation: Recommendation; status: LookStatus; result: GeneratedResult | null;
  error: string; canRetry: boolean;
};
export type GenerationBoundary = {
  generate: (id: string) => Promise<GenerationDetail>;
  status: (id: string) => Promise<GenerationDetail>;
  wait: (ms: number) => Promise<void>;
};
export const initialCards = (rows: Recommendation[]): LookCard[] => rows.map((recommendation) => ({
  recommendation, status: 'pending', result: null, error: '', canRetry: false,
}));

export function applyGenerationDetail(card: LookCard, detail: GenerationDetail): LookCard {
  if (detail.generation.status === 'completed' && detail.result)
    return { ...card, status: 'completed', result: detail.result, error: '', canRetry: false };
  if (detail.generation.status === 'failed')
    return { ...card, status: 'failed', error: detail.generation.error || 'This look could not be generated.',
      canRetry: true };
  return { ...card, status: 'unknown', error: 'This look is still processing. Check its status before continuing.',
    canRetry: false };
}

/** Exactly one POST. Ambiguous replies are resolved by GET; never by another POST. */
export async function generateOne(
  card: LookCard, boundary: GenerationBoundary, update: (card: LookCard) => void,
  maxChecks = 120,
): Promise<'settled' | 'unknown'> {
  update({ ...card, status: 'generating', error: '', canRetry: false });
  let reply: GenerationDetail | null = null;
  try {
    reply = await boundary.generate(card.recommendation.id);
    if (reply.generation.status === 'completed' && reply.result || reply.generation.status === 'failed') {
      update(applyGenerationDetail(card, reply));
      return 'settled';
    }
  } catch (error) {
    if (error instanceof AiClientError && error.status === 403) throw error;
    if (error instanceof AiClientError && !error.ambiguous) {
      update({ ...card, status: 'failed', error: error.message, canRetry: false });
      return 'settled';
    }
  }
  try {
    reply = await boundary.status(card.recommendation.id);
    for (let i = 0; reply.generation.status === 'generating' && i < maxChecks; i++) {
      await boundary.wait(5000);
      reply = await boundary.status(card.recommendation.id);
    }
    if (reply.generation.status === 'completed' && reply.result || reply.generation.status === 'failed') {
      update(applyGenerationDetail(card, reply));
      return 'settled';
    }
    if (reply.generation.status === 'pending') {
      update({ ...card, status: 'failed', error: 'Generation did not start. You can retry this look.',
        canRetry: true });
      return 'settled';
    }
  } catch (error) {
    if (error instanceof AiClientError && error.status === 403) throw error;
  }
  update({ ...card, status: 'unknown', error: 'Generation status is uncertain. Check status before continuing.',
    canRetry: false });
  return 'unknown';
}

export async function generateSequential(
  rows: LookCard[], boundary: GenerationBoundary, update: (card: LookCard) => void,
): Promise<'settled' | 'unknown'> {
  for (const card of rows) {
    if (card.status !== 'pending') continue;
    if (await generateOne(card, boundary, update) === 'unknown') return 'unknown';
  }
  return 'settled';
}
