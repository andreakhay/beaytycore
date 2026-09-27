"""Focused CPU V3 cosmetic transfer for the existing DATA-M001 twenty-image pilot.

The original supplies geometry and high-frequency detail. Raw FLUX supplies only
region-specific Lab appearance statistics. This does not accept training pairs.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
from PIL import Image, ImageDraw

import data_m001_preserve as base


# One compositor, with bounded cosmetic intensity per style and region.
STRENGTH = {
    "natural_makeup":      dict(complexion=.42, cheek=.42, eye=.43, lip=.48, brow=.17, finish=.12),
    "no_makeup_makeup":    dict(complexion=.36, cheek=.32, eye=.27, lip=.32, brow=.13, finish=.08),
    "soft_glam":           dict(complexion=.52, cheek=.55, eye=.73, lip=.67, brow=.28, finish=.15),
    "smoky_glam":          dict(complexion=.35, cheek=.25, eye=.95, lip=.40, brow=.26, finish=.12),
    "dewy_peach":          dict(complexion=.44, cheek=.74, eye=.51, lip=.60, brow=.15, finish=.22),
    "rosy_pink":           dict(complexion=.40, cheek=.69, eye=.66, lip=.72, brow=.16, finish=.12),
    "bronze_golden_glam":  dict(complexion=.47, cheek=.80, eye=.78, lip=.55, brow=.20, finish=.20),
    "matte_nude":          dict(complexion=.45, cheek=.32, eye=.48, lip=.68, brow=.17, finish=.08),
    "classic_red_lip":     dict(complexion=.30, cheek=.27, eye=.19, lip=.95, brow=.10, finish=.08),
    "bold_evening_glam":  dict(complexion=.46, cheek=.56, eye=.91, lip=.80, brow=.25, finish=.18),
}


def smooth_inside(binary, pixels=3):
    distance = cv2.distanceTransform(binary.astype(np.uint8), cv2.DIST_L2, 3)
    return np.clip(distance / pixels, 0, 1).astype(np.float32)


def regions(labels):
    """Source-aligned eyelid and cheek fields, never raw facial silhouettes."""
    yy, xx = np.mgrid[:base.SIZE, :base.SIZE]
    skin = labels == base.SKIN
    eye = np.zeros(labels.shape, np.float32)
    cheek = np.zeros(labels.shape, np.float32)
    eye_samples = []
    cheek_samples = []
    mouth_y = np.where(np.isin(labels, (base.MOUTH, base.UPPER_LIP, base.LOWER_LIP)))[0]
    if mouth_y.size < 20:
        raise ValueError("Parser did not resolve mouth")
    for eye_label in (base.LEFT_EYE, base.RIGHT_EYE):
        ey, ex = np.where(labels == eye_label)
        if len(ex) < 35:
            raise ValueError(f"Parser did not resolve eye label {eye_label}")
        x0, x1, y0, y1 = ex.min(), ex.max(), ey.min(), ey.max()
        width = max(8, x1 - x0 + 1)
        height = max(7, y1 - y0 + 1)
        cx = (x0 + x1) / 2
        # Upper eyelid only, with a small lower-lash allowance. Brow/eyeball
        # labels are still excluded even when the soft field reaches them.
        upper = np.exp(-.5 * (((xx - cx) / (.66 * width)) ** 2 +
                                ((yy - (y0 - .52 * height)) / (.71 * height)) ** 2))
        lower = .22 * np.exp(-.5 * (((xx - cx) / (.55 * width)) ** 2 +
                                     ((yy - (y1 + .12 * height)) / (.31 * height)) ** 2))
        eye = np.maximum(eye, np.maximum(upper, lower).astype(np.float32))
        eye_samples.append((upper > .43) & skin)
        outward = -1 if cx < base.SIZE / 2 else 1
        cy = y1 + .51 * max(15, int(mouth_y.min()) - y1)
        cx_cheek = cx + outward * .36 * width
        patch = np.exp(-.5 * (((xx - cx_cheek) / (.82 * width)) ** 2 +
                                ((yy - cy) / (.65 * max(15, int(mouth_y.min()) - y1))) ** 2))
        cheek = np.maximum(cheek, patch.astype(np.float32))
        cheek_samples.append((patch > .48) & skin)
    # Avoid broad eye masks by suppressing their tails and clipping to source skin.
    eye = np.clip((eye - .24) / .76, 0, 1) ** 1.35
    cheek = np.clip((cheek - .18) / .82, 0, 1) ** 1.1
    return eye * skin, cheek * skin, np.logical_or.reduce(eye_samples), np.logical_or.reduce(cheek_samples)


def median_lab(lab, mask):
    return base.masked_median(lab, mask)


def composite(original, raw, source_labels, raw_labels, style_id):
    if style_id not in STRENGTH:
        raise ValueError(f"Unknown Makeup style: {style_id}")
    if original.shape != (base.SIZE, base.SIZE, 3) or raw.shape != original.shape:
        raise ValueError("Expected 512x512 RGB inputs")
    w = STRENGTH[style_id]
    skin = source_labels == base.SKIN
    brow = np.isin(source_labels, (base.LEFT_BROW, base.RIGHT_BROW))
    lips = np.isin(source_labels, (base.UPPER_LIP, base.LOWER_LIP))
    raw_skin = raw_labels == base.SKIN
    raw_lips = np.isin(raw_labels, (base.UPPER_LIP, base.LOWER_LIP))
    if skin.sum() < 15000 or lips.sum() < 150 or raw_lips.sum() < 150:
        raise ValueError("Implausible face segmentation")
    source_eye, source_cheek, source_eye_sample, source_cheek_sample = regions(source_labels)
    _, _, raw_eye_sample, raw_cheek_sample = regions(raw_labels)
    src = cv2.cvtColor(original, cv2.COLOR_RGB2LAB).astype(np.float32)
    gen = cv2.cvtColor(raw, cv2.COLOR_RGB2LAB).astype(np.float32)
    result = src.copy()
    skin_edge = smooth_inside(skin, 5)

    # Global complexion is a bounded low-frequency statistic, not raw pixels.
    skin_delta = median_lab(gen, raw_skin) - median_lab(src, skin)
    result[:, :, 1:] += (skin_edge[:, :, None] * w["complexion"] *
                          np.clip(skin_delta[1:], -15, 15)[None, None, :])
    # Restrained finish adjustment preserves all original high-frequency texture.
    result[:, :, 0] += skin_edge * w["finish"] * np.clip(skin_delta[0], -12, 12)

    # Cosmetic color is measured relative to each image's complexion. This
    # prevents regenerated face tone from becoming an eye or cheek mask.
    source_skin_color = median_lab(src, skin)
    raw_skin_color = median_lab(gen, raw_skin)
    eye_delta = (median_lab(gen, raw_eye_sample) - raw_skin_color) - (
        median_lab(src, source_eye_sample) - source_skin_color)
    cheek_delta = (median_lab(gen, raw_cheek_sample) - raw_skin_color) - (
        median_lab(src, source_cheek_sample) - source_skin_color)
    eye_alpha = source_eye * skin_edge * w["eye"]
    cheek_alpha = source_cheek * skin_edge * w["cheek"]
    result[:, :, 1:] += eye_alpha[:, :, None] * np.clip(eye_delta[1:], -65, 65)
    result[:, :, 0] += eye_alpha * np.clip(eye_delta[0], -53, 20)
    result[:, :, 1:] += cheek_alpha[:, :, None] * np.clip(cheek_delta[1:], -42, 42)
    result[:, :, 0] += cheek_alpha * np.clip(cheek_delta[0], -18, 16) * .55

    # Original lips alone set the target shape. Feather toward both exterior
    # and inner mouth edges. Protect the mouth label and teeth exactly.
    lip_delta = median_lab(gen, raw_lips) - median_lab(src, lips)
    lip_edge = smooth_inside(lips, 2.7)
    lip_alpha = lip_edge * w["lip"]
    result[:, :, 1:] += lip_alpha[:, :, None] * np.clip(lip_delta[1:], -78, 78)
    # A dark or gray generated lip cannot erase source lip texture or become
    # a flat black patch. Treat such raw appearances as review failures.
    result[:, :, 0] += lip_alpha * np.clip(lip_delta[0], -37, 21)

    raw_brow = np.isin(raw_labels, (base.LEFT_BROW, base.RIGHT_BROW))
    if raw_brow.sum() >= 30 and brow.sum() >= 30:
        brow_delta = median_lab(gen, raw_brow)[0] - median_lab(src, brow)[0]
        result[:, :, 0] += smooth_inside(brow, 2) * w["brow"] * np.clip(brow_delta, -20, 12)

    allowed = skin | lips | brow
    rgb = cv2.cvtColor(np.clip(result, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
    rgb[~allowed] = original[~allowed]
    changed = np.any(rgb != original, axis=2)
    metrics = {
        "changed_outside_allowed": int((changed & ~allowed).sum()),
        "source_eye_pixels_changed": int((changed & np.isin(source_labels, (base.LEFT_EYE, base.RIGHT_EYE))).sum()),
        "source_nose_pixels_changed": int((changed & (source_labels == base.NOSE)).sum()),
        "source_mouth_pixels_changed": int((changed & (source_labels == base.MOUTH)).sum()),
        "source_hair_pixels_changed": int((changed & (source_labels == 13)).sum()),
        "changed_pixels": int(changed.sum()),
        "mean_abs_rgb_change": round(float(np.abs(rgb.astype(np.int16) - original.astype(np.int16)).mean()), 3),
        "raw_lip_delta_lab": [round(float(x), 2) for x in lip_delta],
    }
    if metrics["changed_outside_allowed"]:
        raise AssertionError("Protected source pixels changed")
    masks = {"allowed": allowed, "eye": eye_alpha, "cheek": cheek_alpha, "lip": lip_alpha}
    return rgb, masks, metrics


def sheet(output, identity, styles, page):
    selected = styles[page * 5:(page + 1) * 5]
    canvas = Image.new("RGB", (4 * 512, len(selected) * 545), "white")
    draw = ImageDraw.Draw(canvas)
    for row, style in enumerate(selected):
        folder = output / "targets" / identity / style["id"]
        for column, name in enumerate(("original.jpg", "raw_flux.png", "preserved_v2.png", "preserved_v3.png")):
            with Image.open(folder / name) as image:
                canvas.paste(image.convert("RGB"), (column * 512, row * 545))
        draw.text((8, row * 545 + 516), f"{identity} | {style['name']} | V3 REVIEW PENDING", fill="black")
    for col, label in enumerate(("ORIGINAL", "RAW FLUX", "V2", "V3")):
        draw.text((col * 512 + 8, 2), label, fill="yellow")
    destination = output / "review_sheets" / f"{identity}_part_{page + 1}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=95)


def run(pilot, previous, parser_dir, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Refusing to overwrite V3 output: {output}")
    if base.digest(parser_dir / "model.safetensors") != base.PARSER_WEIGHTS_SHA256:
        raise ValueError("Pinned parser weights hash mismatch")
    config = json.loads((pilot / "config.json").read_text(encoding="utf-8"))
    manifest = json.loads((pilot / "source_manifest.json").read_text(encoding="utf-8"))
    if len(config["styles"]) != 10 or set(STRENGTH) != {x["id"] for x in config["styles"]}:
        raise ValueError("Ten-style config mismatch")
    previous_report = json.loads((previous / "preservation_report.json").read_text(encoding="utf-8"))
    if previous_report["method"] != "source_semantic_lab_appearance_transfer_v2":
        raise ValueError("Expected V2 input")
    import torch
    from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
    torch.set_num_threads(min(4, torch.get_num_threads()))
    processor = SegformerImageProcessor.from_pretrained(parser_dir, local_files_only=True)
    model = SegformerForSemanticSegmentation.from_pretrained(
        parser_dir, use_safetensors=True, local_files_only=True).eval()
    by_id = {x["identity_id"]: x for x in manifest["identities"]}
    v2_rows = {(x["identity_id"], x["style_id"]): x for x in previous_report["results"]}
    output.mkdir(parents=True)
    prov = output / "input_provenance"
    prov.mkdir()
    for name in ("config.json", "source_manifest.json", "plan_pilot.json"):
        shutil.copyfile(pilot / name, prov / name)
    shutil.copyfile(previous / "preservation_report.json", prov / "preservation_v2_report.json")
    records = []
    for identity in config["pilot_train_ids"]:
        source_record = by_id[identity]
        source_path = pilot / source_record["source_path"]
        if source_record["split"] != "TRAIN" or base.digest(source_path) != source_record["source_sha256"]:
            raise ValueError(f"Source provenance mismatch: {identity}")
        with Image.open(source_path) as image:
            source = np.asarray(image.convert("RGB"))
            source_labels = base.parse(image.convert("RGB"), processor, model, torch)
        for style in config["styles"]:
            style_id = style["id"]
            original = previous / "targets" / identity / style_id / "original.jpg"
            raw_path = pilot / "targets" / identity / style_id / "attempt_1.png"
            v2_path = previous / "targets" / identity / style_id / "preserved.png"
            raw_record_path = raw_path.with_suffix(".json")
            raw_record = json.loads(raw_record_path.read_text(encoding="utf-8"))
            v2_record = v2_rows[(identity, style_id)]
            if (base.digest(original) != source_record["source_sha256"] or
                    base.digest(raw_path) != raw_record["target_sha256"] or
                    base.digest(v2_path) != v2_record["preserved_sha256"] or
                    raw_record["lora_active"] is not False or raw_record["adapter_id"] is not None):
                raise ValueError(f"Input hash/adapter mismatch: {identity}/{style_id}")
            with Image.open(raw_path) as image:
                raw = np.asarray(image.convert("RGB"))
                raw_labels = base.parse(image.convert("RGB"), processor, model, torch)
            result, masks, metrics = composite(source, raw, source_labels, raw_labels, style_id)
            folder = output / "targets" / identity / style_id
            folder.mkdir(parents=True)
            shutil.copyfile(source_path, folder / "original.jpg")
            shutil.copyfile(raw_path, folder / "raw_flux.png")
            shutil.copyfile(raw_record_path, folder / "raw_generation.json")
            shutil.copyfile(v2_path, folder / "preserved_v2.png")
            Image.fromarray(result).save(folder / "preserved_v3.png")
            Image.fromarray(source_labels, "L").save(folder / "source_semantics.png")
            Image.fromarray((masks["allowed"] * 255).astype(np.uint8), "L").save(folder / "allowed_region.png")
            for name in ("eye", "cheek", "lip"):
                Image.fromarray((masks[name] * 255).astype(np.uint8), "L").save(folder / f"{name}_strength.png")
            row = {"identity_id": identity, "style_id": style_id, "method": "source_semantic_lab_appearance_transfer_v3",
                   "source_sha256": source_record["source_sha256"], "raw_sha256": raw_record["target_sha256"],
                   "v2_sha256": v2_record["preserved_sha256"], "v3_sha256": base.digest(folder / "preserved_v3.png"),
                   "raw_record_sha256": base.digest(folder / "raw_generation.json"),
                   "style_strength": STRENGTH[style_id], "metrics": metrics,
                   "review_state": "PENDING_VISUAL_REVIEW", "created_utc": datetime.now(timezone.utc).isoformat()}
            base.save_json(folder / "preservation_v3.json", row)
            records.append(row)
            print(f"{identity}/{style_id}: {metrics['changed_pixels']} edited, 0 protected edited", flush=True)
        for page in (0, 1):
            sheet(output, identity, config["styles"], page)
    report = {"method": "source_semantic_lab_appearance_transfer_v3", "parser_model": base.PARSER_ID,
              "parser_revision": base.PARSER_REV, "parser_weights_sha256": base.PARSER_WEIGHTS_SHA256,
              "pilot_plan_sha256": base.digest(prov / "plan_pilot.json"),
              "pilot_config_sha256": base.digest(prov / "config.json"),
              "v2_report_sha256": base.digest(prov / "preservation_v2_report.json"),
              "samples": len(records), "all_protected_pixels_exact": all(
                  x["metrics"]["changed_outside_allowed"] == 0 for x in records),
              "review_state": "PENDING_VISUAL_REVIEW", "results": records}
    base.save_json(output / "preservation_v3_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--v2", type=Path, required=True)
    parser.add_argument("--parser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.pilot, args.v2, args.parser, args.output)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
