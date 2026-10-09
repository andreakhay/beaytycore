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
_CANDIDATE_PATHS = [
    Path(__file__).resolve().parent / "inference_presets.json",
    Path(__file__).resolve().parents[2] / "data/makeup/DATA-M001-paired/inference_presets.json",
    Path(__file__).resolve().parents[1] / "data/makeup/DATA-M001-paired/inference_presets.json",
]
PRESETS_PATH = next((p for p in _CANDIDATE_PATHS if p.is_file()), _CANDIDATE_PATHS[0])
INFERENCE = {"width": 512, "height": 512, "steps": 20, "guidance": 4.0, "seed": 1977}
GENERATOR = "flux2_klein_base_makeup001"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


FALLBACK_PROMPTS = {
    "natural_makeup": "Apply restrained everyday makeup with light upper-lash definition, soft neutral cheek blush and a muted rose lip. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "no_makeup_makeup": "Apply an extremely subtle but visible makeup look with gentle complexion evening, a faint cheek flush, sheer natural lip tint and minimal lash definition. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "soft_glam": "Apply polished soft glam makeup with blended warm neutral upper-eyelid shadow, fine liner, gentle cheek sculpting and a satin nude rose lip. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "smoky_glam": "Apply smoky glam makeup with a localized gradient of deep brown and charcoal shadow on the eyelids and lash lines, defined liner, restrained cheeks and a nude lip. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "dewy_peach": "Apply fresh dewy peach makeup with soft peach blush on the cheeks, warm peach upper-eyelid color, a sheer peach lip and restrained cheekbone glow. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "rosy_pink": "Apply coordinated rosy pink makeup with feathered rose cheek blush, delicate rose upper-eyelid color and a soft pink lip. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "bronze_golden_glam": "Apply warm bronze and golden makeup with blended bronze upper-eyelid shadow, a small gold highlight, softly warmed cheeks and a warm nude lip. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "matte_nude": "Apply matte nude makeup with natural skin texture, subtle neutral brown eyelid definition, light contour and a matte nude lip. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "classic_red_lip": "Apply a classic rich red lipstick within the existing upper and lower lip outlines, with minimal neutral eye makeup and restrained cheeks. Keep teeth and mouth opening unchanged. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
    "bold_evening_glam": "Apply photorealistic bold evening makeup with blended deep brown and plum upper-eyelid shadow, defined lash lines, softly sculpted cheeks and a rich berry-red lip. Edit the supplied photo of the same person. Keep their recognizable identity, face shape, eyes, nose, mouth geometry, expression, natural skin tone and skin texture. Keep the original hairstyle, hair color, clothing, background, pose, framing and lighting. Change makeup only. Keep cosmetic color in plausible facial regions and avoid mask-like patches or plastic skin.",
}


def load_prompts(path: Path = PRESETS_PATH) -> dict[str, str]:
    if not path.is_file():
        return FALLBACK_PROMPTS
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
