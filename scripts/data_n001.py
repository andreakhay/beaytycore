"""Build and review DATA-N001 from real photos, reviewed masks and hand landmarks.

Input selection.json: {"identities": [{"identity_id": "hand001", "split": "train",
"source": "source/hand001.png", "mask": "masks/hand001.png",
"landmarks": [[x,y], ... 21 normalized points], "source_credit": "...",
"source_license": "..."}]}. Source and mask must be 512x512. Nothing is
accepted for training until a reviewer sets every pair to ACCEPT.
"""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.nails.geometry import HandGeometry, validate_nail_mask
from app.nails.render import render_target
from app.nails.styles import NAIL_STYLES


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def safe_path(root: Path, member: str) -> Path:
    path = (root / member).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Selection path escapes source directory")
    return path


def prepare(source_root: Path, selection_path: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing to overwrite existing DATA-N001 output")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    identities = selection.get("identities", [])
    if not identities or len({row["identity_id"] for row in identities}) != len(identities):
        raise ValueError("Selection needs distinct identities")
    rows = []
    exclusions = []
    for record in identities:
        identity = record["identity_id"]
        if not identity.replace("_", "").replace("-", "").isalnum() or record.get("split") not in {"train", "validation"}:
            raise ValueError(f"Invalid identity or split: {identity}")
        if not record.get("source_credit") or not record.get("source_license"):
            raise ValueError(f"Source credit and license are required: {identity}")
        source_path = safe_path(source_root, record["source"])
        mask_path = safe_path(source_root, record["mask"])
        try:
            with Image.open(source_path) as original:
                image = original.convert("RGB")
            with Image.open(mask_path) as original_mask:
                mask = original_mask.convert("L")
            points = tuple(tuple(map(float, pair)) for pair in record["landmarks"])
            if image.size != (512, 512) or mask.size != image.size or len(points) != 21:
                raise ValueError("Expected aligned 512x512 source/mask and 21 landmarks")
            hand = HandGeometry(points, *image.size)
            validate_nail_mask(mask, hand)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            exclusions.append({"identity_id": identity, "reason": str(exc)})
            continue
        for style in NAIL_STYLES:
            pair_id = f"{identity}_{style.id}"
            folder = output / "candidates" / pair_id
            folder.mkdir(parents=True, exist_ok=True)
            reference = folder / "reference.png"
            target = folder / "target.png"
            mask_copy = folder / "mask.png"
            image.save(reference)
            mask.save(mask_copy)
            render_target(image, mask, style.id, hand).save(target)
            sheet = Image.new("RGB", (1536, 540), "white")
            sheet.paste(image, (0, 0))
            sheet.paste(Image.merge("RGB", (mask, mask, mask)), (512, 0))
            sheet.paste(Image.open(target), (1024, 0))
            ImageDraw.Draw(sheet).text((8, 516), f"{pair_id} | Original / Nail Mask / Target", fill="black")
            sheet.save(folder / "review.jpg", quality=94)
            rows.append({
                "pair_id": pair_id, "identity_id": identity, "split": record["split"],
                "style_id": style.id, "source_image": str(reference.relative_to(output).as_posix()),
                "target_image": str(target.relative_to(output).as_posix()),
                "mask_reference": str(mask_copy.relative_to(output).as_posix()),
                "caption": style.prompt, "generation_method": "deterministic_reviewed_mask_v1",
                "review_status": "PENDING", "notes": "", "source_credit": record["source_credit"],
                "source_license": record["source_license"], "source_sha256": digest(source_path),
                "landmarks": points,
                "reference_sha256": digest(reference), "target_sha256": digest(target),
                "mask_sha256": digest(mask_copy),
            })
    write_json(output / "manifests" / "pairs.json", rows)
    write_json(output / "manifests" / "selection.json", selection)
    write_json(output / "manifests" / "reviews.json", [
        {"pair_id": row["pair_id"], "state": "PENDING", "reviewer": "", "note": ""} for row in rows])
    write_json(output / "reports" / "exclusions.json", exclusions)
    result = {"status": "PENDING_HUMAN_REVIEW", "identities_selected": len(identities),
              "identities_usable": len(rows)//5, "pairs_rendered": len(rows), "exclusions": len(exclusions)}
    write_json(output / "reports" / "prepare.json", result)
    return result


def finalize(dataset: Path, archive_path: Path) -> dict:
    rows = json.loads((dataset / "manifests" / "pairs.json").read_text(encoding="utf-8"))
    reviews = json.loads((dataset / "manifests" / "reviews.json").read_text(encoding="utf-8"))
    by_id = {row["pair_id"]: row for row in reviews}
    if len(by_id) != len(rows) or len(reviews) != len(rows):
        raise ValueError("Review count does not match pair count")
    accepted = []
    splits = {"train": set(), "validation": set()}
    counts = Counter()
    target_hashes = set()
    source_owners = {}
    for row in rows:
        decision = by_id.get(row["pair_id"], {})
        if decision.get("state") not in {"ACCEPT", "RETRY", "REJECT"} or not decision.get("reviewer") or not decision.get("note"):
            raise ValueError(f"Explicit review missing: {row['pair_id']}")
        if decision["state"] != "ACCEPT":
            continue
        for field, hash_field in (("source_image", "reference_sha256"), ("target_image", "target_sha256"), ("mask_reference", "mask_sha256")):
            if digest(dataset / row[field]) != row[hash_field]:
                raise ValueError(f"Hash mismatch: {row['pair_id']} {field}")
        if not row["caption"].strip():
            raise ValueError(f"Missing edit instruction: {row['pair_id']}")
        with Image.open(dataset / row["source_image"]) as file:
            reference = np.asarray(file.convert("RGB"))
        with Image.open(dataset / row["target_image"]) as file:
            target = np.asarray(file.convert("RGB"))
        with Image.open(dataset / row["mask_reference"]) as file:
            mask = np.asarray(file.convert("L")) > 127
        if reference.shape != (512, 512, 3) or target.shape != reference.shape or mask.shape != reference.shape[:2]:
            raise ValueError(f"Invalid paired dimensions: {row['pair_id']}")
        if np.count_nonzero(mask) < 150 or not np.any(reference[mask] != target[mask]):
            raise ValueError(f"Empty or ineffective nail mask: {row['pair_id']}")
        if np.any(reference[~mask] != target[~mask]):
            raise ValueError(f"Target edits pixels outside the nail mask: {row['pair_id']}")
        if row["target_sha256"] in target_hashes:
            raise ValueError("Duplicate accepted target hash")
        target_hashes.add(row["target_sha256"])
        owner = source_owners.setdefault(row["source_sha256"], row["identity_id"])
        if owner != row["identity_id"]:
            raise ValueError("The same source photo appears under multiple identities")
        splits[row["split"]].add(row["identity_id"])
        counts[(row["split"], row["style_id"])] += 1
        accepted.append({**row, "review_status": "ACCEPT", "notes": decision["note"]})
    if splits["train"] & splits["validation"]:
        raise ValueError("Identity leakage between train and validation")
    if not accepted:
        raise ValueError("No accepted pairs")
    if archive_path.exists():
        raise ValueError("Refusing to overwrite existing archive")
    training_root = dataset / "final"
    if training_root.exists():
        raise ValueError("Refusing to overwrite existing final data")
    for row in accepted:
        root = training_root / row["split"]
        for role, field in (("reference", "source_image"), ("target", "target_image")):
            destination = root / role / f"{row['pair_id']}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(dataset / row[field], destination)
        (root / "target" / f"{row['pair_id']}.txt").write_text(row["caption"] + "\n", encoding="utf-8")
        destination = root / "masks" / f"{row['pair_id']}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(dataset / row["mask_reference"], destination)
    report = {"status": "FINALIZED_REVIEWED", "accepted_pairs": len(accepted),
              "train_identities": len(splits["train"]), "validation_identities": len(splits["validation"]),
              "style_counts": {f"{split}/{style}": counts[(split, style)] for split in splits for style in (s.id for s in NAIL_STYLES)},
              "review_mode": "explicit_human_review"}
    write_json(training_root / "manifests" / "pairs.json", accepted)
    write_json(training_root / "manifests" / "reviews.json", reviews)
    shutil.copyfile(dataset / "manifests" / "selection.json", training_root / "manifests" / "selection.json")
    segmentation_reviews = dataset / "manifests" / "segmentation_reviews.json"
    if segmentation_reviews.is_file():
        shutil.copyfile(segmentation_reviews, training_root / "manifests" / "segmentation_reviews.json")
    write_json(training_root / "reports" / "qa.json", report)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for path in sorted(training_root.rglob("*")):
            if path.is_file(): archive.write(path, path.relative_to(training_root).as_posix())
    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None: raise ValueError("Archive CRC failed")
    return {**report, "archive": str(archive_path), "archive_sha256": digest(archive_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "finalize"))
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.phase == "prepare":
        if not args.source_root or not args.selection: parser.error("prepare requires --source-root and --selection")
        result = prepare(args.source_root, args.selection, args.dataset)
    else:
        if not args.archive: parser.error("finalize requires --archive")
        result = finalize(args.dataset, args.archive)
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
