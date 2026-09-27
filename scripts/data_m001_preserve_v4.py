"""CPU DATA-M001 V4: bounded local cosmetic difference maps on source anatomy.

The generated portrait supplies appearance statistics, never target geometry or
high-frequency texture. This only reprocesses the frozen twenty-image pilot.
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
import data_m001_preserve_v3 as v3


STRENGTH = {
    "natural_makeup":     dict(complexion=.42, cheek=.56, eye=.50, lip=.48, brow=.17, finish=.18),
    "no_makeup_makeup":   dict(complexion=.38, cheek=.43, eye=.32, lip=.39, brow=.12, finish=.14),
    "soft_glam":          dict(complexion=.45, cheek=.67, eye=.78, lip=.68, brow=.25, finish=.18),
    "smoky_glam":         dict(complexion=.29, cheek=.28, eye=.93, lip=.45, brow=.22, finish=.12),
    "dewy_peach":         dict(complexion=.44, cheek=.77, eye=.58, lip=.65, brow=.14, finish=.27),
    "rosy_pink":          dict(complexion=.39, cheek=.70, eye=.70, lip=.73, brow=.15, finish=.13),
    "bronze_golden_glam": dict(complexion=.43, cheek=.78, eye=.80, lip=.56, brow=.18, finish=.24),
    "matte_nude":         dict(complexion=.44, cheek=.40, eye=.55, lip=.70, brow=.16, finish=.17),
    "classic_red_lip":    dict(complexion=.27, cheek=.28, eye=.22, lip=.92, brow=.10, finish=.10),
    "bold_evening_glam": dict(complexion=.38, cheek=.62, eye=.91, lip=.82, brow=.22, finish=.16),
}


def bounds(binary):
    yy, xx = np.where(binary)
    if len(xx) < 30:
        raise ValueError("Missing required semantic region")
    return (float(xx.min()), float(yy.min()), float(xx.max() + 1), float(yy.max() + 1))


def aligned_lab(raw_lab, source_mask, raw_mask):
    """Resample only the raw appearance field between matching semantic boxes."""
    sx0, sy0, sx1, sy1 = bounds(source_mask)
    rx0, ry0, rx1, ry1 = bounds(raw_mask)
    x_scale = (rx1 - rx0) / (sx1 - sx0)
    y_scale = (ry1 - ry0) / (sy1 - sy0)
    matrix = np.array([[x_scale, 0, rx0 - sx0 * x_scale],
                       [0, y_scale, ry0 - sy0 * y_scale]], np.float32)
    # Destination coordinates map to the raw field; raw pixels are never pasted.
    return cv2.warpAffine(raw_lab, matrix, (base.SIZE, base.SIZE),
                          flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REFLECT_101)


def eye_masks(labels):
    """Parser eye adjacency and brow boundary, rather than a broad ellipse."""
    skin = labels == base.SKIN
    fields = []
    masks = []
    for eye_id, brow_id in ((base.LEFT_EYE, base.LEFT_BROW), (base.RIGHT_EYE, base.RIGHT_BROW)):
        eye = labels == eye_id
        brow = labels == brow_id
        x0, y0, x1, y1 = bounds(eye)
        bx0, by0, bx1, by1 = bounds(brow)
        outside = (~eye).astype(np.uint8)
        distance = cv2.distanceTransform(outside, cv2.DIST_L2, 3)
        yy, xx = np.mgrid[:base.SIZE, :base.SIZE]
        upper_limit = max(by0 - 2, y0 - 26)
        anatomical = ((xx >= min(x0, bx0) - 10) & (xx <= max(x1, bx1) + 10) &
                      (yy >= upper_limit) & (yy <= y1 + 11) & skin)
        # Full eyelid near the lashes, softly decaying toward brow/cheek.
        field = np.clip((25 - distance) / 19, 0, 1) ** 1.25
        field *= anatomical
        field *= v3.smooth_inside(skin, 2)
        fields.append(field.astype(np.float32))
        masks.append((eye, brow))
    return fields, masks


def source_cheeks(labels):
    _, cheeks, _, _ = v3.regions(labels)
    return cheeks.astype(np.float32)


def transfer(original, raw, source_labels, raw_labels, style_id):
    if style_id not in STRENGTH:
        raise ValueError(f"Unknown Makeup style: {style_id}")
    if original.shape != (base.SIZE, base.SIZE, 3) or raw.shape != original.shape:
        raise ValueError("Expected 512x512 RGB inputs")
    w = STRENGTH[style_id]
    skin = source_labels == base.SKIN
    raw_skin = raw_labels == base.SKIN
    lips = np.isin(source_labels, (base.UPPER_LIP, base.LOWER_LIP))
    raw_lips = np.isin(raw_labels, (base.UPPER_LIP, base.LOWER_LIP))
    brows = np.isin(source_labels, (base.LEFT_BROW, base.RIGHT_BROW))
    if skin.sum() < 15000 or raw_skin.sum() < 15000 or lips.sum() < 150 or raw_lips.sum() < 150:
        raise ValueError("Implausible source or raw facial parsing")
    src = cv2.cvtColor(original, cv2.COLOR_RGB2LAB).astype(np.float32)
    gen = cv2.cvtColor(raw, cv2.COLOR_RGB2LAB).astype(np.float32)
    out = src.copy()
    skin_edge = v3.smooth_inside(skin, 4)

    # A local low frequency difference keeps blush, contour and highlight
    # placement. Remove the broad face-level bias caused by raw reconstruction.
    smooth_src = cv2.GaussianBlur(src, (0, 0), 11)
    smooth_gen = cv2.GaussianBlur(gen, (0, 0), 11)
    local = smooth_gen - smooth_src
    global_offset = np.median(local[skin], axis=0)
    residual = local - global_offset
    complexion = np.clip(local, (-13, -17, -17), (13, 17, 17))
    # The original fine texture is unchanged because only smooth differences
    # are added to its Lab channels.
    out[:, :, 1:] += (skin_edge[:, :, None] * w["complexion"] *
                      complexion[:, :, 1:] * .55)
    out[:, :, 0] += skin_edge * w["finish"] * complexion[:, :, 0] * .38

    cheek_weight = source_cheeks(source_labels) * skin_edge * w["cheek"]
    out[:, :, 1:] += cheek_weight[:, :, None] * np.clip(residual[:, :, 1:], -48, 48)
    out[:, :, 0] += cheek_weight * np.clip(residual[:, :, 0], -23, 23) * .6

    # Per eye semantic alignment prevents raw eye drift from moving the
    # makeup. Difference maps remain spatially varying across each eyelid.
    eye_fields, source_parts = eye_masks(source_labels)
    _, raw_parts = eye_masks(raw_labels)
    # A shifted generated eyeball must not become an eye-shadow stamp after
    # alignment. Inpaint only its appearance field before low-pass sampling.
    raw_ocular = np.isin(raw_labels, (base.LEFT_EYE, base.RIGHT_EYE)).astype(np.uint8)
    raw_ocular = cv2.dilate(raw_ocular, np.ones((5, 5), np.uint8), iterations=1)
    eye_reference = cv2.cvtColor(cv2.inpaint(raw, raw_ocular, 5, cv2.INPAINT_TELEA),
                                 cv2.COLOR_RGB2LAB).astype(np.float32)
    eye_weight = np.zeros(skin.shape, np.float32)
    for field, (source_eye, _), (raw_eye, _) in zip(eye_fields, source_parts, raw_parts):
        mapped = aligned_lab(eye_reference, source_eye, raw_eye)
        source_low = cv2.GaussianBlur(src, (0, 0), 2.8)
        raw_low = cv2.GaussianBlur(mapped, (0, 0), 2.8)
        delta = raw_low - source_low
        # Do not transfer whole-face tone differences into eye shadow.
        delta -= np.clip(global_offset, (-18, -16, -16), (18, 16, 16))
        alpha = field * w["eye"]
        eye_weight = np.maximum(eye_weight, alpha)
        out[:, :, 1:] += alpha[:, :, None] * np.clip(delta[:, :, 1:], -67, 67)
        out[:, :, 0] += alpha * np.clip(delta[:, :, 0], -85, 28)

    # Align raw lip appearance to original upper/lower lips separately. The
    # transfer is local, preserving source lip creases and color variation.
    lip_weight = np.zeros(skin.shape, np.float32)
    for label in (base.UPPER_LIP, base.LOWER_LIP):
        source_part = source_labels == label
        raw_part = raw_labels == label
        mapped = aligned_lab(gen, source_part, raw_part)
        lip_delta = cv2.GaussianBlur(mapped, (0, 0), 2.0) - cv2.GaussianBlur(src, (0, 0), 2.0)
        alpha = v3.smooth_inside(source_part, 2.3) * w["lip"]
        lip_weight = np.maximum(lip_weight, alpha)
        out[:, :, 1:] += alpha[:, :, None] * np.clip(lip_delta[:, :, 1:], -82, 82)
        out[:, :, 0] += alpha * np.clip(lip_delta[:, :, 0], -42, 26)

    brow_weight = np.zeros(skin.shape, np.float32)
    for label in (base.LEFT_BROW, base.RIGHT_BROW):
        source_part = source_labels == label
        raw_part = raw_labels == label
        if source_part.sum() < 30 or raw_part.sum() < 30:
            continue
        mapped = aligned_lab(gen, source_part, raw_part)
        delta = cv2.GaussianBlur(mapped[:, :, 0], (0, 0), 2.2) - cv2.GaussianBlur(src[:, :, 0], (0, 0), 2.2)
        alpha = v3.smooth_inside(source_part, 2) * w["brow"]
        brow_weight = np.maximum(brow_weight, alpha)
        out[:, :, 0] += alpha * np.clip(delta, -20, 13)

    allowed = skin | lips | brows
    rgb = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
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
    }
    if metrics["changed_outside_allowed"]:
        raise AssertionError("Protected pixels changed")
    masks = {"allowed": allowed, "eye": eye_weight, "cheek": cheek_weight,
             "lip": lip_weight, "brow": brow_weight}
    return rgb, masks, metrics


def comparison_sheet(output, identity, styles, page):
    selected = styles[page * 5:(page + 1) * 5]
    canvas = Image.new("RGB", (5 * 512, len(selected) * 546), "white")
    draw = ImageDraw.Draw(canvas)
    for row, style in enumerate(selected):
        folder = output / "targets" / identity / style["id"]
        for column, name in enumerate(("original.jpg", "raw_flux.png", "preserved_v2.png",
                                       "preserved_v3.png", "preserved_v4.png")):
            with Image.open(folder / name) as image:
                canvas.paste(image.convert("RGB"), (column * 512, row * 546))
        draw.text((8, row * 546 + 516), f"{identity} | {style['name']} | V4 VISUAL REVIEW", fill="black")
    for column, name in enumerate(("ORIGINAL", "RAW FLUX", "V2", "V3", "V4")):
        draw.text((column * 512 + 8, 2), name, fill="yellow")
    path = output / "review_sheets" / f"{identity}_part_{page + 1}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, quality=95)


def run(pilot, v2_dir, v3_dir, parser_dir, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Refusing to overwrite V4 results: {output}")
    if base.digest(parser_dir / "model.safetensors") != base.PARSER_WEIGHTS_SHA256:
        raise ValueError("Pinned parser weights hash mismatch")
    config = json.loads((pilot / "config.json").read_text(encoding="utf-8"))
    manifest = json.loads((pilot / "source_manifest.json").read_text(encoding="utf-8"))
    v2_report = json.loads((v2_dir / "preservation_report.json").read_text(encoding="utf-8"))
    v3_report = json.loads((v3_dir / "preservation_v3_report.json").read_text(encoding="utf-8"))
    if len(config["styles"]) != 10 or set(STRENGTH) != {x["id"] for x in config["styles"]}:
        raise ValueError("Ten-style config mismatch")
    if v2_report["samples"] != 20 or v3_report["samples"] != 20:
        raise ValueError("Expected complete V2 and V3 pilots")
    import torch
    from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
    torch.set_num_threads(min(4, torch.get_num_threads()))
    processor = SegformerImageProcessor.from_pretrained(parser_dir, local_files_only=True)
    model = SegformerForSemanticSegmentation.from_pretrained(
        parser_dir, use_safetensors=True, local_files_only=True).eval()
    source_by_id = {x["identity_id"]: x for x in manifest["identities"]}
    v2_by_key = {(x["identity_id"], x["style_id"]): x for x in v2_report["results"]}
    v3_by_key = {(x["identity_id"], x["style_id"]): x for x in v3_report["results"]}
    output.mkdir(parents=True)
    provenance = output / "input_provenance"
    provenance.mkdir()
    for filename in ("config.json", "source_manifest.json", "plan_pilot.json"):
        shutil.copyfile(pilot / filename, provenance / filename)
    shutil.copyfile(v2_dir / "preservation_report.json", provenance / "v2_report.json")
    shutil.copyfile(v3_dir / "preservation_v3_report.json", provenance / "v3_report.json")
    records = []
    for identity in config["pilot_train_ids"]:
        source_record = source_by_id[identity]
        source_path = pilot / source_record["source_path"]
        if source_record["split"] != "TRAIN" or base.digest(source_path) != source_record["source_sha256"]:
            raise ValueError(f"Source provenance mismatch: {identity}")
        with Image.open(source_path) as image:
            original = np.asarray(image.convert("RGB"))
            source_labels = base.parse(image.convert("RGB"), processor, model, torch)
        for style in config["styles"]:
            style_id = style["id"]
            raw_path = pilot / "targets" / identity / style_id / "attempt_1.png"
            sidecar_path = raw_path.with_suffix(".json")
            raw_record = json.loads(sidecar_path.read_text(encoding="utf-8"))
            v2_path = v2_dir / "targets" / identity / style_id / "preserved.png"
            v3_path = v3_dir / "targets" / identity / style_id / "preserved_v3.png"
            key = (identity, style_id)
            if (base.digest(raw_path) != raw_record["target_sha256"] or
                    base.digest(v2_path) != v2_by_key[key]["preserved_sha256"] or
                    base.digest(v3_path) != v3_by_key[key]["v3_sha256"] or
                    raw_record["source_sha256"] != source_record["source_sha256"] or
                    raw_record["lora_active"] is not False or raw_record["adapter_id"] is not None):
                raise ValueError(f"Input provenance mismatch: {identity}/{style_id}")
            with Image.open(raw_path) as image:
                raw = np.asarray(image.convert("RGB"))
                raw_labels = base.parse(image.convert("RGB"), processor, model, torch)
            result, masks, metrics = transfer(original, raw, source_labels, raw_labels, style_id)
            folder = output / "targets" / identity / style_id
            folder.mkdir(parents=True)
            shutil.copyfile(source_path, folder / "original.jpg")
            shutil.copyfile(raw_path, folder / "raw_flux.png")
            shutil.copyfile(sidecar_path, folder / "raw_generation.json")
            shutil.copyfile(v2_path, folder / "preserved_v2.png")
            shutil.copyfile(v3_path, folder / "preserved_v3.png")
            Image.fromarray(result).save(folder / "preserved_v4.png")
            Image.fromarray(source_labels, "L").save(folder / "source_semantics.png")
            Image.fromarray(raw_labels, "L").save(folder / "raw_semantics.png")
            for name, mask in masks.items():
                Image.fromarray((mask * 255).astype(np.uint8), "L").save(folder / f"{name}_mask.png")
            row = {"identity_id": identity, "style_id": style_id,
                   "method": "source_local_lab_difference_transfer_v4",
                   "source_sha256": source_record["source_sha256"],
                   "raw_sha256": raw_record["target_sha256"],
                   "raw_record_sha256": base.digest(folder / "raw_generation.json"),
                   "v2_sha256": v2_by_key[key]["preserved_sha256"],
                   "v3_sha256": v3_by_key[key]["v3_sha256"],
                   "v4_sha256": base.digest(folder / "preserved_v4.png"),
                   "source_semantics_sha256": base.digest(folder / "source_semantics.png"),
                   "raw_semantics_sha256": base.digest(folder / "raw_semantics.png"),
                   "allowed_mask_sha256": base.digest(folder / "allowed_mask.png"),
                   "style_strength": STRENGTH[style_id], "metrics": metrics,
                   "review_state": "PENDING_VISUAL_REVIEW", "created_utc": datetime.now(timezone.utc).isoformat()}
            base.save_json(folder / "preservation_v4.json", row)
            records.append(row)
            print(f"{identity}/{style_id}: {metrics['changed_pixels']} edited, 0 protected edited", flush=True)
        for page in (0, 1):
            comparison_sheet(output, identity, config["styles"], page)
    report = {"method": "source_local_lab_difference_transfer_v4",
              "parser_model": base.PARSER_ID, "parser_revision": base.PARSER_REV,
              "parser_weights_sha256": base.PARSER_WEIGHTS_SHA256,
              "pilot_config_sha256": base.digest(provenance / "config.json"),
              "pilot_plan_sha256": base.digest(provenance / "plan_pilot.json"),
              "v2_report_sha256": base.digest(provenance / "v2_report.json"),
              "v3_report_sha256": base.digest(provenance / "v3_report.json"),
              "samples": len(records), "all_protected_pixels_exact": all(
                  x["metrics"]["changed_outside_allowed"] == 0 for x in records),
              "review_state": "PENDING_VISUAL_REVIEW", "results": records}
    base.save_json(output / "preservation_v4_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--v2", type=Path, required=True)
    parser.add_argument("--v3", type=Path, required=True)
    parser.add_argument("--parser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.pilot, args.v2, args.v3, args.parser, args.output)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
