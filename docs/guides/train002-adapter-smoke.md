# TRAIN-002 adapter-switch smoke on Kaggle

Status: **Supervisor reported a passing T4 run on 2026-09-25; output ZIP pending local inspection**. The live application registry remains TRAIN-001 only. This check runs a separate localhost GPU server with a smoke-only registry, three sequential inference requests, and no public tunnel. It does not train or alter either checkpoint.

## PC preparation

The frozen TRAIN-001 bundle is in `F:\HAIR\artifacts\train001_adapter_bundle`; TRAIN-002 is in `F:\HAIR\artifacts\train002_adapter_bundle`. Each contains only `adapter.safetensors` and `metadata.json`. TRAIN-001's checkpoint hash is `7e3991f8a4e502573d3e82e9ac34c89fdf3f0b66fb337abb026a5b4c9ad080ff`; TRAIN-002's is `59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b`. The downloaded training archives remain unchanged. If either bundle is missing, recreate it:

```powershell
cd F:\HAIR
python scripts\package_train001_adapter.py --archive 'D:\Downloads\train001_250_with_evaluation.zip' --output artifacts\train001_adapter_bundle
python scripts\package_train002_adapter.py --archive 'D:\Downloads\train002_500_artifacts.zip' --output artifacts\train002_adapter_bundle
```

The ready-to-upload file is `F:\HAIR\artifacts\train002_switch_both_adapters.zip` (84,752,259 bytes; SHA-256 `eb57d9f60d0ef6848d6e6b690c9386b332a3d8c0c993a45a4782090ef8f58beb`). It contains the minimal inference/smoke code, one test portrait, and **both** verified adapter bundles. If missing, build it locally with `python scripts\package_train002_smoke_handoff.py`. Create **one private Kaggle Dataset** containing this ZIP and attach it to the smoke notebook. Enable the `HAIRCAPSTONE_API_KEY` Kaggle Secret. The full optimizer/training archives are not needed.

## Fresh Kaggle notebook

Select T4 GPU and enable Internet. Run this one code cell after attaching the single private Dataset. It unpacks the smoke handoff if Kaggle has not already unpacked it, then launches the complete check. It does not fetch or update Git. A normal successful run prints `TRAIN-002 SWITCH SMOKE PASS` and a downloadable ZIP path.

```python
from pathlib import Path
from zipfile import ZipFile
import subprocess, sys

inputs = Path('/kaggle/input')
launchers = list(inputs.rglob('train002_smoke_launcher.py'))
if len(launchers) == 1:
    launcher = launchers[0]
else:
    archives = list(inputs.rglob('train002_switch_both_adapters.zip'))
    assert not launchers and len(archives) == 1, f'Attach one combined adapter ZIP: {archives}'
    root = Path('/kaggle/working/train002_smoke_input')
    root.mkdir(parents=True, exist_ok=True)
    with ZipFile(archives[0]) as source:
        assert source.testzip() is None, 'Smoke handoff ZIP is corrupt'
        assert all((root / name).resolve().is_relative_to(root.resolve())
                   for name in source.namelist()), 'Unsafe ZIP member path'
        source.extractall(root)
    launcher = root / 'CometicsAI/scripts/train002_smoke_launcher.py'
assert launcher.is_file(), launcher
subprocess.run([sys.executable, '-u', str(launcher)], check=True)
```

The bootstrap validates both checkpoint hashes and metadata before loading. The smoke makes **crew_cut → pixie_cut → crew_cut** requests, checks each returned adapter ID/hash and 512×512 RGB PNG, and checks `/health` after each switch. The last `/health` must report `active_adapter: train001`. Results are saved under `/kaggle/working/train002_switch_smoke/`; download `/kaggle/working/train002_switch_smoke.zip` and return it with any error log. The server log is `/kaggle/working/haircapstone_runtime/server.log`.

Only after the Supervisor returns a passing smoke result should new styles be considered for the live registry. The evaluation sheet identified `curtain_hair`, `pompadour_undercut`, and `side_part_undercut` for additional visual judgment. The smoke does not resolve visual quality. The smoke registry must never be used as the live local app registry.
