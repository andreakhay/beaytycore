# HAIR CAPSTONE

The local application has Hairstyle, Makeup, and Nails pages that call one FastAPI backend. Hairstyle supports `MockEngine` or `RemoteFluxEngine`; Makeup supports mock or `RemoteMakeupEngine`; Nails supports mock or a hybrid pipeline. The model paths use separate, temporary authenticated Kaggle GPU services configured in `backend/.env`. Nails uses its GPU LoRA for Red and Black, and a local renderer for Nude Pink, French Tip, and Pink Ombre. The Supervisor reports all three feature paths working. No user upload is stored permanently by the application server. Current evidence and quality limits are in [state](context/state.md).

The trained model evidence and live handoffs are in [TRAIN-001](docs/experiments/TRAIN-001.md), [MAKEUP-001 integration](docs/experiments/MAKEUP-001-integration.md), and [Nails hybrid live handoff](docs/experiments/NAILS-001-hybrid-live-handoff.md). Kaggle remains the GPU provider for the next integration milestone. The current feature implementations are preserved before any shared-runtime work; see [state](context/state.md).

## Run locally on Windows

The verified development machine has Node.js 24 and Python 3.11. Use two PowerShell terminals.

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

Open [http://127.0.0.1:3000](http://127.0.0.1:3000) for Hairstyle, [/makeup](http://127.0.0.1:3000/makeup) for Makeup, or [/nails](http://127.0.0.1:3000/nails) for Nails. The backend listens at `http://127.0.0.1:8000`. If you change its address, edit `frontend/.env.local` and restart Next.js. The backend reads `backend/.env` at startup; use [backend/.env.example](backend/.env.example) for the feature-specific mode, URL, and key names. Kaggle sessions and tunnel URLs must be refreshed when they expire. `FRONTEND_ORIGINS` defaults to both `localhost:3000` and `127.0.0.1:3000`.

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

The API accepts JPG and PNG files up to 8 MB. Each image dimension must be 64 to 4096 pixels, with no more than 16,777,216 total pixels. It checks the decoded format, corrects EXIF orientation, and converts to RGB. The generator interface in `backend/app/generation/base.py` accepts the validated image and selected style and returns image bytes. `RemoteFluxEngine` implements that interface without loading FLUX on the local PC.

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

The browser tests use the locally installed Microsoft Edge and a synthetic portrait in `frontend/e2e/fixtures/`. Run them against `npm run build` followed by `npm run start -- --port 3000`; the current Next.js dev server blocks the test origin `127.0.0.1` from its development resources. Tests cover the Hairstyle mock and mocked remote flows plus the Makeup prototype. They do not run the real FLUX model.
