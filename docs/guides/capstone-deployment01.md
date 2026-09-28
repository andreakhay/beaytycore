# Capstone demo launch, Deployment 01

Preparation is locally validated. **Fresh-session rehearsal is pending.** Kaggle provides a temporary demo runtime, not 24/7 hosting. Nail quality improvement is deferred.

The later [one-cell/one-launcher operator guide](capstone-start.md) is the preferred fresh-session workflow. The manual procedure below and this notebook remain intact as explicit rollback. The existing private bundle is reused unchanged.

## One-time handoff

Upload [deployment01_20260928_v2.bin](../../artifacts/deployment01_20260928_v2.bin) as a **private** Kaggle Dataset. Size 128,962,896 bytes, SHA-256 `68f6c9eb2bc0ce12b2c9c6d89e33f22898fb201b33a792887f6c5967ad16ec4e`. This package reuses the accepted Gate 3 assets and adds diagnostics. Keep the original dataset/runtime as rollback. Do not rebuild the package for every demo.

Import [deployment01_kaggle.ipynb](../../notebooks/deployment01_kaggle.ipynb) into a new private Kaggle notebook. Attach the private dataset. Select Tesla T4 GPU, enable Internet, and enable Secret **`AI_REMOTE_API_KEY`** (same private key as the application, at least 24 characters). Enable optional existing `HF_TOKEN` if your pinned Base download requires it. No secret values belong in cells, screenshots or Git. Setup checks the exact reviewed Python/Torch/CUDA/dependency environment and stops if it differs.

## Each fresh demo session

1. Start this notebook/session with its T4, Internet, dataset and Secrets attached.
2. Run **code Cells 1, 2, 3 in order**. They verify/extract the package, run the accepted bootstrap, and print readiness plus one URL. Expect `READY_FOR_LIVE_ACCEPTANCE` from reused bootstrap and `DEPLOYMENT_01_SERVICE_READY` from Cell 3, Base count 1, `diagnostics_version: deployment-01`, Nails steps `[8,12,20]`. Keep the session active. **Do not run the old latency-update cell**; the package already includes it.
3. Edit the ignored `F:\HAIR\backend\.env` with the URL printed by Cell 3 and the same private API key:

```dotenv
GENERATION_ENGINE=remote_flux
MAKEUP_GENERATION_ENGINE=remote_makeup
NAILS_PREVIEW_MODE=hybrid
AI_REMOTE_URL=https://<ONE URL printed by Cell 3, no feature suffix>
AI_REMOTE_API_KEY=<same private Kaggle Secret>
NAILS_INFERENCE_STEPS=8
```

Keep current Nails hand-landmarker, checkpoint and isolated segmentation Python settings. Keep original feature URL/key variables for rollback. The default bundle supports the three TRAIN-001 Hair styles and existing Makeup/Nails catalogs; it does not add TRAIN-002. Do not switch registries or add adapter mappings as part of this rehearsal.

4. In the terminal running FastAPI, stop it with **Ctrl+C**, then restart. Do not start a second backend on occupied port 8000. On this verified machine use the existing system Python environment that served Gate 3 (the backend `.venv` alone lacks MediaPipe):

```powershell
Set-Location F:\HAIR\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For a persistent local diagnostic log, use this launch instead of the command above:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | Tee-Object -FilePath ..\.tmp\deployment01-backend.log
```

5. In a second terminal:

```powershell
Set-Location F:\HAIR\frontend
npm run dev
```

Use the already installed frontend dependencies. Keep `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`. Open the pages at **http://localhost:3000**, not the dev-resource-blocked `127.0.0.1:3000` origin.

6. In a third terminal, check readiness without generating an image:

```powershell
Set-Location F:\HAIR
python scripts/demo_readiness.py
```

Proceed only on exit 0 and `"ready": true`, Base count 1, all three features and diagnostics version `deployment-01`. A stale URL, key, running-client configuration, mock mode, busy/unready worker or old worker fails clearly. A green check verifies communication/configuration; the full Nails CPU processing is tested by rehearsal below.

Whenever Kaggle changes the URL, repeat step 3, stop/restart FastAPI, and rerun readiness. The key stays private; do not edit frontend GPU settings. Original rollback: remove **both** `AI_REMOTE_URL` and `AI_REMOTE_API_KEY`, restore separate feature settings, select `NAILS_INFERENCE_STEPS=20`, restart FastAPI. No automatic route fallback exists.

## Fresh-session rehearsal, once preparation is ready

Before generating in the pages, run these four central application requests on the fresh worker. Approved Hair/Makeup references were extracted locally during package preflight; use the original hand that passed Gate 3. This command generates only Hair, Makeup, Classic Red and Nude Pink, no stress cycle:

```powershell
Set-Location F:\HAIR
python scripts/deployment01_smoke.py --hair .tmp/deployment01-preflight/gate1/inputs/hairstyle.png --makeup .tmp/deployment01-preflight/gate1/inputs/makeup.jpg --hand "D:\Downloads\nais 2.jpg" --output .tmp/deployment01-rehearsal
```

Expect `REHEARSAL_COMPLETED_REVIEW_REQUIRED`. The command records HTTP status, timings, IDs, safe response metadata and worker provenance/crop counts in `.tmp/deployment01-rehearsal/application.json`. Renderer must add zero GPU requests. No images, secrets or tunnel URLs are saved in this summary. If an output directory already exists, choose another name; preserve earlier evidence. A transport/model failure stops the sequence without retry. Backend console/log and worker records are the next evidence, not repeated generations. If your hand file moved, supply its actual path; do not use the Gate 1 prepared nail crop as a full hand input.

Open Hair, Makeup and Nails pages at `localhost:3000` to confirm their styles/upload controls still load. Gate 3 already verified real browser generation; additional expensive page generations are not required for this fresh-session startup rehearsal.

After the requests finish, run notebook **Cell 4 once**. Return:

* Kaggle `/kaggle/working/deployment01/live-evidence.zip`.
* Local `F:\HAIR\.tmp\deployment01-rehearsal\application.json`.
* Backend diagnostic log if any request failed.

Cell 4 preserves startup, version/environment, protected status, safe HTTP probes and server logs/source hashes. It prints `DEPLOYMENT_01_REHEARSAL_REVIEW_REQUIRED`. This is not an automatic deployment pass. Keep Kaggle running until evidence review.

## If a 502 occurs

Copy the `correlation_id` or remote `request_id` from the backend JSON log (the rehearsal also records the hand correlation ID). Query history without inference:

```powershell
python scripts/demo_readiness.py --request-id <UUID from the log>
```

Optional safe snapshot:

```powershell
python scripts/demo_readiness.py --snapshot --output .tmp/deployment01-status.json
```

The log distinguishes preflight versus POST, crop/finger, attempt 1, headers versus complete body receipt, HTTP status, connection/timeout/protocol exception class and elapsed time. Worker history shows whether the ID was observed and whether inference completed. Missing bounded history means **unknown**, not proof that no work began. The server retains ownership while GPU work drains. Wait for an idle ready worker before any deliberate manual retry. Do not retry validation errors or an unready/inference-failed worker blindly. There are **zero automatic retries**, including 429.
