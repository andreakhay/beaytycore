import { NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { db } from '@/db';
import { users } from '@/db/schema';
import { getSession } from '@/lib/auth';

/**
 * Returns the currently signed-in user, or `{ user: null }`.
 *
 * Reads fresh from the DB rather than trusting the JWT claims, so a role
 * change or deleted account takes effect immediately instead of lingering
 * until the cookie expires.
 */
export async function GET() {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ user: null });
    }

    const user = await db.query.users.findFirst({
      where: eq(users.id, session.userId),
      columns: { id: true, name: true, email: true, role: true, avatar: true },
    });

    // Valid cookie, but the account no longer exists.
    if (!user) {
      return NextResponse.json({ user: null });
    }

    return NextResponse.json({ user });
  } catch (error) {
    console.error('[auth/session]', error);
    return NextResponse.json({ user: null });
  }
}
