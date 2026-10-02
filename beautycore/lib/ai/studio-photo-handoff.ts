import type { FeatureId } from './browser-client';

// One navigation in this browser process. Never put a private photo in a URL or storage.
let pending: { feature: FeatureId; file: File } | null = null;

export function rememberCustomPhoto(feature: FeatureId, file: File): void {
  pending = { feature, file };
}

export function takeCustomPhoto(feature: FeatureId): File | null {
  if (pending?.feature !== feature) return null;
  const file = pending.file;
  pending = null;
  return file;
}
