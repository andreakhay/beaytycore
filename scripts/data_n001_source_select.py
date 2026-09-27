"""Metadata shortlist and explicit identity freeze for 11K Hands DATA-N001.

The shortlist never treats a metadata match as visual acceptance. Review the
contact sheets, then set each reviewed candidate's selection_status to ACCEPT
or REJECT and write an exclusion_reason for every REJECT. Freeze copies only
ACCEPT images, one image per subject, and assigns a fixed 16/4 split.
"""

import argparse
import csv
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


SOURCE_URL = "https://sites.google.com/view/11khands"


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def metadata_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    expected = {"id", "imageName", "aspectOfHand", "nailPolish", "accessories", "irregularities"}
    if not rows or not expected <= set(rows[0]):
        raise ValueError("11K Hands metadata columns differ from the expected schema")
    return rows


def eligible(row: dict) -> bool:
    return (row["aspectOfHand"].startswith("dorsal ") and row["nailPolish"] == "0"
            and row["accessories"] == "0" and row["irregularities"] == "0")


def score_photo(data: bytes) -> tuple[float, Image.Image]:
    with Image.open(BytesIO(data)) as image:
        image.load()
        if min(image.size) < 1000:
            raise ValueError("Resolution below source expectation")
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        thumb = ImageOps.contain(rgb, (256, 220), Image.Resampling.LANCZOS)
    gray = cv2.cvtColor(np.asarray(thumb), cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var()), thumb


