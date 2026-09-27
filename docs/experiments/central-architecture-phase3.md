# Central application architecture, Phase 3

2026-09-27. Evidence: VERIFIED locally and with synthetic boundaries. Live GPU validation: DEFERRED by the Supervisor. Base revision: `238f23aa88aeea36c015bde062d76032bb9dc86f`.

## Observations

| Check | Evidence / result |
| --- | --- |
| Discovery and namespaces | `/features` exposes all three features. Remote-mode catalogs and cross-feature style rejection pass; discovery and invalid requests make zero remote calls. Existing dispatcher tests verify central/legacy catalog parity and selected-handler isolation. |
| Hair and Makeup | Central multipart requests call existing handlers and real remote HTTP clients. HTTPX MockTransport verifies destination, authentication header, style ID and 512 PNG upload, then returns synthetic PNG results with existing contract metadata. Each request calls only its own service. |
| Nails | Real `HybridNailsPipeline`, crop preparation, five remote client requests, reconstruction, renderer and final compositing run. Localization and segmentation are synthetic boundaries, including the original-resolution refinement interface. Pixel assertions prove zero changes outside the final refined mask and changes inside it. All three renderer styles work with the Nails remote unavailable and make no remote calls. This does not evaluate MediaPipe/YOLO accuracy or model quality. |
| Outage isolation | Each remote independently fails while the other two features succeed. Clearing the outage restores that feature without restarting the app. |
| Errors | Unknown feature 404; invalid/cross-feature style 400; missing image and JSON instead of multipart 422; empty/unreadable image 400. Remote connection error, timeout, HTTP 500/503, malformed JSON/image/metadata and existing Makeup/Nails provenance failures return controlled 502 details without internal response bodies. Remote unavailable and timeout retain the existing combined 502 behavior; proxy/client timeouts retain the frontend `timeout` category. |
| Browser path | Production Next.js on loopback 3012 with FastAPI 8013: discovery and three catalogs returned 200. Edge uploaded synthetic PNGs and displayed Hair, Makeup and all five Nails results after central generation HTTP 200, with correct style/feature/path metadata, no page errors and no legacy style/generation calls. No browser response interception is used in this harness suite. |
| Client errors | Existing checks plus wrong-shape JSON regression pass. Three Edge checks show safe malformed-result errors, recovered generate buttons, no crashes and no legacy fallback. |

## Focused fixes

Initially, four backend cases failed: Hair/Nails null image fields and null metadata. Hair null metadata escaped into Pydantic response construction. Hair now requires dictionary metadata, and Hair/Nails include `AttributeError` in their existing invalid-response normalization. The 30 new backend cases then passed.

The frontend initially resolved `null` as successful discovery. `frontend/lib/api.ts` now validates common feature, style, image/result and health shapes before returning them to pages. The failing client regression now passes. No generation settings, prompts, GPU code, feature pages, dispatcher or Nails processing changed.

## Validation ledger

- `python -m pytest tests -q` in `backend/`: **152 passed**, one existing `python_multipart` deprecation warning. Includes all 122 previous tests and 30 new central remote path cases.
- `npm run lint` and `npm run build` in `frontend/`: exit 0; production compilation and TypeScript passed.
- `npx playwright test --grep-invert 'synthetic inference boundaries|actual shared client discovers'`: **28 passed** against all-feature mock backend 8012 and production frontend 3012. Includes 11 client tests and 17 Edge flows.
- `CENTRAL_REMOTE_TESTS=1` with `npx playwright test e2e/central-remote.spec.ts`: **8 passed** against synthetic remote harness 8013 and production frontend 3012. Includes actual client discovery and seven Edge generation flows.
- Initial browser assertion mistakes (the empty Next route announcer matching a generic alert locator, and a shortened Nude Pink display name) were corrected to the actual UI/catalog. Both final suites passed.

## Reproduce the synthetic remote browser suite

Only this test module adds `/_test/image` and installs fake vision/HTTP boundaries. Never launch it as the application server. Normal deployment remains `app.main:app`. These commands do not change `.env` files.

