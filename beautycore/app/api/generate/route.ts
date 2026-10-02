import { NextResponse } from 'next/server';
import { db } from '@/db';
import { aiGenerations } from '@/db/schema';
import { getSession } from '@/lib/auth';
import { getPreviewProvider } from '@/lib/ai/preview';
import { decodeImageInput, ImageValidationError, type StyleAnalysis } from '@/lib/ai/types';

/** Image generation is slow — allow well past the default. */
export const maxDuration = 120;

/**
 * POST /api/generate
 *
 * Body: {
 *   sourceImage: string,              // data URL or base64 of the client's photo
 *   prompt: string,                   // recommendation.generationPrompt
 *   styleType: 'hair' | 'nails',
 *   analysis?: StyleAnalysis          // stored alongside for history
 * }
 *
 * Response (success):     { success: true,  imageUrl, generationId, provider }
 * Response (unavailable): { success: false, message, reason, generationId, provider }
 *
 * A failed preview is still recorded, so the client's history shows what they
 * asked for even when no provider was able to render it.
 */
export async function POST(req: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json(
        { error: 'Please sign in to generate previews.' },
        { status: 401 }
      );
    }

    let body: unknown;
    try {
      body = await req.json();
    } catch {
      return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 });
    }

    const { sourceImage, prompt, styleType, analysis } = (body ?? {}) as {
      sourceImage?: string;
      prompt?: string;
      styleType?: string;
      analysis?: StyleAnalysis;
    };

    if (!prompt?.trim()) {
      return NextResponse.json({ error: 'A style prompt is required.' }, { status: 400 });
    }
    if (styleType !== 'hair' && styleType !== 'nails') {
      return NextResponse.json(
        { error: 'styleType must be "hair" or "nails".' },
        { status: 400 }
      );
    }

    // Optional: text-to-image still works without a source photo.
    let decoded: { base64: string; mimeType: string } | undefined;
    if (sourceImage) {
      decoded = decodeImageInput(sourceImage);
    }

    const provider = getPreviewProvider();
    const result = await provider.generate({
      prompt,
      styleType,
      sourceImage: decoded,
    });

    // `style_type` enum is 'hair' | 'nail' (singular) in the DB.
    const dbStyleType = styleType === 'nails' ? 'nail' : 'hair';

    const [row] = await db
      .insert(aiGenerations)
      .values({
        clientId: session.userId,
        sourceImageUrl: sourceImage ?? '',
        promptText: prompt,
        generatedImageUrl: result.ok ? result.imageUrl : null,
        styleType: dbStyleType,
        analysisResult: analysis ?? null,
      })
      .returning({ id: aiGenerations.id });

    if (!result.ok) {
      // 200, not an error status: the request was valid and is recorded — the
      // provider simply has nothing to render. The UI shows `message`.
      return NextResponse.json({
        success: false,
        reason: result.reason,
        message: result.message,
        provider: result.provider,
        generationId: row.id,
      });
    }

    return NextResponse.json({
      success: true,
      imageUrl: result.imageUrl,
      provider: result.provider,
      generationId: row.id,
    });
  } catch (error) {
    if (error instanceof ImageValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    const message = error instanceof Error ? error.message : String(error);
    console.error('[api/generate]', message.slice(0, 500));

    return NextResponse.json(
      { error: 'Preview generation failed. Please try again.' },
      { status: 500 }
    );
  }
}
