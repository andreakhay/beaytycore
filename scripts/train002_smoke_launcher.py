"""Kaggle entry point for the isolated TRAIN-002 adapter-switch smoke."""

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    smoke_registry = ROOT / "backend/app/style_registry_train002_smoke.json"
    if not smoke_registry.is_file():
        raise RuntimeError("Smoke-only registry is missing from the handoff")
    os.environ["HAIRCAPSTONE_STYLE_REGISTRY_PATH"] = str(smoke_registry)
    candidates = set(Path("/kaggle/input").rglob("metadata.json"))
    for name in ("train001_adapter", "train002_adapter"):
        local_metadata = ROOT.parent / name / "metadata.json"
        if local_metadata.is_file():
            candidates.add(local_metadata)
    bundles = {}
    for metadata_path in sorted(candidates):
        directory = metadata_path.parent
        if not (directory / "adapter.safetensors").is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        experiment = metadata.get("experiment")
        if experiment in {"TRAIN-001", "TRAIN-002"}:
            if experiment in bundles:
                raise RuntimeError(f"Duplicate {experiment} bundle: {directory}")
            bundles[experiment] = directory
    if set(bundles) != {"TRAIN-001", "TRAIN-002"}:
        raise RuntimeError("Attach the combined TRAIN-001 plus TRAIN-002 smoke handoff Dataset")
    print("Verified bundle paths:", bundles, flush=True)
    subprocess.run([sys.executable, "-u", str(ROOT / "scripts/kaggle_inference_bootstrap.py"),
                    "--adapter-dir", str(bundles["TRAIN-001"]),
                    "--adapter-dir", str(bundles["TRAIN-002"]), "--local-only"], check=True)
    subprocess.run([sys.executable, "-u", str(ROOT / "scripts/kaggle_train002_switch_smoke.py")],
                   check=True)


if __name__ == "__main__":
    main()
