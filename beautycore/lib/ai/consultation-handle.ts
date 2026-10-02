import { SignJWT, jwtVerify } from 'jose';

const ISSUER = 'beautycore-ai-adapter';
const AUDIENCE = 'beautycore-client-consultation';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MAX_SECONDS = 60 * 60;

function key(secret: string): Uint8Array {
  if (secret.length < 32) throw new Error('AI consultation handle secret is not configured');
  return new TextEncoder().encode(secret);
}

export function isConsultationId(value: unknown): value is string {
  return typeof value === 'string' && UUID.test(value);
}

export async function signConsultationHandle(
  userId: string,
  consultationId: string,
  upstreamExpiresAt: string,
  secret: string,
  now = Date.now(),
): Promise<string> {
  if (!userId || !isConsultationId(consultationId)) throw new Error('Invalid consultation state');
  const nowSeconds = Math.floor(now / 1000);
  const upstreamSeconds = Math.floor(Date.parse(upstreamExpiresAt) / 1000);
  const expires = Math.min(nowSeconds + MAX_SECONDS, upstreamSeconds);
  if (!Number.isFinite(expires) || expires <= nowSeconds) throw new Error('Expired consultation state');

  return new SignJWT({ cid: consultationId })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuer(ISSUER)
    .setAudience(AUDIENCE)
    .setSubject(userId)
    .setIssuedAt(nowSeconds)
    .setExpirationTime(expires)
    .sign(key(secret));
}

export async function verifyConsultationHandle(
  token: string,
  currentUserId: string,
  secret: string,
  now = Date.now(),
): Promise<string | null> {
  try {
    const { payload } = await jwtVerify(token, key(secret), {
      algorithms: ['HS256'],
      issuer: ISSUER,
      audience: AUDIENCE,
      currentDate: new Date(now),
    });
    if (payload.sub !== currentUserId || !isConsultationId(payload.cid)) return null;
    return payload.cid;
  } catch {
    return null;
  }
}
