import { NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { db } from '@/db';
import { users, clientProfiles, userRoleEnum, type UserRole } from '@/db/schema';
import { hashPassword, createSession } from '@/lib/auth';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const name = String(body.name ?? '').trim();
    const email = String(body.email ?? '').toLowerCase().trim();
    const password = String(body.password ?? '');
    const requestedRole = body.role as UserRole | undefined;

    // ─── Validation ─────────────────────────────────────────────────────────
    if (!name || !email || !password) {
      return NextResponse.json(
        { error: 'Name, email, and password are required.' },
        { status: 400 }
      );
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return NextResponse.json(
        { error: 'Please enter a valid email address.' },
        { status: 400 }
      );
    }

    if (password.length < 6) {
      return NextResponse.json(
        { error: 'Password must be at least 6 characters.' },
        { status: 400 }
      );
    }

    // Self-registration is client-only. Admin and stylist accounts are created
    // by an admin, so an attacker can't POST their way to a privileged role.
    let role: UserRole = 'client';
    if (requestedRole && requestedRole !== 'client') {
      if (!userRoleEnum.enumValues.includes(requestedRole)) {
        return NextResponse.json({ error: 'Invalid role.' }, { status: 400 });
      }
      role = 'client';
    }

    const existing = await db.query.users.findFirst({
      where: eq(users.email, email),
    });
    if (existing) {
      return NextResponse.json(
        { error: 'An account with that email already exists.' },
        { status: 409 }
      );
    }

    // ─── Create ─────────────────────────────────────────────────────────────
    const passwordHash = await hashPassword(password);

    const [user] = await db
      .insert(users)
      .values({ name, email, passwordHash, role })
      .returning();

    // Every client gets a profile row so the profile page has somewhere to write.
    await db.insert(clientProfiles).values({ userId: user.id });

    await createSession({
      userId: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
    });

    return NextResponse.json(
      {
        user: {
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
          avatar: user.avatar,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('[auth/register]', error);
    return NextResponse.json(
      { error: 'Something went wrong creating your account.' },
      { status: 500 }
    );
  }
}
