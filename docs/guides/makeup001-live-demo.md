# MAKEUP-001 isolated live demo

Status: implementation and local checks complete; live Kaggle inference NEEDS VERIFICATION. Hair runtime, registry, adapters and UI remain unchanged.

The bundle contains only the approved MAKEUP-001 adapter, the ten exact evaluation prompt presets, inference code and training evidence. It contains no source portraits, optimizer state, training entry point or Hair adapter. MAKEUP-001 is a general Makeup edit LoRA; the ten looks are inference presets, not ten FFHQ training classes. Results can retouch identity details, skin tone and texture.

## 1. Upload and configure

Upload `F:/HAIR/artifacts/makeup001_kaggle_runtime_v2.zip` as a **private** Kaggle Dataset. Bundle size: 42,409,973 bytes. SHA256: `cf9625999b7c107f7c40c3aeb4412bbb1d787f90209868e9c357936b90e9140a`. V2 fixes an optional PyTorch GPU memory statistic that failed before the first model call. The checkpoint, prompt presets and inference settings are unchanged.

Create a separate private notebook with GPU Tesla T4 and Internet on. Attach the new inference Dataset, not the previous training Dataset. Do not run this in a session serving Hair. Create and enable a Kaggle Secret named `MAKEUP001_API_KEY` with a random value of at least 24 characters. Keep that value private; it will also be set in the local backend. This is not your Kaggle or Hugging Face account token. If needed, create a suitable random value locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and store it privately.

## 2. Notebook cell: locate and verify inputs

Kaggle may unpack an uploaded ZIP automatically. This cell supports both layouts and copies no training data.

```python
from pathlib import Path
from zipfile import ZipFile
import hashlib, json, subprocess, sys

server_sha256 = 'ec9dd0c10a102a6bb13b4288994f18423c5164969cd131b02f2a4993ed570854'
roots = [p.parent for p in Path('/kaggle/input').rglob('bundle.json')
         if (p.parent / 'scripts/makeup_inference_server.py').is_file()
         and hashlib.sha256((p.parent / 'scripts/makeup_inference_server.py').read_bytes()).hexdigest() == server_sha256]
if roots:
    assert len(roots) == 1, f'Expected one V2 Makeup runtime bundle: {roots}'
    root = roots[0]
else:
    matches = list(Path('/kaggle/input').rglob('makeup001_kaggle_runtime_v2.zip'))
    assert len(matches) == 1, f'Attach the V2 Makeup inference bundle: {matches}'
    assert hashlib.sha256(matches[0].read_bytes()).hexdigest() == 'cf9625999b7c107f7c40c3aeb4412bbb1d787f90209868e9c357936b90e9140a'
    root = Path('/kaggle/working/makeup001_input_v2')
    assert not root.exists(), 'Inspect the existing input folder before extracting again'
    with ZipFile(matches[0]) as archive:
        assert archive.testzip() is None
        archive.extractall(root)

manifest = json.loads((root / 'bundle.json').read_text())
assert manifest['schema'] == 'MAKEUP-001-runtime-bundle-v1'
for name, expected in manifest['files'].items():
    path = (root / name).resolve()
    assert path.is_relative_to(root.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
print('Verified Makeup inference bundle:', root)
```

If the previous V1 service is still running in this same Kaggle session, stop only its recorded Makeup server after its failed request has finished. Leave the tunnel and all other services alone. First run the V2 verification cell above. Then run this cell once:

```python
import os, signal, time

out = Path('/kaggle/working/makeup001_runtime')
record = json.loads((out / 'server_process.json').read_text())
old_pid = record['pid']
command_path = Path(f'/proc/{old_pid}/cmdline')
command = command_path.read_bytes() if command_path.exists() else b''
if command:
    assert b'uvicorn' in command and b'scripts.makeup_inference_server:app' in command, command
    os.kill(old_pid, signal.SIGTERM)
    for _ in range(30):
        if not command_path.exists() or not command_path.read_bytes():
            break
        time.sleep(1)
    else:
        raise RuntimeError('Old Makeup server did not stop; inspect before launching another')
    print('Stopped only the old Makeup server:', old_pid)
else:
    print('Old Makeup server already stopped')
```

The old tunnel can carry the new server once it is ready. Relaunch V2 without deleting the previous logs:

