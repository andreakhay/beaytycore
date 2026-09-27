# MAKEUP-001 isolated training handoff

Status: **DATA-M001 FINALIZED; MAKEUP-001 TRAINING VERIFIED; PROJECT LEAD APPROVED VISUAL RESULTS; APP IMPLEMENTATION VERIFIED LOCALLY; LIVE REQUEST PENDING** (2026-09-26).

The current task has implemented the isolated Makeup runtime, API and result UI. Full local regression checks passed. Use [the inference-only live demo guide](../guides/makeup001-live-demo.md), not the historical training cells below, for the next run. [Integration evidence](MAKEUP-001-integration.md) distinguishes local checks from the still unverified Kaggle load and live browser request.

The Project Lead reviewed both held-out comparison sheets and approved the rightmost MAKEUP-001 outputs as consistently good. See [evaluation record](MAKEUP-001-evaluation.md) for scope and visible limitations. This permits the isolated app integration under the existing completion direction, but does not establish unchanged identity geometry or subtle-style fidelity.

Local verification of `C:/Users/Gigabyte/Downloads/makeup001_250_with_evaluation.zip` passed ZIP CRC and all listed checkpoint, optimizer and 40 evaluation output hashes. Archive size is 141,368,323 bytes. The full training summary reports success true, exit code 0, highest loss step 250, final save after the last step, and 498 finite recorded loss entries (progress entries can repeat). Runtime including load is 8,623 seconds, with observed whole GPU peak 13,531 MiB. Both held-out identities have ten Base and ten adapter outputs, with `comparison_054109.jpg` and `comparison_056266.jpg`. The archive retains its original `PENDING_HUMAN_REVIEW` state; the subsequent Project Lead approval is recorded separately in the evaluation note. The downloaded archive is sufficient to retain these artifacts after stopping the Kaggle session.

The Project Lead's first Kaggle T4 attempt exited 1 after 140.35 seconds, with `highest_loss_step: 0`, no losses, no checkpoints and no optimizer states. The reported error was `OSError: [Errno 30] Read-only file system` at `/kaggle/input/.../data_m001/train/target/.aitk_size.json`. The pinned AI Toolkit writes a size cache beside training targets, while the initial handoff passed the attached Kaggle Dataset path directly. This was a writable-path integration error, not evidence that the model or paired data failed training. That failed attempt is retained as evidence and was superseded by the successful writable-dataset retry verified above.

The Project Lead reports that the retry at `/kaggle/working/makeup001_250_retry1` has finished. The supplied summary excerpt shows `final_save_logged_after_last_step: true`, a 46,223,600-byte final adapter with SHA256 `f6f0419e4259a75102f08a450222ad806e3aec1c2ae50ff89f875139084ae510`, a 46,223,600-byte step-125 adapter with SHA256 `350bd8f539e937b99ac0225c6b53eb227b5ca6fce8e0690883e4ea569c55838f`, and a 47,115,531-byte optimizer state with SHA256 `b23e6b64ca94774b4946a7043a53a2c8fd48d581221a267a791e7c7cd654447c`. The excerpt does not include `success`, `exit_code`, `highest_loss_step` or finite-loss details. The next notebook cell must assert those fields before calling training complete. No held-out images have been reported.

The Project Lead replaced the failed synthetic DATA-M001 target method with a general Makeup edit LoRA trained on reviewed real FFHQ-Makeup bare to makeup pairs. Numeric `makeup_01` through `makeup_05` positions are not semantic style classes. The ten application styles are evaluation and inference prompt presets only. This handoff does not load TRAIN-001, TRAIN-002, or any Hair adapter.

## DATA-M001 gate

The [frozen selection](../../data/makeup/DATA-M001-paired/selection.json) has ten TRAIN identities (`003681`, `006553`, `015406`, `017290`, `020867`, `022625`, `035149`, `036948`, `051141`, `059106`) and two held-out VALIDATION identities (`054109`, `056266`). All five original archive targets were retained for each. The Project Lead explicitly approved all 60 after inspecting the three contact sheets on 2026-09-26. No pair was rejected or synthesized. The accepted practical gate tolerates some smoothing and retouching but does not prove pixel-exact identity preservation. Real paired targets can still teach some reconstruction; held-out evaluation must test whether the adapter improves rather than amplifies that effect.

The final private dataset is `F:/HAIR/.tmp/data_m001/paired_selection/final_v1/`. Its `reports/qa.json` verifies 50 TRAIN and 10 VALIDATION pairs, 10/2 disjoint identities, explicit reviews, source and target hashes, and captions. `manifests/pairs.json` retains each archive member, identity, split, original photo author/URL/license, target hash, prompt and approval note. `train/reference` and `train/target` carry 50 matching filename stems; validation has 10 matching pairs. The three private review sheets are under `F:/HAIR/.tmp/data_m001/paired_selection/prepared_v1/contact_sheets/`. These image files remain outside Git and should not be published without another rights review. Dataset-level CC BY-NC-SA 4.0 and each original photo's attribution/license are preserved in the manifest.

