# DATA-002 Philippine hairstyle reassessment and GPU handoff

Status: **previously structurally finalized, but the unsaved Kaggle artifacts were lost when the interactive session ended**. The Supervisor reported 120/120 valid generations and successful automated-unreviewed finalization: 100 train and 20 validation identities, 200 train and 40 validation directional pairs, no exclusions or reported exact-hash split leakage. A new session found no generated/final files or ZIP, and no saved notebook version exists; see [recovery plan](../experiments/DATA-002-recovery.md). Visual QA was not performed. No TRAIN-002 checkpoint exists. The live registry continues to enable only TRAIN-001. The previous technical shortlist and hash are preserved in [DATA-002-technical-shortlist](DATA-002-technical-shortlist/); its approval hash is superseded.

## Source and selection

The original photographic source is `yikaiwang/FaceSketches-HairStyle40`, revision `45de974926fe64551fc2d0b80973335e20ca10e2`. The dataset card declares Apache-2.0; rights in individual celebrity and stock portraits have not been separately verified. Use the `image/` photographs, never the sketches. The source ZIP SHA-256, each selected member path and raw-byte SHA-256, source dimensions, split, target class, and status are frozen in [DATA-002-manifest.json](DATA-002-manifest.json). Its SHA-256 is in [DATA-002-manifest.sha256](DATA-002-manifest.sha256).

All selected images were decoded locally and inspected in the [Philippine-priority selection contact sheets](DATA-002-ph-selection-sheets/). The [requested-class audit](DATA-002-ph-audit/), [replacement audit](DATA-002-ph-alternatives/), and [final class gate audit](DATA-002-final-gate-audit/) show the source photographs. The [curation record](DATA-002-curation.json) names every selected train/validation and reserve file and summarizes rejection reasons. The [machine-readable selection report](DATA-002-selection-report.json) lists reserves, rejected files, counts, target balance, and image-hash checks. These sheets supplement exact hashes for identity review; neither hashes nor thumbnails can prove that celebrity identities are unique. Hairstyle relevance to Philippine users is a product hypothesis; the source portraits are not a representative Filipino-identity sample.

| Source class and proposed display style | Train identities | Validation identities | Reserves | Screened usable | Excluded |
| --- | ---: | ---: | ---: | ---: | ---: |
| `CurtainedHair` — Curtain Hair | 10 | 2 | 2 | 14 | 16 |
| `undercutSidepart` — Side-Part Undercut | 10 | 2 | 3 | 15 | 15 |
| `Perm` — Perm-Style Curls | 10 | 2 | 4 | 16 | 15 |
| `UndercutPompadour` — Pompadour Undercut | 10 | 2 | 4 | 16 | 14 |
| `PonyTail` — Ponytail | 10 | 2 | 4 | 16 | 14 |
| `PixieCut` — Pixie Cut | 10 | 2 | 4 | 16 | 14 |
| `ShoulderLenHair` — Shoulder-Length Hair | 10 | 2 | 4 | 16 | 14 |
| `WaveHair` — Wavy Hair | 10 | 2 | 4 | 16 | 14 |
| `shag` — Shag Hair | 10 | 2 | 2 | 14 | 16 |
| `Bun` — Bun | 10 | 2 | 4 | 16 | 14 |

Nine selected source folders contain 30 raw photographs each; `Perm` contains 31. Screened usable means selected plus reserve, based on visible hairstyle, face visibility, image quality, and apparent identity separation. At the Supervisor's request, the final selection uses `Perm` instead of `SpikyHair`. The selected `Perm` photographs show defined curls or ringlets, while the frozen `WaveHair` selection shows softer, looser waves. The photos do not establish whether the curls were chemically permed, so the visual concept and future user-facing label are **Perm-Style Curls**, not a claim about a treatment. The nine other identity selections are unchanged. `CurtainedHair` and `shag` have only two screened reserves and remain lower-confidence labels. All **120 chosen source files** have unique SHA-256 values. A simple difference-hash check found no near duplicates within its narrow threshold; manual identity review remains the stronger evidence.

Final gate comparison of the original-photo sheets (raw file counts are not usable-identity counts):

