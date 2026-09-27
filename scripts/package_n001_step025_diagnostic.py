"""Package approved inputs and inference-only train-set probe for Kaggle."""

from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile, ZIP_DEFLATED

from nails001_trainset_probe import DATA_SHA, CHECKPOINT_SHA, digest


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nails/work/DATA-N001-final.zip"
CHECKPOINT = ROOT / "data/nails/work/NAILS-001-pilot-step025-evidence/nails001/checkpoints/nails001_25step/nails001_25step.safetensors"
PROBE = ROOT / "scripts/nails001_trainset_probe.py"
DESTINATION = ROOT / "data/nails/work/NAILS-001-step025-diagnostic-bundle.zip"
UPLOAD = ROOT / "data/nails/work/NAILS-001-step025-diagnostic-upload.bin"

RUN = """NAILS-001 step-25 INFERENCE-ONLY train-set probe. This does not train or update the checkpoint.

1. In a Kaggle GPU notebook, turn Internet on and attach
   NAILS-001-step025-diagnostic-upload.bin as a private input dataset.
   Ensure Hugging Face access to black-forest-labs/FLUX.2-klein-base-4B (HF_TOKEN secret if required).

2. Run this cell to unpack the byte-identical .bin upload only:

from pathlib import Path
from zipfile import ZipFile
bundle = next(Path('/kaggle/input').rglob('NAILS-001-step025-diagnostic-upload.bin'))
work = Path('/kaggle/working/nails-step025-diagnostic')
work.mkdir(exist_ok=True)
with ZipFile(bundle) as archive:
    assert archive.testzip() is None
    archive.extractall(work)
print(work)

3. Use the SAME working runtime as the previous step-25 evaluation if still available.
   In a fresh notebook, run this setup cell (no training):

import subprocess, sys
from pathlib import Path
import importlib.metadata as md
import torch
toolkit = Path('/kaggle/working/ai-toolkit')
if not toolkit.exists():
    subprocess.run(['git', 'init', str(toolkit)], check=True)
    subprocess.run(['git', '-C', str(toolkit), 'fetch', '--depth', '1',
                    'https://github.com/ostris/ai-toolkit.git',
                    'a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7'], check=True)
    subprocess.run(['git', '-C', str(toolkit), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
assert subprocess.check_output(['git', '-C', str(toolkit), 'rev-parse', 'HEAD'], text=True).strip() == \
    'a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7'
constraints = Path('/kaggle/working/nails-step025-torch-constraints.txt')
constraints.write_text('\\n'.join(f'{name}=={md.version(name)}' for name in
                       ('torch', 'torchvision', 'torchaudio')) + '\\n')
subprocess.run([sys.executable, '-m', 'pip', 'install', '--constraint', str(constraints),
                '-r', str(toolkit / 'requirements.txt')], check=True)

4. In a NEW cell (fresh Python process), run inference only:

import subprocess, sys
subprocess.run([sys.executable, '/kaggle/working/nails-step025-diagnostic/nails001_trainset_probe.py',
                '--data', '/kaggle/working/nails-step025-diagnostic/DATA-N001-final.zip',
                '--checkpoint', '/kaggle/working/nails-step025-diagnostic/nails001_25step.safetensors',
                '--output', '/kaggle/working/nails001-trainset-probe'], check=True)

5. Download /kaggle/working/NAILS-001-step025-trainset-probe-results.zip and provide it to Codex.
   The probe covers 4 train identities x 5 styles = 20 pairs, with Base and adapter output.
   Original step-25 sampler indices were not logged, so exposure of each selected pair is UNKNOWN.
"""


def main():
    if DESTINATION.exists() or UPLOAD.exists():
        raise ValueError("Diagnostic bundle or upload copy exists; refusing overwrite")
    if digest(DATA) != DATA_SHA or digest(CHECKPOINT) != CHECKPOINT_SHA:
        raise ValueError("Approved data or checkpoint hash mismatch")
    with ZipFile(DESTINATION, "w", ZIP_DEFLATED) as archive:
        archive.write(DATA, "DATA-N001-final.zip")
        archive.write(CHECKPOINT, "nails001_25step.safetensors")
        archive.write(PROBE, "nails001_trainset_probe.py")
        archive.writestr("RUN.txt", RUN)
    with ZipFile(DESTINATION) as archive:
        if archive.testzip() is not None:
            raise ValueError("Diagnostic bundle CRC failed")
    copyfile(DESTINATION, UPLOAD)
    if digest(UPLOAD) != digest(DESTINATION):
        raise ValueError("Upload copy differs from the diagnostic bundle")
    print(f"{DESTINATION}\n{UPLOAD}\nSHA-256 {digest(DESTINATION)}\nBytes {DESTINATION.stat().st_size}")


if __name__ == "__main__":
    main()
