"""Evaluated single-nail crops with neighboring context for close hand poses."""

import itertools
import logging
import math

import numpy as np
from PIL import Image, ImageFilter

from app.nails.geometry import HandGeometry, UnusableHand, nail_components


FINGERS = ("thumb", "index", "middle", "ring", "little")
TIP_INDEX = (4, 8, 12, 16, 20)
DIP_INDEX = (3, 7, 11, 15, 19)
SIZE = 512
LOGGER = logging.getLogger(__name__)


def localized_nails(mask: Image.Image, hand: HandGeometry) -> list[dict]:
    """Keep evaluated crops when possible; allow neighboring context when needed."""
    if mask.size != (SIZE, SIZE) or (hand.width, hand.height) != (SIZE, SIZE):
        raise ValueError("Localized Nails geometry requires a 512 by 512 hand")
    groups = nail_components(np.asarray(mask.convert("L")) > 127)
    if not 3 <= len(groups) <= 5:
        raise UnusableHand("Use a clear photo with 3 to 5 separate visible nails.")
    tips = np.asarray([hand.points[i] for i in TIP_INDEX]) * SIZE
    dips = np.asarray([hand.points[i] for i in DIP_INDEX]) * SIZE
    centers = [np.asarray([group[:, 1].mean(), group[:, 0].mean()]) for group in groups]
    assignments = min(itertools.permutations(range(5), len(groups)),
                      key=lambda option: sum(np.linalg.norm(centers[i] - tips[f])
                                             for i, f in enumerate(option)))
    mappings = []
    full = mask.convert("L")
    for group, center, finger in zip(groups, centers, assignments):
        tip_distance = float(np.linalg.norm(center - tips[finger]))
        direction = tips[finger] - dips[finger]
        direction_length = float(np.linalg.norm(direction))
        if tip_distance > 30 or direction_length < 15:
            raise UnusableHand("The nail positions are unclear. Retake with separated fingers facing the camera.")
        angle = math.degrees(math.atan2(direction[0], -direction[1]))
        if abs(angle) < 8:
            angle = 0.0
        xs, ys = group[:, 1], group[:, 0]
        width, height = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
        nail = {"finger_id": FINGERS[finger], "finger_index": finger,
                "center": [round(float(center[0]), 3), round(float(center[1]), 3)],
                "angle_degrees": round(angle, 4), "orientation_confidence": "landmark_matched",
                "tip_distance_px": round(tip_distance, 3),
                "dip_to_tip_px": round(direction_length, 3),
                "nail_bbox_wh": [width, height],
                "crop_side_px": max(56, round(2.4 * max(width, height))),
                "original_nail_pixels": int(len(group))}
        mapping = _crop_geometry(nail, full, group)
        if mapping is None:
            raise UnusableHand("The full nail cannot fit in the crop. Include your fingertips with room around them.")
        mappings.append(mapping)
    return sorted(mappings, key=lambda item: item["finger_index"])


