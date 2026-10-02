import { NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { db } from '@/db';
import { users } from '@/db/schema';

/**
 * GET /api/stylists — public list for the booking form.
 * Returns only non-sensitive fields.
 */
export async function GET() {
  try {
    const rows = await db.query.users.findMany({
      where: eq(users.role, 'stylist'),
      columns: { id: true, name: true, avatar: true },
      orderBy: (u, { asc }) => [asc(u.name)],
    });

    return NextResponse.json({ stylists: rows });
  } catch (error) {
    console.error('[api/stylists]', error);
    return NextResponse.json({ error: 'Could not load stylists.' }, { status: 500 });
  }
}
