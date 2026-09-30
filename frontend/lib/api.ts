export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export type FeatureId = "hairstyle" | "makeup" | "nails";
export type Feature = { id: FeatureId; name: string; description: string };
export type Style = { id: string; name: string; description: string; status: string };
export type GenerateResponse = {
  status: string;
  generator: string;
  style: Style;
  image: { data_url: string; content_type: string; width: number; height: number };
  metadata?: { runtime_seconds?: number; seed?: number; steps?: number; guidance?: number };
};
export type HealthResponse = { status: string; generator: string };

export type ApiErrorCode = "invalid_image" | "invalid_style" | "invalid_feature" | "invalid_request"
  | "backend_unavailable" | "inference_failed" | "timeout" | "invalid_response" | "http_error";

export class ApiError extends Error {
  constructor(message: string, public readonly code: ApiErrorCode, public readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function responseError(response: Response): Promise<ApiError> {
  let message = "The request could not be completed. Please try again.";
  try {
    const body: { detail?: string | { msg: string }[] } = await response.json();
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg).join(" ");
  } catch {
    // Do not expose an HTML proxy error or an internal response body.
  }
  let code: ApiErrorCode = "http_error";
  if (response.status === 404) code = "invalid_feature";
  else if (response.status === 408 || response.status === 504) {
    code = "timeout";
    message = "The request timed out. Please try again.";
  } else if ([400, 413, 415, 422].includes(response.status)) {
    code = /style/i.test(message) ? "invalid_style" : /image|portrait|photo/i.test(message) ? "invalid_image" : "invalid_request";
  } else if (response.status >= 500 || response.status === 429) code = "inference_failed";
  return new ApiError(message, code, response.status);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasStrings(value: Record<string, unknown>, fields: string[]): boolean {
  return fields.every((field) => typeof value[field] === "string");
}

function isFeature(value: unknown): value is Feature {
  return isRecord(value) && hasStrings(value, ["id", "name", "description"]);
}

function isStyle(value: unknown): value is Style {
  return isRecord(value) && hasStrings(value, ["id", "name", "description", "status"]);
}

export function isGeneration(value: unknown): value is GenerateResponse {
  if (!isRecord(value) || !hasStrings(value, ["status", "generator"]) || !isStyle(value.style)
      || !isRecord(value.image)) return false;
  const image = value.image;
  return typeof image.data_url === "string" && /^data:image\/(png|jpeg);base64,/.test(image.data_url)
    && ["image/png", "image/jpeg"].includes(image.content_type as string)
    && Number.isInteger(image.width) && (image.width as number) > 0
    && Number.isInteger(image.height) && (image.height as number) > 0
    && (value.metadata === undefined || isRecord(value.metadata));
}

export async function request<T>(path: string, validate: (value: unknown) => value is T, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch (error) {
    if (error instanceof Error && ["AbortError", "TimeoutError"].includes(error.name)) {
      throw new ApiError("The request timed out. Please try again.", "timeout");
    }
    throw new ApiError("The backend is unavailable. Start the local API, then try again.", "backend_unavailable");
  }
  if (!response.ok) throw await responseError(response);
  try {
    const body: unknown = await response.json();
    if (!validate(body)) throw new Error("Invalid response shape");
    return body;
  } catch {
    throw new ApiError("The backend returned an unreadable response. Please try again.", "invalid_response", response.status);
  }
}

export function getFeatures(): Promise<Feature[]> {
  return request("/features", (body): body is Feature[] => Array.isArray(body) && body.every(isFeature), { cache: "no-store" });
}

export function getStyles(featureId: FeatureId): Promise<Style[]> {
  return request(`/features/${featureId}/styles`, (body): body is Style[] => Array.isArray(body) && body.every(isStyle), { cache: "no-store" });
}

export function generate(featureId: FeatureId, file: File, styleId: string): Promise<GenerateResponse> {
  const form = new FormData();
  form.append("image", file);
  form.append("style_id", styleId);
  return request(`/features/${featureId}/generate`, isGeneration, { method: "POST", body: form });
}

export function getHealth(): Promise<HealthResponse> {
  return request("/health", (body): body is HealthResponse => isRecord(body) && hasStrings(body, ["status", "generator"]), { cache: "no-store" });
}