def _crop_geometry(nail: dict, full_mask: Image.Image, group: np.ndarray) -> dict | None:
    cx, cy = nail["center"]
    angle = nail["angle_degrees"]
    rotated_all = (full_mask.rotate(angle, resample=Image.Resampling.NEAREST,
                   center=(cx, cy), fillcolor=0) if angle else full_mask)
    single = np.zeros((SIZE, SIZE), dtype=np.uint8)
    single[group[:, 0], group[:, 1]] = 255
    one = Image.fromarray(single, "L")
    rotated_one = (one.rotate(angle, resample=Image.Resampling.NEAREST,
                   center=(cx, cy), fillcolor=0) if angle else one)
    all_pixels, one_pixels = np.asarray(rotated_all) > 127, np.asarray(rotated_one) > 127
    others = np.where(all_pixels & ~one_pixels, 255, 0).astype(np.uint8)
    other_support = np.asarray(Image.fromarray(others, "L").filter(ImageFilter.MaxFilter(11))) > 0
    minimum_side = max(48, round(1.8 * max(nail["nail_bbox_wh"])))
    rejected = {"image_boundary": 0, "target_not_contained": 0, "neighbor_support": 0}
    contextual = None
    contextual_pixels = None
    for side in range(nail["crop_side_px"], minimum_side - 1, -1):
        left = round(cx - side / 2)
        top = round(cy + side * .10 - side / 2)
        box = (left, top, left + side, top + side)
        if min(box[:2]) < 0 or max(box[2:]) > SIZE:
            rejected["image_boundary"] += 1
            continue
        sl = np.s_[top:top + side, left:left + side]
        if int(one_pixels[sl].sum()) != int(one_pixels.sum()):
            rejected["target_not_contained"] += 1
            continue
        mapping = {**nail, "crop_side_px": side, "crop_box_rotated": list(box),
                   "model_size": [SIZE, SIZE], "rgb_resampling": "BICUBIC",
                   "mask_resampling": "NEAREST", "rotation_center_original": nail["center"]}
        if np.any(other_support[sl]):
            rejected["neighbor_support"] += 1
            # Neighboring pixels may be conditioning context, never the paste
            # boundary. HybridNailsPipeline restores only the selected nail mask.
            # Keep the least neighboring nail area, preferring more context on ties.
            neighbor_pixels = int((all_pixels & ~one_pixels)[sl].sum())
            if contextual is None or neighbor_pixels < contextual_pixels:
                contextual = mapping
                contextual_pixels = neighbor_pixels
            continue
        return mapping
    if contextual is not None:
        LOGGER.info("Nails crop permits neighboring context: finger=%s side=%s neighbor_nail_pixels=%s",
                    nail["finger_id"], contextual["crop_side_px"], contextual_pixels)
        return {**contextual, "neighbor_context_pixels": contextual_pixels}
    LOGGER.warning(
        "Nails crop rejected before GPU: finger=%s side_range=%s..%s "
        "image_boundary=%s target_not_contained=%s neighbor_support=%s",
        nail["finger_id"], minimum_side, nail["crop_side_px"],
        rejected["image_boundary"], rejected["target_not_contained"], rejected["neighbor_support"],
    )
    return None


def model_crop(image: Image.Image, mapping: dict) -> Image.Image:
    """Apply the identical bicubic rotation/crop/resize used for training."""
    angle = mapping["angle_degrees"]
    rotated = (image.rotate(angle, resample=Image.Resampling.BICUBIC,
               center=tuple(mapping["rotation_center_original"]), fillcolor=(255, 255, 255))
               if angle else image)
    return rotated.crop(tuple(mapping["crop_box_rotated"])).resize(
        (SIZE, SIZE), resample=Image.Resampling.BICUBIC)


def restore_crop(generated: Image.Image, mapping: dict) -> Image.Image:
    """Map one generated crop back before the existing nail-only compositor."""
    if generated.size != (SIZE, SIZE):
        raise ValueError("Expected a 512 by 512 localized model result")
    side = mapping["crop_side_px"]
    canvas = Image.new("RGB", (SIZE, SIZE), "white")
    canvas.paste(generated.convert("RGB").resize((side, side), Image.Resampling.BICUBIC),
                 tuple(mapping["crop_box_rotated"]))
    angle = mapping["angle_degrees"]
    return (canvas.rotate(-angle, resample=Image.Resampling.BICUBIC,
            center=tuple(mapping["rotation_center_original"]), fillcolor=(255, 255, 255))
            if angle else canvas)


def single_nail_mask(full_mask: Image.Image, mapping: dict) -> Image.Image:
    groups = nail_components(np.asarray(full_mask.convert("L")) > 127)
    center = np.asarray(mapping["center"])
    group = min(groups, key=lambda part: np.linalg.norm(
        np.asarray([part[:, 1].mean(), part[:, 0].mean()]) - center))
    if np.linalg.norm(np.asarray([group[:, 1].mean(), group[:, 0].mean()]) - center) > 3:
        raise ValueError("Cannot restore original nail component")
    pixels = np.zeros((SIZE, SIZE), dtype=np.uint8)
    pixels[group[:, 0], group[:, 1]] = 255
    return Image.fromarray(pixels, "L")
