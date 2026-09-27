# NAILS-001 step-25 Kaggle diagnostic (inference only)

Upload `F:\HAIR\data\nails\work\NAILS-001-step025-diagnostic-upload.bin`, SHA-256 `1a0996b3022919bf38016f0e29de37bc28952c8a7c539f9d1f08e99ee626c13f`. This is a byte-identical copy of `NAILS-001-step025-diagnostic-bundle.zip` with a `.bin` extension so Kaggle does not recursively extract the approved nested DATA-N001 archive. It contains the approved dataset ZIP, intact step-25 adapter, inference-only probe, and `RUN.txt`. **Do not run the old training phase.**

1. In the current Kaggle GPU notebook, upload the `.bin` file above as a new private dataset and attach it as an input. The prior ZIP-based input may remain attached but will not be used. Keep Internet on and provide the same Hugging Face `HF_TOKEN` secret used in the first pilot if needed for FLUX.2 Klein Base access.

2. Extract the byte-identical `.bin` upload in a notebook cell. This replaces the earlier ZIP-discovery cells:

   ```python
   from pathlib import Path
   from zipfile import ZipFile
   from hashlib import sha256

   input_root = Path('/kaggle/input')
   work = Path('/kaggle/working/nails-step025-diagnostic')
   work.mkdir(exist_ok=True)
   uploads = list(input_root.rglob('NAILS-001-step025-diagnostic-upload.bin'))
   assert len(uploads) == 1, f'Expected one .bin upload, found {len(uploads)}'

   def file_sha(path):
       h = sha256()
       with path.open('rb') as stream:
           for chunk in iter(lambda: stream.read(1024 * 1024), b''):
               h.update(chunk)
       return h.hexdigest()

   expected_bundle = '1a0996b3022919bf38016f0e29de37bc28952c8a7c539f9d1f08e99ee626c13f'
   assert file_sha(uploads[0]) == expected_bundle
   with ZipFile(uploads[0]) as archive:
       assert archive.testzip() is None
       archive.extractall(work)

   assert file_sha(work / 'DATA-N001-final.zip') == 'd37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb'
   assert file_sha(work / 'nails001_25step.safetensors') == '34bf82238dfcc8e6365cd9fa6b63d36700312780f2e396dc6d91f7cc3f829c91'
   assert (work / 'nails001_trainset_probe.py').is_file()
   print('Diagnostic inputs ready')
   ```

3. If this is the same working Kaggle environment that successfully imported Torch `2.10.0+cu128` and Diffusers `0.39.0.dev0`, proceed to step 4. In a fresh environment, install the **same pinned toolkit dependencies** in a cell:

   ```python
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
   assert subprocess.check_output(['git', '-C', str(toolkit), 'rev-parse', 'HEAD'], text=True).strip() == 'a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7'
   constraints = Path('/kaggle/working/nails-step025-torch-constraints.txt')
   constraints.write_text('\n'.join(f'{name}=={md.version(name)}' for name in
                              ('torch', 'torchvision', 'torchaudio')) + '\n')
   subprocess.run([sys.executable, '-m', 'pip', 'install', '--constraint', str(constraints),
                   '-r', str(toolkit / 'requirements.txt')], check=True)
   ```

4. **Run only this inference command in a new notebook cell** so the Python process sees the installed package versions:

   ```python
   import subprocess, sys
   subprocess.run([sys.executable, '/kaggle/working/nails-step025-diagnostic/nails001_trainset_probe.py',
                   '--data', '/kaggle/working/nails-step025-diagnostic/DATA-N001-final.zip',
                   '--checkpoint', '/kaggle/working/nails-step025-diagnostic/nails001_25step.safetensors',
                   '--output', '/kaggle/working/nails001-trainset-probe'], check=True)
   ```

5. Download `/kaggle/working/NAILS-001-step025-trainset-probe-results.zip` and provide it to Codex. It should contain 20 five-panel sheets plus Base, adapter and final PNGs, metadata and nail-only target error measurements. The exact 25 pairs seen in training were not logged, so the selected train examples have unknown prior exposure. No conclusion about memorization should be drawn from an individual pair without that caveat.
