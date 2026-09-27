"""Derive fingertip edit pairs from the immutable, reviewed DATA-N001 archive.

This is a training representation of DATA-N001, not a new source dataset. It
never renders new polish: both sides of each pair use the same spatial transform
on the approved reference and target pixels.
"""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
import itertools
import json
import math
from pathlib import Path
from statistics import mean, median
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.nails.geometry import nail_components


APPROVED_SHA = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"
STYLES = ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")
FINGERS = ("thumb", "index", "middle", "ring", "little")
TIP_INDEX = (4, 8, 12, 16, 20)
DIP_INDEX = (3, 7, 11, 15, 19)
SIZE = 512
SEED = 1977
CAPTIONS = {
    "classic_red": "Apply glossy classic red polish to this fingernail while preserving the same fingertip, nail shape, and surrounding skin.",
    "nude_pink": "Apply muted nude-pink polish to this fingernail while preserving the same fingertip, nail shape, and surrounding skin.",
    "glossy_black": "Apply glossy black polish to this fingernail while preserving the same fingertip, nail shape, and surrounding skin.",
    "french_tip": "Apply a natural French manicure with a clean thin white distal tip while preserving the nail shape and fingertip.",
    "pink_ombre": "Apply a soft pink ombre gradient from the cuticle toward the nail tip while preserving the same nail and fingertip.",
}


def digest(data: bytes | Path) -> str:
    h = sha256()
    if isinstance(data, Path):
        with data.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
    else:
        h.update(data)
    return h.hexdigest()


def read_image(archive: ZipFile, member: str, expected: str, mode: str) -> Image.Image:
    content = archive.read(member)
    if digest(content) != expected:
        raise ValueError(f"Approved DATA-N001 member hash mismatch: {member}")
    with Image.open(BytesIO(content)) as image:
        result = image.convert(mode)
    if result.size != (SIZE, SIZE):
        raise ValueError(f"Unexpected approved image dimensions: {member}")
    return result


def choose_nails(mask: Image.Image, landmarks: list[list[float]]) -> list[dict]:
    groups = nail_components(np.asarray(mask) > 127)
    if not 3 <= len(groups) <= 5:
        raise ValueError(f"Expected 3 to 5 approved nail islands, got {len(groups)}")
    tips = np.asarray([landmarks[i] for i in TIP_INDEX]) * SIZE
    dips = np.asarray([landmarks[i] for i in DIP_INDEX]) * SIZE
    centers = [np.asarray([group[:, 1].mean(), group[:, 0].mean()]) for group in groups]
    # Exact assignment avoids giving two close components the same fingertip.
    assignments = min(itertools.permutations(range(5), len(groups)),
                      key=lambda option: sum(np.linalg.norm(centers[i] - tips[f])
                                             for i, f in enumerate(option)))
    result = []
    for group, center, finger in zip(groups, centers, assignments):
        tip_distance = float(np.linalg.norm(center - tips[finger]))
        direction = tips[finger] - dips[finger]
        direction_length = float(np.linalg.norm(direction))
        if tip_distance > 30 or direction_length < 15:
            raise ValueError(f"Unreliable nail to landmark match: {FINGERS[finger]} d={tip_distance:.1f}")
        # PIL's positive angle rotates toward image-up (negative y).
        angle = math.degrees(math.atan2(direction[0], -direction[1]))
        if abs(angle) < 8:
            angle = 0.0
        xs, ys = group[:, 1], group[:, 0]
        width, height = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
        side = max(56, round(2.4 * max(width, height)))
        result.append({"finger_id": FINGERS[finger], "finger_index": finger,
                       "center": [round(float(center[0]), 3), round(float(center[1]), 3)],
                       "angle_degrees": round(angle, 4), "orientation_confidence": "landmark_matched",
                       "tip_distance_px": round(tip_distance, 3),
                       "dip_to_tip_px": round(direction_length, 3),
                       "nail_bbox_wh": [width, height], "crop_side_px": side,
                       "original_nail_pixels": int(len(group))})
    return sorted(result, key=lambda item: item["finger_index"])


