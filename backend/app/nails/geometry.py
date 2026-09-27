"""Hand localization, reviewed nail masks, crop mapping and safe compositing."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image, ImageFilter


class UnusableHand(ValueError):
    """A retake is safer than an unsupported edit."""


@dataclass(frozen=True)
class HandGeometry:
    points: tuple[tuple[float, float], ...]  # normalized MediaPipe coordinates
    width: int
    height: int


class HandLocalizer(Protocol):
    def locate(self, image: Image.Image) -> HandGeometry: ...


class MediaPipeHandLocalizer:
    def __init__(self, model_path: Path):
        if not model_path.is_file():
            raise FileNotFoundError(f"Hand Landmarker asset missing: {model_path}")
        import mediapipe as mp
        self.mp = mp
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)), num_hands=2)
        self.detector = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def locate(self, image: Image.Image) -> HandGeometry:
        rgb = np.asarray(image.convert("RGB"))
        result = self.detector.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb))
        if len(result.hand_landmarks) != 1:
            raise UnusableHand("Use a clear photo showing one hand with 3 to 5 visible nails.")
        points = tuple((p.x, p.y) for p in result.hand_landmarks[0])
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        if (max(xs) - min(xs)) * image.width < 120 or (max(ys) - min(ys)) * image.height < 120:
            raise UnusableHand("Move your hand closer so the nails are clearly visible.")
        return HandGeometry(points, image.width, image.height)


class NailSegmenter(Protocol):
    def segment(self, image: Image.Image, hand: HandGeometry) -> Image.Image: ...


class ReviewedMaskSegmenter:
    """Offline development and dataset path; mask must be independently reviewed."""

    def __init__(self, mask: Image.Image):
        self.mask = mask.convert("L")

    def segment(self, image: Image.Image, hand: HandGeometry) -> Image.Image:
        if self.mask.size != image.size:
            raise UnusableHand("Nail mask dimensions do not match the hand photo.")
        return self.mask


def nail_components(mask: np.ndarray) -> list[np.ndarray]:
    """Connected mask islands; tiny isolated pixels do not count as nails."""
    pending = set(zip(*np.nonzero(mask)))
    groups = []
    while pending:
        start = pending.pop()
        stack = [start]
        group = [start]
        while stack:
            y, x = stack.pop()
            for point in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                if point in pending:
                    pending.remove(point)
                    stack.append(point)
                    group.append(point)
        if len(group) >= 30:
            groups.append(np.asarray(group))
    return groups


def validate_nail_mask(mask: Image.Image, hand: HandGeometry) -> None:
    array = np.asarray(mask.convert("L")) > 127
    if not array.any():
        raise UnusableHand("The visible fingernails could not be located. Retake the photo.")
    ys, xs = np.nonzero(array)
    if len(xs) < 150 or max(xs) - min(xs) < 35 or max(ys) - min(ys) < 20:
        raise UnusableHand("Move closer so at least 3 fingernails are clear.")
    if len(xs) > hand.width * hand.height * .12:
        raise UnusableHand("The nail mask is too large to edit safely.")
    if not 3 <= len(nail_components(array)) <= 5:
        raise UnusableHand("Use a clear photo with 3 to 5 separate visible nails.")
    tips = [hand.points[i] for i in (4, 8, 12, 16, 20)]
    tip_pixels = np.array([(x * hand.width, y * hand.height) for x, y in tips])
    near = sum(np.any(np.sum((np.stack((xs, ys), axis=1)[::max(1, len(xs)//2000)] - tip)**2, axis=1) < 75**2) for tip in tip_pixels)
    if near < 3:
        raise UnusableHand("At least 3 visible nails must align with the detected fingertips.")


@dataclass(frozen=True)
class NailCrop:
    box: tuple[int, int, int, int]
    image: Image.Image
    mask: Image.Image


def crop_nails(image: Image.Image, mask: Image.Image, hand: HandGeometry) -> NailCrop:
    validate_nail_mask(mask, hand)
    bounds = mask.point(lambda value: 255 if value > 127 else 0).getbbox()
    assert bounds is not None
    left, top, right, bottom = bounds
    pad = max(24, int(max(right-left, bottom-top) * .2))
    box = (max(0, left-pad), max(0, top-pad), min(image.width, right+pad), min(image.height, bottom+pad))
    return NailCrop(box, image.crop(box), mask.crop(box))


def prepare_model_crop(crop: NailCrop, size: int = 512) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Pad without stretching and record the content window for restoration."""
    width, height = crop.image.size
    scale = min(size / width, size / height)
    scaled = (max(1, round(width * scale)), max(1, round(height * scale)))
    left, top = (size - scaled[0]) // 2, (size - scaled[1]) // 2
    model_input = Image.new("RGB", (size, size), (245, 245, 245))
    model_input.paste(crop.image.convert("RGB").resize(scaled, Image.Resampling.LANCZOS), (left, top))
    return model_input, (left, top, left + scaled[0], top + scaled[1])


def restore_model_crop(model_result: Image.Image, crop: NailCrop,
                       content_box: tuple[int, int, int, int]) -> Image.Image:
    if model_result.width != model_result.height or model_result.width < 128:
        raise ValueError("Expected a square model result")
    if any(value < 0 or value > model_result.width for value in content_box):
        raise ValueError("Invalid model content mapping")
    return model_result.crop(content_box).resize(crop.image.size, Image.Resampling.LANCZOS)


def composite_nails(original: Image.Image, generated_crop: Image.Image, crop: NailCrop) -> Image.Image:
    if generated_crop.size != crop.image.size:
        raise ValueError("Generated crop dimensions do not match the recorded crop mapping")
    # Feather inward. No generated pixels can spill outside the original mask.
    hard = crop.mask.point(lambda value: 255 if value > 127 else 0)
    soft = hard.filter(ImageFilter.GaussianBlur(radius=1.2))
    alpha = Image.fromarray(np.minimum(np.asarray(hard), np.asarray(soft)))
    out = original.convert("RGB").copy()
    original_crop = out.crop(crop.box)
    out.paste(Image.composite(generated_crop.convert("RGB"), original_crop, alpha), crop.box)
    return out
