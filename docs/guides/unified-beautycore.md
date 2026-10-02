# Unified BeautyCore local installation

The client facing application is `beautycore/`. The existing AI backend, Nails CPU processing, Kaggle startup support, and rollback UI are in the **same root folder**. The root `START.bat` launches BeautyCore and private FastAPI; it never opens the old `frontend/`. Kaggle remains the separate GPU provider for the capstone.

## Install once

1. Copy this entire unified root to the client's Windows machine. Keep `beautycore/`, `backend/`, `scripts/`, `notebooks/`, and the tracked `data/makeup/` preset together. Do not copy the original `I:` project separately.
2. Install Python 3.11 and Node 24. Install `backend/requirements.txt` in the Python environment used by root `START.bat`. In `beautycore/`, run `npm ci` from its locked package file.
3. Place the private, ignored Nails files **inside this root** at `data/nails/checkpoints/mediapipe/hand_landmarker.task`, `data/nails/checkpoints/mnemic/nails_seg_s_yolov8_v1.pt`, and the isolated segmenter at `data/nails/work/seg-venv/Scripts/python.exe`. The launcher checks their presence and injects these local paths. It does not use stale absolute paths from a previous checkout. These files are not in Git and must be transferred by an authorized private channel.
4. Create ignored `backend/.env` from `backend/.env.example` with the approved local `AI_REMOTE_API_KEY`, `GEMINI_API_KEY`, and `CONSULTATION_PROVIDER=gemini`; retain the Nails inference step setting. Create ignored `beautycore/.env.local` from `beautycore/.env.local.example` with Neon `DATABASE_URL`, a BeautyCore `GEMINI_API_KEY` for its existing Advisor, `SESSION_SECRET`, and a distinct `AI_CONSULTATION_HANDLE_SECRET`. Never commit or print these values. The current temporary Kaggle URL is discovered by the launcher; no `.env` edit is needed for each session.
5. Keep the configured private Kaggle TRAIN-002 notebook, its approved private dataset, T4 GPU setting, Internet setting, and `AI_REMOTE_API_KEY` Secret. The Base and LoRA assets remain in Kaggle's approved private bundle, not in this Git checkout.

## Each session

1. Run the Kaggle notebook's **START CAPSTONE** cell until `CAPSTONE_AI_READY`.
2. Double-click root `START.bat`. Wait for `BEAUTYCORE CAPSTONE READY`.
3. Use the opened BeautyCore site at `http://127.0.0.1:3000`. Client login and `/client/ai-consultation` use BeautyCore's session and server side adapter. Admin and stylist portals remain in this same Next.js application.
4. When finished, wait for any active generation to complete, then double-click root `STOP.bat`. Stop the Kaggle notebook separately.

The imported BeautyCore specific [launcher guide](../../beautycore/docs/guides/capstone-start.md) describes stages, logs, and the explicit emergency URL override. The old root `START_CAPSTONE.bat` starts the historical HAIR frontend; use root `START.bat` for the unified BeautyCore experience.

## Boundaries and current evidence

BeautyCore and FastAPI remain separate **local processes** inside one project folder. This preserves the working Python Nails pipeline, secure Client adapter, and BeautyCore business system. The normal browser only uses BeautyCore. No account, appointment, inventory, service price, or Neon schema migration is part of this import.

The source import, process path relocation, focused adapter/launcher tests, full FastAPI regression, and BeautyCore build are locally checked. **Live Kaggle plus BeautyCore Client acceptance after this move remains pending.** The working source checkpoints and old frontend are retained for rollback. Source control does not include private Nails artifacts, `.env` files, the Kaggle bundle, or generated images; a client install must provide those separately.