Terminal 1:

```powershell
cd F:\HAIR\backend
$env:FRONTEND_ORIGINS='http://127.0.0.1:3012'
python -m uvicorn central_remote_app:app --app-dir tests --host 127.0.0.1 --port 8013
```

Terminal 2:

```powershell
cd F:\HAIR\frontend
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8013'
npm run build
npm run start -- --hostname 127.0.0.1 --port 3012
```

Terminal 3:

```powershell
cd F:\HAIR\frontend
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8013'
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3012'
$env:CENTRAL_REMOTE_TESTS='1'
npx playwright test e2e/central-remote.spec.ts
```

The opt-in suite is skipped during ordinary tests. After stopping the harness, clear the test overrides and restore a normal frontend build. For standard tests, start all three backend features in mock mode as described in README; the opt-in suite requires the separate harness.

## Architecture review and configuration

`FEATURE_ROUTES` coordinates existing catalog/generation callables without model logic or per-style branches. No feature imports another feature's runtime. Each remote client constructs its own request/client; a request failure does not alter another engine. Valid startup configuration is still required; malformed mode/URL/key configuration can fail startup and differs from a remote outage.

Styles remain owned by Hair `styles.py`/`style_registry*.json`, Makeup `makeup_styles.py`/`makeup_contract.py` and reviewed inference presets, and Nails `styles.py`/`contract.py`. Existing registry expansion tests exercise the real 13-style Hair registry. Adding a style changes its catalog and any needed feature inference support without dispatcher edits. Page colors/tones are presentation metadata, not duplicate style definitions. Nails' model/renderer support sets remain intentional feature constraints.

A future feature needs an implementation, catalog/config, `FeatureRoute` entry and frontend experience (including the known `FeatureId` union/navigation). Generic central endpoints iterate/lookup the registry without an exactly-three requirement. This is source inspection, not implementation or validation of a fourth feature. Existing frontend Kaggle references are descriptive labels, not GPU addressing or routing logic.

Configuration source is ignored `backend/.env`, documented by `backend/.env.example`:

| Feature | Mode / inference client | Remote destination / authentication |
| --- | --- | --- |
| Hair | `GENERATION_ENGINE=remote_flux`, `generation/remote_flux.py` | `FLUX_REMOTE_URL`, `FLUX_REMOTE_API_KEY` |
| Makeup | `MAKEUP_GENERATION_ENGINE=remote_makeup`, `generation/remote_makeup.py` | `MAKEUP_REMOTE_URL`, `MAKEUP_REMOTE_API_KEY` |
| Nails | `NAILS_PREVIEW_MODE=hybrid`, `nails/remote.py` | `NAILS_REMOTE_URL`, `NAILS_REMOTE_API_KEY` |

Nails also uses `NAILS_HAND_LANDMARKER_PATH`, `NAILS_SEGMENT_PYTHON` and `NAILS_SEGMENT_CHECKPOINT` for local vision assets. Backend settings load at startup (Nails pipeline is lazy); restart after configuration changes. Frontend `NEXT_PUBLIC_API_BASE_URL` points only to FastAPI and is bundled at build time; `FRONTEND_ORIGINS` controls allowed browser origins. Restoring live inference later uses existing separate service handoffs and refreshed configuration. No secrets or temporary service URLs are recorded here.

## Deferred gates and next milestone

The central application architecture is implemented, frontend migrated, and locally/mocked validated. Hair, Makeup and Nails have **NOT** been live end-to-end validated through the centralized path against current Kaggle runtimes. Kaggle remains the intended provider; all three runtimes stay separate. No notebook was started, modified or troubleshot. Legacy routes remain without automatic fallback. GPU consolidation, hosted long-request behavior, broader hand/model quality and stronger Hair provenance remain separate future gates.

Recommended next development milestone: incremental style catalog/presentation expansion using existing registries and this local harness, respecting each feature's supported inference styles. Resume live per-feature central acceptance when the Supervisor reopens GPU validation, before deployment signoff or GPU consolidation. No fourth feature, new style, queue or model change was implemented here.
