# NAILS-001-LOCAL-v1 Kaggle run

**Purpose:** one fresh 50-step localized edit-LoRA checkpoint and held-out review. This does not connect an adapter to the app. Keep the Kaggle Dataset and notebook private because the bundle contains hand photos.

## Setup

1. In Kaggle, create a **private Dataset** containing only [NAILS-001-LOCAL-v1-step050-bundle.bin](../../data/nails/work/NAILS-001-LOCAL-v1-step050-bundle.bin). Its SHA-256 is `73f291b6c580201f6eec8d1f525224638c308e54193c60ee29f26afbd0eb8513` (90,867,024 bytes). The `.bin` extension prevents Kaggle from unpacking the nested approved archives during Dataset upload.
2. Create a fresh private notebook. Attach that private Dataset as an input. In notebook settings, enable a **T4 GPU** and **Internet**. Give the notebook access to your `HF_TOKEN` Kaggle secret if the pinned FLUX model requires it. Use a fresh session so `/kaggle/working/ai-toolkit` is absent.
3. Run the following cells **in order**. Each training and evaluation command starts a fresh Python process.

### Cell 1: verify and extract the input

```python
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile

uploads = list(Path('/kaggle/input').rglob('NAILS-001-LOCAL-v1-step050-bundle.bin'))
assert len(uploads) == 1, uploads
upload = uploads[0]
assert sha256(upload.read_bytes()).hexdigest() == '73f291b6c580201f6eec8d1f525224638c308e54193c60ee29f26afbd0eb8513'
with ZipFile(upload) as bundle:
    assert bundle.testzip() is None
    bundle.extractall('/kaggle/working')
print('Bundle extracted and verified')
```

### Cell 2: verify DATA-N001 and the frozen split

```python
!python /kaggle/working/nails001_local_kaggle.py --phase prepare --root /kaggle/working
```

Expected: `PREFLIGHT_PASS_NOT_TRAINED`, **340 train pairs**, **90 validation pairs**, mean localized nail mask about **11.30%**, with 16 train and 4 distinct validation identities. Stop and send the error if any value differs.

### Cell 3: train the fresh localized adapter to step 50

```python
!python /kaggle/working/nails001_local_kaggle.py --phase train --root /kaggle/working
```

Expected: `CHECKPOINT_READY_REVIEW_REQUIRED`, `sample_trace_count: 50`, `trace_step_sequence_valid: true`, a nonempty checkpoint SHA-256, and a finite loss log. This phase pins FLUX.2 Klein Base and AI Toolkit, preserves Kaggle's Torch/CUDA versions, adds only a guarded per-batch trace call to the pinned trainer, and writes a **new** `nails001_local_v1` adapter. It never reads the old step-25 adapter.

### Cell 4: evaluate the four unseen validation identities

```python
!python /kaggle/working/nails001_local_evaluate.py --root /kaggle/working
```

Expected: `PENDING_VISUAL_REVIEW`, **20** localized comparisons, Base and adapter outputs, plus one-nail full-hand composites. It tests French Tip, Pink Ombre and Nude Pink first, followed by Red and Black. This is inference only.

### Cell 5: package the evidence

```python
!python /kaggle/working/nails001_local_package_evidence.py --root /kaggle/working
```

Download `/kaggle/working/NAILS-001-LOCAL-v1-step050-evidence.zip` and provide it to the Implementation Engineer. It includes the LoRA, optimizer, exact pair exposure trace, training config/log/runtime, hashes, and validation images. **Stop at step 50.** The next training stage depends on visual review of these held-out outputs.

If a cell fails, preserve `/kaggle/working/nails001_local/` and send the error plus `train.log`. Do not restart training from Cell 3 against a folder with existing evidence. The first stage is experimental even if all five cells finish.

If an earlier version of Cell 3 already installed the toolkit and downloaded Base but failed on `numpy.dtype size changed` while importing Diffusers, use the [same-session recovery cell](nails001-local-v1-cell3-recovery.md). It verifies and reuses that setup without reuploading this corrected bundle.
