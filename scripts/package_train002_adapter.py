"""Derive a runtime bundle from a verified TRAIN-002 archive without changing it."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
META = "train002_500/adapter/metadata.json"
WEIGHTS = "train002_500/adapter/adapter.safetensors"
SUMMARY = "train002_500/training_summary.json"
EXPECTED_SHA256 = "59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b"
EXPECTED_MANIFEST_SHA256 = "25a3200c9a79be85ce19f690ba81f564d57d55d86d36e6383b0cacd1188ec5ab"


def package(archive: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Output directory is not empty: {output}")
    with ZipFile(archive) as source:
        if source.testzip() is not None:
            raise ValueError("TRAIN-002 archive failed ZIP integrity check")
        metadata = json.loads(source.read(META))
        summary = json.loads(source.read(SUMMARY))
        data = source.read(WEIGHTS)
    if not (summary.get("success") is True and summary.get("exit_code") == 0
            and summary.get("highest_loss_step") == 500):
        raise ValueError("Archive does not prove successful 500-step training")
    digest = hashlib.sha256(data).hexdigest()
    if (digest != EXPECTED_SHA256 or metadata.get("checkpoint_sha256") != digest
            or metadata.get("checkpoint_bytes") != len(data)
            or metadata.get("experiment") != "TRAIN-002"
            or metadata.get("training_steps") != 500
            or metadata.get("dataset_version") != "DATA-002"
            or metadata.get("dataset_manifest_sha256") != EXPECTED_MANIFEST_SHA256
            or metadata.get("review_mode") != "automated_unreviewed"):
        raise ValueError("TRAIN-002 checkpoint or provenance differs from the verified run")
    registry = json.loads((ROOT / "backend/app/style_registry_train002_smoke.json").read_text(encoding="utf-8"))
    if set(metadata.get("supported_style_ids", [])) != {
            item["style_id"] for item in registry["styles"] if item["adapter_id"] == "train002"}:
        raise ValueError("TRAIN-002 style claims differ from the smoke registry")
    if len(data) < 16:
        raise ValueError("Adapter is too small")
    header_length = struct.unpack("<Q", data[:8])[0]
    if not 0 < header_length < 8 * 1024 * 1024:
        raise ValueError("Invalid safetensors header")
    header = json.loads(data[8:8 + header_length])
    if not isinstance(header, dict) or not any("lora" in key.lower() for key in header):
        raise ValueError("Adapter has no LoRA tensors")
    training = metadata.get("training") or {}
    lora = metadata.get("lora") or {}
    if (training.get("dtype") != "bf16" or training.get("noise_scheduler") != "flowmatch"
            or training.get("lr") != 0.0001 or lora.get("linear") != 16):
        raise ValueError("Training configuration differs from the approved run")
    metadata["adapter_id"] = "train002"
    metadata["training_config"] = {
        "dtype": training["dtype"], "scheduler": training["noise_scheduler"],
        "lora_rank": lora["linear"], "learning_rate": training["lr"],
        "dataset_manifest_sha256": metadata["dataset_manifest_sha256"],
    }
    metadata["deployment_bundle_source"] = archive.name
    metadata["status"] = "SMOKE_TEST_ONLY"
    output.mkdir(parents=True, exist_ok=True)
    (output / "adapter.safetensors").write_bytes(data)
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/train002_adapter_bundle"))
    args = parser.parse_args()
    metadata = package(args.archive, args.output)
    print(json.dumps({"output": str(args.output.resolve()), "checkpoint_sha256": metadata["checkpoint_sha256"],
                      "styles": metadata["supported_style_ids"]}, indent=2))


if __name__ == "__main__":
    main()