Captions use one truthful general editing instruction: "Apply realistic makeup visible in the target portrait while preserving the person's identity, facial structure, expression, hairstyle, clothing, and scene." Per-image makeup descriptors were not auto-inferred from the variable archive positions; inventing incorrect style labels would be worse than this common edit instruction. The model's fine-grained prompt responsiveness is an evaluation question, not established by the captions.

## Frozen input and training design

Upload the private [Kaggle input ZIP](../../.tmp/data_m001/paired_selection/data_m001_makeup001_kaggle_input_v3.zip), 5,774,036 bytes, SHA256 `29d9b0b7404d67c05a803dbda21b8ffb60757dc6a5fef98130d1d9feb4c2e046`. It contains the finalized dataset, [MAKEUP-001 runner](../../notebooks/train_m001_kaggle.py) and [ten inference presets](../../data/makeup/DATA-M001-paired/inference_presets.json). The ZIP passed CRC. The runner's local CPU prepare check passed and 56 targeted Makeup tests passed. No GPU training is implied by those checks.

The starting configuration follows the successful TRAIN-001 250-step T4 BF16 Edit-LoRA: AI Toolkit commit `a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7`, FLUX.2 Klein Base 4B revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, 512 resolution, batch 1, LoRA linear rank/alpha 16/16 and conv 8/8, AdamW 8-bit, LR 1e-4, flowmatch, weighted timesteps, gradient checkpointing, quantization and low VRAM mode. It saves at steps 125 and 250. The only deliberate trainer change is the input dataset, job name, and loading the transformer's **pinned local Hugging Face snapshot path**. The pinned AI Toolkit loader accepts a local directory containing `flux-2-klein-base-4b.safetensors`; this prevents an unpinned Hub HEAD download through `name_or_path`. Its Qwen text encoder and VAE still follow the proven AI Toolkit component paths. See [the pinned loader code](https://github.com/ostris/ai-toolkit/blob/a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7/extensions_built_in/diffusion_models/flux2/flux2_model.py) and the [pinned model files](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B/tree/a3b4f4849157f664bdbc776fd7453c2783562f4d). The revised local path has not yet been tested on Kaggle; a loader error would be a concrete technical blocker to fix there.

## Kaggle T4 notebook, exact next run

Create a private Kaggle Dataset from the ZIP. Use a Kaggle GPU notebook with a Tesla T4 and Internet on. Attach that Dataset. The first cell finds either Kaggle's unpacked files or the ZIP:

```python
from pathlib import Path
from zipfile import ZipFile
import hashlib, subprocess, sys

roots = [p.parent for p in Path('/kaggle/input').rglob('train_m001_kaggle.py')
         if (p.parent / 'data_m001/reports/qa.json').is_file()]
if not roots:
    zips = list(Path('/kaggle/input').rglob('data_m001_makeup001_kaggle_input_v3.zip'))
    assert len(zips) == 1, f'Expected one attached bundle: {zips}'
    assert hashlib.sha256(zips[0].read_bytes()).hexdigest() == '29d9b0b7404d67c05a803dbda21b8ffb60757dc6a5fef98130d1d9feb4c2e046'
    root = Path('/kaggle/working/makeup001_input')
    assert not root.exists(), 'Inspect existing input folder before extracting again'
    root.mkdir(parents=True)
    with ZipFile(zips[0]) as archive:
        assert archive.testzip() is None
        archive.extractall(root)
else:
    assert len(roots) == 1, f'Expected one unpacked input root: {roots}'
    root = roots[0]
dataset = root / 'data_m001'
runner = root / 'train_m001_kaggle.py'
assert subprocess.run([sys.executable, '-c', 'import torch; assert torch.cuda.is_available()']).returncode == 0
print('DATA-M001:', dataset, 'GPU ready')
```

Prepare the pinned AI Toolkit checkout and its dependencies. This installation cell may take time. Do not change the notebook's CUDA PyTorch build. A fresh kernel after installation is fine, then rerun cell 1:

