# Recover Cell 3 after the NumPy/Diffusers import error

The submitted Cell 3 traceback stopped at `import diffusers` in the launcher, after the toolkit installation and Base-model download but before `train.log` was created. Pip changed NumPy on disk while the launcher process retained an older imported NumPy extension. The training subprocess never started. This recovery reuses the downloaded Base and the already pinned, patched AI Toolkit checkout. It verifies both before training.

Run **this one Python cell** in the same Kaggle session. Do not rerun Cell 1 or Cell 2. Do not restart the notebook before this recovery, or the temporary Base-model cache may be lost.

```python
import subprocess, sys

recovery = r'''
import json, sys
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, '/kaggle/working')
import nails001_local_kaggle as n

root = Path('/kaggle/working')
out = root / 'nails001_local'
toolkit = root / 'ai-toolkit'
assert (out / 'preflight.json').is_file(), 'Cell 2 preflight is missing'
assert not (out / 'train.log').exists(), 'A training log exists; stop and inspect it'
assert not (out / 'sample_trace.jsonl').exists(), 'A sample trace exists; stop and inspect it'
assert n.checked(['git', 'rev-parse', 'HEAD'], cwd=toolkit) == n.TOOLKIT_COMMIT

trainer = toolkit / 'jobs/process/BaseSDTrainProcess.py'
content = trainer.read_text(encoding='utf-8')
assert content.count(n.INSERT) == 1, 'Expected trace hook is missing or duplicated'
assert sha256(content.replace(n.INSERT, n.ANCHOR).encode('utf-8')).hexdigest() == n.TRACE_SOURCE_SHA_NORMALIZED_LF
assert n.digest(toolkit / 'nails001_local_trace.py') == n.digest(root / 'nails001_local_trace.py')
compile(content, str(trainer), 'exec')

# A new Python process sees the final installed NumPy and Diffusers versions.
import numpy, torch, diffusers
assert torch.cuda.is_available(), 'Kaggle GPU is unavailable'
print('Fresh imports:', numpy.__version__, torch.__version__, diffusers.__version__, flush=True)

def reuse_verified_setup(_root):
    return {'toolkit_commit': n.TOOLKIT_COMMIT, 'reused_verified_setup': True,
            'constraints': (out / 'kaggle_torch_constraints.txt').read_text().splitlines(),
            'packages': {name: n.version(name) for name in
                         ('torch', 'diffusers', 'transformers', 'accelerate',
                          'peft', 'huggingface-hub', 'bitsandbytes')}}

def verified_trace(_toolkit, _root):
    return {'original_trainer_sha256_normalized_lf': n.TRACE_SOURCE_SHA_NORMALIZED_LF,
            'patched_trainer_sha256': n.digest(trainer),
            'trace_module_sha256': n.digest(toolkit / 'nails001_local_trace.py'),
            'patch': 'Verified existing guarded batch trace hook'}

n.install_toolkit_local = reuse_verified_setup
n.patch_trace = verified_trace
print(json.dumps(n.train(root), indent=2))
'''
subprocess.run([sys.executable, '-c', recovery], check=True)
```

Expected: `Fresh imports: ...` followed by `CHECKPOINT_READY_REVIEW_REQUIRED`, `sample_trace_count: 50`, a checkpoint SHA-256, and `trace_step_sequence_valid: true`. This is **real step-50 training**, not a simulation. If the fresh import fails, send that error and stop. If training starts but fails, preserve `nails001_local/train.log` and `sample_trace.jsonl` and send the error; do not rerun training into the same folder.

After a successful recovery, run the original Cell 4 evaluation and Cell 5 evidence packaging from the [main Kaggle guide](nails001-local-v1-kaggle.md). Do not continue past step 50 before visual review.
