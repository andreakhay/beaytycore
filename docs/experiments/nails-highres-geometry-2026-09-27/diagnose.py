"""Reproduce the two-hand automatic geometry check; manual masks are evaluation only."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "docs/experiments/manual-mask-ceiling-2026-09-27"))
from run_diagnostic import (current_finger_masks, manual_masks, mask_metrics,
                            overlay, full_composite, map_original_mask_to_512,
                            map_512_to_original)
from app.nails.geometry import MediaPipeHandLocalizer
from app.nails.hybrid import HybridNailsPipeline, normalized_hand
from app.nails.render import render_target
from app.nails.segmentation import IsolatedYoloNailSegmenter
from app.nails.styles import NAIL_STYLE_BY_ID

SOURCE = ROOT / "data/nails/work/manual-mask-ceiling-20260927"
OUTPUT = ROOT / "data/nails/work/nails-highres-geometry-20260927"
ANNOTATIONS = ROOT / "docs/experiments/manual-mask-ceiling-2026-09-27/contours.json"
FINGERS = ("little", "ring", "middle", "index", "thumb")


def make_sheet(original, old, refined, manual, old_result, refined_result, fingers, dest):
    images = (original, overlay(original, old, (0, 255, 0)),
              overlay(original, refined, (0, 180, 255)),
              overlay(original, manual, (255, 0, 255)), old_result, refined_result)
    headings = ("Original", "Old", "Refined automatic", "Manual diagnostic", "Old result", "Refined result")
    width, height = 310, 233
    sheet = Image.new("RGB", (width * 6, 280 + 170 * len(fingers)), "white")
    draw = ImageDraw.Draw(sheet)
    for col, (heading, im) in enumerate(zip(headings, images)):
        sheet.paste(im.resize((width, height), Image.Resampling.LANCZOS), (col * width, 32))
        draw.text((col * width + 6, 8), heading, fill="black")
    for row, finger in enumerate(fingers):
        mm = np.asarray(fingers[finger]) > 127
        ys, xs = np.nonzero(mm)
        box = (max(0, int(xs.min()) - 24), max(0, int(ys.min()) - 24),
               min(original.width, int(xs.max()) + 25), min(original.height, int(ys.max()) + 25))
        draw.text((6, 284 + row * 170), finger, fill="black")
        for col, im in enumerate(images):
            crop = ImageOps.contain(im.crop(box), (230, 150), Image.Resampling.NEAREST)
            sheet.paste(crop, (col * width + (width - crop.width) // 2, 300 + row * 170))
    sheet.save(dest, quality=93)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checkpoint = ROOT / "data/nails/checkpoints/mnemic/nails_seg_s_yolov8_v1.pt"
    segmenter = IsolatedYoloNailSegmenter(
        ROOT / "data/nails/work/seg-venv/Scripts/python.exe", checkpoint,
        ROOT / "scripts/nails_segment_once.py")
    localizer = MediaPipeHandLocalizer(
        ROOT / "data/nails/checkpoints/mediapipe/hand_landmarker.task")
    annotation = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))["hands"]
    report = {"checkpoint": str(checkpoint), "hands": {}}
    for identity in ("0000045", "0001593"):
        entry = annotation[identity]
        original = Image.open(SOURCE / f"{identity}_original.png").convert("RGB")
        coarse = Image.open(SOURCE / f"{identity}_current_mask.png").convert("L")
        normalized, content_box = normalized_hand(original)
        hand = localizer.locate(normalized)
        coarse512 = Image.open(ROOT / f"data/nails/work/seg-review-v4/{identity}/predicted_mask.png").convert("L")
        start = time.perf_counter()
        refined, refined_parts = segmenter.segment_fingertips(original, coarse512, hand, content_box)
        seconds = time.perf_counter() - start
        refined.save(OUTPUT / f"{identity}_refined_mask.png")
        old_parts = current_finger_masks(coarse, refined_parts)
        manual, manual_parts = manual_masks(original.size, entry["fingers"])
        hand_metrics = {finger: {"old": mask_metrics(old_parts[finger], manual_parts[finger]),
                                 "refined": mask_metrics(refined_parts[finger], manual_parts[finger])}
                        for finger in FINGERS}
        record = {"source_resolution": list(original.size), "roi_seconds": round(seconds, 3),
                  "metrics": hand_metrics, "styles": {}}
        proposal512 = ImageChops.lighter(coarse512, map_original_mask_to_512(refined))
        for style in ("nude_pink", "french_tip", "pink_ombre"):
            proposal = map_512_to_original(render_target(normalized, proposal512, style, hand,
                                      production_palette=True), original.size)
            old_result, old_outside = full_composite(original, proposal, coarse)
            refined_result, refined_outside = full_composite(original, proposal, refined)
            old_result.save(OUTPUT / f"{identity}_{style}_old.png")
            refined_result.save(OUTPUT / f"{identity}_{style}_refined.png")
            make_sheet(original, coarse, refined, manual, old_result, refined_result,
                       manual_parts, OUTPUT / f"{identity}_{style}_sheet.jpg")
            record["styles"][style] = {"old_outside_changed": old_outside,
                                       "refined_outside_changed": refined_outside}
        for style in ("classic_red", "glossy_black"):
            proposal = Image.open(SOURCE / f"{identity}_{style}_index_only_fixed_proposal.png").convert("RGB")
            old_result, old_outside = full_composite(original, proposal, old_parts["index"])
            refined_result, refined_outside = full_composite(original, proposal, refined_parts["index"])
            make_sheet(original, old_parts["index"], refined_parts["index"],
                       manual_parts["index"], old_result, refined_result,
                       {"index": manual_parts["index"]}, OUTPUT / f"{identity}_{style}_index_sheet.jpg")
            record["styles"][style] = {"scope": "saved step-50 index output only",
                                       "old_outside_changed": old_outside,
                                       "refined_outside_changed": refined_outside}
        report["hands"][identity] = record
        print(identity, "ROI seconds", seconds)
        for finger, values in hand_metrics.items():
            print(finger, values["old"]["iou"], values["refined"]["iou"],
                  values["old"]["overcoverage_pct_of_current"],
                  values["refined"]["overcoverage_pct_of_current"])
        # Exercise the production renderer route using the same localizer and checkpoint.
        for style in ("nude_pink", "french_tip", "pink_ombre"):
            wall_started = time.perf_counter()
            result = asyncio.run(HybridNailsPipeline(localizer, segmenter, None).run(
                original, NAIL_STYLE_BY_ID[style]))
            record.setdefault("production_renderer_seconds", {})[style] = result.phase_seconds
            record.setdefault("production_renderer_wall_seconds", {})[style] = round(
                time.perf_counter() - wall_started, 3)
            result.image.save(OUTPUT / f"{identity}_{style}_production.png")
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
