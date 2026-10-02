/**
 * Authentication utilities — password hashing and JWT session management.
 *
 * Sessions are stateless: a signed JWT stored in an HTTP-only cookie.
 * No session table, no NextAuth dependency.
 */
import 'server-only';

import bcrypt from 'bcryptjs';
import { SignJWT, jwtVerify } from 'jose';
import { cookies } from 'next/headers';
import type { UserRole } from '@/db/schema';

const COOKIE_NAME = 'beautycore_session';
const SESSION_DURATION_DAYS = 7;

/** The claims we store in the JWT. Never include the password hash. */
export interface SessionPayload {
  userId: string;
  email: string;
  name: string;
  role: UserRole;
  [key: string]: unknown; // satisfies jose's JWTPayload index signature
}

function getSecret(): Uint8Array {
  const secret = process.env.SESSION_SECRET;
  if (!secret) {
    throw new Error(
      'SESSION_SECRET is not set. Add it to .env.local — see .env.local.example.'
    );
  }
  return new TextEncoder().encode(secret);
}

// ─── Passwords ──────────────────────────────────────────────────────────────

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10);
}

export async function verifyPassword(
  password: string,
  hash: string
): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

// ─── JWT ────────────────────────────────────────────────────────────────────

export async function signSession(payload: SessionPayload): Promise<string> {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(`${SESSION_DURATION_DAYS}d`)
    .sign(getSecret());
}

export async function verifySession(
  token: string
): Promise<SessionPayload | null> {
  try {
    const { payload } = await jwtVerify(token, getSecret(), {
      algorithms: ['HS256'],
    });
    return payload as SessionPayload;
  } catch {
    // Expired, tampered with, or signed by a different secret.
    return null;
  }
}

// ─── Cookie-backed session ──────────────────────────────────────────────────

/** Signs a JWT for this user and writes it to the session cookie. */
export async function createSession(payload: SessionPayload): Promise<void> {
  const token = await signSession(payload);
  const cookieStore = await cookies();

  cookieStore.set(COOKIE_NAME, token, {
    httpOnly: true, // not readable from JS — blocks XSS token theft
    secure: process.env.NODE_ENV === 'production', // allows http://localhost in dev
    sameSite: 'lax', // CSRF protection while keeping normal navigation working
    path: '/',
    maxAge: SESSION_DURATION_DAYS * 24 * 60 * 60,
  });
}

/** Reads and verifies the current session. Returns null when logged out. */
export async function getSession(): Promise<SessionPayload | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  if (!token) return null;
  return verifySession(token);
}

/** Clears the session cookie. */
export async function destroySession(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
}

/**
 * Server-side guard for route handlers.
 * Returns the session, or null if absent / not in `allowedRoles`.
 */
export async function requireRole(
  allowedRoles: UserRole[]
): Promise<SessionPayload | null> {
  const session = await getSession();
  if (!session) return null;
  if (!allowedRoles.includes(session.role)) return null;
  return session;
}
