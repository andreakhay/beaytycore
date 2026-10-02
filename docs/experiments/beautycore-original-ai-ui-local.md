# BeautyCore Client AI studio import, local evidence

**Date:** 2026-10-02. **Status:** LOCAL AND MOCKED VERIFIED; LIVE KAGGLE ACCEPTANCE PENDING.

The Client Consultation, Hairstyle, Makeup and Nails pages now reuse the existing HAIR frontend presentation and shared AI studio components inside BeautyCore. The HAIR frontend source remains unchanged for rollback. A small BeautyCore client bridge maps the imported page calls to its existing signed `/api/ai/*` adapter. The browser does not receive a FastAPI consultation UUID, a private FastAPI address, an API key or a Kaggle URL. BeautyCore still owns authentication and current client role checks. Existing FastAPI generation and Gemini behavior were not edited.

The prior BeautyCore Advisor Client page now redirects to the imported Consultation. Client sidebar, dashboard and public calls to action lead to Consultation and the three real feature pages. The previous Hair and Nail preset builder component was removed from the Client UI. Historical `/api/generations` remains because Admin market trends still reads it; no Neon rows or schema were changed.

Local checks:

- `npm run typecheck` in `beautycore/`: passed.
- `npm run build` in `beautycore/`: passed, including the new `/client/makeup-studio` route.
- `node node_modules/tsx/dist/cli.mjs --test tests/ai-adapter.test.ts tests/ai-client-flow.test.ts tests/ai-studio-integration.test.ts`: 26 passed.
- Headless Edge against the existing local BeautyCore dev server with mocked session and AI responses: Client Consultation selected Hair, uploaded one sample PNG, received a Gemini shaped turn and exactly three recommendations, issued three generation POSTs in order, and selected a result. Custom Hairstyle opened the imported Hair page with the same photo. Hairstyle, Makeup and Nails each loaded an approved style, issued a protected generation POST and opened the original comparison dialog. The former Advisor URL redirected to Consultation. A 390px Consultation viewport had no horizontal overflow. This used no real client account, Gemini, Kaggle worker or GPU image generation.
- The mock image was a one pixel nonprivate PNG. Browser screenshots and the temporary browser probe remain ignored under `.tmp/`.

Remaining gate: restart the one folder launcher with the current Kaggle notebook, sign in as a real BeautyCore Client, and verify the adapted original UI through Gemini, sequential generation, Select, Custom handoff and each direct feature page. Preserve the separate existing HAIR frontend and original BeautyCore checkpoint until this live gate passes.
