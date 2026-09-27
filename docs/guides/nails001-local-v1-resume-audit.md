# Read-only NAILS-001-LOCAL-v1 resume audit

The [step-50 held-out evaluation](../experiments/NAILS-001-LOCAL-v1-step050-evaluation.md) is PARTIAL. No continuation should run until the pinned AI Toolkit's actual checkpoint and optimizer resume behavior is inspected. The evidence ZIP contains checkpoint/optimizer bytes but not the toolkit source.

In the **same Kaggle session**, run this read-only Python cell and download the resulting small ZIP. It does not invoke training or change the checkpoint:

```python
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import sha256
import subprocess, json

root = Path('/kaggle/working/ai-toolkit')
files = [
    'jobs/process/BaseSDTrainProcess.py',
    'extensions_built_in/sd_trainer/SDTrainer.py',
    'toolkit/config_modules.py',
    'toolkit/optimizer.py',
]
commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
assert commit == 'a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7'
output = Path('/kaggle/working/NAILS-001-LOCAL-v1-resume-audit.zip')
assert (root / files[0]).is_file(), 'Pinned trainer source missing'
with ZipFile(output, 'w', ZIP_DEFLATED) as bundle:
    for relative in files:
        path = root / relative
        if path.is_file():
            bundle.write(path, relative)
    bundle.writestr('audit.json', json.dumps({
        'toolkit_commit': commit,
        'checkpoint_sha256': '5bff16c67e0014c78a6d938813347685f914f8a608d76407b10f5b54b7a0eb1f',
        'note': 'Source inspection only; no training or checkpoint change',
    }, indent=2))
print(output, 'SHA-256', sha256(output.read_bytes()).hexdigest())
```

Provide that ZIP to the Implementation Engineer. The next code review will determine whether the 50-step LoRA and optimizer can safely resume to a bounded later checkpoint with an uninterrupted exact sample trace. If Kaggle has already reset, the downloaded step-50 evidence remains intact; the source can be obtained from a fresh pinned checkout, without launching training.
