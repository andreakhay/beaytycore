"""Pinned production selection for the hybrid Nails pilot."""

from hashlib import sha256
from pathlib import Path


MODEL_STYLES = frozenset(("classic_red", "glossy_black"))
RENDERER_STYLES = frozenset(("nude_pink", "french_tip", "pink_ombre"))
ADAPTER_ID = "NAILS-001-LOCAL-v1"
ADAPTER_SHA256 = "5bff16c67e0014c78a6d938813347685f914f8a608d76407b10f5b54b7a0eb1f"
MODEL_ID = "black-forest-labs/FLUX.2-klein-base-4B"
MODEL_REVISION = "a3b4f4849157f664bdbc776fd7453c2783562f4d"
GENERATOR = "nails001_local_step050"
SEED = 1977
STEPS = 20
GUIDANCE = 4.0
PROMPTS = {
    "classic_red": "Apply glossy classic red polish to this fingernail while preserving the same fingertip, nail shape, and surrounding skin.",
    "glossy_black": "Apply glossy black polish to this fingernail while preserving the same fingertip, nail shape, and surrounding skin.",
}


def verify_adapter(path: Path) -> None:
    if not path.is_file() or path.stat().st_size != 46223600:
        raise ValueError("The selected Nails step-50 checkpoint is missing or has the wrong size")
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != ADAPTER_SHA256:
        raise ValueError("The selected Nails step-50 checkpoint hash changed")
