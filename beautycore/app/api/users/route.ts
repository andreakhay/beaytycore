import { NextResponse } from 'next/server';
import { eq, sql, desc } from 'drizzle-orm';
import { db } from '@/db';
import { users, userRoleEnum, appointments, type UserRole } from '@/db/schema';
import { requireRole } from '@/lib/auth';

/**
 * GET /api/users — directory for admin screens.
 *
 * Query: ?role=client to filter. Never returns password hashes.
 */
export async function GET(req: Request) {
  try {
    const session = await requireRole(['admin']);
    if (!session) {
      return NextResponse.json({ error: 'Admins only.' }, { status: 403 });
    }

    const role = new URL(req.url).searchParams.get('role') as UserRole | null;
    const valid = role && userRoleEnum.enumValues.includes(role);

    const rows = await db
      .select({
        id: users.id,
        name: users.name,
        email: users.email,
        role: users.role,
        avatar: users.avatar,
        createdAt: users.createdAt,
        appointmentCount: sql<number>`(
          select count(*)::int from appointments a where a.client_id = ${users.id}
        )`,
        totalSpent: sql<number>`(
          select coalesce(sum(a.total_price), 0)::int from appointments a
          where a.client_id = ${users.id} and a.status = 'completed'
        )`,
      })
      .from(users)
      .where(valid ? eq(users.role, role) : undefined)
      .orderBy(desc(users.createdAt));

    return NextResponse.json({ users: rows });
  } catch (error) {
    console.error('[api/users GET]', error);
    return NextResponse.json({ error: 'Could not load users.' }, { status: 500 });
  }
}

/** PATCH /api/users — change a user's role. Admin only. */
export async function PATCH(req: Request) {
  try {
    const session = await requireRole(['admin']);
    if (!session) {
      return NextResponse.json({ error: 'Admins only.' }, { status: 403 });
    }

    const { id, role } = await req.json();

    if (!id || !role) {
      return NextResponse.json({ error: 'User id and role are required.' }, { status: 400 });
    }
    if (!userRoleEnum.enumValues.includes(role)) {
      return NextResponse.json({ error: 'Invalid role.' }, { status: 400 });
    }

    // Guard against an admin removing their own access and locking everyone out.
    if (id === session.userId && role !== 'admin') {
      return NextResponse.json(
        { error: 'You cannot change your own role.' },
        { status: 400 }
      );
    }

    const [updated] = await db
      .update(users)
      .set({ role })
      .where(eq(users.id, id))
      .returning({
        id: users.id,
        name: users.name,
        email: users.email,
        role: users.role,
      });

    if (!updated) {
      return NextResponse.json({ error: 'User not found.' }, { status: 404 });
    }

    return NextResponse.json({ user: updated });
  } catch (error) {
    console.error('[api/users PATCH]', error);
    return NextResponse.json({ error: 'Could not update user.' }, { status: 500 });
  }
}
