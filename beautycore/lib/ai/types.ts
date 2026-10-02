/**
 * Shared types for the AI pipeline.
 *
 * Step 1 (`/api/analyze`) produces a StyleAnalysis from an uploaded photo.
 * Step 2 (`/api/generate`) turns one recommendation's `generationPrompt` into
 * a preview image.
 */

export type StyleCategory = 'hair' | 'nails';

export interface CurrentAttributes {
  shapeOrCut: string;
  color: string;
  condition: string;
}

export interface StyleRecommendation {
  title: string;
  colorPalette: string;
  designDetails: string;
  reasoning: string;
  /** Ready-to-use prompt for the image provider. */
  generationPrompt: string;
}

export interface StyleAnalysis {
  category: StyleCategory;
  currentAttributes: CurrentAttributes;
  recommendations: StyleRecommendation[];
}

/** Narrows a data URL / raw base64 string into parts the SDK needs. */
export interface DecodedImage {
  base64: string;
  mimeType: string;
}

const ALLOWED_MIME = ['image/jpeg', 'image/png', 'image/webp'] as const;
/** 8 MB ceiling on the decoded image, to keep requests inside limits. */
const MAX_BYTES = 8 * 1024 * 1024;

export class ImageValidationError extends Error {}

/**
 * Accepts either a `data:image/...;base64,xxx` URL or bare base64, and
 * validates type and size before it reaches the model.
 */
export function decodeImageInput(input: string): DecodedImage {
  if (!input || typeof input !== 'string') {
    throw new ImageValidationError('No image was provided.');
  }

  let mimeType = 'image/jpeg';
  let base64 = input.trim();

  const dataUrl = base64.match(/^data:([a-zA-Z0-9/+.-]+);base64,([\s\S]*)$/);
  if (dataUrl) {
    mimeType = dataUrl[1];
    base64 = dataUrl[2];
  }

  base64 = base64.replace(/\s/g, '');

  if (!ALLOWED_MIME.includes(mimeType as (typeof ALLOWED_MIME)[number])) {
    throw new ImageValidationError(
      `Unsupported image type "${mimeType}". Please upload a JPEG, PNG, or WebP.`
    );
  }

  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(base64)) {
    throw new ImageValidationError('The image data appears to be corrupted.');
  }

  // 4 base64 chars encode 3 bytes.
  const bytes = Math.floor((base64.length * 3) / 4);
  if (bytes > MAX_BYTES) {
    throw new ImageValidationError(
      `That image is ${(bytes / 1024 / 1024).toFixed(1)} MB. Please upload one under 8 MB.`
    );
  }
  if (bytes < 1024) {
    throw new ImageValidationError('That image looks too small to analyse.');
  }

  return { base64, mimeType };
}
