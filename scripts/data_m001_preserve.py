"""CPU-only, source-geometry Makeup appearance transfer for DATA-M001.

Never pastes a generated face. The original supplies every pixel's structure;
source-aligned semantic masks permit bounded color and low-frequency tone edits.
All outputs remain PENDING explicit human review.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
from PIL import Image, ImageDraw


PARSER_ID = "jonathandinu/face-parsing"
PARSER_REV = "758b82e15a0178c9db39c1ff666a8b56e3a550c8"
PARSER_WEIGHTS_SHA256 = "c2bec795a8c243db71bd95be538fd62559003566466c71237e45c99b920f4b62"
SIZE = 512
SKIN, NOSE, LEFT_EYE, RIGHT_EYE, LEFT_BROW, RIGHT_BROW, MOUTH, UPPER_LIP, LOWER_LIP = 1, 2, 4, 5, 6, 7, 10, 11, 12

# These are conservative transfer strengths, not trained or optimized values.
# Original luminance/texture is retained except bounded local cosmetic tone.
STYLE = {
    "natural_makeup":       {"skin": .10, "eye": .30, "cheek": .35, "lip": .35, "brow": .12, "eye_l": .23, "lip_l": .20},
    "no_makeup_makeup":     {"skin": .08, "eye": .19, "cheek": .20, "lip": .23, "brow": .10, "eye_l": .12, "lip_l": .12},
    "soft_glam":            {"skin": .12, "eye": .52, "cheek": .42, "lip": .56, "brow": .22, "eye_l": .44, "lip_l": .35},
    "smoky_glam":           {"skin": .08, "eye": .67, "cheek": .17, "lip": .37, "brow": .18, "eye_l": .72, "lip_l": .22},
    "dewy_peach":           {"skin": .10, "eye": .36, "cheek": .54, "lip": .52, "brow": .12, "eye_l": .26, "lip_l": .30},
    "rosy_pink":            {"skin": .08, "eye": .43, "cheek": .47, "lip": .58, "brow": .12, "eye_l": .28, "lip_l": .30},
    "bronze_golden_glam":   {"skin": .10, "eye": .49, "cheek": .48, "lip": .45, "brow": .14, "eye_l": .37, "lip_l": .25},
    "matte_nude":           {"skin": .08, "eye": .30, "cheek": .20, "lip": .49, "brow": .12, "eye_l": .20, "lip_l": .27},
    "classic_red_lip":      {"skin": .05, "eye": .13, "cheek": .16, "lip": .90, "brow": .06, "eye_l": .09, "lip_l": .70},
    "bold_evening_glam":   {"skin": .10, "eye": .62, "cheek": .43, "lip": .78, "brow": .20, "eye_l": .65, "lip_l": .65},
}

EYE_PIGMENT = {
    "natural_makeup": (.22, .18), "no_makeup_makeup": (.12, .10),
    "soft_glam": (.48, .26), "smoky_glam": (.42, .63),
    "dewy_peach": (.38, .15), "rosy_pink": (.48, .22),
    "bronze_golden_glam": (.48, .27), "matte_nude": (.28, .16),
    "classic_red_lip": (.12, .09), "bold_evening_glam": (.50, .58),
}


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse(image: Image.Image, processor, model, torch) -> np.ndarray:
    inputs = processor(images=image, return_tensors="pt")
    with torch.inference_mode():
        logits = model(**inputs).logits
        resized = torch.nn.functional.interpolate(logits, size=(SIZE, SIZE), mode="bilinear", align_corners=False)
    return resized.argmax(1)[0].byte().cpu().numpy()


def soft_semantic_mask(binary: np.ndarray, sigma: float = 2.5) -> np.ndarray:
    """Feather inward, never across protected source labels."""
    raw = binary.astype(np.float32)
    return cv2.GaussianBlur(raw, (0, 0), sigma) * raw


def eye_and_cheek_fields(labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[:SIZE, :SIZE]
    eye_field = np.zeros((SIZE, SIZE), np.float32)
    cheek_field = np.zeros((SIZE, SIZE), np.float32)
    mouth_y = np.where(np.isin(labels, [MOUTH, UPPER_LIP, LOWER_LIP]))[0]
    if mouth_y.size < 20:
        raise ValueError("Parser did not resolve the mouth")
    mouth_top = int(mouth_y.min())
    for side, eye_label in enumerate((LEFT_EYE, RIGHT_EYE)):
        ey, ex = np.where(labels == eye_label)
        if len(ex) < 35:
            raise ValueError(f"Parser did not resolve eye label {eye_label}")
        x0, x1, y0, y1 = ex.min(), ex.max(), ey.min(), ey.max()
        width, height = max(8, x1 - x0 + 1), max(7, y1 - y0 + 1)
        center_x = (x0 + x1) / 2
        eye_center_y = y0 - .12 * height
        eye_blob = np.exp(-.5 * (((xx - center_x) / (.66 * width)) ** 2 +
                                  ((yy - eye_center_y) / (.96 * height)) ** 2))
        eye_field = np.maximum(eye_field, eye_blob.astype(np.float32))
        outward = -1 if center_x < SIZE / 2 else 1
        cheek_x = center_x + outward * .30 * width
        cheek_y = y1 + .42 * max(18, mouth_top - y1)
        cheek_blob = np.exp(-.5 * (((xx - cheek_x) / (.92 * width)) ** 2 +
                                    ((yy - cheek_y) / (1.05 * max(12, mouth_top - y1))) ** 2))
        cheek_field = np.maximum(cheek_field, cheek_blob.astype(np.float32))
    return eye_field, cheek_field


def masked_median(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if int(mask.sum()) < 30:
        raise ValueError("Too few semantic pixels for color transfer")
    return np.median(values[mask], axis=0).astype(np.float32)


def transfer(original: np.ndarray, raw: np.ndarray, source_labels: np.ndarray,
             raw_labels: np.ndarray, style_id: str, enhance_eyes: bool = False) -> tuple[np.ndarray, dict, dict]:
    """Transfer pigment/soft tone only; no generated texture or shape is pasted."""
    if original.shape != (SIZE, SIZE, 3) or raw.shape != original.shape:
        raise ValueError("Expected aligned 512x512 RGB inputs")
    if style_id not in STYLE:
        raise ValueError(f"Unknown Makeup style: {style_id}")
    weights = STYLE[style_id]
    skin = source_labels == SKIN
    source_lips = np.isin(source_labels, (UPPER_LIP, LOWER_LIP))
    raw_lips = np.isin(raw_labels, (UPPER_LIP, LOWER_LIP))
    brows = np.isin(source_labels, (LEFT_BROW, RIGHT_BROW))
    eye_field, cheek_field = eye_and_cheek_fields(source_labels)
    if skin.sum() < 15000 or source_lips.sum() < 150 or raw_lips.sum() < 150:
        raise ValueError("Implausible source or generated facial segmentation")

    # Convert to Lab. Source L is the base of the result, retaining its fine
    # facial detail. Blur generated-minus-source appearance so altered generated
    # facial boundaries never imprint onto the source.
    src = cv2.cvtColor(original, cv2.COLOR_RGB2LAB).astype(np.float32)
    gen = cv2.cvtColor(raw, cv2.COLOR_RGB2LAB).astype(np.float32)
    smooth_src = cv2.GaussianBlur(src, (0, 0), 9)
    smooth_gen = cv2.GaussianBlur(gen, (0, 0), 9)
    delta = smooth_gen - smooth_src
    global_shift = masked_median(delta, skin)
    local = delta - global_shift
    result = src.copy()

    # Global complexion adjustment is deliberately small; only chroma moves.
    skin_soft = soft_semantic_mask(skin, 3)
    broad = weights["skin"] * skin_soft
    result[:, :, 1:] += broad[:, :, None] * np.clip(global_shift[1:], -12, 12)

    # Eye color and tone are localized to original skin around eyelids. The
    # segmented eyeballs/iris/pupils have exactly zero contribution.
    eye_alpha = skin_soft * np.clip(eye_field * 1.25, 0, 1) * weights["eye"]
    result[:, :, 1:] += eye_alpha[:, :, None] * np.clip(local[:, :, 1:], -55, 55)
    result[:, :, 0] += (skin_soft * eye_field * weights["eye_l"] *
                         np.clip(local[:, :, 0], -48, 18))

    # Blush, bronzer and highlights use broad, feathered cheek fields, but
    # local differences are low passed and original texture is retained.
    cheek_alpha = skin_soft * cheek_field * weights["cheek"]
    result[:, :, 1:] += cheek_alpha[:, :, None] * np.clip(local[:, :, 1:], -42, 42)
    result[:, :, 0] += cheek_alpha * np.clip(local[:, :, 0], -12, 12) * .38

    # Pigment comes from the generated lip region, geometry from source lips.
    lip_src = masked_median(src, source_lips)
    lip_gen = masked_median(gen, raw_lips)
    lip_alpha = soft_semantic_mask(source_lips, 1.4) * weights["lip"]
    result[:, :, 1:] += lip_alpha[:, :, None] * np.clip(lip_gen[1:] - lip_src[1:], -90, 90)
    result[:, :, 0] += (soft_semantic_mask(source_lips, 1.4) * weights["lip_l"] *
                         np.clip(lip_gen[0] - lip_src[0], -75, 28))

    # Groom the existing brow only; generated brow silhouettes are discarded.
    brow_alpha = soft_semantic_mask(brows, 1.2) * weights["brow"]
    brow_shift = np.clip(masked_median(gen, np.isin(raw_labels, (LEFT_BROW, RIGHT_BROW)))[0] -
                         masked_median(src, brows)[0], -28, 12)
    result[:, :, 0] += brow_alpha * brow_shift

    eye_pigment_delta = None
    if enhance_eyes:
        # Raw geometry may move, so gather pigment from its own parsed eye
        # neighborhood. Apply the measured color to the source eye neighborhood.
        # The peak stays at the source upper eyelid and fades away smoothly.
        raw_eye_field, _ = eye_and_cheek_fields(raw_labels)
        source_eyelid = (eye_field > .38) & skin
        raw_eyelid = (raw_eye_field > .38) & (raw_labels == SKIN)
        source_eye_color = masked_median(src, source_eyelid)
        raw_eye_color = masked_median(gen, raw_eyelid)
        eye_pigment_delta = raw_eye_color - source_eye_color
        chroma_strength, tone_strength = EYE_PIGMENT[style_id]
        pigment_alpha = skin_soft * (eye_field ** 1.35)
        result[:, :, 1:] += (pigment_alpha[:, :, None] * chroma_strength *
                             np.clip(eye_pigment_delta[1:], -52, 52))
        # Dark shadow can be transferred; global face lightening cannot.
        result[:, :, 0] += (pigment_alpha * tone_strength *
                             np.clip(eye_pigment_delta[0], -78, 0))

    allowed = skin | source_lips | brows
    result = np.clip(result, 0, 255).astype(np.uint8)
    rgb = cv2.cvtColor(result, cv2.COLOR_LAB2RGB)
    # Exact pixel preservation outside all editable source anatomy, including
    # eyeballs, nose, teeth, hair, background, ears, neck, clothing and scene.
    rgb[~allowed] = original[~allowed]
    unchanged_outside = bool(np.array_equal(rgb[~allowed], original[~allowed]))
    if not unchanged_outside:
        raise AssertionError("Protected pixels changed")
    changed = np.any(rgb != original, axis=2)
    masks = {"allowed": allowed, "skin": skin, "lips": source_lips, "brows": brows,
             "eye_weight": eye_alpha, "cheek_weight": cheek_alpha}
    metrics = {"source_skin_pixels": int(skin.sum()), "source_lip_pixels": int(source_lips.sum()),
               "allowed_pixels": int(allowed.sum()), "changed_pixels": int(changed.sum()),
               "changed_outside_allowed": int((changed & ~allowed).sum()),
               "protected_pixels_unchanged": unchanged_outside,
               "source_eye_pixels_changed": int((changed & np.isin(source_labels, (LEFT_EYE, RIGHT_EYE))).sum()),
               "source_nose_pixels_changed": int((changed & (source_labels == NOSE)).sum()),
               "source_mouth_pixels_changed": int((changed & (source_labels == MOUTH)).sum()),
               "source_hair_pixels_changed": int((changed & (source_labels == 13)).sum()),
               "mean_abs_rgb_change": round(float(np.abs(rgb.astype(np.int16) - original.astype(np.int16)).mean()), 3),
               "eye_pigment_delta_lab": None if eye_pigment_delta is None else
                   [round(float(value), 2) for value in eye_pigment_delta]}
    return rgb, masks, metrics


def comparison_sheet(root: Path, output: Path, identity: str, styles: list[dict], page: int) -> Path:
    selected = styles[page * 5:(page + 1) * 5]
    sheet = Image.new("RGB", (3 * 512, len(selected) * 550), "white")
    draw = ImageDraw.Draw(sheet)
    for row, style in enumerate(selected):
        folder = output / "targets" / identity / style["id"]
        paths = [folder / "original.jpg", folder / "raw_flux.png", folder / "preserved.png"]
        for column, path in enumerate(paths):
            with Image.open(path) as image:
                sheet.paste(image.convert("RGB"), (column * 512, row * 550))
        draw.text((8, row * 550 + 517), f"{identity} | {style['name']} | PENDING HUMAN REVIEW", fill="black")
    for column, name in enumerate(("ORIGINAL", "RAW FLUX", "PRESERVED TARGET")):
        draw.text((column * 512 + 8, 2), name, fill="yellow" if column == 1 else "black")
    path = output / "review_sheets" / f"{identity}_part_{page + 1}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=94)
    return path


def run(root: Path, output: Path, parser_dir: Path, enhance_eyes: bool = False) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Refusing to overwrite preservation results: {output}")
    if digest(parser_dir / "model.safetensors") != PARSER_WEIGHTS_SHA256:
        raise ValueError("Pinned face parser weight SHA256 mismatch")
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "source_manifest.json").read_text(encoding="utf-8"))
    styles = config["styles"]
    if len(styles) != 10 or set(STYLE) != {style["id"] for style in styles}:
        raise ValueError("Ten-style taxonomy mismatch")
    by_id = {record["identity_id"]: record for record in manifest["identities"]}
    import torch
    from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

    torch.set_num_threads(min(4, torch.get_num_threads()))
    processor = SegformerImageProcessor.from_pretrained(parser_dir, local_files_only=True)
    model = SegformerForSemanticSegmentation.from_pretrained(
        parser_dir, use_safetensors=True, local_files_only=True).eval()
    output.mkdir(parents=True)
    provenance_dir = output / "input_provenance"
    provenance_dir.mkdir()
    for filename in ("config.json", "source_manifest.json", "plan_pilot.json"):
        shutil.copyfile(root / filename, provenance_dir / filename)
    records = []
    for identity in config["pilot_train_ids"]:
        source_record = by_id[identity]
        source_path = root / source_record["source_path"]
        if source_record["split"] != "TRAIN" or digest(source_path) != source_record["source_sha256"]:
            raise ValueError(f"Source split/hash mismatch: {identity}")
        with Image.open(source_path) as source_image:
            original = np.asarray(source_image.convert("RGB"))
            source_labels = parse(source_image.convert("RGB"), processor, model, torch)
        if original.shape != (SIZE, SIZE, 3):
            raise ValueError(f"Unexpected source size: {identity}")
        for style in styles:
            style_id = style["id"]
            raw_path = root / "targets" / identity / style_id / "attempt_1.png"
            raw_record = json.loads(raw_path.with_suffix(".json").read_text(encoding="utf-8"))
            if (not raw_record["success"] or digest(raw_path) != raw_record["target_sha256"]
                    or raw_record["source_sha256"] != source_record["source_sha256"]
                    or raw_record["lora_active"] is not False or raw_record["adapter_id"] is not None):
                raise ValueError(f"Raw generation provenance mismatch: {identity}/{style_id}")
            with Image.open(raw_path) as raw_image:
                raw = np.asarray(raw_image.convert("RGB"))
                raw_labels = parse(raw_image.convert("RGB"), processor, model, torch)
            preserved, masks, metrics = transfer(original, raw, source_labels, raw_labels, style_id,
                                                 enhance_eyes=enhance_eyes)
            folder = output / "targets" / identity / style_id
            folder.mkdir(parents=True)
            shutil.copyfile(source_path, folder / "original.jpg")
            shutil.copyfile(raw_path, folder / "raw_flux.png")
            shutil.copyfile(raw_path.with_suffix(".json"), folder / "raw_generation.json")
            Image.fromarray(preserved).save(folder / "preserved.png")
            Image.fromarray(source_labels, "L").save(folder / "source_semantics.png")
            Image.fromarray(raw_labels, "L").save(folder / "raw_semantics.png")
            Image.fromarray(masks["allowed"].astype(np.uint8) * 255, "L").save(folder / "allowed_region.png")
            # Diagnostic preview only; not itself a compositing input.
            mask_preview = np.zeros((SIZE, SIZE, 3), np.uint8)
            mask_preview[masks["skin"]] = (35, 100, 180)
            mask_preview[masks["brows"]] = (240, 170, 0)
            mask_preview[masks["lips"]] = (230, 30, 60)
            mask_preview[:, :, 1] = np.maximum(mask_preview[:, :, 1],
                                                (masks["eye_weight"] * 255).astype(np.uint8))
            Image.fromarray(mask_preview).save(folder / "region_preview.png")
            record = {"dataset_id": "DATA-M001", "identity_id": identity, "style_id": style_id,
                      "source_sha256": source_record["source_sha256"],
                      "raw_sha256": raw_record["target_sha256"],
                      "raw_record_sha256": digest(folder / "raw_generation.json"),
                      "preserved_sha256": digest(folder / "preserved.png"),
                      "source_semantics_sha256": digest(folder / "source_semantics.png"),
                      "raw_semantics_sha256": digest(folder / "raw_semantics.png"),
                      "allowed_region_sha256": digest(folder / "allowed_region.png"),
                      "method": "source_semantic_lab_appearance_transfer_v2" if enhance_eyes else
                                "source_semantic_lab_appearance_transfer_v1",
                      "parser_model": PARSER_ID, "parser_revision": PARSER_REV,
                      "parser_weights_sha256": PARSER_WEIGHTS_SHA256,
                      "style_weights": STYLE[style_id], "metrics": metrics,
                      "review_state": "PENDING_HUMAN_REVIEW", "created_utc": datetime.now(timezone.utc).isoformat()}
            save_json(folder / "preservation.json", record)
            records.append(record)
            print(f"{identity}/{style_id}: {metrics['changed_pixels']} changed, 0 protected changed", flush=True)
        for page in (0, 1):
            comparison_sheet(root, output, identity, styles, page)
    report = {"method": "source_semantic_lab_appearance_transfer_v2" if enhance_eyes else
                        "source_semantic_lab_appearance_transfer_v1",
              "parser_model": PARSER_ID, "parser_revision": PARSER_REV,
              "parser_weights_sha256": PARSER_WEIGHTS_SHA256,
              "input_pilot_sha256": digest(root / "plan_pilot.json"),
              "input_config_sha256": digest(provenance_dir / "config.json"),
              "input_source_manifest_sha256": digest(provenance_dir / "source_manifest.json"),
              "samples": len(records), "all_protected_pixels_exact": all(
                  row["metrics"]["changed_outside_allowed"] == 0 for row in records),
              "review_state": "PENDING_HUMAN_REVIEW", "results": records}
    save_json(output / "preservation_report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--parser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enhance-eyes", action="store_true",
                        help="Version 2: source-aligned transfer of representative generated eyelid pigment")
    args = parser.parse_args()
    report = run(args.pilot, args.output, args.parser, enhance_eyes=args.enhance_eyes)
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