| Folder | Raw photos | Visual decision |
| --- | ---: | --- |
| `Fauxhawk` | 30 | Some clear central peaks, but many quiffs, ordinary spikes, children, and repeat celebrities weaken the truthful label. Prior screening had 12 selected and 3 reserves. |
| `SpikyHair` | 30 | Clear upright spikes and 12 previously selected identities, but superseded by the Supervisor's choice of defined curls. No counterpart was generated. |
| `Perm` | 31 | Twelve selected portraits and four reserves show defined curls/ringlets that differ from the softer `WaveHair` selection. Selected as Perm-Style Curls; chemical treatment is unknown. |
| `UndercutLong` | 30 | Some clear long hair with shaved sides, but others hide the shaved side or show profile/rear views; a more niche catalog option. |
| `UndercutCurly` | 30 | Several curly cuts lack visibly short sides; a strict 12-identity undercut selection is uncertain. |
| `CombOver` | 29 | Mixes modern side parts, baldness-covering combovers, wigs, and parody, with apparent repeats; no consistent truthful label separate from `undercutSidepart`. |

## Pairing and calculated budget

Every source style has **two** target neighbors. The graph is two edge-disjoint directed cycles, defined once in `scripts/data002_freeze_manifest.py` and materialized as an explicit `target_style` on each sample in the manifest. Generation and finalization consume the manifest; they do not recalculate the graph. Cycle A is `CurtainedHair → undercutSidepart → UndercutPompadour → Perm → PixieCut → ShoulderLenHair → WaveHair → shag → Bun → PonyTail → CurtainedHair`. Cycle B is `CurtainedHair → Perm → undercutSidepart → PonyTail → Bun → ShoulderLenHair → shag → WaveHair → PixieCut → UndercutPompadour → CurtainedHair`. Selected examples alternate between the two edges, including one validation identity for each edge.

The manifest planner calculates **100 train + 20 validation identities**, **120 first-attempt generation jobs**, and, if every counterpart passes review, **200 train + 40 validation directional pairs**. Each target style receives **20 train + 4 validation pairs** from its own originals and incoming edits. Both directions of an identity remain in the same split. These are exact counts for the revised manifest, conditional on all 120 outputs passing human review. If a rejected case has no acceptable bounded retry/reserve replacement, the finalizer refuses to silently drop it.

`DATA-002-manifest.json` is the source of truth for sample IDs, source paths/hashes, selected status, split, target, prompts via style definitions, generation policy, planning counts, and pair construction. Each `sample_id` also serves as its one-photo `identity_group_id`. The original ZIP and FLUX Base revision are pinned. TRAIN-001 registry and adapter remain untouched.

## Approval gate and fresh Kaggle setup

The generation runner requires the exact manifest hash as an explicit approval argument. **Do not run `--all` until the Project Lead approves the selected classes, source sheets, and pairing graph.** The code must first be available in the GitHub repository the notebook clones. In a fresh Kaggle notebook, select a T4 GPU and enable Internet, then run this setup cell:

```python
from pathlib import Path
import subprocess, sys

repo = Path("/kaggle/working/CometicsAI")
if repo.exists():
    subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], check=True)
else:
    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/mark-juswa/CometicsAI.git", str(repo)], check=True)

import torch
assert torch.cuda.is_available() and torch.version.cuda, "Select Kaggle GPU and restart the session"
print(sys.executable, torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))
sys.path.insert(0, str(repo))
from scripts.kaggle_inference_bootstrap import OUT, dependencies
OUT.mkdir(parents=True, exist_ok=True)
dependencies(torch.__version__, torch.version.cuda)
```

Confirm the plan without GPU generation:

```python
subprocess.run([sys.executable, str(repo / "notebooks/data002_generate_kaggle.py"), "--plan"], check=True)
```

**Only after the Project Lead approves this exact manifest**, launch the resumable Supervisor-run bulk job. The direct `subprocess.run` launcher inherited Kaggle notebook output and repeatedly stalled while the loader wrote progress or warning text. First interrupt that cell and confirm no old generation process remains. Then redirect both child output streams to a file:

```python
import psutil

runner = str(repo / "notebooks/data002_generate_kaggle.py")
active = []
for process in psutil.process_iter(["pid", "cmdline"]):
    try:
        if runner in (process.info["cmdline"] or []):
            active.append(process.info["pid"])
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
assert not active, f"An earlier generation process still runs: {active}"

output = Path("/kaggle/working/data002")
output.mkdir(parents=True, exist_ok=True)
log_path = output / "generation_run.log"
command = [
    sys.executable, "-u", runner, "--all",
    "--approved-manifest-sha256", "25a3200c9a79be85ce19f690ba81f564d57d55d86d36e6383b0cacd1188ec5ab",
]
with log_path.open("a", encoding="utf-8") as log:
    generation_process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
(output / "generation.pid").write_text(str(generation_process.pid), encoding="utf-8")
print("Started PID:", generation_process.pid, "Log:", log_path)
```

