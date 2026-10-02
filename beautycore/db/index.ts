import { neon } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-http';
import * as schema from './schema';
import * as dotenv from 'dotenv';

dotenv.config({ path: '.env.local', quiet: true });

if (!process.env.DATABASE_URL) {
  throw new Error(
    'DATABASE_URL is not set. Add it to .env.local — see .env.local.example.'
  );
}

const sql = neon(process.env.DATABASE_URL);

export const db = drizzle(sql, { schema });

// ─── Re-exports ─────────────────────────────────────────────────────────────
// Lets routes/components import tables and types from a single place:
//   import { db, users, type User } from '@/db';
export * from './schema';
export { schema };
