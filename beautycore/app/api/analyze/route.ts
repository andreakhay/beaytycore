import { NextResponse } from 'next/server';
import { getSession } from '@/lib/auth';
import { analyzePhoto } from '@/lib/ai/gemini';
import { decodeImageInput, ImageValidationError } from '@/lib/ai/types';

/** Vision analysis can take a while on larger photos. */
export const maxDuration = 60;

/**
 * POST /api/analyze
 *
 * Body:     { imageBase64: string }   // data URL or bare base64
 * Response: { analysis: StyleAnalysis, model: string }
 */
export async function POST(req: Request) {
  try {
    // Analysis costs an API call, so require a signed-in user.
    const session = await getSession();
    if (!session) {
      return NextResponse.json(
        { error: 'Please sign in to use the AI Advisor.' },
        { status: 401 }
      );
    }

    let body: unknown;
    try {
      body = await req.json();
    } catch {
      return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 });
    }

    const { imageBase64 } = (body ?? {}) as { imageBase64?: string };
    if (!imageBase64) {
      return NextResponse.json(
        { error: 'Please upload a photo to analyse.' },
        { status: 400 }
      );
    }

    const { base64, mimeType } = decodeImageInput(imageBase64);

    const { analysis, model } = await analyzePhoto(base64, mimeType);

    return NextResponse.json({ analysis, model });
  } catch (error) {
    if (error instanceof ImageValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    const message = error instanceof Error ? error.message : String(error);
    console.error('[api/analyze]', message.slice(0, 500));

    // Surface quota separately — it's actionable, unlike a generic 500.
    if (message.includes('429') || message.toLowerCase().includes('quota')) {
      return NextResponse.json(
        { error: 'The AI service is over its quota. Please try again shortly.' },
        { status: 429 }
      );
    }

    if (message.includes('API key') || message.includes('GEMINI_API_KEY')) {
      return NextResponse.json(
        { error: 'The AI service is not configured. Check GEMINI_API_KEY in .env.local.' },
        { status: 500 }
      );
    }

    return NextResponse.json(
      { error: 'We could not analyse that photo. Please try another one.' },
      { status: 500 }
    );
  }
}
