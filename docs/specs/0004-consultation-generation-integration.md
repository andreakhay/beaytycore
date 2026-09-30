# CONSULTATION-02: existing-generator integration

2026-09-30. **IMPLEMENTED; LOCAL/MOCKED AND REPRESENTATIVE LIVE INTEGRATION VERIFIED.** This record builds on the [CONSULTATION-01 foundation](0003-consultation-foundation.md). The deterministic provider, active catalog, three-item validator, backend-owned demo service estimates, photo validator, and one-hour process-local store remain authoritative. The [live gate](../experiments/CONSULTATION-02-live-gate.md) exercised three real recommended looks per feature through the unified Kaggle worker and confirmed a later Hair restoration; it did not assess all styles or visual quality.

## Application path

`/consultation` offers service selection, one photo, short structured preferences and exactly three validated recommendations. The page issues one generation POST per primary recommendation, awaiting Look 1 before Look 2 and Look 2 before Look 3. It updates cards as each result arrives. A status GET can read the saved outcome if a generation response is lost; it never sends a replacement generation POST automatically. Complementary styles appear as text and are not generated.

`POST /consultations/{id}/recommendations/{recommendation_id}/generation` resolves the recommendation from backend state, rechecks its primary style against the **current** enabled catalog and consultation exclusions, then calls `app.main.dispatch_feature`. The existing central `/features/{feature}/generate` route calls that same dispatcher. The dispatcher invokes `FEATURE_ROUTES[feature].generate`, preserving Hair, Makeup and Nails validation, image processing, remote clients, Nails model/renderer routing, diagnostics and GPU ownership. It does not send HTTP to itself. The original validated photo bytes are wrapped in an `UploadFile` for the existing feature handler; no second upload/storage path exists.

## State and failure boundary

`ConsultationState.generations` holds one small status per recommendation: `pending`, `generating`, `completed` or `failed`, plus attempts, safe error and result availability. Full existing `GenerateResponse` payloads are stored once per completed look in the bounded in-memory consultation entry and returned only by the per-look generation GET/POST. The general state endpoint never returns image bytes. One active recommendation per consultation is enforced atomically in the store; photo changes, preference updates and recommendation replacement are blocked while it runs. The unified GPU worker remains responsible for cross-consultation serialization.

One failed look leaves completed siblings untouched. Failed looks can be manually retried by the user; the page sends **zero automatic generation retries**. A canceled HTTP caller cannot release the consultation generation slot while the original handler is still running: the handler task is shielded and drained before the slot is finalized. An uncertain client response triggers status reads, not another generation request. The page blocks continuation while outcome is unknown.

`POST /consultations/{id}/recommendations/{recommendation_id}/select` records the ID of a completed primary recommendation in backend state. Its style, result, service estimate and complements remain available through the existing recommendation set and per-look result endpoint. This is a session summary, not booking or payment.

## Custom and limits

Custom links go to the original `/`, `/makeup` or `/nails` page. The browser transfers the already chosen `File` once through an in-memory module during client navigation; the manual page owns its normal upload and generation controls afterward. Refreshing or opening Custom in a new tab loses this transfer and the user can upload manually. No photo goes into browser storage or a URL.

The original 10-session/one-hour process-local limit still applies. Generated image data URLs increase per-session RAM usage up to three primary results; they are not durable and vanish on restart/expiry. No LLM, booking, complementary image generation, or multiworker persistence is included. CONSULTATION-03 may replace only the deterministic recommendation provider with a conversational provider; backend catalog validation, price/duration ownership and generation dispatch remain unchanged.

[Local validation evidence](../experiments/CONSULTATION-02-local.md) and [representative live gate](../experiments/CONSULTATION-02-live-gate.md).
