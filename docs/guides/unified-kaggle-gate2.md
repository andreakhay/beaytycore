# Unified Kaggle Gate 2 handoff

2026-09-28. **Gate 2 DONE; GATE_2_PASSED** after independent review of the returned GPU evidence. No rerun is required for acceptance. The notebook/cells below remain the exact reproduction handoff; their completion status still requires review and never auto-passes a gate. Gate 1 results remain unchanged; Gate 3 has not started. See [reviewed results and limits](../experiments/unified-kaggle-gate2.md).

## Files and notebook settings

1. You can create a **new private Kaggle notebook**, keeping the original feature notebooks and Gate 1 session unchanged.
2. You can select **GPU T4 x2** (the setting used for the observed two T4 devices). This experiment uses GPU 0 only. You can enable **Internet** for exact dependency installation and the pinned Base download.
3. You can upload `F:/HAIR/artifacts/unified_gate2_20260928_v5.bin` to a **new private Kaggle dataset**, then attach it as notebook input. This single bundle includes all three read only adapters, approved fixed inputs, verified Gate 1 outputs and experiment code. No other dataset is needed.
4. No inference API keys or tunnel secrets are needed. **HF_TOKEN is optional**, only if Hugging Face account access is needed for download. You can add it through Kaggle Secrets and enable access for this new notebook. Never paste a token into a cell.
5. You can import [unified_gate2_kaggle.ipynb](../../notebooks/unified_gate2_kaggle.ipynb) and run its three code cells in order. Alternatively, the exact cells below are ready to copy and paste.

Bundle: **128,940,681 bytes**, SHA-256 **`0e5ffd854f394f86e5c1ca49d47b9b230b0088aae2da828d893601330d190feb`**, 39 members. Earlier local bundles are drafts; only `_v5.bin` is the handoff. The `.bin` file is a ZIP container; you do not need to rename or manually extract it.

The notebook checks exact observed Python 3.12.13, Torch 2.10.0+cu128, CUDA 12.8 and Tesla T4 before installing dependencies. It stops on a mismatch. It installs exact observed package versions, including Safetensors 0.9.0rc1, and checks the Diffusers commit. A failure is useful evidence; no package/model adjustment is made automatically.

## Cell 1, verify and extract

```python
from pathlib import Path
from hashlib import sha256
import json
import zipfile

BUNDLE_NAME = "unified_gate2_20260928_v5.bin"
BUNDLE_SHA256 = "0e5ffd854f394f86e5c1ca49d47b9b230b0088aae2da828d893601330d190feb"
ROOT = Path("/kaggle/working/gate2_bundle")
OUT = Path("/kaggle/working/unified_gate2")

matches = list(Path("/kaggle/input").rglob(BUNDLE_NAME))
if len(matches) != 1:
    raise RuntimeError("Attach exactly one private Gate 2 bundle dataset.")
if ROOT.exists() or OUT.exists():
    raise RuntimeError("Use a fresh notebook session. Existing experiment files will not be overwritten.")
digest = sha256()
with matches[0].open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != BUNDLE_SHA256:
    raise RuntimeError("Wrong or corrupt Gate 2 upload. Do not extract it.")
with zipfile.ZipFile(matches[0]) as archive:
    names = archive.namelist()
    if len(names) != len(set(names)) or archive.testzip() is not None:
        raise RuntimeError("Bundle inventory or CRC failed.")
    manifest = json.loads(archive.read("gate2_bundle.json"))
    if manifest.get("schema") != "unified-kaggle-gate2-v1":
        raise RuntimeError("Not a Gate 2 bundle.")
    if set(names) != set(manifest["files"]) | {"gate2_bundle.json"}:
        raise RuntimeError("Unexpected bundle member.")
    for name in names:
        path = Path(name)
        target = (ROOT / path).resolve()
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name or not target.is_relative_to(ROOT.resolve()):
            raise RuntimeError("Unsafe bundle path.")
        if name in manifest["files"] and sha256(archive.read(name)).hexdigest() != manifest["files"][name]:
            raise RuntimeError("Bundle file hash failed.")
    ROOT.mkdir(parents=True)
    archive.extractall(ROOT)
print("GATE_2_BUNDLE_VERIFIED", len(names), "members")
print("Next: run Cell 2. No GPU inference has run yet.")
```

