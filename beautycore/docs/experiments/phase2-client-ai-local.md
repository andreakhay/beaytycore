# Integration Phase 2 — BeautyCore Client AI Consultation

**Date:** 2026-10-02
**Status:** LOCAL/MOCKED VERIFIED. No live Gemini, Kaggle, image generation, Neon mutation, or booking request was run.

The Client sidebar now has an additive AI Consultation entry beside the existing AI Advisor. One BeautyCore Client route presents Service → Direction → Your Looks. It creates and uploads through the Phase 1 same-origin adapter, collects service-relevant preferences, uses the configured Gemini or deterministic Consultation mode, and accepts only the backend's three validated recommendations. Generation is explicit and sequential. Each card retains its own pending, generating, completed, failed, or uncertain state; successful siblings remain visible. An ambiguous POST is followed by the existing generation-status GET, never an automatic retry POST. Manual retry is enabled only after a known failed or pending state. Select uses the existing Consultation endpoint and creates no appointment.

Custom Hair, Makeup, and Nails stay inside this same route, reuse the in-memory uploaded File, discover current styles and call the Phase 1 manual feature route. No photo is written to Neon. The browser retains the signed consultation handle only in React memory. The browser client discards FastAPI state IDs and sends only the handle header. A narrow Phase 1 response correction also removes the upstream consultation UUID from create/state/turn/select responses; handle validation and upstream calls are unchanged. A 403 for a bound consultation returns the page to a clean restart state.

Validation used a temporary clean source copy with offline-installed dependencies and a temporary preview route that was never added to BeautyCore Git:

- `npx tsx tests/ai-client-flow.test.ts` — 9 passed.
- `npx tsx tests/ai-adapter.test.ts` — 14 passed.
- `npm run typecheck` — passed.
- `npm run build` — passed with a dummy local DATABASE_URL; existing Google Fonts required network for build.
- Temporary Chrome browser with mocked `/api/ai/*`: Service → photo → Gemini turns → three recommendations → sequential Look 1/2/3 POSTs → Select → Custom style discovery/generation. All requests stayed on the BeautyCore adapter. A separate mocked 403 during startup displayed the expired-consultation restart message.
- Visual inspection at 1440px and a true 390px CSS viewport found no horizontal overflow. Reduced-motion-aware stage, photo and result transitions use the existing Framer Motion dependency.

The next gate is an authenticated Client session against the real private FastAPI boundary and unified worker. This local gate does not prove live Gemini/GPU behavior, hosting request-size limits, or cross-process persistence. The old AI Advisor, roles, appointments, pricing, schema, and AI backend remain unchanged.
