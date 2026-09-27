"""Offline YOLOv8 nail-mask pilot on frozen 11K Hands source identities.

Use only in the isolated Nails evaluation environment. Predictions remain
PENDING until the Original | Predicted Masks | Overlay sheets are reviewed.
"""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run(source_root: Path, checkpoint: Path, output: Path, confidence: float, imgsz: int) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing to overwrite segmentation review")
    if not checkpoint.is_file():
        raise ValueError("Local segmentation checkpoint is missing")
    manifest_path = source_root / "source_selection.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = [row for row in manifest["candidates"] if row["selection_status"] == "ACCEPT"]
    if len(selected) != manifest["selected_identities"]:
        raise ValueError("Source selection count differs from frozen manifest")
    from ultralytics import YOLO
    model = YOLO(str(checkpoint))
    records = []
    for row in selected:
        identity = row["identity_id"]
        source = source_root / row["normalized_source"]
        if digest(source) != row["normalized_sha256"]:
            raise ValueError(f"Frozen source changed: {identity}")
        with Image.open(source) as image:
            rgb = image.convert("RGB")
        result = model.predict(source=rgb, conf=confidence, imgsz=imgsz,
                               retina_masks=True, device="cpu", verbose=False)[0]
        mask = np.zeros((rgb.height, rgb.width), dtype=np.uint8)
        polygons = result.masks.xy if result.masks is not None else []
        for polygon in polygons:
            if len(polygon) >= 3:
                cv2.fillPoly(mask, [np.rint(polygon).astype(np.int32)], 255)
        folder = output / identity
        folder.mkdir(parents=True, exist_ok=True)
        mask_path = folder / "predicted_mask.png"
        Image.fromarray(mask).save(mask_path)
        original = np.asarray(rgb)
        overlay = original.copy()
        overlay[mask > 0] = np.round(.45 * original[mask > 0] + .55 * np.array([218, 25, 77])).astype(np.uint8)
        sheet = Image.new("RGB", (rgb.width * 3, rgb.height + 28), "white")
        sheet.paste(rgb, (0, 0))
        sheet.paste(Image.fromarray(np.stack((mask, mask, mask), axis=2)), (rgb.width, 0))
        sheet.paste(Image.fromarray(overlay), (rgb.width * 2, 0))
        labels = ("Original", "Predicted Nail Masks", "Overlay")
        for index, label in enumerate(labels):
            ImageDraw.Draw(sheet).text((index * rgb.width + 5, rgb.height + 5),
                                       f"{identity} {label}", fill="black")
        sheet.save(folder / "review.jpg", quality=94)
        records.append({"identity_id": identity, "split": row["split"],
                        "source_path": row["normalized_source"],
                        "source_sha256": row["normalized_sha256"],
                        "mask_path": str(mask_path.relative_to(output).as_posix()),
                        "mask_sha256": digest(mask_path),
                        "detections": len(polygons), "mask_pixels": int(np.count_nonzero(mask)),
                        "confidences": [round(float(value), 4) for value in
                                        (result.boxes.conf.cpu().numpy() if result.boxes is not None else [])],
                        "review_status": "PENDING", "notes": ""})
    report = {"status": "PENDING_HUMAN_REVIEW", "model_id": "mnemic/nails_seg_yolov8",
              "checkpoint_sha256": digest(checkpoint), "source_manifest_sha256": digest(manifest_path),
              "confidence": confidence, "imgsz": imgsz, "device": "cpu",
              "offline_requested": os.environ.get("HF_HUB_OFFLINE") == "1",
              "images_tested": len(records), "records": records}
    save_json(output / "segmentation_predictions.json", report)
    return {key: value for key, value in report.items() if key != "records"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()
    if not 0 < args.confidence < 1 or not 320 <= args.imgsz <= 1280:
        parser.error("confidence and imgsz are outside the bounded pilot range")
    print(json.dumps(run(args.source_root, args.checkpoint, args.output,
                         args.confidence, args.imgsz), indent=2))


if __name__ == "__main__": main()
