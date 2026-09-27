"""Promote explicitly reviewed 11K Hands masks into DATA-N001 input.

This does not judge masks. A separate human-authored review file must mark each
frozen identity ACCEPT before any paired targets can be rendered.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.nails.geometry import MediaPipeHandLocalizer, validate_nail_mask


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--segmentation-root", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--hand-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Refusing to overwrite DATA-N001 selection input")
    source_manifest_path = args.source_root / "source_selection.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    segmentation = json.loads((args.segmentation_root / "segmentation_predictions.json").read_text(encoding="utf-8"))
    reviews = json.loads(args.reviews.read_text(encoding="utf-8"))
    selected = {row["identity_id"]: row for row in source_manifest["candidates"]
                if row["selection_status"] == "ACCEPT"}
    predictions = {row["identity_id"]: row for row in segmentation["records"]}
    decisions = {row["identity_id"]: row for row in reviews["records"]}
    if (len(selected) != source_manifest["selected_identities"]
            or len(predictions) != len(selected) or len(decisions) != len(selected)
            or set(selected) != set(predictions) or set(selected) != set(decisions)):
        raise ValueError("Frozen identities, predictions and reviews differ")
    if segmentation["source_manifest_sha256"] != digest(source_manifest_path):
        raise ValueError("Segmentation was run on a different source freeze")
    if reviews["checkpoint_sha256"] != segmentation["checkpoint_sha256"]:
        raise ValueError("Review does not match the segmentation checkpoint")
    if any(row["status"] != "ACCEPT" or not row.get("note") or not row.get("reviewer")
           for row in decisions.values()):
        raise ValueError("All selected nail masks need explicit ACCEPT decisions")

    localizer = MediaPipeHandLocalizer(args.hand_model)
    identities = []
    for identity, row in sorted(selected.items()):
        prediction = predictions[identity]
        source = args.source_root / row["normalized_source"]
        mask = args.segmentation_root / prediction["mask_path"]
        if digest(source) != row["normalized_sha256"] or digest(mask) != prediction["mask_sha256"]:
            raise ValueError(f"Frozen source or mask changed: {identity}")
        with Image.open(source) as file:
            image = file.convert("RGB")
        with Image.open(mask) as file:
            mask_image = file.convert("L")
        hand = localizer.locate(image)
        validate_nail_mask(mask_image, hand)
        target_source = args.output / "source" / f"{identity}.png"
        target_mask = args.output / "masks" / f"{identity}.png"
        target_source.parent.mkdir(parents=True, exist_ok=True)
        target_mask.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target_source)
        shutil.copyfile(mask, target_mask)
        identities.append({
            "identity_id": identity, "split": row["split"],
            "source": f"source/{identity}.png", "mask": f"masks/{identity}.png",
            "landmarks": [[round(x, 7), round(y, 7)] for x, y in hand.points],
            "source_credit": "Afifi, 11K Hands dataset (2019)",
            "source_license": source_manifest["usage_terms"],
            "source_member": row["source_member"],
            "source_sha256": row["source_sha256"],
            "mask_sha256": prediction["mask_sha256"],
            "segmentation_review_note": decisions[identity]["note"],
        })
    if len({r["identity_id"] for r in identities}) != len(identities):
        raise ValueError("Duplicate selected identity")
    splits = {name: {r["identity_id"] for r in identities if r["split"] == name}
              for name in ("train", "validation")}
    if splits["train"] & splits["validation"]:
        raise ValueError("Identity leakage")
    report = {"identities": identities, "source_manifest_sha256": digest(source_manifest_path),
              "segmentation_checkpoint_sha256": segmentation["checkpoint_sha256"],
              "segmentation_reviews_sha256": digest(args.reviews),
              "hand_model_sha256": digest(args.hand_model)}
    (args.output / "selection.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"identities": len(identities),
                      "train": len(splits["train"]), "validation": len(splits["validation"])}, indent=2))


if __name__ == "__main__":
    main()