## Cell 2, setup and persistent switching

```python
import subprocess
import sys

result = subprocess.run(
    [sys.executable, str(ROOT / "scripts/unified_gate2_bootstrap.py"), "--output", str(OUT)],
    cwd=ROOT,
)
print("Bootstrap exit code:", result.returncode)
print("Run Cell 3 even if setup or switching failed, so partial evidence can be downloaded.")
```

Cell 2 downloads the same Base once, loads one foundation in one persistent process, and runs Hair → Makeup → Nails → Hair → Makeup plus one short Nails → Hair → Makeup cycle. Five controlled adapter failure probes each have a recovery inference. Two competing real inference requests and two cancellation probe requests verify ownership. There are 17 inference outputs on the normal path. Gate 1 observed about 64 to 67 seconds per inference; this is context, not a promised Gate 2 duration. Optional isolated diagnostic repeats run only if output differences appear and only after the shared process exits. No three foundations are resident together.

You can keep the session active until Cell 2 exits, then run Cell 3 even after a failure. Progress is logged under `/kaggle/working/unified_gate2/`.

## Cell 3, status and evidence download

```python
from IPython.display import FileLink, display

setup_path = OUT / "setup.json"
summary_path = OUT / "results/summary.json"
if setup_path.exists():
    setup = json.loads(setup_path.read_text())
    print("Setup status:", setup["status"], "phase:", setup["phase"])
    if setup.get("error"):
        print("Recorded failure:", setup["error"])
if summary_path.exists():
    summary = json.loads(summary_path.read_text())
    print("Probe status:", summary["status"])
    print("Foundation load count:", summary["foundation_load_count"])
    for row in summary["results"]:
        print(row["label"], row["requested_feature"], row["requested_style"],
              "Gate 1 RGB equality:", row["versus_gate1"]["rgb_pixels_equal"],
              "restored RGB equality:", (row["versus_first_shared"] or {}).get("rgb_pixels_equal"),
              "adapter:", row["active_adapter_id"])
    print("Recovery/concurrency probes:", summary["recovery"])
    print("Isolated repeat features:", summary.get("isolated_repeat_required_features", []))
print("No automatic Gate 2 pass. Gate 3 has not started.")
if (OUT / "evidence.zip").exists():
    display(FileLink(str(OUT / "evidence.zip")))
else:
    print("No evidence archive exists yet. Return the cell output if bootstrap never started.")
```

## What you can return

You can download **`/kaggle/working/unified_gate2/evidence.zip`** from Cell 3 or the Kaggle files panel and attach it here, along with all Cell 3 text and the actual accelerator setting. You do not need to extract/review it manually first. Even failed or partial runs should be returned.

Expected successful setup status: **`SWITCHING_COMPLETED_REVIEW_REQUIRED`**, phase `completed`. Expected probe status without differences: **`SWITCHING_COMPLETED_REVIEW_REQUIRED`**, foundation load count `1`. If differences trigger isolated diagnostics, the probe reports `SWITCHING_COMPLETED_ISOLATED_REPEATS_REQUIRED`; the setup finishes with review required after preserving the additional comparisons. Neither status is a Gate 2 pass.

The evidence contains exact environment/provenance, per request PNG/response/comparison, complete ownership/switch/failure events, stage timings, RSS/system RAM, PyTorch allocated/reserved/peaks and whole device samples. Cancellation still preserves its completed inference output. Controlled invalid files are harmless scratch text, never modified real weights. No model/cache weights, credentials or temporary URLs enter the evidence package. **Gate 3 has not started.**
