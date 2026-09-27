"""Prepare and finalize a reviewed, real FFHQ Makeup paired edit dataset.

No FLUX generation, GPU, Hair asset, or artificial makeup class is used.
"""

import argparse
from collections import Counter
from hashlib import md5, sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageOps


CAPTION = ("Apply realistic makeup visible in the target portrait while preserving "
           "the person's identity, facial structure, expression, hairstyle, clothing, and scene.")


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = sha256() if algorithm == "sha256" else md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_selection(selection: dict) -> list[tuple[str, str]]:
    train, validation = selection["train_ids"], selection["validation_ids"]
    if len(train) != 10 or len(validation) != 2 or len(set(train + validation)) != 12:
        raise ValueError("Selection requires ten train and two disjoint validation identities")
    if any(len(identity) != 6 or not identity.isdigit() for identity in train + validation):
        raise ValueError("Identity IDs must be six digit archive IDs")
    variants = selection["variant_positions"]
    if variants != [f"makeup_{n:02d}" for n in range(1, 6)]:
        raise ValueError("Expected five archive variant positions, not style classes")
    return [(identity, "train" if identity in train else "validation") for identity in train + validation]


def checked_jpeg(raw: bytes, member: str) -> Image.Image:
    with Image.open(BytesIO(raw)) as image:
        image.load()
        if image.format != "JPEG" or image.size != (512, 512):
            raise ValueError(f"Invalid 512x512 JPEG: {member}")
        return image.convert("RGB")


def prepare(archive_path: Path, metadata_path: Path, selection_path: Path, output: Path) -> dict:
    selection = read_json(selection_path)
    identities = validate_selection(selection)
    if digest(archive_path) != selection["source_archive_sha256"]:
        raise ValueError("Pinned archive hash mismatch")
    if digest(metadata_path, "md5") != selection["ffhq_metadata_md5"]:
        raise ValueError("Pinned FFHQ metadata hash mismatch")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Refusing to replace existing review folder: {output}")
    metadata = read_json(metadata_path)
    output.mkdir(parents=True, exist_ok=True)
    rows, reviews, source_hashes, target_hashes = [], [], set(), set()
    with ZipFile(archive_path) as archive:
        for identity, split in identities:
            credit = metadata[str(int(identity))]["metadata"]
            if not all(credit.get(field) for field in ("author", "photo_url", "license", "license_url")):
                raise ValueError(f"Missing original photo provenance: {identity}")
            if not any(word in credit["license"] for word in ("Attribution", "Public Domain", "CC0")):
                raise ValueError(f"Unreviewed original license: {identity}")
            source_member = f"{identity}/bare.jpg"
            source_raw = archive.read(source_member)
            checked_jpeg(source_raw, source_member)
            source_hash = sha256(source_raw).hexdigest()
            if source_hash in source_hashes:
                raise ValueError(f"Duplicate source image: {identity}")
            source_hashes.add(source_hash)
            source_path = Path("originals") / f"{identity}.jpg"
            (output / source_path).parent.mkdir(exist_ok=True)
            (output / source_path).write_bytes(source_raw)
            for variant in selection["variant_positions"]:
                target_member = f"{identity}/{variant}.jpg"
                target_raw = archive.read(target_member)
                checked_jpeg(target_raw, target_member)
                target_hash = sha256(target_raw).hexdigest()
                if target_hash in source_hashes or target_hash in target_hashes:
                    raise ValueError(f"Duplicate target image: {target_member}")
                target_hashes.add(target_hash)
                pair_id = f"{identity}_{variant}"
                target_path = Path("targets") / identity / f"{variant}.jpg"
                (output / target_path).parent.mkdir(parents=True, exist_ok=True)
                (output / target_path).write_bytes(target_raw)
                rows.append({
                    "pair_id": pair_id, "identity_id": identity, "split": split,
                    "source_archive_member": source_member, "target_archive_member": target_member,
                    "source_path": source_path.as_posix(), "target_path": target_path.as_posix(),
                    "source_sha256": source_hash, "target_sha256": target_hash,
                    "caption": CAPTION, "target_variant_position": variant,
                    "target_variant_is_style_class": False,
                    "source_photo": {field: credit.get(field) for field in
                                     ("author", "photo_title", "photo_url", "license", "license_url")},
                    "source_dataset_license": selection["source_dataset_license"],
                })
                reviews.append({"pair_id": pair_id, "state": "PENDING_HUMAN_REVIEW",
                                "reviewer": None, "note": None})
    write_json(output / "selection.json", selection)
    manifest = {"schema": "DATA-M001-paired-candidate-v1", "selection_sha256": digest(selection_path),
                "source_archive_sha256": digest(archive_path), "metadata_md5": digest(metadata_path, "md5"),
                "pairs": rows}
    write_json(output / "candidate_manifest.json", manifest)
    write_json(output / "reviews.json", {"schema": "DATA-M001-human-review-v1", "reviews": reviews})
    make_contact_sheets(output, rows)
    qa = {"status": "PENDING_HUMAN_REVIEW", "identity_counts": {"train": 10, "validation": 2},
          "pair_counts": dict(Counter(row["split"] for row in rows)),
          "unique_source_hashes": len(source_hashes), "unique_target_hashes": len(target_hashes),
          "split_leakage": "NONE", "caption_strategy": "generic visible target makeup edit; no invented style label"}
    write_json(output / "qa_candidates.json", qa)
    return qa