Check progress from a separate cell. This only reads files and process state:

```python
from pathlib import Path
import psutil

output = Path("/kaggle/working/data002")
pid = int((output / "generation.pid").read_text())
print("Exit code (None means running):",
      generation_process.poll() if "generation_process" in globals() else "unknown after kernel restart")
print("PID present:", psutil.pid_exists(pid))
log_path = output / "generation_run.log"
print("\n".join(log_path.read_text(errors="replace").splitlines()[-20:]))
print("Completed images:", len(list((output / "generated").glob("*/generated.png"))))
```

The runner uses FLUX.2 Klein Base revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, FP16 inference, CPU offload on one GPU, 512×512, 20 steps, guidance 4.0, seed 1977. It downloads the pinned source ZIP and Base into `/tmp/data002-hf-cache`, verifies the source ZIP/member hashes, loads Base once, and writes `/kaggle/working/data002/generated/<sample_id>/original.png`, `generated.png`, and `generated.json`. It skips only completed results whose sidecar and hashes verify. Review sheets are written under `/kaggle/working/data002/review_sheets/`. Results remain **PENDING_VISUAL_REVIEW**, never accepted automatically. The manifest hash in `/kaggle/working/data002/manifest.sha256` prevents mixing runs. On a new Kaggle session, restore the entire `data002` output directory before rerunning `--all` to resume.
During Base loading, the runner prints a heartbeat every 60 seconds and writes a Python stack trace every 180 seconds to `/kaggle/working/data002/base_load_trace.log`. This was added after the Supervisor reported repeated long Base-load stalls with zero generated images; Kaggle did not show the timed tracebacks sent to notebook stderr. If loading stalls again, interrupt once and preserve the trace file before another attempt; repeating the run without a diagnosis wastes the Kaggle session.
The Supervisor's first saved trace showed both the Transformers weight loader and tqdm monitor blocked in `tqdm.std.fp_write` while the weight display remained at about 155/398. Disabling Transformers progress bars moved the next stall to Python warning output inside Diffusers. Both attempts inherited notebook output. The log-file launch above is the next bounded test; it changes no model or generation parameter. See [stall evidence](../experiments/DATA-002-base-load-stall.md).

## Human review, bounded retry, and later finalization

The Supervisor's log-redirected frozen-manifest run exited `0` and reported 120 `generated.png` files and four review sheets. These are first-attempt outputs, not accepted training pairs. Preserve `/kaggle/working/data002` before the Kaggle session ends. The four sheets and individual images still require explicit human review.

### Authorized fast path for TRAIN-002

The Supervisor subsequently authorized **automated structural acceptance without exhaustive visual review** for DATA-002. This does not change the frozen manifest, generated files, or the normal human-review path below. It records `review_mode: automated_unreviewed`, `TECHNICAL_ACCEPT` decisions, `visual_qa: NOT PERFORMED`, and exact exclusions. It must run against the actual Kaggle output directory before any TRAIN-002 preparation. The previously reported 120 PNG count and exit code do not by themselves establish integrity.

Pull the repository version containing `scripts/paired_dataset.py`'s `audit` and `automated_unreviewed` modes. Then run:

```python
from pathlib import Path
import json, subprocess, sys

repo = Path("/kaggle/working/CometicsAI")
out = Path("/kaggle/working/data002")
approved = "25a3200c9a79be85ce19f690ba81f564d57d55d86d36e6383b0cacd1188ec5ab"
subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], check=True)
with (out / "audit_console.json").open("w", encoding="utf-8") as log:
    subprocess.run([
        sys.executable, str(repo / "scripts/paired_dataset.py"), "audit",
        "--manifest", str(repo / "docs/data/DATA-002-manifest.json"),
        "--generation-dir", str(out / "generated"),
        "--approved-manifest-sha256", approved,
        "--output", str(out / "generation_audit.json"),
    ], check=True, stdout=log)
audit = json.loads((out / "generation_audit.json").read_text())
print({key: audit[key] for key in (
    "expected_generation_jobs", "actual_generated_png_count", "actual_metadata_json_count",
    "valid_generation_count", "actual_pair_counts", "actual_target_distribution",
    "issues", "severely_underrepresented", "exact_hash_split_leakage")})
```

