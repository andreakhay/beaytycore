"""Localize, crop, generate and composite without replacing non-nail pixels."""

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

from PIL import Image

from app.generation.base import GeneratedImage
from app.nails.geometry import (HandLocalizer, NailSegmenter, crop_nails,
                                composite_nails, prepare_model_crop, restore_model_crop)
from app.nails.styles import NailStyle


class NailCropGenerator(Protocol):
    async def generate(self, image: Image.Image, style: NailStyle) -> Image.Image: ...


class ImageGenerationEngine(Protocol):
    async def generate(self, image: Image.Image, style: NailStyle) -> GeneratedImage: ...


class EngineCropGenerator:
    """Adapt the shared GenerationEngine result shape to a Nails model crop."""

    def __init__(self, engine: ImageGenerationEngine):
        self.engine = engine

    async def generate(self, image: Image.Image, style: NailStyle) -> Image.Image:
        result = await self.engine.generate(image, style)
        with Image.open(BytesIO(result.content)) as decoded:
            decoded.load()
            if decoded.size != (result.width, result.height):
                raise ValueError("Generation engine image dimensions differ from metadata")
            return decoded.convert("RGB")


@dataclass(frozen=True)
class NailsResult:
    image: Image.Image
    mask: Image.Image
    model_input: Image.Image
    model_output: Image.Image
    crop_box: tuple[int, int, int, int]


class NailsPipeline:
    def __init__(self, localizer: HandLocalizer, segmenter: NailSegmenter,
                 generator: NailCropGenerator):
        self.localizer = localizer
        self.segmenter = segmenter
        self.generator = generator

    async def run(self, original: Image.Image, style: NailStyle) -> NailsResult:
        hand = self.localizer.locate(original)
        mask = self.segmenter.segment(original, hand)
        crop = crop_nails(original, mask, hand)
        model_input, content_box = prepare_model_crop(crop)
        model_output = await self.generator.generate(model_input, style)
        restored = restore_model_crop(model_output, crop, content_box)
        final = composite_nails(original, restored, crop)
        return NailsResult(final, mask, model_input, model_output, crop.box)