def shortlist(csv_path: Path, archive_path: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing to overwrite an existing shortlist")
    rows = metadata_rows(csv_path)
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if eligible(row):
            grouped.setdefault(row["id"], []).append(row)
    candidates = []
    sheet = None
    current_page = -1
    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("11K Hands archive CRC failed")
        members = set(archive.namelist())
        for subject_id, options in sorted(grouped.items()):
            best = None
            # Bound the visual comparison within each subject. Every subject
            # remains eligible for review; only one image is proposed.
            for row in options[:6]:
                member = "Hands/" + row["imageName"]
                if member not in members:
                    continue
                raw = archive.read(member)
                try:
                    focus, thumb = score_photo(raw)
                except (OSError, ValueError):
                    continue
                if best is None or focus > best[0]:
                    best = (focus, thumb, raw, row, member)
            if best is None:
                continue
            focus, thumb, raw, row, member = best
            candidates.append({
                "identity_id": subject_id, "source_member": member,
                "source_path": str(archive_path.resolve()), "source_sha256": digest(raw),
                "hand_side": row["aspectOfHand"].split()[-1],
                "aspect_of_hand": "dorsal", "nail_polish": row["nailPolish"],
                "accessories": row["accessories"], "irregularities": row["irregularities"],
                "skin_color": row.get("skinColor", ""), "focus_score": round(focus, 2),
                "selection_status": "PENDING", "exclusion_reason": "", "split": None,
            })
            page_number = (len(candidates) - 1) // 20
            cell = (len(candidates) - 1) % 20
            page = output / "review" / f"source_page_{page_number + 1:02d}.jpg"
            if page_number != current_page:
                if sheet is not None:
                    prior = output / "review" / f"source_page_{current_page + 1:02d}.jpg"
                    prior.parent.mkdir(parents=True, exist_ok=True)
                    sheet.save(prior, quality=94)
                sheet = Image.new("RGB", (4 * 270, 5 * 255), "white")
                current_page = page_number
            x, y = cell % 4 * 270, cell // 4 * 255
            sheet.paste(thumb, (x + (256 - thumb.width)//2, y))
            ImageDraw.Draw(sheet).text((x + 3, y + 222),
                                       f"{subject_id} {row['aspectOfHand']} {row['imageName']}", fill="black")
        if sheet is not None:
            page = output / "review" / f"source_page_{current_page + 1:02d}.jpg"
            page.parent.mkdir(parents=True, exist_ok=True)
            sheet.save(page, quality=94)
    save_json(output / "source_candidates.json", {"dataset": "11K Hands", "source_url": SOURCE_URL,
        "metadata_sha256": sha256(csv_path.read_bytes()).hexdigest(),
        "archive_sha256": sha256(archive_path.read_bytes()).hexdigest(),
        "records_inspected": len(rows), "metadata_eligible_records": sum(map(eligible, rows)),
        "candidate_identities": len(candidates), "candidates": candidates})
    return {"records_inspected": len(rows), "metadata_eligible_records": sum(map(eligible, rows)),
            "candidate_identities": len(candidates), "review_pages": (len(candidates) + 19)//20}


def freeze(candidates_path: Path, archive_path: Path, output: Path) -> dict:
    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates = data["candidates"]
    undecided = [row["identity_id"] for row in candidates if row["selection_status"] == "PENDING"]
    if undecided:
        raise ValueError(f"Visual selection pending for {len(undecided)} identities")
    selected = [row for row in candidates if row["selection_status"] == "ACCEPT"]
    if any(row["selection_status"] not in {"ACCEPT", "REJECT"} for row in candidates):
        raise ValueError("Unknown selection status")
    if any(not row["exclusion_reason"] for row in candidates if row["selection_status"] == "REJECT"):
        raise ValueError("Every rejected image needs an exclusion reason")
    if len(selected) > 20:
        raise ValueError("V1 may select at most 20 identities")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing to overwrite source freeze")
    selected.sort(key=lambda row: row["identity_id"])
    with ZipFile(archive_path) as archive:
        for index, row in enumerate(selected):
            raw = archive.read(row["source_member"])
            if digest(raw) != row["source_sha256"]:
                raise ValueError(f"Source photo changed: {row['identity_id']}")
            row["split"] = "validation" if index % 5 == 4 else "train"
            with Image.open(BytesIO(raw)) as image:
                normalized = ImageOps.pad(ImageOps.exif_transpose(image).convert("RGB"), (512, 512),
                                          Image.Resampling.LANCZOS, color=(255, 255, 255))
            target = output / "source" / f"{row['identity_id']}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            normalized.save(target)
            row["normalized_source"] = str(target.relative_to(output).as_posix())
            row["normalized_sha256"] = sha256(target.read_bytes()).hexdigest()
    report = {"dataset": "11K Hands", "usage_terms": "free for reasonable academic fair use; cite Afifi 2019",
              "source_url": SOURCE_URL, "metadata_sha256": data["metadata_sha256"],
              "archive_sha256": data["archive_sha256"], "candidate_identities_reviewed": len(candidates),
              "selected_identities": len(selected),
              "train_identities": sum(row["split"] == "train" for row in selected),
              "validation_identities": sum(row["split"] == "validation" for row in selected),
              "selection_status": "FROZEN_VISUAL_SELECTION"}
    save_json(output / "source_selection.json", {**report, "candidates": candidates})
    return report


def apply_review(candidates_path: Path, accepted_ids_path: Path) -> dict:
    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    review = json.loads(accepted_ids_path.read_text(encoding="utf-8"))
    accepted_ids = set(review["accepted_identity_ids"])
    if len(accepted_ids) != len(review["accepted_identity_ids"]) or len(accepted_ids) > 20:
        raise ValueError("Selection has duplicate IDs or exceeds 20 identities")
    available = {row["identity_id"] for row in data["candidates"]}
    if not accepted_ids <= available:
        raise ValueError(f"Unknown reviewed identities: {sorted(accepted_ids - available)}")
    for row in data["candidates"]:
        if row["identity_id"] in accepted_ids:
            row["selection_status"] = "ACCEPT"
            row["exclusion_reason"] = ""
            row["review_note"] = "Dorsal unpolished hand; visible separated nails in source contact-sheet review."
        else:
            row["selection_status"] = "REJECT"
            row["exclusion_reason"] = "Not chosen for the 20-identity pilot after source contact-sheet review."
            row["review_note"] = "Reserve or less suitable hand framing for this pilot."
    data["review_source"] = str(accepted_ids_path.resolve())
    save_json(candidates_path, data)
    return {"reviewed": len(data["candidates"]), "accepted": len(accepted_ids),
            "rejected": len(data["candidates"]) - len(accepted_ids)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("shortlist", "review", "freeze"))
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--accepted-ids", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.phase == "shortlist":
        if not args.metadata or not args.archive or not args.output:
            parser.error("shortlist requires --metadata, --archive and --output")
        result = shortlist(args.metadata, args.archive, args.output)
    elif args.phase == "review":
        if not args.candidates or not args.accepted_ids:
            parser.error("review requires --candidates and --accepted-ids")
        result = apply_review(args.candidates, args.accepted_ids)
    else:
        if not args.candidates or not args.archive or not args.output:
            parser.error("freeze requires --candidates, --archive and --output")
        result = freeze(args.candidates, args.archive, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