```python
from pathlib import Path
import importlib.metadata, subprocess, sys

toolkit = Path('/tmp/exp001-ai-toolkit')
commit = 'a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7'
if not toolkit.exists():
    toolkit.mkdir(parents=True)
    subprocess.run(['git', 'init'], cwd=toolkit, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', 'https://github.com/ostris/ai-toolkit.git'], cwd=toolkit, check=True)
    subprocess.run(['git', 'fetch', '--depth', '1', 'origin', commit], cwd=toolkit, check=True)
    subprocess.run(['git', 'checkout', '--detach', 'FETCH_HEAD'], cwd=toolkit, check=True)
actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=toolkit, text=True).strip()
assert actual == commit, actual
torch_before = importlib.metadata.version('torch')
constraints = Path('/kaggle/working/makeup001_torch_constraints.txt')
pins = [f'torch=={torch_before}']
for name in ('torchvision', 'torchaudio'):
    try:
        pins.append(f'{name}=={importlib.metadata.version(name)}')
    except importlib.metadata.PackageNotFoundError:
        pass
constraints.write_text('\n'.join(pins) + '\n')
subprocess.run([sys.executable, '-m', 'pip', 'install', '--constraint', str(constraints),
                '-r', str(toolkit / 'requirements.txt')], check=True)
assert importlib.metadata.version('torch') == torch_before
subprocess.run([sys.executable, '-c', 'import torch; assert torch.cuda.is_available()'], check=True)
print('Pinned trainer ready:', actual)
```

AI Toolkit writes `.aitk_size.json` beside its training images. Kaggle mounts attached datasets read only, so copy the same reviewed dataset to writable `/kaggle/working` before preparation. The runner rechecks all 60 image hashes after this copy. This is a storage correction, not a new dataset or model configuration:

```python
from pathlib import Path
import shutil, subprocess, sys

staged_dataset = Path('/kaggle/working/data_m001_writable')
if not staged_dataset.exists():
    shutil.copytree(dataset, staged_dataset)
dataset = staged_dataset
out = Path('/kaggle/working/makeup001_250')
base = [sys.executable, str(runner), '--dataset', str(dataset), '--out', str(out)]
subprocess.run(base + ['--phase', 'prepare'], check=True)
print((out / 'train_config.yaml').read_text())
print((out / 'dataset_evidence.json').read_text())
```

If an earlier run failed with `OSError: [Errno 30] Read-only file system` while writing `.aitk_size.json`, leave its logs and `training_summary.json` untouched. Reuse the installed AI Toolkit and the original attached bundle, stage the dataset as above, and prepare a fresh `/kaggle/working/makeup001_250_retry1` output directory. The failed run reached zero training steps and contains no checkpoint. Do not rerun the launch cell with the old output directory.

Only after `PREPARED_NOT_STARTED` and the 50/10 split are shown, launch the one authorized run. The runner will download the pinned transformer file during preflight, record its SHA256, and write `train.log`, `runtime.json`, `command.json`, checkpoints and a final `training_summary.json`:

```python
import subprocess

assert not (out / 'train.log').exists(), 'A MAKEUP-001 run has already started here'
launcher_log = out / 'launcher.log'
with launcher_log.open('w', encoding='utf-8') as stream:
    train_process = subprocess.Popen(base + ['--phase', 'execute'], stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
print('MAKEUP-001 PID:', train_process.pid)
```

Monitor in a separate cell without launching another process:

```python
print('Exit code, None means running:', train_process.poll())
for name in ('launcher.log', 'train.log', 'training_summary.json'):
    path = out / name
    print(name, path.read_text(encoding='utf-8', errors='replace')[-1500:] if path.exists() else 'not yet written')
```

Success requires `success: true`, `highest_loss_step: 250`, finite losses, a final `.safetensors` checkpoint and optimizer state. Preserve the run output before ending Kaggle. When training succeeds, the next cell evaluates both Base and MAKEUP-001 on the same two held-out identities and ten prompt presets:

```python
import json, subprocess

summary = json.loads((out / 'training_summary.json').read_text())
assert summary['success'] is True and summary['highest_loss_step'] == 250
checkpoints = list((out / 'checkpoints').rglob('*.safetensors'))
assert checkpoints
checkpoint = max(checkpoints, key=lambda path: path.stat().st_mtime)
subprocess.run(base + ['--phase', 'evaluate', '--checkpoint', str(checkpoint),
                       '--prompts', str(root / 'inference_presets.json')], check=True)
```

Evaluation creates 20 Base and 20 adapter outputs, two comparison sheets, exact prompts and hashes, all marked `PENDING_HUMAN_REVIEW`. Do not wire the app merely from a successful training exit. Package and download all run artifacts before ending Kaggle:

```python
result_zip = Path('/kaggle/working/makeup001_250_artifacts.zip')
subprocess.run([sys.executable, str(runner), '--phase', 'package',
                '--out', str(out), '--zip', str(result_zip)], check=True)
print('Download:', result_zip)
```

## Current blocker

Training and held-out generation artifacts have been verified from the downloaded ZIP, and the Project Lead approved the displayed MAKEUP-001 results. The isolated runtime, API and UI implementation now passes local tests. The remaining check is a new Kaggle inference session and actual browser request, using [the live guide](../guides/makeup001-live-demo.md). Default Makeup mode remains an explicit mock until the remote settings are configured; Hair remains untouched.