def geometry(nail: dict, full_mask: Image.Image) -> dict | None:
    cx, cy = nail["center"]
    angle = nail["angle_degrees"]
    rotated_all = (full_mask.rotate(angle, resample=Image.Resampling.NEAREST,
                   center=(cx, cy), fillcolor=0) if angle else full_mask)
    groups = nail_components(np.asarray(full_mask) > 127)
    group = min(groups, key=lambda part: np.linalg.norm(
        np.asarray([part[:, 1].mean(), part[:, 0].mean()]) - nail["center"]))
    single = np.zeros((SIZE, SIZE), dtype=np.uint8)
    single[group[:, 0], group[:, 1]] = 255
    one = Image.fromarray(single, "L")
    rotated_one = (one.rotate(angle, resample=Image.Resampling.NEAREST,
                   center=(cx, cy), fillcolor=0) if angle else one)
    all_pixels, one_pixels = np.asarray(rotated_all) > 127, np.asarray(rotated_one) > 127
    other_pixels = np.where(all_pixels & ~one_pixels, 255, 0).astype(np.uint8)
    other_support = np.asarray(Image.fromarray(other_pixels, "L").filter(ImageFilter.MaxFilter(11))) > 0
    minimum_side = max(48, round(1.8 * max(nail["nail_bbox_wh"])))
    # After orientation normalization the nail tip points up. Give more room
    # below the nail for the cuticle and nearby finger skin.
    for side in range(nail["crop_side_px"], minimum_side - 1, -1):
        left = round(cx - side / 2)
        top = round(cy + side * 0.10 - side / 2)
        box = (left, top, left + side, top + side)
        if min(box[:2]) < 0 or max(box[2:]) > SIZE:
            continue
        sl = np.s_[top:top + side, left:left + side]
        if int(one_pixels[sl].sum()) != int(one_pixels.sum()):
            continue
        if np.any(other_support[sl]):
            continue
        return {**nail, "crop_side_px": side, "crop_box_rotated": list(box),
                "model_size": [SIZE, SIZE], "rgb_resampling": "BICUBIC",
                "mask_resampling": "NEAREST", "rotation_center_original": nail["center"]}
    return None


def transform(image: Image.Image, mapping: dict, *, mask: bool = False) -> Image.Image:
    method = Image.Resampling.NEAREST if mask else Image.Resampling.BICUBIC
    fill = 0 if mask else (255, 255, 255)
    angle = mapping["angle_degrees"]
    rotated = (image.rotate(angle, resample=method, center=tuple(mapping["rotation_center_original"]),
                            fillcolor=fill) if angle else image)
    return rotated.crop(tuple(mapping["crop_box_rotated"])).resize((SIZE, SIZE), resample=method)


def png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def inspect_source(archive: ZipFile) -> list[dict]:
    if archive.testzip() is not None:
        raise ValueError("Approved DATA-N001 ZIP CRC failure")
    rows = json.loads(archive.read("manifests/pairs.json"))
    qa = json.loads(archive.read("reports/qa.json"))
    if qa.get("status") != "FINALIZED_REVIEWED" or qa.get("accepted_pairs") != 100 or len(rows) != 100:
        raise ValueError("Approved DATA-N001 review gate changed")
    identities = defaultdict(set)
    counts = Counter()
    for row in rows:
        if row["review_status"] != "ACCEPT" or row["style_id"] not in STYLES:
            raise ValueError(f"Unapproved or unknown style {row['pair_id']}")
        identities[row["split"]].add(row["identity_id"])
        counts[row["split"], row["style_id"]] += 1
    if len(identities["train"]) != 16 or len(identities["validation"]) != 4:
        raise ValueError("Approved identity split changed")
    if identities["train"] & identities["validation"]:
        raise ValueError("Identity leakage in source DATA-N001")
    if any(counts[split, style] != expected for split, expected in (("train", 16), ("validation", 4))
           for style in STYLES):
        raise ValueError("Approved identity by style counts changed")
    return rows


