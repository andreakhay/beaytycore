# Integration Phase 1 — Secure AI adapter validation

**Date:** 2026-10-02
**Status:** VERIFIED locally with a mocked FastAPI boundary; no live Gemini, Kaggle, image generation, or BeautyCore database request was run.

BeautyCore now exposes only the fixed operations in the approved Phase 1 specification through `/api/ai/[...path]`. The route verifies the existing session, rereads the current `users.id` and role from Neon, and requires `client` on every allowed operation. Consultation operations derive the FastAPI UUID from a signed, user-bound, expiring header handle. Mutations require a matching Origin. The server-only destination is restricted to local loopback for this initial deployment boundary. Browser cookies and credentials are never forwarded upstream.

Uploads accept JPEG/PNG files of at most 8 MiB and forward multipart data directly. FastAPI remains responsible for decoding and full image validation. The adapter writes no photo, result, or consultation record to Neon. Generation has no automatic retry; the existing generation-status GET is available for a client to inspect an ambiguous result before user-initiated retry.

Local validation used a clean temporary source copy with offline-installed dependencies because the supplied BeautyCore directory has no `node_modules`. No private `.env.local` was copied.

- `npx tsx tests/ai-adapter.test.ts` — 14 passed, 0 failed, mocked FastAPI only.
- `npm run typecheck` — passed.
- `npm run build` — passed with a dummy local `DATABASE_URL`; existing Google Fonts required network access for this build.
- Existing `npm run lint` remains the documented preexisting broken Next 16 script and was not changed.

The adapter has no Consultation UI yet. Phase 2 must keep the signed handle in memory, submit requests only to the same-origin BeautyCore routes, generate recommendations sequentially, and check generation status before any manual retry following an ambiguous connection failure. The signed handle does not secure FastAPI if FastAPI is later exposed publicly; a separate server-to-server authentication decision is required before such deployment.
