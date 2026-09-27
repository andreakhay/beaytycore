# DATA-M001 bounded global FLUX prompt refinement

Status: **20/20 GENERATED; VISUAL GATE FAILED** (2026-09-25). See the [completed visual review](DATA-M001-global-v2-review.md). The following notebook instructions are retained as a reproducible handoff record, not a request to rerun or expand the dataset.

The project lead selected the original global FLUX.2 Klein Base edit workflow as the DATA-M001 target method. The old global 20 remain diagnostic only. Preservation, compositing and inpainting results remain documented research, but are not inputs or postprocessing for this run. This is one bounded rerun of the same two TRAIN identities and ten styles, not an authorization to generate the remaining 100 or train MAKEUP-001 yet.

## Diagnostic basis and one controlled change

The [first 20 review](DATA-M001-pilot-review.md) found severe face reconstruction and smoothing in Natural, Dewy Peach and Matte Nude; mask shaped pigment in Smoky, Rosy, Bronze and Bold; heavy brow/lash changes in Soft; mouth or lip contour changes in Red Lip; and a nearly invisible No-Makeup look. Hair and scene were often recognizable, so this pass focuses on cosmetic intensity, anatomical placement and explicit photographic identity constraints. These weaknesses are observations from two identities, not measured population failure rates.

All ten style instructions and the shared preservation instruction were revised once in [the frozen V2 configuration](../../data/makeup/DATA-M001/config.json). The exact prompt for a job is still its `instruction` followed by one space and `preservation_instruction`. The revised text asks for bounded color in eyelids, cheeks and original lip tissue, natural skin texture and brows, and avoids the observed eye masks, flat pigment, plastic smoothing and black lips. No identity specific prompt or new style was added. The No-Makeup instruction requests a small but visible change while staying subtler than Natural.

The model and inference values are **unchanged** from the first global pilot: `black-forest-labs/FLUX.2-klein-base-4B` revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, Diffusers 0.40.0, 512 by 512, 20 steps, guidance 4.0, seed 1977, FP16, CPU offload, no LoRA. This isolates prompt effects. Any improvement or failure must be assessed visually against the original and first pilot outputs; the revised language itself is not evidence of improvement.

## Frozen input and CPU checks

The [new Kaggle input ZIP](../../.tmp/data_m001/global_v2_release/data_m001_kaggle_input.zip) has SHA256 `96edfc8cc2edfb621ecc1ccdc9867655ec10fa8a6fb8e148ebc6b1d5935d8150`. Its ZIP CRC passed and it contains twelve original source portraits, the frozen source manifest, V2 config and global generation runner, with no raw target, parser, mask, preservation or inpainting asset. The CPU plan verified 20 jobs for `003025` and `054109`, ten unique styles, unchanged inference settings, and `no_lora_confirmation: true`. The original source archive and source metadata hashes were revalidated while preparing this bundle. Forty nine targeted Makeup tests passed. No GPU image has yet been generated from this V2 bundle.

## Kaggle handoff, pilot only

Attach this **new** ZIP as a private Kaggle Dataset to a T4 notebook with Internet enabled. Do not reuse the old input dataset as the runner path. The notebook may use a fresh working folder such as `/kaggle/working/data_m001_global_v2_input`; set `--output` to `/kaggle/working/data_m001_global_v2`, never the old pilot output folder. First extract the ZIP or use Kaggle's already extracted dataset root, then run:

```text
python data_m001_generate_kaggle.py --phase plan --inputs <new-input-root>
python data_m001_generate_kaggle.py --phase pilot --inputs <new-input-root> --output /kaggle/working/data_m001_global_v2
```

Run the same pinned dependency installation used in the successful global pilot if the notebook environment is fresh. The plan should state `job_count: 20`, `prompt_version: global-v2-bounded-refinement`, the two pilot identity IDs and no LoRA. No `--phase remaining` or training command belongs in this notebook yet. The runner creates `/kaggle/working/data_m001_global_v2_results.zip` with all original portraits, full resolution targets, exact prompts, per attempt metadata and hashes, generation log, review sheets and pending reviews. Download it before ending the session.