def make_contact_sheets(output: Path, rows: list[dict]) -> None:
    grouped = {}
    for row in rows:
        grouped.setdefault(row["identity_id"], []).append(row)
    folder = output / "contact_sheets"
    folder.mkdir(exist_ok=True)
    for page_start in range(0, len(grouped), 4):
        identities = list(grouped)[page_start:page_start + 4]
        sheet = Image.new("RGB", (6 * 220, len(identities) * 244), "white")
        draw = ImageDraw.Draw(sheet)
        for y_index, identity in enumerate(identities):
            pair_rows = grouped[identity]
            paths = [output / pair_rows[0]["source_path"]] + [output / row["target_path"] for row in pair_rows]
            names = ["bare"] + [row["target_variant_position"] for row in pair_rows]
            for x_index, (path, name) in enumerate(zip(paths, names)):
                with Image.open(path) as image:
                    thumb = ImageOps.contain(image.convert("RGB"), (214, 214))
                x, y = x_index * 220, y_index * 244
                draw.text((x + 5, y + 3), f"{identity} {name}", fill="black")
                sheet.paste(thumb, (x + 3, y + 24))
        sheet.save(folder / f"pairs_{page_start // 4 + 1:02d}.jpg", quality=94)


def record_all_approval(candidate: Path, reviewer: str, note: str) -> dict:
    """Record an explicit review decision, never infer it from image decoding."""
    if not reviewer.strip() or not note.strip():
        raise ValueError("Reviewer and approval evidence are required")
    path = candidate / "reviews.json"
    data = read_json(path)
    if data.get("schema") != "DATA-M001-human-review-v1" or len(data["reviews"]) != 60:
        raise ValueError("Expected the complete 60-pair review template")
    if any(row["state"] != "PENDING_HUMAN_REVIEW" for row in data["reviews"]):
        raise ValueError("Refusing to overwrite existing review decisions")
    for row in data["reviews"]:
        row.update({"state": "ACCEPT", "reviewer": reviewer, "note": note})
    write_json(path, data)
    return {"accepted": len(data["reviews"]), "reviewer": reviewer}


def finalize(candidate: Path, output: Path) -> dict:
    manifest = read_json(candidate / "candidate_manifest.json")
    reviews = read_json(candidate / "reviews.json")["reviews"]
    rows = manifest["pairs"]
    if len({row["pair_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate pair IDs")
    decisions = {review["pair_id"]: review for review in reviews}
    if set(decisions) != {row["pair_id"] for row in rows}:
        raise ValueError("Review IDs do not match candidate manifest")
    if any(review["state"] not in {"ACCEPT", "REJECT"} or not review.get("reviewer")
           or not review.get("note") for review in reviews):
        raise ValueError("Every pair requires explicit human ACCEPT or REJECT with reviewer and note")
    accepted = [row for row in rows if decisions[row["pair_id"]]["state"] == "ACCEPT"]
    train_ids = {row["identity_id"] for row in accepted if row["split"] == "train"}
    validation_ids = {row["identity_id"] for row in accepted if row["split"] == "validation"}
    if train_ids & validation_ids or len(train_ids) != 10 or len(validation_ids) != 2:
        raise ValueError("Final dataset requires ten train and two disjoint validation identities")
    if len(accepted) < 48 or sum(row["split"] == "validation" for row in accepted) < 9:
        raise ValueError("Too few reviewed pairs; replace poor identities instead of silently shrinking data")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Refusing to overwrite final dataset: {output}")
    for row in rows:
        for field, hash_field in (("source_path", "source_sha256"), ("target_path", "target_sha256")):
            path = candidate / row[field]
            if digest(path) != row[hash_field]:
                raise ValueError(f"Candidate image hash mismatch: {path}")
            with Image.open(path) as image:
                image.verify()
    output.mkdir(parents=True, exist_ok=True)
    final_rows = []
    for row in accepted:
        stem = row["pair_id"]
        split = row["split"]
        reference_path = Path(split) / "reference" / f"{stem}.jpg"
        target_path = Path(split) / "target" / f"{stem}.jpg"
        caption_path = Path(split) / "target" / f"{stem}.txt"
        for original, relative in ((row["source_path"], reference_path), (row["target_path"], target_path)):
            (output / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate / original, output / relative)
        (output / caption_path).write_text(row["caption"] + "\n", encoding="utf-8")
        final_rows.append({**row, "reference": reference_path.as_posix(),
                           "target": target_path.as_posix(), "caption_path": caption_path.as_posix(),
                           "review": decisions[stem]})
    write_json(output / "manifests" / "pairs.json", final_rows)
    write_json(output / "manifests" / "reviews.json", reviews)
    write_json(output / "manifests" / "selection.json", read_json(candidate / "selection.json"))
    qa = {"status": "FINALIZED", "train_pairs": sum(row["split"] == "train" for row in final_rows),
          "validation_pairs": sum(row["split"] == "validation" for row in final_rows),
          "train_identities": len(train_ids), "validation_identities": len(validation_ids),
          "rejected_pairs": sorted(set(decisions) - {row["pair_id"] for row in final_rows}),
          "split_leakage": "NONE", "review_mode": "explicit_human_review",
          "source_archive_sha256": manifest["source_archive_sha256"]}
    write_json(output / "reports" / "qa.json", qa)
    return qa


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "approve-all", "finalize"])
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--reviewer")
    parser.add_argument("--approval-note")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "prepare":
        if not all((args.archive, args.metadata, args.selection)):
            parser.error("prepare requires --archive, --metadata and --selection")
        result = prepare(args.archive, args.metadata, args.selection, args.output)
    elif args.phase == "approve-all":
        if not args.candidate or not args.reviewer or not args.approval_note:
            parser.error("approve-all requires --candidate, --reviewer and --approval-note")
        result = record_all_approval(args.candidate, args.reviewer, args.approval_note)
    else:
        if not args.candidate:
            parser.error("finalize requires --candidate")
        result = finalize(args.candidate, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
