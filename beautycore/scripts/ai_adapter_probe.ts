/** Read-only local startup probe through the existing Phase 1 adapter core. */
import { handleAiRequest } from '../lib/ai/adapter-core';

const result = await handleAiRequest(
  new Request('http://127.0.0.1:3000/api/ai/features'),
  ['features'],
  {
    baseUrl: process.env.AI_FASTAPI_URL ?? '',
    handleSecret: process.env.AI_CONSULTATION_HANDLE_SECRET ?? '',
    currentUser: async () => ({ id: 'startup-probe', role: 'client' }),
    upstreamFetch: fetch,
  },
);

if (result.status !== 200) process.exit(1);
const value: unknown = await result.json();
if (!Array.isArray(value) || !['hairstyle', 'makeup', 'nails'].every(
  (feature) => value.some((row) => row && typeof row === 'object' && row.id === feature),
)) process.exit(1);
