# Capstone operator guide

Startup automation is locally verified. The fresh session rehearsal is pending. No deployment acceptance is claimed yet.

## ONE-TIME SETUP

1. Keep the existing private Kaggle Dataset containing `deployment01_20260928_v2.bin`. No new model bundle or upload is needed if it is already available.
2. Import `F:\HAIR\notebooks\capstone_start.ipynb` as a new private Kaggle notebook. Attach that same dataset. Select T4 GPU and Internet manually in Kaggle. Enable `AI_REMOTE_API_KEY` and optional existing `HF_TOKEN`. These settings remain notebook platform setup, not automated changes.
3. Keep the same private API key in the ignored local `backend\.env`, plus the existing Nails asset/interpreter/step settings. Existing Python, Node and frontend dependencies remain installed. No new discovery account, token, topic configuration or `.env` URL editing is needed.
4. Stop any previously manually launched FastAPI/Next servers in their own terminals with Ctrl+C once. The launcher refuses to kill unmanaged processes on ports 8000/3000. After this handover it manages its own processes.

The notebook fetches two small public support scripts from an exact Git commit and verifies their hashes before executing. The attached private bundle, existing notebooks, worker, dependencies and models remain unchanged. Startup can take several minutes in a fresh Kaggle session because exact dependency verification and the Base download/load remain necessary.

## NORMAL CAPSTONE STARTUP

### Kaggle

1. Open the configured notebook.
2. Run the cell labeled **START CAPSTONE**.
3. Wait for **CAPSTONE_AI_READY**.

### Laptop

1. Double-click `F:\HAIR\START_CAPSTONE.bat`.
2. Wait for **CAPSTONE READY**.
3. Open/use http://localhost:3000.

No URL copying, `.env` editing, separate terminals or manual readiness command. A new tunnel URL is discovered automatically. Repeating START on the same healthy managed session reuses it. Changing the session replaces only launcher-owned local processes. No automatic generation retries.

## Shutdown

Double-click `F:\HAIR\STOP_CAPSTONE.bat`. It closes only launcher-owned local backend/frontend processes and their children. Finish the current generation first to keep its result. It does not terminate Kaggle, change adapters or release remote GPU ownership. Stop the Kaggle session manually when finished.

## Failure and emergency override

The notebook/launcher prints `CAPSTONE_STARTUP_FAILED stage=...`. Logs remain in Kaggle `/kaggle/working/capstone/` and local `F:\HAIR\.tmp\capstone\`. An invalid, expired or unreachable discovery record never falls back to an older URL. Discovery records expire after four hours; re-run START CAPSTONE on the same idle healthy notebook to republish without loading Base again.

If the temporary mailbox is unavailable, the notebook still prepares the worker but reports failed publication. To recover explicitly, read the current worker URL in a separate emergency Kaggle cell:

```python
import json
from pathlib import Path
print(json.loads(Path('/kaggle/working/capstone/session/endpoint.json').read_text())['url'])
```

Then in PowerShell:

```powershell
Set-Location F:\HAIR
.\START_CAPSTONE.bat --url <current HTTPS Quick Tunnel URL>
```

The override still checks worker identity/readiness/auth and does not write `.env`. If initialization failed before a URL existed, inspect the reported stage/log and restart a fresh Kaggle session after correcting it. The original Deployment-01 and separate-runtime runbooks remain explicit rollback, not silent launcher fallback.

## Fresh-session rehearsal using this workflow

1. Start a fresh Kaggle session using **START CAPSTONE** above. Do not run the old Cells 1/2/3 or latency-update cell.
2. Double-click **START_CAPSTONE.bat** and wait for **CAPSTONE READY**. Before other generations, run only this four-request rehearsal:

```powershell
Set-Location F:\HAIR
python scripts/deployment01_smoke.py --hair .tmp/deployment01-preflight/gate1/inputs/hairstyle.png --makeup .tmp/deployment01-preflight/gate1/inputs/makeup.jpg --hand "D:\Downloads\nais 2.jpg" --output .tmp/one-click-rehearsal
```

It generates Crew Cut, Natural Makeup, Classic Red Nails, then renderer Nude Pink. It verifies crop counts, correct result contracts, readiness and zero renderer GPU calls; it stops at the first failure without retry. Open the Hair/Makeup/Nails pages to confirm styles and upload controls. No extra stress cycle or image generations are needed.

3. Run the notebook's **COLLECT REHEARSAL EVIDENCE** cell once after the requests. This second cell collects evidence only; normal startup needs just START CAPSTONE.
4. Return Kaggle `/kaggle/working/capstone/session/live-evidence.zip`, local `F:\HAIR\.tmp\one-click-rehearsal\application.json`, and `.tmp\capstone\<session>\startup.json`. If a request failed, also return that session's `backend.log`/`failure.json` and stop, do not repeatedly retry. **Do not send `control.json`**, which contains the private local shutdown token.

Keep Kaggle running until review. If the output directory already exists, choose a fresh name to preserve evidence. `CAPSTONE_DEPLOYMENT_READY` still requires review of this fresh rehearsal.
