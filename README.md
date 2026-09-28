# HAIR CAPSTONE

The local application has Hairstyle, Makeup, and Nails pages that call one FastAPI backend. Hairstyle supports `MockEngine` or `RemoteFluxEngine`; Makeup supports mock or `RemoteMakeupEngine`; Nails supports mock or a hybrid pipeline. The verified unified model path uses one temporary authenticated Kaggle GPU service configured in `backend/.env`; original separate services remain rollback. Nails uses its GPU LoRA for Red and Black, and a local renderer for Nude Pink, French Tip, and Pink Ombre. No user upload is stored permanently by the application server. Current evidence and quality limits are in [state](context/state.md).

Gate 3 passed reviewed live application integration with one URL and one persistent Base. Set the complete `AI_REMOTE_URL`/`AI_REMOTE_API_KEY` pair to route Hair, Makeup and Nails AI crop generation to that service; original endpoint settings remain rollback when both are removed. Deployment 01 adds startup/readiness/transport diagnostics and is locally validated; its fresh-session rehearsal is pending. Follow the [exact capstone launch runbook](docs/guides/capstone-deployment01.md) and import [the four-cell notebook](notebooks/deployment01_kaggle.ipynb). This is temporary capstone hosting, not persistent public deployment.

Preferred capstone startup is now additive automation: [import the START CAPSTONE notebook](notebooks/capstone_start.ipynb) once with the same private dataset/Secrets/settings, then run its one startup cell and double-click [START_CAPSTONE.bat](START_CAPSTONE.bat). Signed temporary discovery removes manual URL copying and `.env` edits; [STOP_CAPSTONE.bat](STOP_CAPSTONE.bat) stops only launcher-owned local processes. [Short operator guide](docs/guides/capstone-start.md). This workflow is locally verified (343 backend tests); fresh-session acceptance is pending. Original notebooks/runtime/configuration remain rollback.

The original capstone package includes three TRAIN-001 Hair styles. For Bun and the other ten TRAIN-002 styles, use the separate [expanded private candidate guide](docs/guides/capstone-train002.md). Its real artifacts and mocked shared runtime checks pass locally; live unified TRAIN-002 inference is still pending. The launcher selects the matching catalog automatically from the signed package publication.

The trained model evidence and earlier separate-runtime handoffs are in [TRAIN-001](docs/experiments/TRAIN-001.md), [MAKEUP-001 integration](docs/experiments/MAKEUP-001-integration.md), and [Nails hybrid live handoff](docs/experiments/NAILS-001-hybrid-live-handoff.md). Kaggle remains the current GPU provider. Feature implementations and original runtimes are preserved; see [state](context/state.md).

## Run locally on Windows

The verified development machine has Node.js 24 and Python 3.11. Use two PowerShell terminals.

The initial mock setup below creates a virtual environment; it does not install the full local Nails vision environment. For the verified three-feature demo, use the existing working system Python and retained Nails asset/isolated segmenter configuration in the [deployment runbook](docs/guides/capstone-deployment01.md). Do not rebuild environments each demo.

Terminal 1, backend:

```powershell
cd F:\HAIR\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, frontend:

```powershell
cd F:\HAIR\frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for Hairstyle, [/makeup](http://localhost:3000/makeup) for Makeup, or [/nails](http://localhost:3000/nails) for Nails. The backend listens at `http://127.0.0.1:8000`. If you change its address, edit `frontend/.env.local` and restart Next.js. The backend reads `backend/.env` at startup; use [backend/.env.example](backend/.env.example) for mode, URL, and key names. Each new Kaggle tunnel URL requires updating the ignored backend configuration and restarting FastAPI. `FRONTEND_ORIGINS` defaults to both `localhost:3000` and `127.0.0.1:3000`.

## API contract

| Route | Purpose |
| --- | --- |
| `GET /health` | Returns local API status and the configured generator. |
| `GET /styles` | Returns six prototype styles in mock mode or the three trained style IDs in remote mode. |
| `POST /generate` | Accepts multipart fields `image` and `style_id`; returns status, generator, chosen style, and an image data URL with MIME type and dimensions. |
| `GET /makeup/styles` | Returns ten Makeup presets, independent of the hairstyle adapter registry. |
| `POST /makeup/generate` | Accepts `image` and a Makeup `style_id`; uses the configured mock or remote Makeup engine. |
| `GET /nails/styles` | Returns five Nails styles. |
| `POST /nails/generate` | Accepts `image` and a Nails `style_id`; uses the configured mock or hybrid pipeline. |
| `GET /features` | Lists `hairstyle`, `makeup`, and `nails` with frontend-safe names and descriptions. |
| `GET /features/{feature_id}/styles` | Returns the selected feature's existing style catalog. |
| `POST /features/{feature_id}/generate` | Accepts the same multipart `image` and `style_id` fields and delegates to the selected existing feature handler. |
| `GET /deployment/readiness` | Checks unified configuration/auth, ready idle Base, load count 1 and supported features without images. |
| `GET /deployment/diagnostics[/UUID]` | Safe bounded remote request history; missing history does not imply safe retry. |

The API accepts JPG and PNG files up to 8 MB. Each image dimension must be 64 to 4096 pixels, with no more than 16,777,216 total pixels. It checks the decoded format, corrects EXIF orientation, and converts to RGB. The generator interface in `backend/app/generation/base.py` accepts the validated image and selected style and returns image bytes. `RemoteFluxEngine` implements that interface without loading FLUX on the local PC.

All three pages use `frontend/lib/api.ts` to discover styles and generate results through `/features/{feature_id}`. The client also exposes `getFeatures()`. Legacy backend routes remain available for compatibility, with no automatic frontend fallback. Hair still calls `/health` for its existing mock/model label. Unknown feature IDs return 404; each feature retains its own style validation and remote client. Unified GPU routing is selected explicitly by the shared configuration pair.

## Verify

With both servers running:

```powershell
cd F:\HAIR\backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd F:\HAIR\frontend
npm run lint
npm run build
npm run test:e2e
```

The browser tests use the locally installed Microsoft Edge and a synthetic portrait in `frontend/e2e/fixtures/`. Run them against `npm run build` followed by `npm run start -- --port 3000`; the current Next.js dev server blocks the test origin `127.0.0.1` from its development resources. Use a backend in mock mode for all three features. Tests cover all three central-route browser workflows, mocked model responses, and shared client request/error handling. They do not run the real FLUX model. For an alternate test frontend port, set `PLAYWRIGHT_BASE_URL`; `NEXT_PUBLIC_API_BASE_URL` must select the matching backend at build time.

Phase 3 originally validated the central architecture with 152 backend tests, 28 standard frontend tests and 8 opt-in synthetic remote client/Edge checks. Its test-only server must never be deployed; commands/limits are in [Phase 3 evidence](docs/experiments/central-architecture-phase3.md). Later [Gate 3](docs/experiments/unified-kaggle-gate3.md) independently passed live model/application integration. Deployment 01's full backend suite passes 299 tests; fresh-session startup rehearsal is pending. Separate runtimes and legacy routes remain available. From the repository root, `python scripts/demo_readiness.py` is the image-free pre-demo check; transport generation has no automatic retries.
