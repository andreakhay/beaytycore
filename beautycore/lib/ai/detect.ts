import { Type } from '@google/genai';
import { createHash } from 'node:crypto';
import { getGemini, ANALYSIS_MODEL } from './gemini';

/**
 * Locate the fingernails in a photo so a preview can be masked to them.
 *
 * WHY THIS EXISTS
 * ---------------
 * Plain image-to-image has no spatial control: noise is added uniformly across
 * the frame, so the model spends its change budget wherever it likes. Each nail
 * is roughly 1% of a typical hand photo (~5% for a whole hand), which in
 * practice meant previews left the nails untouched and restyled the rings and
 * background instead. Confining the repaint to a mask fixes that, and these
 * boxes are what the mask is built from.
 *
 * The boxes go to the LoRA server as numbers; the mask itself is rasterised
 * there with PIL. Nothing in this app draws pixels.
 *
 * Deliberately NOT part of `analyzePhoto()`:
 *   - `StyleAnalysis` is persisted to `ai_generations.analysisResult` and
 *     rendered in the UI. Boxes are a rendering detail, and keeping them out
 *     means no schema change.
 *   - Detection wants `temperature: 0`; the stylist prompt wants 0.9.
 *   - It only needs to run for nails on the LoRA path, not on every analysis.
 *
 * No `server-only` guard here, matching ./gemini.ts: both are plain Gemini
 * helpers that CLI scripts import directly. The guard lives on ./preview.ts,
 * which is the layer that must never reach a component.
 */

/** One nail, as Gemini returns it: `[ymin, xmin, ymax, xmax]`, scaled 0–1000. */
export type NailBox = [number, number, number, number];

/**
 * A hand has at most 10 nails visible. More than that means the model started
 * boxing fingers and knuckles, so the extras are dropped — smallest kept first,
 * since a nail is the smallest thing in this photo it could plausibly box.
 */
const MAX_BOXES = 10;

/**
 * Reject the whole detection if the boxes cover more than this share of the
 * frame. A mask that big is the model having boxed the hand rather than the
 * nails, and inpainting at 0.95 through it would repaint the entire photo —
 * strictly worse than the unmasked path we would otherwise fall back to.
 *
 * Overlapping boxes are double-counted, so this over-estimates coverage. That
 * is the right direction to err: it fails toward the safe path.
 */
const MAX_COVERAGE = 0.6;

/** Plenty — the advisor shows three recommendations for one photo. */
const CACHE_MAX = 16;

/**
 * Detection is a prelude to a render that has its own 180s budget, so it must
 * not be able to stall one. Giving up returns `[]`, which costs a mask — not
 * the preview.
 */
const TIMEOUT_MS = 20_000;

/**
 * Wording matters here: naming the thumbnail explicitly is what stopped it
 * being missed, and ruling out jewellery is what keeps rings out of the mask.
 * Kept in sync with scripts/nail-boxes.ts, which is the manual version of this.
 */
const DETECT_PROMPT =
  'Detect every visible fingernail in this photo, including the ' +
  'thumbnail. For each, give box_2d as [ymin, xmin, ymax, xmax] ' +
  'normalised to 0-1000, tight to the nail plate only. Do not ' +
  'include fingers, skin, rings, or jewellery.';

const DETECT_SCHEMA = {
  type: Type.ARRAY,
  items: {
    type: Type.OBJECT,
    properties: {
      label: { type: Type.STRING },
      box_2d: { type: Type.ARRAY, items: { type: Type.NUMBER } },
    },
    required: ['label', 'box_2d'],
  },
} as const;

/** Keyed on a hash of the image bytes. Insertion-ordered, so FIFO eviction. */
const cache = new Map<string, NailBox[]>();

const clamp = (n: number) => Math.min(1000, Math.max(0, n));

/**
 * Turn a raw model response into boxes we are willing to build a mask from.
 * Anything malformed is dropped rather than repaired — a wrong box puts paint
 * on someone's knuckle.
 */
function sanitize(raw: unknown): NailBox[] {
  if (!Array.isArray(raw)) return [];

  const boxes: NailBox[] = [];

  for (const item of raw) {
    const b = (item as { box_2d?: unknown } | null)?.box_2d;
    if (!Array.isArray(b) || b.length !== 4) continue;

    const nums = b.map(Number);
    if (nums.some((v) => !Number.isFinite(v))) continue;

    // Clamp before the ordering check, so an out-of-range box collapses and
    // gets dropped rather than silently spanning the whole axis.
    const [ymin, xmin, ymax, xmax] = nums.map(clamp);
    if (ymin >= ymax || xmin >= xmax) continue;

    boxes.push([ymin, xmin, ymax, xmax]);
  }

  if (boxes.length === 0) return [];

  const area = (box: NailBox) => (box[2] - box[0]) * (box[3] - box[1]);

  const kept =
    boxes.length > MAX_BOXES
      ? [...boxes].sort((a, b) => area(a) - area(b)).slice(0, MAX_BOXES)
      : boxes;

  const coverage = kept.reduce((sum, box) => sum + area(box), 0) / (1000 * 1000);
  if (coverage > MAX_COVERAGE) {
    console.warn(
      `[ai/detect] discarding ${kept.length} boxes covering ` +
        `${(coverage * 100).toFixed(0)}% of the frame — that is not nails`
    );
    return [];
  }

  return kept;
}

/**
 * Ask Gemini where the nails are. Returns `[]` — never throws — if detection
 * is unavailable or unconvincing, because a preview must still render when
 * this fails. The caller treats an empty result as "no mask, use the old
 * unmasked path".
 */
export async function detectNailBoxes(
  base64: string,
  mimeType: string
): Promise<NailBox[]> {
  const key = createHash('sha256').update(base64).digest('hex').slice(0, 16);

  const hit = cache.get(key);
  if (hit) return hit;

  let timer: ReturnType<typeof setTimeout> | undefined;

  try {
    const ai = getGemini();

    const res = await Promise.race([
      ai.models.generateContent({
        model: ANALYSIS_MODEL,
        contents: [
          {
            role: 'user',
            parts: [{ inlineData: { mimeType, data: base64 } }, { text: DETECT_PROMPT }],
          },
        ],
        config: {
          responseMimeType: 'application/json',
          responseSchema: DETECT_SCHEMA,
          temperature: 0, // measurement, not creativity — same photo, same boxes
        },
      }),
      new Promise<null>((resolve) => {
        timer = setTimeout(() => resolve(null), TIMEOUT_MS);
      }),
    ]);

    if (!res) {
      console.warn(
        `[ai/detect] gave up after ${TIMEOUT_MS / 1000}s — rendering unmasked`
      );
      return [];
    }

    const boxes = sanitize(JSON.parse(res.text ?? '[]'));

    // Cached even when empty: a photo with no detectable nails should not be
    // re-queried for each of the three recommendations. Failures below are not
    // cached, since those are usually transient.
    if (cache.size >= CACHE_MAX) {
      const oldest = cache.keys().next().value;
      if (oldest !== undefined) cache.delete(oldest);
    }
    cache.set(key, boxes);

    return boxes;
  } catch (err) {
    console.error('[ai/detect]', err instanceof Error ? err.message : err);
    return [];
  } finally {
    clearTimeout(timer);
  }
}
