"""Freeze twelve FFHQ bare sources and make a small, auditable Kaggle input bundle.

This is CPU only. The ZIP's makeup_01..05 targets are never extracted.
"""

import argparse
from hashlib import md5, sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageDraw, ImageOps


def digest(path: Path, algorithm="sha256") -> str:
    hash_value = sha256() if algorithm == "sha256" else md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hash_value.update(chunk)
    return hash_value.hexdigest()


def prepare(archive_path: Path, metadata_path: Path, config_path: Path, output: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if digest(archive_path) != config["source_archive_sha256"]:
        raise ValueError("FFHQ-Makeup archive SHA256 does not match pinned input")
    if digest(metadata_path, "md5") != config["ffhq_metadata_md5"]:
        raise ValueError("Original FFHQ metadata MD5 does not match published input")
    train, validation = config["train_ids"], config["validation_ids"]
    if len(train) != 10 or len(validation) != 2 or len(set(train + validation)) != 12:
        raise ValueError("Expected ten disjoint train and two validation identities")
    if len(config["pilot_train_ids"]) != 2 or not set(config["pilot_train_ids"]) <= set(train):
        raise ValueError("Pilot must contain exactly two train identities")
    if len(config["styles"]) != 10 or len({s["id"] for s in config["styles"]}) != 10:
        raise ValueError("Expected ten unique styles")
    source_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    source_dir = output / "sources"
    source_dir.mkdir(exist_ok=True)
    rows = []
    sheet = Image.new("RGB", (4 * 260, 3 * 284), "white")
    draw = ImageDraw.Draw(sheet)
    with ZipFile(archive_path) as archive:
        for index, identity in enumerate(train + validation):
            member = f"{identity}/bare.jpg"
            raw = archive.read(member)
            with Image.open(BytesIO(raw)) as image:
                image.load()
                if image.format != "JPEG" or image.size != (512, 512):
                    raise ValueError(f"Invalid bare portrait: {member}")
                tile = ImageOps.contain(image.convert("RGB"), (250, 250))
            original = source_metadata[str(int(identity))]["metadata"]
            license_name = original["license"]
            if not any(term in license_name for term in ("Attribution", "Public Domain", "CC0")):
                raise ValueError(f"Unreviewed per-photo license for {identity}: {license_name}")
            if not original.get("author") or not original.get("photo_url") or not original.get("license_url"):
                raise ValueError(f"Missing original photo credit or license for {identity}")
            target = source_dir / f"{identity}.jpg"
            if target.exists() and target.read_bytes() != raw:
                raise ValueError(f"Previously extracted source changed: {target}")
            target.write_bytes(raw)
            x, y = (index % 4) * 260, (index // 4) * 284
            draw.text((x + 5, y + 3), f"{identity}  {'TRAIN' if identity in train else 'VALIDATION'}", fill="black")
            sheet.paste(tile, (x + (260 - tile.width) // 2, y + 25))
            rows.append({
                "identity_id": identity, "split": "TRAIN" if identity in train else "VALIDATION",
                "source_member": member, "source_path": f"sources/{identity}.jpg",
                "source_sha256": sha256(raw).hexdigest(), "format": "JPEG", "width": 512, "height": 512,
                "original_ffhq_photo": {key: original.get(key) for key in
                                         ("author", "photo_title", "photo_url", "license", "license_url")},
                "source_dataset_license": config["dataset_license"],
                "selection_note": "Visually screened for clear mostly frontal face and usable lighting; age and individual consent are not independently verified",
            })
    if len({r["source_sha256"] for r in rows}) != 12:
        raise ValueError("Duplicate source portrait hash")
    sheet_path = output / "source_selection_sheet.jpg"
    sheet.save(sheet_path, quality=92)
    manifest = {
        "schema": "DATA-M001-source-v1", "dataset_id": config["dataset_id"],
        "source_repository": config["source_repository"], "source_revision": config["source_revision"],
        "source_archive": config["source_archive"], "source_archive_sha256": config["source_archive_sha256"],
        "ffhq_metadata_md5": config["ffhq_metadata_md5"],
        "split_counts": {"TRAIN": 10, "VALIDATION": 2}, "identities": rows,
    }
    (output / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    bundle = output.parent / "data_m001_kaggle_input.zip"
    with ZipFile(bundle, "w", ZIP_DEFLATED) as zip_output:
        for path in [output / "config.json", output / "source_manifest.json", sheet_path, *sorted(source_dir.glob("*.jpg"))]:
            zip_output.write(path, path.relative_to(output).as_posix())
        runner = Path(__file__).resolve().parents[1] / "notebooks" / "data_m001_generate_kaggle.py"
        zip_output.write(runner, runner.name)
    return {"output": str(output), "bundle": str(bundle), "source_count": len(rows),
            "train": 10, "validation": 2, "pilot_jobs": 20, "remaining_jobs": 100,
            "bundle_sha256": digest(bundle)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("data/makeup/DATA-M001/config.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, args.metadata, args.config, args.output), indent=2))


if __name__ == "__main__":
    main()
