# Integrated capstone startup

## First-time setup

1. Keep the existing configured private unified Kaggle notebook and its dataset/Secrets. No notebook change is needed. Use the approved TRAIN-002 notebook if those Hair styles are required.
2. Keep `backend\.env` at the **unified project root** with the existing unified worker API key, Gemini key, `CONSULTATION_PROVIDER=gemini`, and Nails local assets. The temporary worker URL is discovered at startup; do not edit it into a file.
3. Create BeautyCore's ignored `.env.local` from `.env.local.example` and configure its Neon `DATABASE_URL`, `SESSION_SECRET`, `GEMINI_API_KEY` for the existing Advisor, and a separate `AI_CONSULTATION_HANDLE_SECRET` of at least 32 characters. `AI_FASTAPI_URL` may be omitted; the launcher supplies the private loopback address to the Next process. Do not put either secret in Git.
4. Install `backend\requirements.txt` into the chosen Python environment and run `npm ci` once in the `beautycore` directory. Keep Python and Node on PATH. The launcher resolves all source paths from its own location, so the unified folder can move without an external HAIR checkout. The Nails segmentation interpreter and private checkpoints must be installed under the root `data\nails\` paths used by the backend.
5. Stop old manually started services on ports 8000 and 3000. The launcher reuses only its own verified session. It refuses unmanaged listeners because their process configuration cannot be matched safely to the current Kaggle URL.

## Every demo session

1. In the already configured Kaggle notebook, run **START CAPSTONE** and wait for `CAPSTONE_AI_READY`.
2. Double-click `START.bat` at the **unified project root**, beside `backend\` and `beautycore\`.
3. Wait for `BEAUTYCORE CAPSTONE READY`; use the BeautyCore page opened at `http://127.0.0.1:3000` and sign in as a Client for AI Consultation.

The signed discovery record provides the current temporary endpoint. The launcher checks Kaggle readiness, starts private FastAPI with the URL in its process environment, then starts BeautyCore with `AI_FASTAPI_URL` injected in its process environment. It never edits `.env` files. No images are generated during startup. The Gemini check confirms configured Gemini mode and key presence; it does not make a live Gemini call. The anonymous HTTP check verifies the Client guard. A separate local read-only probe runs the unchanged adapter core against FastAPI `/features` with synthetic client identity; real authenticated Client use is still verified after sign-in.

## Shutdown

Double-click `STOP.bat` at the unified project root. It contacts this launcher's authenticated loopback controller and closes only its Windows job children. Stop the Kaggle notebook separately. Wait for any active generation to finish before stopping local services.

## Failure and recovery

The launcher prints `BEAUTYCORE_STARTUP_FAILED stage=...` with a safe reason. It does not start mocks, rewrite configuration, or silently reuse an old endpoint. Logs are in ignored `beautycore\.tmp\capstone\<session>\`. If the worker cannot be discovered, confirm `CAPSTONE_AI_READY` and rerun root `START.bat`. If the discovery service is unavailable but the current verified Quick Tunnel URL is known, run root `START.bat --url <current HTTPS URL>` as an explicit emergency override. This value is validated and remains process-only. If a port is occupied by an unmanaged process, close that specific terminal/process yourself; the launcher will not kill it.
