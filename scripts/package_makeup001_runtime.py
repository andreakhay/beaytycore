"""Create an inference-only MAKEUP-001 Kaggle bundle from verified training evidence."""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.makeup_contract import (ADAPTER_BYTES, ADAPTER_ID, ADAPTER_SHA256, INFERENCE, MODEL_ID,
                                 MODEL_REVISION, PRESETS_PATH, PRESETS_SHA256, PROMPTS)


def package(archive: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Refusing to overwrite an existing Makeup runtime bundle")
    with ZipFile(archive) as source:
        if source.testzip():
            raise ValueError("MAKEUP-001 results ZIP failed CRC")
        summary = json.loads(source.read("training_summary.json"))
        runtime = json.loads(source.read("runtime.json"))
        evaluation = json.loads(source.read("evaluation/metadata.json"))
        if (summary.get("success") is not True or summary.get("exit_code") != 0
                or summary.get("highest_loss_step") != 250 or not summary.get("final_save_logged_after_last_step")
                or not summary.get("losses") or not all(math.isfinite(row["loss"]) for row in summary["losses"])):
            raise ValueError("Training evidence does not prove finite successful 250-step training")
        if runtime.get("base_model_id") != MODEL_ID or runtime.get("base_model_revision") != MODEL_REVISION:
            raise ValueError("Training used a different Base model")
        if evaluation.get("prompt_presets_sha256") != PRESETS_SHA256 or len(evaluation.get("records", [])) != 40:
            raise ValueError("Missing reviewed-preset held-out evaluation evidence")
        data = source.read("checkpoints/makeup001_250step/makeup001_250step.safetensors")
        if len(data) != ADAPTER_BYTES or sha256(data).hexdigest() != ADAPTER_SHA256:
            raise ValueError("Not the approved MAKEUP-001 checkpoint")
        header_length = struct.unpack("<Q", data[:8])[0]
        if not 0 < header_length < 8 * 1024 * 1024:
            raise ValueError("Invalid safetensors checkpoint header")
        header = json.loads(data[8:8 + header_length])
        if not any("lora" in key.lower() for key in header):
            raise ValueError("No LoRA tensors")
        evidence = {name: source.read(name) for name in
                    ("training_summary.json", "runtime.json", "train_config.yaml", "dataset_evidence.json")}
    metadata = {"schema_version": 1, "artifact_type": "project_trained_lora", "experiment": ADAPTER_ID,
                "adapter_id": ADAPTER_ID, "training_steps": 250, "base_model_id": MODEL_ID,
                "base_model_revision": MODEL_REVISION, "checkpoint_file": "adapter.safetensors",
                "checkpoint_bytes": ADAPTER_BYTES, "checkpoint_sha256": ADAPTER_SHA256,
                "prompt_presets_sha256": PRESETS_SHA256, "inference_style_ids": list(PROMPTS),
                "control_method": "fixed_inference_prompt_presets", "training_objective": "general_makeup_edit",
                "dataset_version": "DATA-M001-real-paired", "train_pairs": 50, "validation_pairs": 10,
                "inference": INFERENCE, "source_archive": archive.name,
                "review": "Project Lead approved both held-out comparison sheets on 2026-09-26",
                "limitations": "Facial retouching persists. Natural and No-Makeup may be heavier than intended.",
                "source_license_note": "FFHQ-Makeup CC BY-NC-SA 4.0 and original photo credits retained in DATA-M001. Academic demo only; redistribution rights for adapter require separate review."}
    members = {"adapter/adapter.safetensors": data,
               "adapter/metadata.json": (json.dumps(metadata, indent=2) + "\n").encode(),
               PRESETS_PATH.relative_to(ROOT).as_posix(): PRESETS_PATH.read_bytes()}
    for path in ("backend/app/makeup_contract.py", "scripts/makeup_inference_server.py",
                 "scripts/makeup_inference_bootstrap.py", "scripts/kaggle_inference_requirements.txt"):
        members[path] = (ROOT / path).read_bytes()
    members.update({"evidence/" + name: content for name, content in evidence.items()})
    manifest = {"schema": "MAKEUP-001-runtime-bundle-v1", "adapter_id": ADAPTER_ID,
                "files": {name: sha256(content).hexdigest() for name, content in members.items()}}
    members["bundle.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as destination:
        for name, content in sorted(members.items()):
            destination.writestr(name, content)
    with ZipFile(output) as check:
        if check.testzip():
            raise ValueError("Makeup runtime ZIP failed CRC")
    return {"bundle": str(output.resolve()), "bytes": output.stat().st_size,
            "sha256": sha256(output.read_bytes()).hexdigest(), "adapter_sha256": ADAPTER_SHA256,
            "hair_assets_included": False, "training_included": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/makeup001_kaggle_runtime.zip"))
    args = parser.parse_args()
    print(json.dumps(package(args.archive, args.output), indent=2))
