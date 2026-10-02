import 'server-only';

import { detectNailBoxes, type NailBox } from './detect';
import type { StyleCategory } from './types';

/**
 * Image-generation providers.
 *
 * Preview generation sits behind an interface because the hosted options all
 * failed on this project's free-tier keys (HuggingFace retired SDXL
 * serverless; Gemini image models return quota `limit: 0` without billing;
 * Replicate needs a paid token). Analysis never depended on any of them, so
 * the app stayed useful while a generator was sorted out.
 *
 * The working path is now `lora`: a self-trained Stable Diffusion 1.5 LoRA
 * served over HTTP from Colab. See scripts/colab_lora_server.py.
 *
 * To switch providers, set PREVIEW_PROVIDER in .env.local. No route changes.
 */

export interface GenerateRequest {
  prompt: string;
  styleType: StyleCategory;
  /** Base64 source photo for image-to-image, when the provider supports it. */
  sourceImage?: { base64: string; mimeType: string };
}

export interface GenerateSuccess {
  ok: true;
  /** Data URL or hosted URL of the generated preview. */
  imageUrl: string;
  provider: string;
}

export interface GenerateUnavailable {
  ok: false;
  reason: 'not_configured' | 'quota' | 'provider_error';
  /** Shown to the user — must be plain and non-technical. */
  message: string;
  provider: string;
}

export type GenerateResult = GenerateSuccess | GenerateUnavailable;

export interface PreviewProvider {
  name: string;
  /** False when required credentials are absent. */
  isConfigured(): boolean;
  generate(req: GenerateRequest): Promise<GenerateResult>;
}

// ─── Stub (default) ─────────────────────────────────────────────────────────

/**
 * Always reports unavailable, with an honest explanation. Keeps the full
 * upload → analyse → (attempt preview) flow exercisable end to end.
 */
const stubProvider: PreviewProvider = {
  name: 'stub',
  isConfigured: () => true,
  async generate(): Promise<GenerateResult> {
    return {
      ok: false,
      reason: 'not_configured',
      message:
        'Preview generation is not enabled yet. Your style analysis and recommendations above are live — image previews need a generation provider to be configured.',
      provider: 'stub',
    };
  },
};

// ─── Gemini (requires billing) ──────────────────────────────────────────────

const geminiProvider: PreviewProvider = {
  name: 'gemini',
  isConfigured: () => Boolean(process.env.GEMINI_API_KEY),

  async generate({ prompt, sourceImage }): Promise<GenerateResult> {
    if (!this.isConfigured()) {
      return {
        ok: false,
        reason: 'not_configured',
        message: 'Image generation is not configured.',
        provider: 'gemini',
      };
    }

    try {
      const { GoogleGenAI } = await import('@google/genai');
      const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });
      const model = process.env.GEMINI_IMAGE_MODEL ?? 'gemini-2.5-flash-image';

      // With a source photo this becomes an edit rather than a fresh render,
      // which is what keeps the client's own hand/face in the preview.
      const parts: Array<Record<string, unknown>> = [];
      if (sourceImage) {
        parts.push({
          inlineData: { mimeType: sourceImage.mimeType, data: sourceImage.base64 },
        });
        parts.push({
          text: `Edit this photo to show the following style, keeping the person's actual hand/face structure, skin tone, lighting, and background unchanged. Only change the styled element. Style: ${prompt}`,
        });
      } else {
        parts.push({ text: prompt });
      }

      const res = await ai.models.generateContent({
        model,
        contents: [{ role: 'user', parts }],
        config: { responseModalities: ['IMAGE'] },
      });

      const out = res.candidates?.[0]?.content?.parts?.find((p) => p.inlineData);
      if (!out?.inlineData?.data) {
        return {
          ok: false,
          reason: 'provider_error',
          message: 'The image provider did not return an image. Please try again.',
          provider: 'gemini',
        };
      }

      const mime = out.inlineData.mimeType ?? 'image/png';
      return {
        ok: true,
        imageUrl: `data:${mime};base64,${out.inlineData.data}`,
        provider: 'gemini',
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      const isQuota = msg.includes('429') || msg.toLowerCase().includes('quota');

      console.error('[preview/gemini]', msg.slice(0, 400));

      return {
        ok: false,
        reason: isQuota ? 'quota' : 'provider_error',
        message: isQuota
          ? 'Image generation is over its quota. This model requires a billed Google Cloud account.'
          : 'Preview generation failed. Please try again in a moment.',
        provider: 'gemini',
      };
    }
  },
};

// ─── LoRA (Colab-hosted, via tunnel) ────────────────────────────────────────

/**
 * Talks to a self-hosted LoRA inference server — the Colab notebook in
 * scripts/colab_lora_server.py, exposed through a cloudflared tunnel.
 *
 * Contract:
 *   POST {LORA_ENDPOINT_URL}/generate
 *   { prompt, image?, prompt_strength, mask_boxes?, mask_strength?, lora_scale? }
 *     -> { image: "<base64 png>" }
 *
 * `mask_boxes` switches the server from image-to-image to masked inpainting,
 * which is what makes nail previews work at all: unmasked, the model repaints
 * the whole frame and spends its budget on rings and background rather than on
 * nails that are ~1% of the image each. See ./detect.ts.
 *
 * The two strengths are separate on purpose. `prompt_strength` means exactly
 * what it always meant — how much of the whole frame img2img may destroy — and
 * `mask_strength` only applies inside the mask. A server predating this change
 * ignores both new fields and falls back to `prompt_strength`, i.e. today's
 * behaviour, instead of repainting the entire photo at 0.95.
 *
 * The tunnel URL changes on every notebook restart, so failures here are
 * expected and get a specific message rather than a generic error.
 *
 * LORA_STYLE_SCOPE limits which categories this model is allowed to render.
 * A LoRA trained only on nails will happily paint nail art onto a head of
 * hair, which looks worse than admitting the model isn't ready — so
 * out-of-scope requests return the honest "not available" path instead.
 */
