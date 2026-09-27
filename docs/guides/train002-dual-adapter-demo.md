# Experimental TRAIN-001 + TRAIN-002 web demo

The isolated T4 smoke verified `crew_cut` (TRAIN-001) → `pixie_cut` (TRAIN-002) → `crew_cut` (TRAIN-001), including adapter hashes and an identical first/third output. This handoff exposes the **same optional 13-style registry** through a temporary public tunnel and the existing local web app. The default registry remains the three TRAIN-001 styles. No real portrait request through this two-adapter public path has been verified yet.

## Kaggle: start the public GPU endpoint

In the new Kaggle account, attach the same private `train002-switch-both-adapters` Dataset used for the passing smoke. Select a T4 GPU, enable Internet, and enable the existing `HAIRCAPSTONE_API_KEY` Kaggle Secret. Keep that value private. Run this single cell. It handles an unpacked Kaggle Input or the original combined ZIP, validates the ZIP hash when extraction is needed, finds both adapter bundles, and runs the existing bootstrap **without** `--local-only`. The bootstrap validates their metadata and hashes, loads the pinned Base, and checks public `/health` before printing READY. If the smoke server is still healthy in this session, it can be reused.

```python
from pathlib import Path
from zipfile import ZipFile
import hashlib, json, os, subprocess, sys

inputs = Path('/kaggle/input')
roots = sorted({p.parent.parent for p in inputs.rglob('kaggle_inference_bootstrap.py')
                if (p.parent.parent / 'backend/app/style_registry_train002_smoke.json').is_file()})
if len(roots) == 1:
    repo = roots[0]
else:
    archives = list(inputs.rglob('train002_switch_both_adapters.zip'))
    assert not roots and len(archives) == 1, f'Attach one combined adapter Dataset: {roots}, {archives}'
    expected = 'eb57d9f60d0ef6848d6e6b690c9386b332a3d8c0c993a45a4782090ef8f58beb'
    assert hashlib.sha256(archives[0].read_bytes()).hexdigest() == expected, 'Handoff ZIP hash mismatch'
    root = Path('/kaggle/working/train002_demo_input')
    root.mkdir(parents=True, exist_ok=True)
    with ZipFile(archives[0]) as source:
        assert source.testzip() is None, 'Handoff ZIP is corrupt'
        assert all((root / name).resolve().is_relative_to(root.resolve())
                   for name in source.namelist()), 'Unsafe ZIP member path'
        source.extractall(root)
    repo = root / 'CometicsAI'

registry = repo / 'backend/app/style_registry_train002_smoke.json'
assert registry.is_file(), registry
os.environ['HAIRCAPSTONE_STYLE_REGISTRY_PATH'] = str(registry)
bundles = {}
for name in ('train001_adapter', 'train002_adapter'):
    directory = repo.parent / name
    metadata = json.loads((directory / 'metadata.json').read_text())
    assert (directory / 'adapter.safetensors').is_file(), directory
    assert metadata['experiment'] in ('TRAIN-001', 'TRAIN-002')
    assert metadata['experiment'] not in bundles, 'Duplicate experiment bundle'
    bundles[metadata['experiment']] = directory
assert set(bundles) == {'TRAIN-001', 'TRAIN-002'}
subprocess.run([
    sys.executable, '-u', str(repo / 'scripts/kaggle_inference_bootstrap.py'),
    '--adapter-dir', str(bundles['TRAIN-001']),
    '--adapter-dir', str(bundles['TRAIN-002']),
], check=True)
```

Wait for `HAIR CAPSTONE GPU SERVER READY` and a `https://…trycloudflare.com` Health URL. The URL must be HTTPS; `127.0.0.1:8765` is only reachable inside Kaggle. The bootstrap refuses to print public READY unless public `/health` confirms Base, both adapter hashes, and all 13 style IDs. It does **not** make a generation request. Keep the Kaggle session running.

The earlier adapter-switch smoke used `--local-only`. Its `http://127.0.0.1:8765` address cannot serve the PC app. Each new Kaggle session needs a fresh public tunnel, and the PC `.env` must use the URL printed by that session. A previous `trycloudflare.com` URL may remain in `.env` while the local API still reports `remote_flux` and all 13 styles; check the printed public `/health` before generating.

If startup stops, inspect `/kaggle/working/haircapstone_runtime/server.log` or `tunnel.log` according to the error. The Base cache and tunnel are temporary and must be rebuilt in a fresh session. The private Kaggle Dataset is durable.

## PC: select the optional 13-style catalog

Edit `F:\HAIR\backend\.env` (copy `.env.example` first if absent) and set these four values. Use the current READY URL without `/health`; use the **same secret value** as the Kaggle Secret. Never paste the secret into chat or source code.

```ini
GENERATION_ENGINE=remote_flux
FLUX_REMOTE_URL=https://<current-session>.trycloudflare.com
FLUX_REMOTE_API_KEY=<same secret as Kaggle>
HAIRCAPSTONE_STYLE_REGISTRY_PATH=F:/HAIR/backend/app/style_registry_train002_smoke.json
```

The file name reflects its original smoke purpose. It is now the explicit opt-in experimental catalog. The frontend learns the 13 IDs from FastAPI `/styles`; it does not select adapters. Restart the local backend after editing `.env`:

```powershell
cd F:\HAIR\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another PowerShell window:

```powershell
cd F:\HAIR\frontend
npm run dev
```

Open `http://127.0.0.1:3000`. Before inference, check `http://127.0.0.1:8000/health` reports `remote_flux` and `http://127.0.0.1:8000/styles` contains 13 styles, including `crew_cut` and `pixie_cut`. Upload one real portrait and try one TRAIN-002 style, then one TRAIN-001 style. The GPU server should keep its Base loaded and route to the corresponding adapter. Each request in the switch smoke took roughly 63 seconds on the T4; a public request can take longer. Confirm the returned image appears on the page and inspect its visual quality. A passing smoke fixture alone does not establish portrait quality.

To restore the three-style fallback, remove or comment out `HAIRCAPSTONE_STYLE_REGISTRY_PATH` in `backend/.env` and restart FastAPI. Keep the same endpoint only while its Kaggle session remains alive. After session expiry, rerun the Kaggle cell in a new session and update `FLUX_REMOTE_URL` locally.
