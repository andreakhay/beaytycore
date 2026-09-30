# CONSULTATION-01: consultation foundation

**Status:** Implemented; CPU and local API verified on 2026-09-30. No LLM or image generation is part of this slice.

## Existing components reused

- `app.main.FEATURE_ROUTES` and each feature's existing `styles()` callback supply the **active** style IDs, names and availability. Hair uses its configured registry when remote and the six prototype styles when mock; Makeup uses its ten presets; Nails uses its five hybrid styles.
- `app.main.validated_image` checks the consultation upload with the same image rules as generation. Existing feature handlers, remote clients and routes remain untouched.
- Nails `MODEL_STYLES` and `RENDERER_STYLES` label the candidate's intended hybrid execution path for future use. In mock mode, Nails still returns its existing placeholder; consultation does not run either path.

## Implemented contract

`POST /consultations` creates a UUID consultation for `hairstyle`, `makeup` or `nails`. `PUT /consultations/{id}/photo` validates and stores the original uploaded bytes privately in the process, returning only a UUID photo reference, type and dimensions. `PATCH /consultations/{id}` merges structured preferences and optionally appends one user message. `GET /consultations/{id}` returns state. `GET /consultations/catalog` returns active styles with editorial tags and demo service estimates. `POST /consultations/{id}/recommendations` requires a photo and returns exactly three primary recommendations. Preferences and a new photo invalidate earlier recommendations. Status is `collecting` or `recommended`.

Preferences cover occasion, vibe, likes, avoids and notes, plus a few optional Hair, Makeup and Nails fields. The deterministic provider ranks actual candidates by tag overlap, excludes explicitly avoided tags, and may suggest one supported style from another service. It has a narrow `RecommendationProvider.recommend(state, candidates)` boundary for a later LLM. User message and free-text notes are stored as context but are not interpreted by the mock ranker.

Each proposed item has `primary: {feature, style_id}`, a short `reason`, and optional `complements: [{feature, style_id}]`. Strict Pydantic structures reject extra provider fields. The backend validator requires three unique primary styles for the consultation's feature, verifies all IDs against the currently active catalog and filtered candidates, and checks complements belong to other enabled features. It then attaches style names, the Nails model/renderer label, and **backend-owned** service estimates. A provider cannot supply a price or duration. If fewer than three candidates remain, the API returns a clear 422 rather than inventing styles.

`app.consultation.metadata` holds only editorial tags keyed by style ID. The existing catalogs remain authoritative for names, availability and generator settings. An active style without tags makes consultation catalog discovery fail closed until tagged. The sidecar covers the default and expanded Hair registries plus the mock Hair catalog, all Makeup presets and all Nails styles. It never edits prompts, LoRA routing or rendering.

## Service and photo limitations

Service estimates are **demo-only configuration**, not a salon quote: Hairstyle PHP 600/60 minutes, Makeup PHP 500/45 minutes, Nails PHP 350/45 minutes. No appointment slots or availability exist in this backend. A future booking integration should replace this source before presenting live quotes.

There is no current database or consultation session mechanism. The process-local store holds at most 10 consultations. Each becomes inaccessible one hour after its last change; expired bytes are removed on the next store access or process restart, not by a background timer. It does not survive a backend restart or span multiple workers. UUIDs make references difficult to guess, but there is no user authentication or durable private-photo retention policy yet. The API never returns the photo bytes. The capstone launcher currently uses one backend process; multiuser deployment needs authenticated persistence and explicit retention rules.

The existing manual pages remain `/`, `/makeup` and `/nails`. CONSULTATION-01 does not alter them or navigate to them. Later, Custom can route to the matching page while preserving the browser `File` in shared client state, or use this private photo reference through a new authenticated backend handoff. Neither transfer is implemented in this slice. The uploaded photo is not analyzed for visual traits.

## Next phases

- **CONSULTATION-02:** revalidate the selected recommendation against the then-current active catalog, then connect it and the stored photo reference to the existing feature generation dispatcher. Add the guided frontend and Custom handoff. Preserve the feature handlers and Nails hybrid boundary.
- **CONSULTATION-03:** replace the deterministic provider with a conversational LLM provider that only proposes candidates; keep backend state, validation, pricing and generation authority.

[Local test evidence](../experiments/CONSULTATION-01-local.md).
