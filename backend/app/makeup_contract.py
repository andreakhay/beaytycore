"""Frozen MAKEUP-001 inference contract, independent of Hair registries."""

from hashlib import sha256
import json
from pathlib import Path
import struct


MODEL_ID = "black-forest-labs/FLUX.2-klein-base-4B"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
ADAPTER_ID = "MAKEUP-001"
ADAPTER_SHA256 = "f6f0419e4259a75102f08a450222ad806e3aec1c2ae50ff89f875139084ae510"
ADAPTER_BYTES = 46223600
PRESETS_SHA256 = "8e6e244f6174dc70f33cb15a037f5e67e2a245f15278967f4d2f85bc909cd5f5"
PRESETS_PATH = Path(__file__).resolve().parents[2] / "data/makeup/DATA-M001-paired/inference_presets.json"
INFERENCE = {"width": 512, "height": 512, "steps": 20, "guidance": 4.0, "seed": 1977}
GENERATOR = "flux2_klein_base_makeup001"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def load_prompts(path: Path = PRESETS_PATH) -> dict[str, str]:
    if digest(path) != PRESETS_SHA256:
        raise ValueError("MAKEUP-001 presets differ from the reviewed evaluation")
    presets = json.loads(path.read_text(encoding="utf-8"))
    styles = presets["styles"]
    if (presets.get("schema") != "MAKEUP-001-inference-presets-v1" or len(styles) != 10
            or len({style["id"] for style in styles}) != 10):
        raise ValueError("Expected the ten reviewed Makeup inference presets")
    return {style["id"]: style["instruction"] + " " + presets["preservation_instruction"] for style in styles}


PROMPTS = load_prompts()


def verify_adapter(directory: Path) -> dict:
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    required = {
        "schema_version": 1, "artifact_type": "project_trained_lora", "adapter_id": ADAPTER_ID,
        "experiment": ADAPTER_ID, "training_steps": 250, "base_model_id": MODEL_ID,
        "base_model_revision": MODEL_REVISION, "checkpoint_file": "adapter.safetensors",
        "checkpoint_sha256": ADAPTER_SHA256, "checkpoint_bytes": ADAPTER_BYTES,
        "prompt_presets_sha256": PRESETS_SHA256, "control_method": "fixed_inference_prompt_presets",
        "inference": INFERENCE,
    }
    if any(metadata.get(key) != value for key, value in required.items()):
        raise ValueError("MAKEUP-001 metadata differs from the approved checkpoint")
    if sorted(metadata.get("inference_style_ids", [])) != sorted(PROMPTS):
        raise ValueError("MAKEUP-001 inference preset IDs do not match")
    checkpoint = directory / "adapter.safetensors"
    if checkpoint.stat().st_size != ADAPTER_BYTES or digest(checkpoint) != ADAPTER_SHA256:
        raise ValueError("MAKEUP-001 checkpoint hash or size mismatch")
    with checkpoint.open("rb") as stream:
        length = struct.unpack("<Q", stream.read(8))[0]
        if not 0 < length < 8 * 1024 * 1024:
            raise ValueError("Invalid safetensors header length")
        header = json.loads(stream.read(length))
    if not isinstance(header, dict) or not any("lora" in key.lower() for key in header):
        raise ValueError("MAKEUP-001 contains no LoRA tensors")
    return metadata