The side by side review of Original, global V1 and global V2 is complete and failed the visual gate. The 20 successful generations remain official review `PENDING`, with no accepted training pairs. Do not freeze these prompts for the remaining DATA-M001 targets. See the [review and exact blocker](DATA-M001-global-v2-review.md).

### Copy and paste notebook cells

Cell 1 finds the newly attached V2 bundle whether Kaggle exposes its ZIP or unpacked members, verifies its prompt version and plan, and installs the proven package versions. Use a T4 with Internet on. If a model snapshot is already cached from the prior global run, keep that session to avoid another download.

```python
from pathlib import Path
from zipfile import ZipFile
import json, subprocess, sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q",
    "diffusers==0.40.0", "transformers==5.0.0", "accelerate>=1.10,<2",
    "peft>=0.17,<1", "huggingface-hub>=1.23,<2",
    "safetensors>=0.8,<1", "Pillow>=10.1,<13"], check=True)

version = "global-v2-bounded-refinement"
roots = []
for path in Path("/kaggle/input").rglob("config.json"):
    try:
        if json.loads(path.read_text()).get("prompt_version") == version and (path.parent / "data_m001_generate_kaggle.py").is_file():
            roots.append(path.parent)
    except (OSError, ValueError):
        pass
if not roots:
    matches = []
    for path in Path("/kaggle/input").rglob("data_m001_kaggle_input.zip"):
        with ZipFile(path) as archive:
            if json.loads(archive.read("config.json")).get("prompt_version") == version:
                matches.append(path)
    assert len(matches) == 1, f"Expected one V2 input ZIP: {matches}"
    root = Path("/kaggle/working/data_m001_global_v2_input")
    assert not root.exists(), "V2 input folder already exists; inspect before extracting again"
    root.mkdir(parents=True)
    with ZipFile(matches[0]) as archive:
        assert archive.testzip() is None
        archive.extractall(root)
else:
    assert len(roots) == 1, f"Expected one unpacked V2 input root: {roots}"
    root = roots[0]

plan = json.loads(subprocess.run([sys.executable, str(root / "data_m001_generate_kaggle.py"),
    "--phase", "plan", "--inputs", str(root)], check=True, capture_output=True, text=True).stdout)
assert plan["job_count"] == 20
assert plan["prompt_version"] == version
assert {item["identity_id"] for item in plan["jobs"]} == {"003025", "054109"}
assert len({item["style_id"] for item in plan["jobs"]}) == 10
assert plan["inference"]["lora_active"] is False
print("V2 plan verified: 20 global Base edits, same two identities, ten styles, no LoRA")
print("Input:", root)
```

Cell 2 runs only the 20 image pilot and prints an image count every 30 seconds. It keeps the existing output if interrupted, rather than deleting or silently replacing it. No `remaining` or training phase is invoked.

```python
from pathlib import Path
import json, subprocess, sys, time

output = Path("/kaggle/working/data_m001_global_v2")
log = Path("/kaggle/working/data_m001_global_v2_monitor.log")
assert not (output / "summary_pilot.json").exists(), "Pilot already completed; download its ZIP"
command = [sys.executable, "-u", str(root / "data_m001_generate_kaggle.py"),
           "--phase", "pilot", "--inputs", str(root), "--output", str(output)]
started = time.monotonic()
with log.open("ab") as stream:
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
    while process.poll() is None:
        time.sleep(30)
        images = list((output / "targets").rglob("attempt_1.png")) if (output / "targets").exists() else []
        elapsed = int(time.monotonic() - started)
        print(f"Elapsed {elapsed}s | completed images {len(images)}/20", flush=True)
        if elapsed >= 600 and not images:
            print("No first image after ten minutes. Stop and inspect the log before retrying.")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            break
print("Exit code:", process.returncode)
print("Last log text:", log.read_text(errors="replace")[-2500:])
summary_path = output / "summary_pilot.json"
if process.returncode == 0 and summary_path.is_file():
    print("Summary:", summary_path.read_text())
    result = Path("/kaggle/working/data_m001_global_v2_results.zip")
    print("Download:", result, "exists:", result.is_file())
```
