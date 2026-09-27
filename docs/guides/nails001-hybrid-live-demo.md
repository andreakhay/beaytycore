# Nails hybrid live demo

**Status:** Local renderer path and five-style routing are implemented. Live Kaggle GPU loading and real Red and Black browser requests still need a Supervisor run. No training occurs in this guide.

The private runtime bundle contains only the verified `NAILS-001-LOCAL-v1` step-50 LoRA and inference code. It contains no hand photos, training data, or optimizer. The adapter SHA-256 is `5bff16c67e0014c78a6d938813347685f914f8a608d76407b10f5b54b7a0eb1f`. The pinned Base revision is `a3b4f4849157f664bdbc776fd7453c2783562f4d`.

## 1. Start the Nails GPU service on Kaggle

Upload `F:/HAIR/data/nails/work/NAILS-001-LOCAL-v1-runtime-v2.bin` as a **private** Kaggle Dataset. Bundle size is 42,214,993 bytes and SHA-256 is `adf324b0e2bcf6f23f34641c6448b8874898e4b910750c7cc8fe9c002f072699`. Use a separate private notebook with a T4 GPU and Internet enabled. Attach that dataset. Create and enable a Kaggle Secret named `NAILS001_API_KEY` containing a random value of at least 24 characters. The same value goes in the local backend later. If the pinned Base download needs Hugging Face authentication, also enable the existing `HF_TOKEN` Secret.

Run this notebook cell once. It verifies the opaque ZIP before extracting it:

```python
from pathlib import Path
from zipfile import ZipFile
import hashlib, json, subprocess, sys

expected = "adf324b0e2bcf6f23f34641c6448b8874898e4b910750c7cc8fe9c002f072699"
matches = [p for p in Path("/kaggle/input").rglob("*.bin")
           if p.name == "NAILS-001-LOCAL-v1-runtime-v2.bin"]
assert len(matches) == 1, f"Attach exactly one Nails inference Dataset: {matches}"
bundle = matches[0]
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == expected, "Runtime bundle changed"
root = Path("/kaggle/working/nails001_inference")
assert not root.exists(), "This bundle was already extracted. Use the monitor cell."
with ZipFile(bundle) as archive:
    assert archive.testzip() is None, "ZIP CRC failure"
    assert all(not Path(name).is_absolute() and ".." not in Path(name).parts
               for name in archive.namelist()), "Unsafe archive member"
    archive.extractall(root)
manifest = json.loads((root / "bundle.json").read_text())
for name, digest in manifest["files"].items():
    path = (root / name).resolve()
    assert path.is_relative_to(root.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
print("Verified Nails step-50 runtime:", root)
```

Before launching, confirm the notebook can access its attached Secret. Run this cell; it never prints the key:

```python
from kaggle_secrets import UserSecretsClient
key = UserSecretsClient().get_secret("NAILS001_API_KEY")
assert key is not None and len(key) >= 24, "Attach a Nails key of at least 24 characters"
print("NAILS001_API_KEY is attached to this notebook")
```

