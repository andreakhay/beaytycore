# TRAIN-002 adapter-switch smoke on Kaggle

Status: **prepared; not yet run on a T4**. The live application registry remains TRAIN-001 only. This check runs a separate localhost GPU server with a smoke-only registry, three sequential inference requests, and no public tunnel. It does not train or alter either checkpoint.

## PC preparation

The derived TRAIN-002 bundle has been created in `F:\HAIR\artifacts\train002_adapter_bundle`. It contains only `adapter.safetensors` and `metadata.json`; the checkpoint hash is `59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b`. The source archive `D:\Downloads\train002_500_artifacts.zip` remains unchanged. If the bundle is missing, recreate it:

```powershell
cd F:\HAIR
python scripts\package_train002_adapter.py --archive 'D:\Downloads\train002_500_artifacts.zip' --output artifacts\train002_adapter_bundle
```

Create a **private Kaggle Dataset** from the two files in `artifacts\train002_adapter_bundle`. Attach it to the smoke notebook along with the existing private TRAIN-001 adapter Dataset. Keep the already used `HAIRCAPSTONE_API_KEY` Kaggle Secret enabled. Do not upload the full optimizer/training archive for this test.

## Fresh Kaggle notebook

Select T4 GPU and enable Internet. Run this one code cell after attaching both adapter Datasets. It obtains the current repository, finds exactly one verified bundle per training run, loads FLUX Base once, and makes three requests. A normal successful run prints `TRAIN-002 SWITCH SMOKE PASS` and a downloadable ZIP path.

```python
from pathlib import Path
import json, os, subprocess, sys

repo = Path('/kaggle/working/CometicsAI')
if repo.exists():
    subprocess.run(['git', '-C', str(repo), 'pull', '--ff-only'], check=True, timeout=180)
else:
    subprocess.run(['git', 'clone', '--depth', '1',
                    'https://github.com/mark-juswa/CometicsAI.git', str(repo)],
                   check=True, timeout=180)

os.environ['HAIRCAPSTONE_STYLE_REGISTRY_PATH'] = str(
    repo / 'backend/app/style_registry_train002_smoke.json')
assert Path(os.environ['HAIRCAPSTONE_STYLE_REGISTRY_PATH']).is_file()

bundles = {}
for meta_path in Path('/kaggle/input').rglob('metadata.json'):
    directory = meta_path.parent
    if not (directory / 'adapter.safetensors').is_file():
        continue
    metadata = json.loads(meta_path.read_text(encoding='utf-8'))
    experiment = metadata.get('experiment')
    if experiment in {'TRAIN-001', 'TRAIN-002'}:
        assert experiment not in bundles, f'Duplicate {experiment} adapter bundle'
        bundles[experiment] = directory
assert set(bundles) == {'TRAIN-001', 'TRAIN-002'}, f'Attach both private adapter Datasets: {bundles}'
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
