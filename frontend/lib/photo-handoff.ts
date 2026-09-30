import type { FeatureId } from "@/lib/api";

// A one-navigation handoff only. No browser storage or extra photo endpoint.
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
