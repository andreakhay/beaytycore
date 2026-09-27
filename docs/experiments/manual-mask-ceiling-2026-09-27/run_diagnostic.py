"""Offline mask-only A/B for two held-out 11K Hands photos.

This script reads frozen artifacts and writes diagnostic images under data/nails/work.
It does not update datasets, train models, or modify the application.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend"))
from app.nails.geometry import HandGeometry, NailCrop, composite_nails  # noqa: E402
from app.nails.render import render_target  # noqa: E402
from app.nails.localized import restore_crop  # noqa: E402


FINGERS = ("little", "ring", "middle", "index", "thumb")
RENDERER_STYLES = ("nude_pink", "french_tip", "pink_ombre")
MODEL_STYLES = ("classic_red", "glossy_black")
EXPECTED_FINAL = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
EXPECTED_LOCAL = "d7440f1cc1a8987c48235fed36f8ff23581c17719b219fc2a7e600ad867bcf90"
EXPECTED_EVAL = "a0c7ec088bc648cd50dd6f4329b8f80eb76efe42764f0ff89a9cb010aa31566c"


def digest_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_member(archive: ZipFile, name: str, mode: str = "RGB") -> Image.Image:
    with Image.open(BytesIO(archive.read(name))) as im:
        return im.convert(mode)


def manual_masks(size: tuple[int, int], fingers: dict[str, list[list[int]]]):
    whole = Image.new("L", size, 0)
    individual = {}
    for finger in FINGERS:
        one = Image.new("L", size, 0)
        ImageDraw.Draw(one).polygon([tuple(p) for p in fingers[finger]], fill=255)
        individual[finger] = one
        whole = Image.fromarray(np.maximum(np.asarray(whole), np.asarray(one)))
    return whole, individual


def current_finger_masks(current: Image.Image, manual: dict[str, Image.Image]):
    binary = (np.asarray(current) > 127).astype(np.uint8)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(binary, 8)
    islands = [(i, centers[i]) for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 30]
    if len(islands) != 5:
        raise ValueError(f"Expected five current mask islands, got {len(islands)}")
    selected = {}
    taken = set()
    for finger in FINGERS:
        yy, xx = np.nonzero(np.asarray(manual[finger]) > 127)
        center = np.array([xx.mean(), yy.mean()])
        island = min((entry for entry in islands if entry[0] not in taken),
                     key=lambda entry: np.linalg.norm(entry[1] - center))
        taken.add(island[0])
        selected[finger] = Image.fromarray(np.where(labels == island[0], 255, 0).astype(np.uint8))
    return selected


def mask_metrics(current: Image.Image, manual: Image.Image) -> dict:
    c = np.asarray(current) > 127
    m = np.asarray(manual) > 127
    union = c | m
    yy, xx = np.nonzero(union)
    region = np.s_[max(0, yy.min()-5):min(c.shape[0], yy.max()+6),
                   max(0, xx.min()-5):min(c.shape[1], xx.max()+6)]
    c, m = c[region], m[region]
    tp = int((c & m).sum())
    under = int((m & ~c).sum())
    over = int((c & ~m).sum())
    c_edge = cv2.morphologyEx(c.astype(np.uint8), cv2.MORPH_GRADIENT,
                              np.ones((3, 3), np.uint8)) > 0
    m_edge = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT,
                              np.ones((3, 3), np.uint8)) > 0
    dist_to_m = cv2.distanceTransform((~m_edge).astype(np.uint8), cv2.DIST_L2, 3)
    dist_to_c = cv2.distanceTransform((~c_edge).astype(np.uint8), cv2.DIST_L2, 3)
    distances = np.concatenate((dist_to_m[c_edge], dist_to_c[m_edge]))
    return {"iou": round(tp/(tp+under+over), 4),
            "precision": round(tp/(tp+over), 4),
            "recall": round(tp/(tp+under), 4),
            "undercovered_manual_pixels": under,
            "overcovered_current_pixels": over,
            "undercoverage_pct_of_manual": round(100*under/(tp+under), 2),
            "overcoverage_pct_of_current": round(100*over/(tp+over), 2),
            "symmetric_mean_boundary_px": round(float(distances.mean()), 2),
            "symmetric_p95_boundary_px": round(float(np.percentile(distances, 95)), 2)}


def map_512_to_original(im: Image.Image, original_size: tuple[int, int], mask=False):
    return im.crop((0, 64, 512, 448)).resize(
        original_size, Image.Resampling.NEAREST if mask else Image.Resampling.BICUBIC)


def map_original_mask_to_512(im: Image.Image):
    resized = im.resize((512, 384), Image.Resampling.NEAREST)
    out = Image.new("L", (512, 512), 0)
    out.paste(resized, (0, 64))
    return out


def overlay(source: Image.Image, mask: Image.Image, color: tuple[int, int, int]):
    rgb = np.asarray(source).copy()
    edge = cv2.morphologyEx((np.asarray(mask) > 127).astype(np.uint8),
                            cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    rgb[edge] = color
    return Image.fromarray(rgb)


def full_composite(original: Image.Image, proposal: Image.Image, mask: Image.Image):
    whole = NailCrop((0, 0, *original.size), original, mask)
    result = composite_nails(original, proposal, whole)
    outside = np.asarray(mask) <= 127
    changed = int(np.any(np.asarray(result) != np.asarray(original), axis=2)[outside].sum())
    if changed:
        raise AssertionError(f"Changed {changed} pixels outside selected mask")
    return result, changed


def sheet(original: Image.Image, current_mask: Image.Image, manual_mask: Image.Image,
          current_result: Image.Image, manual_result: Image.Image,
          fingers: dict[str, Image.Image], destination: Path):
    images = (original, overlay(original, current_mask, (0, 255, 0)),
              overlay(original, manual_mask, (255, 0, 255)),
              current_result, manual_result)
    headings = ("Original", "YOLO mask", "Manual mask", "YOLO result", "Manual result")
    width, height = 360, 270
    canvas = Image.new("RGB", (width*5, 320 + 150*len(fingers)), "white")
    draw = ImageDraw.Draw(canvas)
    for col, (title, im) in enumerate(zip(headings, images)):
        thumb = im.resize((width, height), Image.Resampling.LANCZOS)
        canvas.paste(thumb, (col*width, 30))
        draw.text((col*width+6, 6), title, fill="black")
    for row, (finger, mask) in enumerate(fingers.items()):
        yy, xx = np.nonzero(np.asarray(mask) > 127)
        box = (max(0, int(xx.min())-18), max(0, int(yy.min())-18),
               min(original.width, int(xx.max())+19), min(original.height, int(yy.max())+19))
        draw.text((5, 320+row*150), finger, fill="black")
        for col, im in enumerate(images):
            crop = im.crop(box)
            fit = ImageOps.contain(crop, (145, 140), Image.Resampling.NEAREST)
            canvas.paste(fit, (col*width+(width-fit.width)//2, 320+row*150))
    canvas.save(destination, quality=94)


def run(eval_path: Path):
    root = REPO / "data/nails/work/manual-mask-ceiling-20260927"
    root.mkdir(parents=True, exist_ok=True)
    final_path = REPO / "data/nails/work/DATA-N001-final.zip"
    local_path = REPO / "data/nails/work/NAILS-001-LOCAL-v1-sim-v2/DATA-N001-LOCAL-v1.zip"
    for path, expected in ((final_path, EXPECTED_FINAL), (local_path, EXPECTED_LOCAL),
                           (eval_path, EXPECTED_EVAL)):
        actual = digest_file(path)
        if actual != expected:
            raise ValueError(f"Artifact hash mismatch: {path}: {actual}")
    annotations = json.loads((Path(__file__).parent / "contours.json").read_text())
    source_selection = json.loads((REPO / "data/nails/work/source-frozen-v4/source_selection.json").read_text())
    records = {r["identity_id"]: r for r in source_selection["candidates"]}
    report = {"artifact_hashes": {"final": EXPECTED_FINAL, "local": EXPECTED_LOCAL,
                                   "evaluation": EXPECTED_EVAL}, "hands": {}}
    with ZipFile(REPO / "data/nails/source/11k-hands/Hands-original.zip") as sources, \
         ZipFile(final_path) as final, ZipFile(local_path) as local, ZipFile(eval_path) as evaluation:
        final_rows = {r["pair_id"]: r for r in json.loads(final.read("manifests/pairs.json"))}
        local_rows = {r["pair_id"]: r for r in json.loads(local.read("manifests/pairs.json"))}
        eval_metadata = json.loads(evaluation.read("metadata.json"))
        eval_records = {(r["pair_id"], r["mode"]): r for r in eval_metadata["records"]}
        for identity, annotation in annotations["hands"].items():
            selection = records[identity]
            if selection["split"] != "validation" or selection["source_member"] != annotation["source_member"]:
                raise ValueError("Identity/source mismatch")
            source_bytes = sources.read(selection["source_member"])
            if sha256(source_bytes).hexdigest() != selection["source_sha256"]:
                raise ValueError("Original source hash mismatch")
            original = Image.open(BytesIO(source_bytes)).convert("RGB")
            if original.size != (1600, 1200):
                raise ValueError("Unexpected original geometry")
            normalized = ImageOps.pad(original, (512, 512), Image.Resampling.LANCZOS, color="white")
            row = final_rows[f"{identity}_classic_red"]
            approved_ref = image_member(final, f"validation/reference/{identity}_classic_red.png")
            if not np.array_equal(np.asarray(normalized), np.asarray(approved_ref)):
                raise ValueError("Source normalization differs from frozen DATA-N001")
            current_512 = image_member(final, f"validation/masks/{identity}_classic_red.png", "L")
            reviewed = Image.open(REPO / f"data/nails/work/seg-review-v4/{identity}/predicted_mask.png").convert("L")
            if not np.array_equal(np.asarray(current_512), np.asarray(reviewed)):
                raise ValueError("Reviewed YOLO mask differs from approved archive")
            current = map_512_to_original(current_512, original.size, mask=True)
            manual, manual_parts = manual_masks(original.size, annotation["fingers"])
            current_parts = current_finger_masks(current, manual_parts)
            original.save(root / f"{identity}_original.png")
            current.save(root / f"{identity}_current_mask.png")
            manual.save(root / f"{identity}_manual_mask.png")
            overlay(original, current, (0, 255, 0)).save(root / f"{identity}_current_overlay.png")
            overlay(original, manual, (255, 0, 255)).save(root / f"{identity}_manual_overlay.png")
            hand_report = {"source_member": selection["source_member"],
                           "original_resolution": list(original.size), "split": "validation",
                           "mask_metrics": {}, "styles": {}}
            for finger in FINGERS:
                hand_report["mask_metrics"][finger] = mask_metrics(current_parts[finger], manual_parts[finger])
            hand = HandGeometry(tuple(tuple(p) for p in row["landmarks"]), 512, 512)
            manual_512 = map_original_mask_to_512(manual)
            union_512 = Image.fromarray(np.maximum(np.asarray(current_512), np.asarray(manual_512)))
            for style in RENDERER_STYLES:
                # One unchanged renderer invocation with union support; both A/B composites
                # receive the exact same RGB proposal. Only the final hard mask differs.
                proposal_512 = render_target(normalized, union_512, style, hand,
                                             production_palette=True)
                proposal = map_512_to_original(proposal_512, original.size)
                current_result, current_outside = full_composite(original, proposal, current)
                manual_result, manual_outside = full_composite(original, proposal, manual)
                stem = f"{identity}_{style}"
                proposal.save(root / f"{stem}_fixed_proposal.png")
                current_result.save(root / f"{stem}_current.png")
                manual_result.save(root / f"{stem}_manual.png")
                sheet(original, current, manual, current_result, manual_result,
                      manual_parts, root / f"{stem}_sheet.jpg")
                hand_report["styles"][style] = {
                    "coverage": "all five nails", "path": "unchanged deterministic renderer",
                    "fixed_proposal_sha256": digest_file(root / f"{stem}_fixed_proposal.png"),
                    "outside_current_changed": current_outside,
                    "outside_manual_changed": manual_outside}
            for style in MODEL_STYLES:
                pair = f"{identity}_{style}__index"
                info = local_rows[pair]
                raw = evaluation.read(f"{pair}/adapter.png")
                if sha256(raw).hexdigest() != eval_records[(pair, "adapter")]["output_sha256"]:
                    raise ValueError("Raw step-50 crop hash mismatch")
                generated = Image.open(BytesIO(raw)).convert("RGB")
                restored = restore_crop(generated, info["transform"])
                proposal = map_512_to_original(restored, original.size)
                current_result, current_outside = full_composite(original, proposal, current_parts["index"])
                manual_result, manual_outside = full_composite(original, proposal, manual_parts["index"])
                stem = f"{identity}_{style}_index_only"
                proposal.save(root / f"{stem}_fixed_proposal.png")
                current_result.save(root / f"{stem}_current.png")
                manual_result.save(root / f"{stem}_manual.png")
                sheet(original, current_parts["index"], manual_parts["index"],
                      current_result, manual_result, {"index": manual_parts["index"]},
                      root / f"{stem}_sheet.jpg")
                hand_report["styles"][style] = {
                    "coverage": "index nail only (saved held-out raw adapter crop)",
                    "path": "NAILS-001-LOCAL-v1 step 50, 20 steps, seed 1977",
                    "raw_adapter_sha256": sha256(raw).hexdigest(),
                    "fixed_proposal_sha256": digest_file(root / f"{stem}_fixed_proposal.png"),
                    "outside_current_changed": current_outside,
                    "outside_manual_changed": manual_outside}
            report["hands"][identity] = hand_report
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-zip", type=Path,
                        default=Path("D:/Downloads/NAILS-001-LOCAL-v1-step050-evaluation.zip"))
    args = parser.parse_args()
    result = run(args.evaluation_zip)
    print(json.dumps({"hands": list(result["hands"]), "status": "COMPARISONS_WRITTEN"}))