If Kaggle says no user secret exists for this kernel and label, open **Add-ons → Secrets**, create or select the exact `NAILS001_API_KEY` label, and enable/attach it to this notebook. Rerun the check before starting the service. [Kaggle's User Secrets announcement](https://www.kaggle.com/product-feedback/114053) explains that account secrets must also be attached to a notebook.

Run this second launch cell once. It starts a GPU service and a temporary tunnel in separate processes, so notebook output can return while model loading continues:

```python
out = Path("/kaggle/working/nails001_runtime")
out.mkdir(exist_ok=True)
log = out / "launcher.log"
assert not log.exists(), "Setup was already launched. Use the monitor cell."
with log.open("w", encoding="utf-8") as stream:
    process = subprocess.Popen(
        [sys.executable, "-u", str(root / "scripts/nails001_inference_bootstrap.py")],
        cwd=root, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
print("Nails setup PID:", process.pid)
```

Rerun only this monitor cell while setup works:

```python
print("Setup exit code (None means still running):", process.poll())
for name in ("progress.json", "launcher.log", "dependency_check.log",
             "server.log", "endpoint.json", "health.json"):
    path = out / name
    print("\n" + name + ":")
    print(path.read_text(errors="replace")[-2500:] if path.exists() else "Not written yet")
```

Continue when `progress.json` says `READY` and `health.json` says `lora_active: true`, `adapter_steps: 50`, the exact adapter hash above, and supported styles `classic_red` and `glossy_black`. If setup says `FAILED`, retain the logs and report them. Do not rerun training. A restarted Kaggle session gets a new URL and needs inference setup again.

If the **only** failure was an unattached `NAILS001_API_KEY`, attach it, pass the preflight cell, and retry bootstrap without reuploading or re-extracting the bundle:

```python
from pathlib import Path
import json, subprocess, sys
root = Path("/kaggle/working/nails001_inference")
out = Path("/kaggle/working/nails001_runtime")
assert root.is_dir()
assert json.loads((out / "progress.json").read_text())["stage"] == "FAILED"
retry_log = out / "launcher-retry.log"
assert not retry_log.exists(), "Retry already launched; monitor its log"
with retry_log.open("w", encoding="utf-8") as stream:
    process = subprocess.Popen(
        [sys.executable, "-u", str(root / "scripts/nails001_inference_bootstrap.py")],
        cwd=root, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
print("Nails inference retry PID:", process.pid)
```

Monitor `progress.json`, `launcher-retry.log`, `server.log`, `endpoint.json`, and `health.json`. Preserve the original `launcher.log` as evidence of the first failure.

## 2. Connect the local backend

Keep Kaggle running. Add the following to `F:/HAIR/backend/.env`, preserving Hair and Makeup settings:

```dotenv
NAILS_PREVIEW_MODE=hybrid
NAILS_REMOTE_URL=https://YOUR-NAILS-SESSION.trycloudflare.com
NAILS_REMOTE_API_KEY=YOUR-PRIVATE-NAILS001-SECRET
```

The local default paths already point to the downloaded MediaPipe asset, isolated segmentation Python, and reviewed YOLO nail checkpoint. To use other paths, set `NAILS_HAND_LANDMARKER_PATH`, `NAILS_SEGMENT_PYTHON`, and `NAILS_SEGMENT_CHECKPOINT`. The Ultralytics runtime stays outside Hair and Makeup. For a public deployment, check the [Ultralytics license](https://docs.ultralytics.com/) and the [checkpoint model card](https://huggingface.co/mnemic/nails_seg_yolov8) against the intended distribution.

If the isolated segmentation environment must be recreated on Windows, create a separate virtual environment and install `F:/HAIR/backend/requirements-nails-segmenter.txt` there. Set `NAILS_SEGMENT_PYTHON` to that environment's Python. Keep `mediapipe` in the backend interpreter via `requirements-nails.txt`. Verify the checkpoint and Hand Landmarker file paths before starting the API.

From `F:/HAIR/backend`, start the API:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `F:/HAIR/frontend`, start the page:

```powershell
npm run dev
```

Open `http://localhost:3000/nails`. A clear dorsal hand with 3 to 5 visible nails should work for all five styles. Red and Black call the real step-50 GPU adapter once per isolated nail. Nude Pink, French Tip, and Pink Ombre use the local DATA-N001 renderer. All five outputs pass through the original-mask compositor. The API response metadata records `inference_path` and times; the page does not show that internal route.

For a request using the API directly:

```powershell
curl.exe -F "image=@F:/HAIR/data/nails/work/source-frozen-v4/source/0000000.png;type=image/png" -F "style_id=classic_red" http://127.0.0.1:8000/nails/generate
```

The JSON includes a large base64 image. Use the browser for visual review. If the GPU URL is absent, Red and Black return a clear service error; the renderer styles can still run locally. If a nail mask or crop is unsafe, the API returns a retake message. Do not treat a local fake generator test as live model evidence.

## 3. Run the real two-hand smoke check

Keep Kaggle, the backend, and the frontend running. In a **third** PowerShell window, run:

```powershell
Set-Location F:\HAIR
python scripts/nails001_live_smoke.py
```

If an earlier run stopped after saving some results, restart the backend and run `python scripts/nails001_live_smoke.py --resume` instead. The script verifies each saved image against its recorded SHA-256 and skips those requests; it then runs only the missing styles/hands and writes the final sheet and QA report.

This calls `POST /nails/generate`, not the GPU service directly. It uses reviewed real source hands `0000000` and held-out `0000088`, both rechecked locally with five usable nail masks. It requests Red and Black on both hands, then Nude Pink, French Tip and Pink Ombre on the first hand. It also sends an invalid image and expects a safe error. The script saves `data/nails/work/live-smoke/review-sheet.png`, every result, both nail masks, and `report.json`. The report includes API stage timings, caller wall time, route, nail count, output hash, and outside-mask pixel-change count. Visually inspect the full-size outputs; a passing script alone cannot establish style quality.

The `timing_seconds` metadata reports image validation, normalization, hand localization, nail segmentation, mask/crop preparation, GPU request, server model generation, result reconstruction, compositing, and total API request time. GPU request is the sum of the five sequential per-nail calls; model generation is the sum of server-reported inference durations and sits **inside** GPU request, so do not add the two values together. The first model request measures first-use inference after service load; `health.json` records the separate model-load duration. Later model requests are warm. Keep `environment.json`, `health.json`, `server.log`, and `endpoint.json` from Kaggle for provenance. Do not share the private API key.
