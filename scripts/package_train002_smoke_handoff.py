"""Make a local, minimal Kaggle upload for the isolated TRAIN-002 switch test."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[1]
CODE_FILES = (
    "backend/app/__init__.py",
    "backend/app/registry.py",
    "backend/app/styles.py",
    "backend/app/style_registry.json",
    "backend/app/style_registry_train002_smoke.json",
    "scripts/kaggle_inference_bootstrap.py",
    "scripts/kaggle_inference_requirements.txt",
    "scripts/kaggle_inference_server.py",
    "scripts/kaggle_train002_switch_smoke.py",
    "scripts/train002_smoke_launcher.py",
    "frontend/e2e/fixtures/portrait.png",
)
EXPECTED_ADAPTER_SHA256 = "59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b"
EXPECTED_TRAIN001_SHA256 = "7e3991f8a4e502573d3e82e9ac34c89fdf3f0b66fb337abb026a5b4c9ad080ff"


def package(bundle: Path, train001_bundle: Path, output: Path) -> None:
    checkpoint = bundle / "adapter.safetensors"
    metadata_path = bundle / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (not checkpoint.is_file() or hashlib.sha256(checkpoint.read_bytes()).hexdigest() != EXPECTED_ADAPTER_SHA256
            or metadata.get("checkpoint_sha256") != EXPECTED_ADAPTER_SHA256
            or metadata.get("adapter_id") != "train002"):
        raise ValueError("TRAIN-002 deployment bundle is missing or invalid")
    train001_checkpoint = train001_bundle / "adapter.safetensors"
    train001_metadata_path = train001_bundle / "metadata.json"
    train001_metadata = json.loads(train001_metadata_path.read_text(encoding="utf-8"))
    if (not train001_checkpoint.is_file()
            or hashlib.sha256(train001_checkpoint.read_bytes()).hexdigest() != EXPECTED_TRAIN001_SHA256
            or train001_metadata.get("checkpoint_sha256") != EXPECTED_TRAIN001_SHA256
            or train001_metadata.get("experiment") != "TRAIN-001"
            or train001_metadata.get("training_steps") != 250):
        raise ValueError("Frozen TRAIN-001 deployment bundle is missing or invalid")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite handoff ZIP: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for relative in CODE_FILES:
            path = ROOT / relative
            if not path.is_file():
                raise FileNotFoundError(path)
            archive.write(path, "CometicsAI/" + relative)
        archive.write(checkpoint, "train002_adapter/adapter.safetensors")
        archive.write(metadata_path, "train002_adapter/metadata.json")
        archive.write(train001_checkpoint, "train001_adapter/adapter.safetensors")
        archive.write(train001_metadata_path, "train001_adapter/metadata.json")
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Handoff ZIP integrity failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, default=ROOT / "artifacts/train002_adapter_bundle")
    parser.add_argument("--train001-bundle", type=Path, default=ROOT / "artifacts/train001_adapter_bundle")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/train002_switch_both_adapters.zip")
    args = parser.parse_args()
    package(args.bundle, args.train001_bundle, args.output)
    print(json.dumps({"handoff_zip": str(args.output.resolve()), "bytes": args.output.stat().st_size,
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
