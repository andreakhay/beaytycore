# TRAIN-002 adapter-switch smoke on Kaggle

Status: **prepared; not yet run on a T4**. The live application registry remains TRAIN-001 only. This check runs a separate localhost GPU server with a smoke-only registry, three sequential inference requests, and no public tunnel. It does not train or alter either checkpoint.

## PC preparation

The derived TRAIN-002 bundle has been created in `F:\HAIR\artifacts\train002_adapter_bundle`. It contains only `adapter.safetensors` and `metadata.json`; the checkpoint hash is `59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b`. The source archive `D:\Downloads\train002_500_artifacts.zip` remains unchanged. If the bundle is missing, recreate it:

```powershell
cd F:\HAIR
python scripts\package_train002_adapter.py --archive 'D:\Downloads\train002_500_artifacts.zip' --output artifacts\train002_adapter_bundle
```

The ready-to-upload file is `F:\HAIR\artifacts\train002_smoke_handoff.zip` (42,415,302 bytes; SHA-256 `82b14928bb6dba39a41b1b8b4c7601a6ed2f2764351bad63a99e84cf6268cc67`). It contains only the minimal inference/smoke code, one test portrait, and the derived TRAIN-002 adapter bundle. If missing, build it locally with `python scripts\package_train002_smoke_handoff.py`. Create a **private Kaggle Dataset** containing this ZIP and attach it to the smoke notebook along with the existing private TRAIN-001 adapter Dataset. Keep the already used `HAIRCAPSTONE_API_KEY` Kaggle Secret enabled. The full optimizer/training archive is not needed.

## Fresh Kaggle notebook

Select T4 GPU and enable Internet. Run this one code cell after attaching the two Datasets. It unpacks the smoke handoff if Kaggle has not already unpacked it, then launches the complete check. It does not fetch or update Git. A normal successful run prints `TRAIN-002 SWITCH SMOKE PASS` and a downloadable ZIP path.

```python
from pathlib import Path
from zipfile import ZipFile
import subprocess, sys

inputs = Path('/kaggle/input')
launchers = list(inputs.rglob('train002_smoke_launcher.py'))
if len(launchers) == 1:
    launcher = launchers[0]
else:
    archives = list(inputs.rglob('train002_smoke_handoff.zip'))
    assert not launchers and len(archives) == 1, f'Attach one TRAIN-002 smoke ZIP: {archives}'
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
