import { NextResponse } from 'next/server';
import { eq } from 'drizzle-orm';
import { db } from '@/db';
import { users } from '@/db/schema';
import { verifyPassword, createSession } from '@/lib/auth';

export async function POST(req: Request) {
  try {
    const { email, password } = await req.json();

    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email and password are required.' },
        { status: 400 }
      );
    }

    const user = await db.query.users.findFirst({
      where: eq(users.email, String(email).toLowerCase().trim()),
    });

    // Same message and code whether the email is unknown or the password is
    // wrong — otherwise this endpoint becomes a way to enumerate accounts.
    const invalid = NextResponse.json(
      { error: 'Invalid email or password.' },
      { status: 401 }
    );

    if (!user) return invalid;

    const ok = await verifyPassword(password, user.passwordHash);
    if (!ok) return invalid;

    await createSession({
      userId: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
    });

    return NextResponse.json({
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        avatar: user.avatar,
      },
    });
  } catch (error) {
    console.error('[auth/login]', error);
    return NextResponse.json(
      { error: 'Something went wrong signing you in.' },
      { status: 500 }
    );
  }
}
