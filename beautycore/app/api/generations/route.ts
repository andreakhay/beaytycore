import { NextResponse } from 'next/server';
import { eq, desc } from 'drizzle-orm';
import { db } from '@/db';
import { aiGenerations } from '@/db/schema';
import { getSession } from '@/lib/auth';

/**
 * GET /api/generations — the signed-in client's AI history.
 *
 * Omits sourceImageUrl by default: those are base64 data URLs and would make
 * the payload enormous. Pass ?full=true when the images are actually needed.
 */
export async function GET(req: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: 'Not signed in.' }, { status: 401 });
    }

    const full = new URL(req.url).searchParams.get('full') === 'true';

    const rows = await db.query.aiGenerations.findMany({
      where: eq(aiGenerations.clientId, session.userId),
      orderBy: [desc(aiGenerations.createdAt)],
      limit: 24,
      columns: full
        ? undefined
        : {
            id: true,
            promptText: true,
            generatedImageUrl: true,
            styleType: true,
            analysisResult: true,
            createdAt: true,
          },
    });

    return NextResponse.json({ generations: rows });
  } catch (error) {
    console.error('[api/generations]', error);
    return NextResponse.json(
      { error: 'Could not load your history.' },
      { status: 500 }
    );
  }
}