The audit checks the frozen manifest marker, all expected IDs and paths, source and target classes, split, Base model and revision, prompt, seed, attempt, dimensions, RGB decode, timestamps, nonempty files, and image SHA-256 values. It reports unexpected directories, exact duplicate hashes, and exact-hash split leakage. The audit cannot establish that two different photographs show different people or that a hairstyle looks correct.

If `issues` is empty, all ten styles remain balanced, and the reported counts are valid, finalize without creating human ACCEPT claims:

```python
subprocess.run([
    sys.executable, str(repo / "scripts/paired_dataset.py"), "finalize",
    "--manifest", str(repo / "docs/data/DATA-002-manifest.json"),
    "--generation-dir", str(out / "generated"),
    "--output", str(out / "final"),
    "--review-mode", "automated_unreviewed",
    "--approved-manifest-sha256", approved,
], check=True)
print((out / "final/reports/qa.json").read_text())
```

If a small number of jobs are missing or invalid, the audit lists their exact sample IDs. The fast path can finalize the remaining technically valid groups and calculates actual counts, provided every style retains at least half its planned target representation in each split. Preserve the audit and report exclusions to the Project Lead; do not label the resulting data human-reviewed. The runner's `--all` skips complete outputs whose metadata and hashes verify, so missing jobs can be rerun without repeating successful jobs. A corrupt existing file requires inspection and a deliberate targeted repair before rerunning; the runner will not silently overwrite it.

The final DATA-002 output contains `train|val/reference`, `train|val/target`, target caption `.txt` files, `manifests/pairs.json`, `manifests/selection.json`, `manifests/reviews.json`, copied generation metadata, `reports/generation_audit.json`, `reports/qa.json`, and identity/directional contact sheets. The Supervisor's Kaggle QA report calculated 100 train plus 20 validation identities and 200 train plus 40 validation directional pairs. The files have not been independently inspected in this workspace.

After generation, initialize a review manifest (this writes **PENDING**, not ACCEPT):

```python
subprocess.run([sys.executable, str(repo / "scripts/data002_review.py"), "init",
                "--reviews", "/kaggle/working/data002/reviews.json"], check=True)
```

For each image, visually compare original/result in the review sheets and explicitly set `status` to `ACCEPT`, `REGENERATE`, or `REJECT`, with a review note and the accepted attempt number. Accept recognizable hairstyle/identity with no severe artifacts or major scene/pose replacement. Minor hair-color, light, clothing-detail, or accessory drift may pass. The summary command checks all decisions:

```python
subprocess.run([sys.executable, str(repo / "scripts/data002_review.py"), "summary",
                "--reviews", "/kaggle/working/data002/reviews.json"], check=True)
```

For one decision marked `REGENERATE` at attempt 1, run exactly one seed-only retry:

```python
sample_id = "<sample_id_from_review_summary>"
subprocess.run([
    sys.executable, "-u", str(repo / "notebooks/data002_generate_kaggle.py"),
    "--retry", sample_id,
    "--reviews", "/kaggle/working/data002/reviews.json",
    "--approved-manifest-sha256", "25a3200c9a79be85ce19f690ba81f564d57d55d86d36e6383b0cacd1188ec5ab",
], check=True)
```

Review the new `generated_r2.png`, then set `ACCEPT` with `attempt: 2`, or `REJECT`. There is no third attempt. A reserve replacement requires an explicit documented manifest revision before generation and must not cross identity splits.

Only after **all 120 explicit ACCEPT decisions**, finalize with:

```python
subprocess.run([
    sys.executable, str(repo / "scripts/paired_dataset.py"), "finalize",
    "--manifest", str(repo / "docs/data/DATA-002-manifest.json"),
    "--generation-dir", "/kaggle/working/data002/generated",
    "--reviews", "/kaggle/working/data002/reviews.json",
    "--output", "/kaggle/working/data002/final",
], check=True)
```

The finalizer validates generation provenance, hashes, captions, image decoding/RGB/size, duplicate images, class balance, and train/validation grouping before writing `final/train|val/reference|target`, manifests, QA report, and both identity and directional contact sheets. Training is a later phase. Before ending a Kaggle session, preserve `/kaggle/working/data002` as a Kaggle output or archive; `/tmp` model caches are temporary and need not be saved.