const loraProvider: PreviewProvider = {
  name: 'lora',
  isConfigured: () => Boolean(process.env.LORA_ENDPOINT_URL),

  async generate({ prompt, styleType, sourceImage }): Promise<GenerateResult> {
    const base = process.env.LORA_ENDPOINT_URL?.replace(/\/+$/, '');
    if (!base) {
      return {
        ok: false,
        reason: 'not_configured',
        message:
          'The style model is not connected. Start the Colab notebook and set LORA_ENDPOINT_URL in .env.local.',
        provider: 'lora',
      };
    }

    // Defaults to nails only: that is the model that exists today. Set
    // LORA_STYLE_SCOPE=hair,nails once a hair LoRA is trained and loaded.
    const scope = (process.env.LORA_STYLE_SCOPE ?? 'nails')
      .split(',')
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);

    if (!scope.includes(styleType)) {
      return {
        ok: false,
        reason: 'not_configured',
        message: `${styleType === 'hair' ? 'Hair' : 'Nail'} previews aren't available yet — that style model is still being trained. Your analysis and recommendations above are live.`,
        provider: 'lora',
      };
    }

    // Find the nails so the repaint can be confined to them. Skipped for hair
    // (a box mask doesn't describe hair) and when there's no source photo to
    // mask. LORA_NAIL_MASK=0 forces the old unmasked path, for comparing them.
    let maskBoxes: NailBox[] = [];
    if (styleType === 'nails' && sourceImage && process.env.LORA_NAIL_MASK !== '0') {
      maskBoxes = await detectNailBoxes(sourceImage.base64, sourceImage.mimeType);
    }

    // How much of the WHOLE frame img2img may destroy. Stays low: nails need
    // the hand kept intact, hair can move further. This is also the value a
    // server that predates masking falls back to, which is why it must not be
    // raised — 0.95 across the whole frame destroys the photo.
    const promptStrength = styleType === 'nails' ? 0.5 : 0.65;

    // Inside a mask, high strength is the entire point: it's the only way to
    // get a real colour change, and nothing outside the nails can be touched.
    const rawMaskStrength = Number(process.env.LORA_MASK_STRENGTH ?? '0.95');
    const maskStrength = Number.isFinite(rawMaskStrength) ? rawMaskStrength : 0.95;

    const rawScale = Number(process.env.LORA_SCALE ?? '0.8');
    const loraScale = Number.isFinite(rawScale) ? rawScale : 0.8;

    // Logged because a disappointing preview has two very different causes —
    // no mask, or a mask that missed — and they are indistinguishable from the
    // image alone.
    console.log(
      `[preview/lora] ${styleType} · ` +
        (maskBoxes.length
          ? `inpainting ${maskBoxes.length} nail(s) @ strength ${maskStrength}`
          : `unmasked img2img @ strength ${promptStrength}`) +
        ` · lora_scale ${loraScale}`
    );

    // Cold start loads SD 1.5 onto the Colab GPU, which is slow the first time.
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 180_000);

    try {
      const res = await fetch(`${base}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          prompt,
          image: sourceImage
            ? `data:${sourceImage.mimeType};base64,${sourceImage.base64}`
            : undefined,
          prompt_strength: promptStrength,
          // Omitted entirely when detection found nothing, so the server takes
          // its plain img2img path rather than inpainting through an empty mask.
          mask_boxes: maskBoxes.length ? maskBoxes : undefined,
          mask_strength: maskStrength,
          lora_scale: loraScale,
        }),
      });

      if (!res.ok) {
        console.error('[preview/lora] HTTP', res.status);
        return {
          ok: false,
          reason: 'provider_error',
          message: `The style model returned an error (${res.status}). Check the Colab notebook is still running.`,
          provider: 'lora',
        };
      }

      const data = (await res.json()) as { image?: string; error?: string };

      if (data.error) {
        console.error('[preview/lora]', data.error);
        return {
          ok: false,
          reason: 'provider_error',
          message: 'The style model failed to render this look. Please try another style.',
          provider: 'lora',
        };
      }

      if (!data.image) {
        return {
          ok: false,
          reason: 'provider_error',
          message: 'The style model returned no image. Please try again.',
          provider: 'lora',
        };
      }

      const img = data.image.startsWith('data:')
        ? data.image
        : `data:image/png;base64,${data.image}`;

      return { ok: true, imageUrl: img, provider: 'lora' };
    } catch (err) {
      const aborted = err instanceof Error && err.name === 'AbortError';
      console.error('[preview/lora]', err instanceof Error ? err.message : err);

      return {
        ok: false,
        reason: 'provider_error',
        message: aborted
          ? 'The style model took too long to respond. The Colab GPU may be loading — try again in a minute.'
          : 'Could not reach the style model. Check the Colab notebook is running and LORA_ENDPOINT_URL is current.',
        provider: 'lora',
      };
    } finally {
      clearTimeout(timeout);
    }
  },
};

// ─── Selection ──────────────────────────────────────────────────────────────

const providers: Record<string, PreviewProvider> = {
  stub: stubProvider,
  gemini: geminiProvider,
  lora: loraProvider,
};

export function getPreviewProvider(): PreviewProvider {
  const name = (process.env.PREVIEW_PROVIDER ?? 'stub').toLowerCase();
  const provider = providers[name];

  if (!provider) {
    console.warn(
      `[preview] Unknown PREVIEW_PROVIDER "${name}". Falling back to stub. Valid: ${Object.keys(providers).join(', ')}`
    );
    return stubProvider;
  }
  return provider;
}
