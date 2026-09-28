# Unified Kaggle Gate 1 handoff

2026-09-28. **Completed run reviewed: GATE_1_PASSED for the three approved individual cases.** See [results and limits](../experiments/unified-kaggle-gate1.md). The exact cells below remain reproduction instructions; no rerun is needed for this accepted archive. No final unified server, Gate 2 or application migration.

## What you upload

Use one NEW private Kaggle notebook and one private Dataset containing only:

- `F:/HAIR/artifacts/unified_gate1_20260928_v2.bin`
- Size: **128,203,008 bytes**
- SHA-256: `8ed784714d534ff767dd261bd5d440d643b526cfac60f2d8dccd47e2c9d44293`

This opaque ZIP upload contains three immutable adapter copies in distinct directories, current unchanged feature runtime source/contracts, fixed inputs, historical reference images and the experimental scripts. It excludes Base weights, training payloads, optimizer states and secrets. Keep it private. Do not attach or extract the three original bundles into the same directory. The old notebooks and inputs remain untouched.

The ready notebook is [unified_gate1_kaggle.ipynb](../../notebooks/unified_gate1_kaggle.ipynb). Import it into a **new** private Kaggle notebook, or paste the three code cells below. Outputs/execution counts in the saved notebook are empty.

## Notebook settings

1. Accelerator: **T4**, or **T4 x2** if that is the available selection. The experiment uses only GPU 0. Record the actual assigned device; no two-GPU pooling.
2. Internet: **ON**.
3. Add Input: attach the private Dataset containing the exact `.bin` above. Do not rename it.
4. Secrets: **no Hair, Makeup, Nails or unified API key is needed**. No server or tunnel starts. Optionally create/enable `HF_TOKEN` through Kaggle Secrets if Hugging Face download access requires it; never paste a token into a cell.
5. Start fresh. Do not run old runtime bootstrap cells in this notebook. Dependency installation changes this new notebook environment only.

## Exact cells

Run cells 1, 2, 3 in order. Cell 2 can take time for package installation, Base download and three separate model loads. Progress/details are saved under `/kaggle/working/unified_gate1/`.

### Cell 1, verify and extract

```python
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import json, shutil, sys, time

BUNDLE_NAME = "unified_gate1_20260928_v2.bin"
EXPECTED_SHA256 = "8ed784714d534ff767dd261bd5d440d643b526cfac60f2d8dccd47e2c9d44293"
ROOT = Path("/kaggle/working/gate1_bundle")
OUT = Path("/kaggle/working/unified_gate1")
started = time.monotonic()
free_before = shutil.disk_usage("/tmp").free
matches = list(Path("/kaggle/input").rglob(BUNDLE_NAME))
if len(matches) != 1:
    raise RuntimeError(f"Attach exactly one private dataset containing {BUNDLE_NAME}; found {len(matches)}")
bundle = matches[0]
h = sha256()
with bundle.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(chunk)
if h.hexdigest() != EXPECTED_SHA256:
    raise RuntimeError("Wrong or corrupted Gate 1 upload. Do not extract it.")
if ROOT.exists() or OUT.exists():
    raise RuntimeError("Prior evidence exists. Use a fresh session, or change ROOT and OUT to new paths.")
ROOT.mkdir(parents=True)
with ZipFile(bundle) as archive:
    if archive.testzip() is not None:
        raise RuntimeError("Bundle CRC failure")
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate ZIP members")
    for name in names:
        target = (ROOT / name).resolve()
        if name.startswith("/") or "\\" in name or ":" in name or not target.is_relative_to(ROOT.resolve()):
            raise RuntimeError("Unsafe ZIP member")
    manifest = json.loads(archive.read("gate1_bundle.json"))
    if set(names) != set(manifest["files"]) | {"gate1_bundle.json"}:
        raise RuntimeError("Unexpected bundle members")
    for name, expected in manifest["files"].items():
        if sha256(archive.read(name)).hexdigest() != expected:
            raise RuntimeError(f"Member hash mismatch: {name}")
    archive.extractall(ROOT)
print("BUNDLE VERIFIED", bundle.name, bundle.stat().st_size, "bytes")
print("Free scratch before extraction:", free_before, "bytes")
print("Extraction/preflight:", round(time.monotonic() - started, 2), "seconds")
```

### Cell 2, install candidate and run the three probes

```python
import subprocess

result = subprocess.run(
    [sys.executable, str(ROOT / "scripts/unified_gate1_bootstrap.py"), "--output", str(OUT)],
    cwd=ROOT,
    check=False,
)
print("Bootstrap exit code:", result.returncode)
print("Run the next cell and return evidence even if this code is nonzero.")
```

### Cell 3, show status and download evidence

```python
from IPython.display import FileLink, display

setup_file = OUT / "setup.json"
if setup_file.exists():
    setup = json.loads(setup_file.read_text())
    print("Setup status:", setup["status"], "phase:", setup["phase"])
    if setup.get("error"):
        print(setup["error"])
summary_file = OUT / "results/summary.json"
if summary_file.exists():
    summary = json.loads(summary_file.read_text())
    print("Probe status:", summary["status"])
    for feature in summary["results"]:
        print(feature["feature"], feature.get("style_id"), feature["status"],
              feature.get("failure_category"), feature.get("error"))
print("No automatic Gate 1 pass. Gate 2 has not started.")
evidence = OUT / "evidence.zip"
if evidence.exists():
    display(FileLink(str(evidence)))
else:
    print("No evidence ZIP. Send the cell error and setup/log files that exist.")
```

Do not change prompts, model settings or dependencies to force a passing run. A failed feature is recorded and the next feature runs in a fresh process. A setup/import failure prevents inference and still produces setup evidence. A stopped notebook/kernel can prevent final ZIP creation; send surviving logs and the exact cell error. If you rerun, use fresh ROOT/OUT paths or a new session so old results are preserved.

## What to send back

Download and attach **`/kaggle/working/unified_gate1/evidence.zip`**, even if a feature failed. Also send the Cell 3 status output and the notebook's actual accelerator selection. The ZIP contains:

- setup/dependency logs, constraints, resolved environment and Base snapshot provenance;
- per-feature report, exact output response, candidate PNG and Input / Historical reference / Candidate comparison;
- original input/reference images and their selected historical records;
- sampled RSS/system RAM, PyTorch allocated/reserved/peaks, whole-device memory, load/adapter/inference timing;
- exact failure boundary, exception and traceback when a worker fails.

Return the ZIP privately. It includes evaluation portraits/crops and generated images; do not commit it or publish the Dataset/notebook.

## Meaning of the result

`INDIVIDUAL_INFERENCE_COMPLETED_REVIEW_REQUIRED` means all three existing generation methods produced contract-valid outputs under the candidate environment. It is **not automatically GATE_1_PASSED**. Codex and the Supervisor must inspect dependency evidence, resources and observed reference differences. There is no invented pixel/quality tolerance.

Historical held-out references are the best available fixed comparisons. Hair/Makeup records do not record their full evaluation dependency versions, and they are not fresh current-service captures. Differences cannot automatically be attributed to this candidate stack. This experiment also does not validate HTTP serving, frontend/backend integration or cross-feature adapter switching.

See [design and local evidence](../experiments/unified-kaggle-gate1.md). Gate 2 has not begun.
