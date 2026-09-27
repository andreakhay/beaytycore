"""Package finalized real DATA-M001 pairs for isolated Kaggle MAKEUP-001 training."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def package(dataset: Path, runner: Path, presets: Path, output: Path) -> dict:
    qa = json.loads((dataset / "reports" / "qa.json").read_text(encoding="utf-8"))
    if qa.get("status") != "FINALIZED" or qa.get("train_pairs") != 50 or qa.get("validation_pairs") != 10:
        raise ValueError("DATA-M001 is not finalized at the reviewed 50/10 pair count")
    if output.exists():
        raise ValueError(f"Refusing to overwrite existing Kaggle bundle: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(dataset.rglob("*")):
            if path.is_file():
                archive.write(path, (Path("data_m001") / path.relative_to(dataset)).as_posix())
        archive.write(runner, runner.name)
        archive.write(presets, "inference_presets.json")
    with ZipFile(output) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Kaggle bundle CRC failed: {bad}")
        names = archive.namelist()
    return {"bundle": str(output), "bytes": output.stat().st_size, "sha256": digest(output),
            "members": len(names), "dataset_pairs": 60, "training_status": "NOT_STARTED"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--runner", type=Path, default=Path("notebooks/train_m001_kaggle.py"))
    parser.add_argument("--presets", type=Path, default=Path("data/makeup/DATA-M001-paired/inference_presets.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.dataset, args.runner, args.presets, args.output), indent=2))


if __name__ == "__main__":
    main()
