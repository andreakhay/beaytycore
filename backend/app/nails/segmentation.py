"""Isolated offline inference for the reviewed pilot nail-mask checkpoint."""

import os
import json
import itertools
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image

from app.nails.geometry import HandGeometry, UnusableHand, nail_components
from app.nails.localized import FINGERS, TIP_INDEX


class IsolatedYoloNailSegmenter:
    def __init__(self, python: Path, checkpoint: Path, script: Path):
        for name, path in (("Python", python), ("nail checkpoint", checkpoint), ("segmenter", script)):
            if not path.is_file():
                raise FileNotFoundError(f"{name} missing: {path}")
        self.python, self.checkpoint, self.script = python, checkpoint, script

    def segment(self, image: Image.Image, hand: HandGeometry) -> Image.Image:
        if image.size != (hand.width, hand.height):
            raise ValueError("Hand and image dimensions differ")
        with TemporaryDirectory(prefix="nails-segment-") as directory:
            root = Path(directory)
            source, target = root / "source.png", root / "mask.png"
            image.convert("RGB").save(source)
            env = os.environ.copy()
            env["HF_HUB_OFFLINE"] = "1"
            config = root / "yolo"
            config.mkdir()
            env["YOLO_CONFIG_DIR"] = str(config)
            try:
                result = subprocess.run(
                    [str(self.python), str(self.script), "--image", str(source),
                     "--checkpoint", str(self.checkpoint), "--mask", str(target)],
                    capture_output=True, text=True, timeout=120, env=env, check=False)
            except subprocess.TimeoutExpired as exc:
                raise UnusableHand("Nail detection timed out. Please try again.") from exc
            if result.returncode or not target.is_file():
                raise RuntimeError(f"Nail segmenter failed: {result.stderr[-1200:]}")
            with Image.open(target) as opened:
                if opened.size != image.size:
                    raise RuntimeError("Nail segmenter returned wrong mask dimensions")
                return opened.convert("L")

    def segment_fingertips(self, original: Image.Image, coarse: Image.Image,
                           hand: HandGeometry, content_box: tuple[int, int, int, int]
                           ) -> tuple[Image.Image, dict[str, Image.Image]]:
        """One isolated YOLO load for all source-resolution fingertip ROIs."""
        if coarse.size != (512, 512) or (hand.width, hand.height) != (512, 512):
            raise ValueError("Expected 512-pixel coarse nail geometry")
        groups = nail_components(np.asarray(coarse.convert("L")) > 127)
        tips = np.asarray([hand.points[index] for index in TIP_INDEX]) * 512
        centers = [np.asarray([group[:, 1].mean(), group[:, 0].mean()]) for group in groups]
        assignment = min(itertools.permutations(range(5), len(groups)),
                         key=lambda option: sum(np.linalg.norm(centers[i] - tips[f])
                                                for i, f in enumerate(option)))
        if any(np.linalg.norm(center - tips[finger]) > 30
               for center, finger in zip(centers, assignment)):
            raise UnusableHand("The nails do not align with the fingertips. Retake the photo.")
        with TemporaryDirectory(prefix="nails-fingertips-") as directory:
            root = Path(directory)
            specs = []
            boxes = {}
            for group, finger_index in zip(groups, assignment):
                finger = FINGERS[finger_index]
                pixels = np.zeros((512, 512), dtype=np.uint8)
                pixels[group[:, 0], group[:, 1]] = 255
                single = Image.fromarray(pixels, "L").crop(content_box).resize(
                    original.size, Image.Resampling.NEAREST)
                bounds = single.getbbox()
                if bounds is None:
                    raise UnusableHand("A fingernail could not be located. Retake the photo.")
                x0, y0, x1, y1 = bounds
                width, height = x1 - x0, y1 - y0
                if min(width, height) < 12:
                    raise UnusableHand("A fingernail is too small for a reliable polish edge. Move closer.")
                side = min(max(120, round(3.5 * max(width, height))),
                           original.width, original.height)
                left = max(0, min(round((x0 + x1 - side) / 2), original.width - side))
                top = max(0, min(round((y0 + y1 - side) / 2), original.height - side))
                box = (left, top, left + side, top + side)
                if x0 < left or y0 < top or x1 > left + side or y1 > top + side:
                    raise UnusableHand("A fingertip is too close to the image edge. Retake the photo.")
                source = root / f"{finger}-source.png"
                anchor = root / f"{finger}-coarse.png"
                original.crop(box).convert("RGB").save(source)
                single.crop(box).save(anchor)
                specs.append({"finger_id": finger, "image": str(source),
                              "coarse_mask": str(anchor)})
                boxes[finger] = box
            manifest = root / "rois.json"
            manifest.write_text(json.dumps(specs), encoding="utf-8")
            output = root / "refined"
            env = os.environ.copy()
            env["HF_HUB_OFFLINE"] = "1"
            config = root / "yolo"
            config.mkdir()
            env["YOLO_CONFIG_DIR"] = str(config)
            try:
                result = subprocess.run(
                    [str(self.python), str(self.script), "--checkpoint", str(self.checkpoint),
                     "--roi-manifest", str(manifest), "--roi-output", str(output)],
                    capture_output=True, text=True, timeout=180, env=env, check=False)
            except subprocess.TimeoutExpired as exc:
                raise UnusableHand("Fingernail edge detection timed out. Please retry.") from exc
            if result.returncode:
                if "ValueError: " in result.stderr:
                    raise UnusableHand("The fingernail edges are unclear. Retake with nails in focus.")
                raise RuntimeError(f"Fingernail segmenter failed: {result.stderr[-1200:]}")
            combined = np.zeros((original.height, original.width), dtype=np.uint8)
            per_finger = {}
            for spec in specs:
                finger = spec["finger_id"]
                box = boxes[finger]
                path = output / f"{finger}.png"
                if not path.is_file():
                    raise RuntimeError("Fingernail segmenter omitted a nail mask")
                with Image.open(path) as opened:
                    if opened.size != (box[2] - box[0], box[3] - box[1]):
                        raise RuntimeError("Fingernail segmenter returned wrong dimensions")
                    roi = np.asarray(opened.convert("L")) > 127
                full = np.zeros_like(combined)
                full[box[1]:box[3], box[0]:box[2]] = roi.astype(np.uint8) * 255
                if np.any((combined > 0) & (full > 0)):
                    raise UnusableHand("Fingernail edges overlap. Retake with separated fingers.")
                combined = np.maximum(combined, full)
                per_finger[finger] = Image.fromarray(full, "L")
            return Image.fromarray(combined, "L"), per_finger
