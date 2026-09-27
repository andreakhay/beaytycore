"""One backend route for localized model styles and deterministic styles."""

import asyncio
from dataclasses import dataclass
import threading
import time
from typing import Protocol

import numpy as np
from PIL import Image, ImageChops, ImageOps

from app.nails.contract import MODEL_STYLES, RENDERER_STYLES
from app.nails.geometry import (NailCrop, composite_nails,
                                nail_components, validate_nail_mask)
from app.nails.localized import localized_nails, model_crop, restore_crop, single_nail_mask
from app.nails.render import render_target
from app.nails.styles import NailStyle


class LocalizedGenerator(Protocol):
    async def generate(self, image: Image.Image, style: NailStyle) -> Image.Image: ...


@dataclass(frozen=True)
class HybridResult:
    image: Image.Image
    path: str
    nail_count: int
    model_seconds: float | None
    renderer_seconds: float | None
    phase_seconds: dict[str, float] | None = None


def normalized_hand(original: Image.Image) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Use the same white aspect pad as approved DATA-N001 sources."""
    fitted = ImageOps.contain(original.convert("RGB"), (512, 512), Image.Resampling.LANCZOS)
    left, top = round((512 - fitted.width) * .5), round((512 - fitted.height) * .5)
    normalized = Image.new("RGB", (512, 512), "white")
    normalized.paste(fitted, (left, top))
    return normalized, (left, top, left + fitted.width, top + fitted.height)


def _to_original(image: Image.Image, content_box: tuple[int, int, int, int],
                 size: tuple[int, int], *, mask: bool = False) -> Image.Image:
    return image.crop(content_box).resize(
        size, Image.Resampling.NEAREST if mask else Image.Resampling.BICUBIC)


def _to_normalized_mask(image: Image.Image, content_box: tuple[int, int, int, int]) -> Image.Image:
    result = Image.new("L", (512, 512))
    result.paste(image.resize((content_box[2] - content_box[0],
                               content_box[3] - content_box[1]), Image.Resampling.NEAREST),
                 content_box[:2])
    return result


class HybridNailsPipeline:
    def __init__(self, localizer, segmenter, model: LocalizedGenerator | None):
        self.localizer, self.segmenter, self.model = localizer, segmenter, model
        self._localizer_lock = threading.Lock()

    def _locate(self, image: Image.Image):
        with self._localizer_lock:
            return self.localizer.locate(image)

    async def run(self, original: Image.Image, style: NailStyle) -> HybridResult:
        if style.id not in MODEL_STYLES | RENDERER_STYLES:
            raise ValueError("Unsupported Nails style")
        phases: dict[str, float] = {}
        started = time.monotonic()
        normalized, content_box = normalized_hand(original)
        phases["normalization"] = time.monotonic() - started
        started = time.monotonic()
        hand = await asyncio.to_thread(self._locate, normalized)
        phases["hand_localization"] = time.monotonic() - started
        started = time.monotonic()
        mask = await asyncio.to_thread(self.segmenter.segment, normalized, hand)
        validate_nail_mask(mask, hand)
        phases["nail_segmentation"] = time.monotonic() - started
        started = time.monotonic()
        # Renderer styles can edit neighboring visible nails. Model crops must
        # isolate each nail, using the exact training geometry.
        nail_count = len(nail_components(np.asarray(mask.convert("L")) > 127))
        original_mask = _to_original(mask, content_box, original.size, mask=True)
        phases["mask_preparation"] = time.monotonic() - started
        finger_masks = None
        if hasattr(self.segmenter, "segment_fingertips"):
            started_refinement = time.monotonic()
            original_mask, finger_masks = await asyncio.to_thread(
                self.segmenter.segment_fingertips, original, mask, hand, content_box)
            phases["mask_refinement"] = time.monotonic() - started_refinement
        proposal_mask = (ImageChops.lighter(mask, _to_normalized_mask(original_mask, content_box))
                         if finger_masks is not None else mask)
        if style.id in RENDERER_STYLES:
            started = time.monotonic()
            rendered_normalized = await asyncio.to_thread(
                render_target, normalized, proposal_mask, style.id, hand, production_palette=True)
            phases["style_rendering"] = time.monotonic() - started
            started = time.monotonic()
            rendered = _to_original(rendered_normalized, content_box, original.size)
            whole = NailCrop((0, 0, original.width, original.height), original, original_mask)
            final = composite_nails(original, rendered, whole)
            phases["compositing"] = time.monotonic() - started
            elapsed = phases["style_rendering"] + phases["compositing"]
            path, model_seconds, renderer_seconds = "renderer", None, elapsed
        else:
            if self.model is None:
                raise RuntimeError("The Nails GPU model is not configured")
            started = time.monotonic()
            mappings = localized_nails(mask, hand)
            phases["crop_preparation"] = time.monotonic() - started
            phases["gpu_request"] = 0.0
            phases["model_generation"] = 0.0
            phases["result_reconstruction"] = 0.0
            phases["compositing"] = 0.0
            assembled = normalized.copy()
            for mapping in mappings:
                started = time.monotonic()
                reference = model_crop(normalized, mapping)
                phases["crop_preparation"] += time.monotonic() - started
                started = time.monotonic()
                generated = await self.model.generate(reference, style)
                phases["gpu_request"] += time.monotonic() - started
                runtime = generated.info.get("runtime_seconds")
                if isinstance(runtime, (int, float)) and runtime >= 0:
                    phases["model_generation"] += runtime
                started = time.monotonic()
                restored = restore_crop(generated, mapping)
                single = single_nail_mask(mask, mapping)
                if finger_masks is not None:
                    single = ImageChops.lighter(
                        single, _to_normalized_mask(finger_masks[mapping["finger_id"]], content_box))
                phases["result_reconstruction"] += time.monotonic() - started
                started = time.monotonic()
                assembled = composite_nails(assembled, restored,
                    NailCrop((0, 0, 512, 512), normalized, single))
                phases["compositing"] += time.monotonic() - started
            started = time.monotonic()
            generated_original = _to_original(assembled, content_box, original.size)
            phases["result_reconstruction"] += time.monotonic() - started
            started = time.monotonic()
            whole = NailCrop((0, 0, original.width, original.height), original, original_mask)
            final = composite_nails(original, generated_original, whole)
            phases["compositing"] += time.monotonic() - started
            elapsed = sum(phases[key] for key in ("crop_preparation", "gpu_request",
                      "result_reconstruction", "compositing"))
            path, model_seconds, renderer_seconds = "model", elapsed, None
        outside = np.asarray(original_mask) <= 127
        if np.any(np.asarray(final)[outside] != np.asarray(original.convert("RGB"))[outside]):
            raise RuntimeError("Nails preservation check failed")
        return HybridResult(final, path, nail_count, model_seconds, renderer_seconds,
                            {key: round(value, 3) for key, value in phases.items()})