def build(approved: Path, output: Path) -> dict:
    if digest(approved) != APPROVED_SHA:
        raise ValueError("Approved DATA-N001 archive hash mismatch")
    if output.exists():
        raise ValueError("Refusing to replace existing localized dataset")
    output.parent.mkdir(parents=True, exist_ok=True)
    local_rows = []
    mask_fractions = []
    changed_fractions = []
    original_fractions = []
    review = {}
    with ZipFile(approved) as source, ZipFile(output, "w", ZIP_DEFLATED) as localized:
        rows = inspect_source(source)
        by_identity = defaultdict(list)
        for row in rows:
            by_identity[row["identity_id"]].append(row)
        for identity, style_rows in sorted(by_identity.items()):
            style_rows.sort(key=lambda row: STYLES.index(row["style_id"]))
            first = style_rows[0]
            split, first_pair = first["split"], first["pair_id"]
            original = read_image(source, f"{split}/reference/{first_pair}.png", first["reference_sha256"], "RGB")
            full_mask = read_image(source, f"{split}/masks/{first_pair}.png", first["mask_sha256"], "L")
            candidates = choose_nails(full_mask, first["landmarks"])
            nails = [mapping for item in candidates if (mapping := geometry(item, full_mask)) is not None]
            excluded = [item["finger_id"] for item in candidates if item["finger_id"] not in
                        {nail["finger_id"] for nail in nails}]
            review[identity] = {"split": split, "nails": len(nails),
                                "excluded_fingers": excluded,
                                "exclusion_reason": "neighbor nail enters minimum context crop" if excluded else None}
            for row in style_rows:
                pair = row["pair_id"]
                if row["split"] != split or row["reference_sha256"] != first["reference_sha256"]:
                    raise ValueError(f"Identity source or split changed: {pair}")
                if row["landmarks"] != first["landmarks"] or row["mask_sha256"] != first["mask_sha256"]:
                    raise ValueError(f"Identity mask/landmarks differ across styles: {pair}")
                target = read_image(source, f"{split}/target/{pair}.png", row["target_sha256"], "RGB")
                caption = source.read(f"{split}/target/{pair}.txt").decode("utf-8").strip()
                if caption != row["caption"]:
                    raise ValueError(f"Approved caption mismatch: {pair}")
                if np.any(np.asarray(original)[np.asarray(full_mask) <= 127] !=
                          np.asarray(target)[np.asarray(full_mask) <= 127]):
                    raise ValueError(f"Approved target changed pixels outside mask: {pair}")
                original_fractions.append(float((np.asarray(full_mask) > 127).mean()))
                for nail in nails:
                    local_id = f"{pair}__{nail['finger_id']}"
                    one_mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
                    # The approved mask islands are disjoint and aligned with
                    # these landmark assignments, so isolate this one finger.
                    groups = nail_components(np.asarray(full_mask) > 127)
                    matching = min(groups, key=lambda group: np.linalg.norm(
                        np.asarray([group[:, 1].mean(), group[:, 0].mean()]) - nail["center"]))
                    one_mask[matching[:, 0], matching[:, 1]] = 255
                    finger_mask = Image.fromarray(one_mask, "L")
                    reference_crop = transform(original, nail)
                    # Geometry excludes neighboring nails, so this is the
                    # literal matching crop of the approved styled target.
                    target_crop = transform(target, nail)
                    mask_crop = transform(finger_mask, nail, mask=True)
                    hard = np.asarray(mask_crop) > 127
                    if hard.sum() < 200:
                        raise ValueError(f"Crop lost its nail: {local_id}")
                    mask_fraction = float(hard.mean())
                    changed = np.any(np.asarray(reference_crop) != np.asarray(target_crop), axis=2)
                    # Bicubic RGB transforms can interpolate a narrow edge
                    # around the nearest-neighbor mask. Keep this measured.
                    # RGB bicubic interpolation reaches a few source pixels
                    # beyond the hard boundary before the large upscale.
                    support_original = finger_mask.filter(ImageFilter.MaxFilter(9))
                    mask_support = np.asarray(transform(support_original, nail, mask=True)) > 0
                    outside_support = int(np.count_nonzero(changed & ~mask_support))
                    if outside_support > 50:
                        raise ValueError(f"Localized target differs too far outside transformed nail support: {local_id} ({outside_support})")
                    if mask_fraction < 0.03:
                        raise ValueError(f"Localized nail signal under 3%: {local_id}")
                    ref_bytes, target_bytes, mask_bytes = map(png_bytes,
                        (reference_crop, target_crop, mask_crop))
                    for folder, data in (("reference", ref_bytes), ("target", target_bytes),
                                         ("masks", mask_bytes)):
                        localized.writestr(f"{split}/{folder}/{local_id}.png", data)
                    localized.writestr(f"{split}/target/{local_id}.txt", CAPTIONS[row["style_id"]] + "\n")
                    local_rows.append({"pair_id": local_id, "parent_pair_id": pair,
                        "identity_id": identity, "split": split, "finger_id": nail["finger_id"],
                        "style_id": row["style_id"], "caption": CAPTIONS[row["style_id"]],
                        "approved_reference_sha256": row["reference_sha256"],
                        "approved_target_sha256": row["target_sha256"],
                        "approved_mask_sha256": row["mask_sha256"],
                        "reference_sha256": digest(ref_bytes), "target_sha256": digest(target_bytes),
                        "mask_sha256": digest(mask_bytes),
                        "mask_pct": round(100 * mask_fraction, 5),
                        "changed_pct": round(100 * float(changed.mean()), 5),
                        "outside_mask_support_changed_pixels": outside_support,
                        "transform": nail})
                    mask_fractions.append(mask_fraction)
                    changed_fractions.append(float(changed.mean()))
        localized.writestr("manifests/pairs.json", json.dumps(local_rows, indent=2) + "\n")
        counts = Counter((row["split"], row["style_id"]) for row in local_rows)
        evidence = {"status": "DERIVED_REVIEW_REQUIRED", "source_dataset_sha256": APPROVED_SHA,
            "source_pairs": len(rows), "localized_pairs": len(local_rows),
            "train_pairs": sum(row["split"] == "train" for row in local_rows),
            "validation_pairs": sum(row["split"] == "validation" for row in local_rows),
            "train_identities": 16, "validation_identities": 4,
            "style_counts": {f"{split}/{style}": counts[split, style]
                             for split in ("train", "validation") for style in STYLES},
            "original_mask_pct": {"mean": round(100 * mean(original_fractions), 5),
                                  "median": round(100 * median(original_fractions), 5),
                                  "min": round(100 * min(original_fractions), 5),
                                  "max": round(100 * max(original_fractions), 5)},
            "localized_mask_pct": {"mean": round(100 * mean(mask_fractions), 5),
                                   "median": round(100 * median(mask_fractions), 5),
                                   "min": round(100 * min(mask_fractions), 5),
                                   "max": round(100 * max(mask_fractions), 5)},
            "localized_changed_pct": {"mean": round(100 * mean(changed_fractions), 5),
                                      "median": round(100 * median(changed_fractions), 5),
                                      "min": round(100 * min(changed_fractions), 5),
                                      "max": round(100 * max(changed_fractions), 5)},
            "identities": review, "crop_rule": "start max(56, round(2.4 * max nail bbox)); shrink to at least max(48, round(1.8 * max bbox)) to exclude neighboring nails, otherwise omit finger",
            "orientation": "MediaPipe DIP to tip, nearest unique reviewed nail island; rotate tip toward image-up when abs(angle)>=8 degrees",
            "rgb_resampling": "BICUBIC", "model_size": [SIZE, SIZE]}
        localized.writestr("reports/qa.json", json.dumps(evidence, indent=2) + "\n")
    with ZipFile(output) as check:
        if check.testzip() is not None:
            raise ValueError("Localized dataset ZIP CRC failure")
    evidence["archive_sha256"] = digest(output)
    evidence["archive_bytes"] = output.stat().st_size
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.approved, args.output), indent=2))


if __name__ == "__main__":
    main()
