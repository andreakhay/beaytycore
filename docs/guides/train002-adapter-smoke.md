# TRAIN-002 adapter-switch smoke on Kaggle

Status: **prepared; not yet run on a T4**. The live application registry remains TRAIN-001 only. This check runs a separate localhost GPU server with a smoke-only registry, three sequential inference requests, and no public tunnel. It does not train or alter either checkpoint.

## PC preparation

The derived TRAIN-002 bundle has been created in `F:\HAIR\artifacts\train002_adapter_bundle`. It contains only `adapter.safetensors` and `metadata.json`; the checkpoint hash is `59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b`. The source archive `D:\Downloads\train002_500_artifacts.zip` remains unchanged. If the bundle is missing, recreate it:

```powershell
cd F:\HAIR
python scripts\package_train002_adapter.py --archive 'D:\Downloads\train002_500_artifacts.zip' --output artifacts\train002_adapter_bundle
```

The ready-to-upload file is `F:\HAIR\artifacts\train002_smoke_handoff.zip` (42,414,343 bytes; SHA-256 `f4923e4a39c10248aee171825bee04ae95cb8777514906c8505fa8abfdb03b87`). It contains only the minimal inference/smoke code, one test portrait, and the derived TRAIN-002 adapter bundle. If missing, build it locally with `python scripts\package_train002_smoke_handoff.py`. Create a **private Kaggle Dataset** containing this ZIP and attach it to the smoke notebook along with the existing private TRAIN-001 adapter Dataset. Keep the already used `HAIRCAPSTONE_API_KEY` Kaggle Secret enabled. The full optimizer/training archive is not needed.

## Fresh Kaggle notebook

Select T4 GPU and enable Internet. Run this one code cell after attaching the two Datasets. It unpacks the smoke handoff if Kaggle has not already unpacked it, finds exactly one verified bundle per training run, loads FLUX Base once, and makes three requests. It does not fetch or update Git. A normal successful run prints `TRAIN-002 SWITCH SMOKE PASS` and a downloadable ZIP path.

```python
from pathlib import Path
from zipfile import ZipFile
import json, os, shutil, subprocess, sys

inputs = Path('/kaggle/input')
code_roots = sorted({p.parent.parent for p in inputs.rglob('kaggle_inference_bootstrap.py')
                     if p.parent.name == 'scripts' and
                     (p.parent.parent / 'backend/app/style_registry_train002_smoke.json').is_file()})
if len(code_roots) == 1:
    handoff_root = code_roots[0].parent
else:
    archives = list(inputs.rglob('train002_smoke_handoff.zip'))
    assert not code_roots and len(archives) == 1, f'Attach one private TRAIN-002 smoke ZIP: {archives}'
    handoff_root = Path('/kaggle/working/train002_smoke_input')
    handoff_root.mkdir(parents=True, exist_ok=True)
    with ZipFile(archives[0]) as source:
        assert source.testzip() is None, 'Smoke handoff ZIP is corrupt'
        assert all((handoff_root / name).resolve().is_relative_to(handoff_root.resolve())
                   for name in source.namelist()), 'Unsafe ZIP member path'
        source.extractall(handoff_root)

code_root = handoff_root / 'CometicsAI'
repo = Path('/kaggle/working/CometicsAI')
assert code_root.is_dir() and not repo.exists(), 'Use a fresh notebook session for this isolated smoke'
shutil.copytree(code_root, repo)

os.environ['HAIRCAPSTONE_STYLE_REGISTRY_PATH'] = str(
    repo / 'backend/app/style_registry_train002_smoke.json')
assert Path(os.environ['HAIRCAPSTONE_STYLE_REGISTRY_PATH']).is_file()

bundles = {}
for meta_path in sorted(set(inputs.rglob('metadata.json')) | set(handoff_root.rglob('metadata.json'))):
    directory = meta_path.parent
    if not (directory / 'adapter.safetensors').is_file():
        continue
    metadata = json.loads(meta_path.read_text(encoding='utf-8'))
    experiment = metadata.get('experiment')
    if experiment in {'TRAIN-001', 'TRAIN-002'}:
        assert experiment not in bundles, f'Duplicate {experiment} adapter bundle'
        bundles[experiment] = directory
assert set(bundles) == {'TRAIN-001', 'TRAIN-002'}, f'Attach the TRAIN-001 Dataset and TRAIN-002 smoke ZIP: {bundles}'
print('Adapter bundles:', bundles, flush=True)

subprocess.run([sys.executable, '-u', str(repo / 'scripts/kaggle_inference_bootstrap.py'),
                '--adapter-dir', str(bundles['TRAIN-001']),
                '--adapter-dir', str(bundles['TRAIN-002']), '--local-only'],
               check=True)
subprocess.run([sys.executable, '-u', str(repo / 'scripts/kaggle_train002_switch_smoke.py')],
               check=True)
```

The bootstrap validates both checkpoint hashes and metadata before loading. The smoke makes **crew_cut → pixie_cut → crew_cut** requests, checks each returned adapter ID/hash and 512×512 RGB PNG, and checks `/health` after each switch. The last `/health` must report `active_adapter: train001`. Results are saved under `/kaggle/working/train002_switch_smoke/`; download `/kaggle/working/train002_switch_smoke.zip` and return it with any error log. The server log is `/kaggle/working/haircapstone_runtime/server.log`.

Only after the Supervisor returns a passing smoke result should new styles be considered for the live registry. The evaluation sheet identified `curtain_hair`, `pompadour_undercut`, and `side_part_undercut` for additional visual judgment. The smoke does not resolve visual quality. The smoke registry must never be used as the live local app registry.