```python
retry_log = out / 'launcher_v2.log'
assert not retry_log.exists(), 'V2 setup already launched; monitor it instead'
with retry_log.open('w', encoding='utf-8') as log:
    setup_process = subprocess.Popen(
        [sys.executable, '-u', str(root / 'scripts/makeup_inference_bootstrap.py')],
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
print('V2 Makeup setup PID:', setup_process.pid)
```

Monitor `progress.json`, `launcher_v2.log`, `server.log`, `endpoint.json` and `health.json` using the monitor cell below, substituting `launcher_v2.log` for `launcher.log`. If Kaggle restarted the session while attaching V2, use the normal start cell below instead. Do not run both launch cells.

## 3. Notebook cell: start once

The setup installs only inference dependencies with CUDA Torch constrained, obtains the pinned Base snapshot in `/tmp`, loads MAKEUP-001 once in FP16 with CPU offload, and opens an authenticated generation service through a temporary tunnel. It writes progress and log files so model download/loading does not depend on notebook output streaming. It does not train or generate a sample during setup. Use this cell for a fresh session only, not after the V2 same-session relaunch above.

```python
out = Path('/kaggle/working/makeup001_runtime')
out.mkdir(parents=True, exist_ok=True)
assert not (out / 'launcher.log').exists(), 'Setup already launched here; inspect the monitor before starting again'
with (out / 'launcher.log').open('w', encoding='utf-8') as log:
    setup_process = subprocess.Popen(
        [sys.executable, '-u', str(root / 'scripts/makeup_inference_bootstrap.py')],
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
print('Makeup setup PID:', setup_process.pid)
```

## 4. Notebook cell: monitor

Rerun only this cell to inspect progress. A setup exit code of 0 means setup finished; the GPU server and tunnel continue running in separate processes. Failure does not imply you should restart training.

```python
print('Setup exit code (None means running):', setup_process.poll())
for name in ('progress.json', 'launcher.log', 'server.log', 'endpoint.json', 'health.json'):
    path = out / name
    print('\n' + name + ':')
    print(path.read_text(errors='replace')[-2500:] if path.exists() else 'Not written yet')
```

Wait for `READY` and a verified public health response showing `feature: makeup`, `adapter_id: MAKEUP-001`, `lora_active: true`, and adapter hash `f6f0419e4259a75102f08a450222ad806e3aec1c2ae50ff89f875139084ae510`. Stop and report the log if setup fails. No real GPU service load is claimed until this check passes.

## 5. Local connection

The setup prints the public `MAKEUP_REMOTE_URL`. Add or update only these Makeup variables in `F:/HAIR/backend/.env`. Preserve all existing Hair variables, URLs and secrets:

```dotenv
MAKEUP_GENERATION_ENGINE=remote_makeup
MAKEUP_REMOTE_URL=https://YOUR-MAKEUP-SESSION.trycloudflare.com
MAKEUP_REMOTE_API_KEY=YOUR-PRIVATE-MAKEUP001-SECRET
```

Restart the local backend using its existing interpreter/environment. Normal launch from `F:/HAIR/backend`:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend normally from `F:/HAIR/frontend`:

```powershell
npm run dev
```

Open `http://localhost:3000/makeup`. Ten style cards should show `MAKEUP-001 preset`, and the action should say `Generate makeup`. Upload a portrait, choose a style, and generate. The local API sends only a normalized 512 by 512 portrait and preset ID to the Makeup service. The GPU service uses the original reviewed prompt, 20 steps, guidance 4.0 and seed 1977, with the verified adapter always active. There is no adapter switching and no preservation/inpainting stage. The client rejects a wrong adapter, revision or preset response instead of silently showing it as MAKEUP-001.

The first live request and visual result are still required. Record the style, returned adapter hash, runtime and visible result. Keep the Kaggle inference session running while using the page. Its temporary URL expires when the session/tunnel stops. No rerun or retraining is needed to restart inference later, but a fresh URL may be needed.

## Mock mode and failures

`MAKEUP_GENERATION_ENGINE=mock` keeps the existing clearly labeled unchanged preview. A configured remote service that times out or fails returns a visible error; it never silently falls back to a mock result. `/makeup/health` reports local configuration only, not a verified remote GPU load. Public GPU `/health` is the separate load check.

GPU requests require the secret and are limited to one in flight. Photos are processed in memory; this service does not save uploaded portraits. Do not make source data, this bundle or the private key public. This remains an academic demo, not permanent deployment or verified identity preservation.
