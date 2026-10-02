# Phase 1: Secure AI Adapter and Client Identity

**Status:** IMPLEMENTED (Phase 1 local mocked gate passed; live integration pending)
**Date:** 2026-10-02
**Basis:** Read-only inspection of BeautyCore source at this baseline and the existing F:/HAIR FastAPI contracts. No integration code or database change is included here.

## Goal

Let a signed-in BeautyCore client reach the existing FastAPI Consultation and feature APIs through BeautyCore server routes. BeautyCore remains the identity and business-data authority. FastAPI remains the recommendation and generation authority. Keep the existing BeautyCore AI Advisor and all existing AI routes operational.

## Deployment precondition

For the initial local capstone integration, run FastAPI on a loopback or otherwise private address reachable only from the BeautyCore server. Existing FastAPI Consultation and feature routes do not authenticate BeautyCore users. A signed browser handle does not secure a publicly reachable FastAPI server. If the two servers will be hosted separately, approve and test server-to-server authentication and private transport before exposing the adapter. Do not treat CORS as authentication.

## Ownership and authorization

1. Browser sends its existing HttpOnly BeautyCore session cookie only to same-origin BeautyCore routes.
2. On every AI adapter operation, BeautyCore verifies the cookie with existing getSession(), then reads users by session.userId from Neon and requires the current database role to equal client. A deleted or changed user is denied even if the JWT still has an old client claim.
3. On consultation create, BeautyCore forwards {primary_service} to FastAPI and returns its state plus a short-lived signed consultation handle. Use the already installed jose library with a dedicated server-only AI_CONSULTATION_HANDLE_SECRET, a fixed issuer/audience, current user ID, FastAPI consultation UUID, and expiry no later than the FastAPI state expiry. The handle is kept in browser memory, not in a URL or persistent browser storage.
4. Every later consultation operation requires that handle in a request header. Verify signature, expiry, audience and current user ID before deriving the upstream consultation ID. Never accept a client-supplied upstream ID or URL. Another client's handle, a changed ID, an expired handle, and a removed/changed-role account must fail closed.
5. Require a same-origin Origin check on mutating BeautyCore AI routes. The existing SameSite cookie remains unchanged. No BeautyCore cookie, JWT, handle signing key, Gemini key, or Kaggle API key is forwarded to FastAPI or Kaggle.
6. Treat handle expiry as a normal expired-consultation state. Do not silently recreate a consultation or retry generation.

## BeautyCore-facing API

Use small same-origin routes under app/api/ai/ backed by a server-only allowlisted adapter module in lib/ai/. A catch-all route is acceptable only with a fixed operation/method allowlist; it must never become an arbitrary URL proxy.

| Operation | BeautyCore route concept | Existing FastAPI call |
| --- | --- | --- |
| Mode and eligible catalog | GET /api/ai/mode, GET /api/ai/catalog | GET /consultations/mode, GET /consultations/catalog |
| Create | POST /api/ai/consultations | POST /consultations |
| State | GET /api/ai/consultations/state with handle | GET /consultations/{id} |
| Photo | PUT /api/ai/consultations/photo with handle and multipart image | PUT /consultations/{id}/photo |
| Preferences or message | PATCH /api/ai/consultations/state with handle | PATCH /consultations/{id} |
| Gemini turn | POST /api/ai/consultations/turn with handle | POST /consultations/{id}/turn |
| Recommendations | POST /api/ai/consultations/recommendations with handle | POST /consultations/{id}/recommendations |
| Generate or user retry | POST /api/ai/consultations/recommendations/{recommendationId}/generation with handle | Same FastAPI POST |
| Generation status after uncertainty | GET on that generation path with handle | Same FastAPI GET |
| Select | POST /api/ai/consultations/recommendations/{recommendationId}/select with handle | Same FastAPI POST |
| Custom/manual catalog and generation | GET /api/ai/features, GET /api/ai/features/{feature}/styles, POST /api/ai/features/{feature}/generate | Existing /features routes |

In Gemini mode, /turn returns readiness and, when ready, the validated three recommendations. The recommendations POST is still required for deterministic mode and returns the saved set in Gemini mode. Generation remains one recommendation at a time. The adapter relays controlled response shapes and HTTP status, blocks arbitrary feature/route targets, and never logs image bytes or credentials. It adds no automatic generation retry. After an ambiguous disconnect, the client checks the existing generation-status GET before any user-initiated retry.

## Image and data contract

Browser uploads one JPEG or PNG File as multipart form data with field image. BeautyCore enforces a request/file ceiling compatible with FastAPI's 8 MiB file limit and rejects other types, then forwards the file without transforming it into a data URL. FastAPI remains the final authority for actual format, dimensions (64 to 4096 per side), pixel count and style validation. BeautyCore's old Advisor keeps its existing WebP/data-URL behavior unchanged. Check the actual hosting platform's body-size and long-request limits before remote deployment; Next request.formData() may buffer the upload. Use no-store responses for private state/results.

FastAPI keeps consultation photo bytes and generated results in its bounded process-local store, which expires after about one hour and is lost on restart. Phase 1 writes no AI photo or result to Neon and does not use the old ai_generations table. The signed handle is an access capability, not durable storage.

## Database and booking boundary

No Neon schema change or migration is required for Phase 1. Protect users, client_profiles, appointments, ai_generations, inventory, and lib/services.ts. User ID from users.id is the ownership key at the adapter. There is no selected-result-to-appointment foreign key today.

Recommendations are advisory. BeautyCore alone determines bookable service, actual price, appointment time, stylist and booking creation. FastAPI demo_only price and duration must never be submitted as authoritative booking values. Booking integration is out of Phase 1.

## Likely files to add or change in Phase 1

- Add a server-only BeautyCore AI transport and handle module under lib/ai/.
- Add narrowly scoped app/api/ai/ route handlers and focused tests.
- Add server-only AI_FASTAPI_URL and AI_CONSULTATION_HANDLE_SECRET configuration. Do not put these in NEXT_PUBLIC variables. Keep existing BeautyCore auth and FastAPI configuration unchanged.
- A client navigation entry or integrated Consultation UI belongs to a later phase after the adapter passes its gate. Existing app/client/ai-advisor/page.tsx is untouched.

## Acceptance gate

Using a mocked FastAPI boundary, prove: authenticated current client succeeds; anonymous, admin, stylist, deleted and role-changed accounts fail; tampered, expired and cross-user handles fail; only allowlisted upstream operations are reachable; one JPEG/PNG photo is forwarded without Neon persistence; invalid/oversize/WebP uploads are rejected in the new route; three recommendations and per-look generation/status/select preserve existing contracts; Custom feature routes use the same authorization; upstream errors stay controlled; no generation auto-retry occurs; no cookie, key, image bytes or private URL appears in logs or client configuration. Run BeautyCore type/build checks and its existing core workflow checks before any live AI gate.

## Open decision before remote deployment

The current proposal assumes a private same-host FastAPI connection. If BeautyCore runs on a hosted platform separate from FastAPI, settle the reachable private/authenticated server-to-server transport and hosting request limits first. This is a deployment decision, not a reason to rewrite Consultation or generation.
