# TRAIN-002: isolated ten-style Edit-LoRA handoff

Status: **500-step training complete; preliminary evaluation reviewed; runtime smoke prepared**. The Supervisor supplied the completed artifact and evaluation archives; local verification passed. See [TRAIN-002 run evidence](TRAIN-002-run.md), [evaluation](TRAIN-002-evaluation.md), and [smoke handoff](../guides/train002-adapter-smoke.md). TRAIN-001 and the three enabled live hairstyles remain unchanged.

## Gate before training

The frozen DATA-002 manifest is SHA-256 `25a3200c9a79be85ce19f690ba81f564d57d55d86d36e6383b0cacd1188ec5ab`. The Supervisor reported a completed Kaggle artifact audit with 120/120 valid generations, no issues, and no reported exact-hash split leakage. The automated finalizer exited zero and wrote `/kaggle/working/data002/final/reports/qa.json`: 100 train and 20 validation identities, 200 train and 40 validation directional pairs, balanced target classes, and no exclusions. The finalized files are preserved in the validated `data002_final.zip` archive; restore them into a fresh Kaggle session before training. This fast path records `review_mode: automated_unreviewed` and no visual QA. The ordinary human-review mode remains available.

`notebooks/train002_kaggle.py` validates the final dataset before writing a training config. It checks source manifest equality, frozen SHA-256, audit provenance, identity and pair counts, target balance, 512×512 RGB decoding, caption alignment, both directions per accepted identity, and absence of exact-hash split leakage. Severe loss of a style or a changed dataset stops preparation. It trains only on `final/train/target` with paired `final/train/reference`. Validation identities never enter the trainer.

## Training choice

Use one new `train002_500step` job, 500 optimizer steps, with checkpoints at 250 and 500. If all 120 generated groups pass structural audit, DATA-002 contains 200 train and 40 validation directions, so 500 steps correspond to about 2.5 training exposures per train pair at batch size one. The class graph yields 20 training targets per style. The 250-step milestone is an inspectable checkpoint within this same run. A 750-step extension is **not** authorized by this plan.

The configuration preserves the TRAIN-001 proven T4 baseline: pinned FLUX.2 Klein Base revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, pinned AI Toolkit commit `a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7`, BF16 training, FP16 adapter save, flowmatch, rank/alpha 16/16 linear and 8/8 conv, AdamW8bit, learning rate `1e-4`, gradient checkpointing, qfloat8 model quantization, low VRAM, 512 resolution, one Tesla T4, and batch size one. The separate output root is `/kaggle/working/train002_500`. No TRAIN-001 artifact or live registry entry is read or written by the trainer.

TRAIN-001 measured 31.84 seconds per step and 8,531 seconds including setup for 250 steps, with a 13,531 MiB peak. At the same step rate, 500 steps would take about **4 hours 25 minutes** of loop time, or roughly **4 hours 35 minutes** with comparable setup overhead. This is a projection, not a guarantee for DATA-002. T4 memory remains tight.

## Kaggle commands

Keep the finalized DATA-002 directory and the frozen repository checkout available in the current session. A fresh session must restore `/kaggle/working/data002/final` from a durable archive first. Run trainer setup only after final QA passes:

```python
from pathlib import Path
import subprocess, sys

repo = Path("/kaggle/working/CometicsAI")
runner = repo / "notebooks/train002_kaggle.py"
out = Path("/kaggle/working/train002_500")
out.mkdir(parents=True, exist_ok=True)
assert (Path("/kaggle/working/data002/final/reports/qa.json")).is_file()
with (out / "bootstrap.log").open("w", encoding="utf-8") as log:
    subprocess.run([sys.executable, "-u", str(runner), "--phase", "bootstrap"],
                   stdout=log, stderr=subprocess.STDOUT, check=True)
print("Trainer setup finished. Log:", out / "bootstrap.log")
```

Restart the Kaggle kernel if the installer changed packages. Then confirm CUDA and prepare without training:

```python
from pathlib import Path
import subprocess, sys, torch

repo = Path("/kaggle/working/CometicsAI")
runner = repo / "notebooks/train002_kaggle.py"
out = Path("/kaggle/working/train002_500")
assert torch.cuda.is_available() and torch.version.cuda, "STOP: Kaggle GPU/CUDA unavailable"
subprocess.run([sys.executable, "-u", str(runner), "--phase", "prepare"], check=True)
print((out / "dataset_evidence.json").read_text())
print((out / "train_config.yaml").read_text())
```

Only after the printed dataset counts and config are correct, start the long Supervisor-run job with notebook output redirected:

```python
with (out / "launcher.log").open("w", encoding="utf-8") as log:
    train002_job = subprocess.Popen(
        [sys.executable, "-u", str(runner), "--phase", "execute"],
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
print("TRAIN-002 PID:", train002_job.pid)
```

Status cell, run periodically without starting a second job:

```python
print("Exit code (None = running):", train002_job.poll())
log = out / "train.log"
print(log.read_text(errors="replace")[-2500:] if log.exists() else "Trainer has not opened train.log")
summary = out / "training_summary.json"
print(summary.read_text() if summary.exists() and train002_job.poll() is not None else "")
```

Success requires `training_summary.json` to say `success: true`, `highest_loss_step: 500`, `exit_code: 0`, and `stop_reason: null`, with finite losses, a final `.safetensors` adapter whose embedded step is 500, and `optimizer.pt`. The runner stops at the first non-finite loss. On success it writes `/kaggle/working/train002_500/adapter/adapter.safetensors` and `metadata.json` with checkpoint hash, class IDs, Base/model revision, exact dataset counts, frozen manifest and final pair hashes, BF16 configuration, and the `automated_unreviewed` warning. Preserve the complete output folder, especially the 250-step checkpoint, 500-step checkpoint, optimizer state, logs, and metadata. Do not publish or enable this adapter in the app yet.

The pinned trainer is known to save model step metadata and `optimizer.pt`; complete optimizer restoration after an interrupted Kaggle session has **not** been verified. `--phase resume-check` reads retained checkpoint steps and optimizer presence without starting training. The execution command refuses to overwrite an existing run. If the run stops early, preserve the directory and inspect `resume-check` plus logs before a controlled continuation. Do not blindly restart training from zero or claim full-state resume.

After a successful run, a separate lightweight evaluation phase can generate one held-out Base and adapter output per style with identical inputs, prompts, seed, resolution, steps, and guidance:

```python
with (out / "evaluation_launcher.log").open("w", encoding="utf-8") as log:
    evaluation_job = subprocess.Popen(
        [sys.executable, "-u", str(runner), "--phase", "evaluate"],
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
print("Evaluation PID:", evaluation_job.pid)
```

This creates ten Base PNGs, ten TRAIN-002 PNGs, `evaluation/metadata.json`, and `evaluation/reference_base_adapter_target.jpg`. Human review should check intended class, identity, realism, catastrophic failures, and whether Perm-Style Curls differs from Wavy Hair. The evaluation code does not automatically enable any new style.
