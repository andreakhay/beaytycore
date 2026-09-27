export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export type Style = { id: string; name: string; description: string; status: string };
export type GenerateResponse = {
  status: string;
  generator: string;
  style: Style;
  image: { data_url: string; content_type: string; width: number; height: number };
  metadata?: { runtime_seconds?: number; seed?: number; steps?: number; guidance?: number };
};
export type HealthResponse = { status: string; generator: string };

async function responseError(response: Response): Promise<Error> {
  try {
    const body: { detail?: string | { msg: string }[] } = await response.json();
    if (typeof body.detail === "string") return new Error(body.detail);
    if (Array.isArray(body.detail)) return new Error(body.detail.map((item) => item.msg).join(" "));
  } catch {
    // The API did not return a usable error body.
  }
  return new Error("The request could not be completed. Please try again.");
}

export async function getStyles(): Promise<Style[]> {
  const response = await fetch(`${API_BASE_URL}/styles`, { cache: "no-store" });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as Style[];
}

export async function getMakeupStyles(): Promise<Style[]> {
  const response = await fetch(`${API_BASE_URL}/makeup/styles`, { cache: "no-store" });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as Style[];
}

export async function getNailStyles(): Promise<Style[]> {
  const response = await fetch(`${API_BASE_URL}/nails/styles`, { cache: "no-store" });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as Style[];
}

export async function generateNailsPreview(file: File, styleId: string): Promise<GenerateResponse> {
  const form = new FormData();
  form.append("image", file);
  form.append("style_id", styleId);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/nails/generate`, { method: "POST", body: form });
  } catch {
    throw new Error("The backend is unavailable. Start the local API, then try again.");
  }
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as GenerateResponse;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as HealthResponse;
}

export async function generatePortrait(file: File, styleId: string): Promise<GenerateResponse> {
  const form = new FormData();
  form.append("image", file);
  form.append("style_id", styleId);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/generate`, { method: "POST", body: form });
  } catch {
    throw new Error("The backend is unavailable. Start the local API, then try again.");
  }
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as GenerateResponse;
}

export async function generateMakeupPortrait(file: File, styleId: string): Promise<GenerateResponse> {
  const form = new FormData();
  form.append("image", file);
  form.append("style_id", styleId);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/makeup/generate`, { method: "POST", body: form });
  } catch {
    throw new Error("The backend is unavailable. Start the local API, then try again.");
  }
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as GenerateResponse;
}
