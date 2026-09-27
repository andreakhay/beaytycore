"""Run the pilot nail segmenter in its isolated Python environment."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def _predict(model, rgb: Image.Image):
    return model.predict(source=rgb, conf=.25, imgsz=640, retina_masks=True,
                         device="cpu", verbose=False)[0]


def _roi_batch(model, manifest: Path, output: Path) -> None:
    """Keep the native ROI raster; never reduce it to polygon coordinates."""
    specs = json.loads(manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for spec in specs:
        with Image.open(spec["image"]) as opened:
            rgb = opened.convert("RGB")
        with Image.open(spec["coarse_mask"]) as opened:
            coarse = np.asarray(opened.convert("L")) > 127
        result = _predict(model, rgb)
        if result.masks is None:
            raise ValueError(f"No ROI nail prediction for {spec['finger_id']}")
        candidates = result.masks.data.cpu().numpy()
        best, best_iou = None, 0.0
        for candidate in candidates:
            raster = cv2.resize(candidate.astype(np.float32), rgb.size,
                                interpolation=cv2.INTER_LINEAR) > .5
            union = np.count_nonzero(raster | coarse)
            iou = np.count_nonzero(raster & coarse) / union if union else 0.0
            if iou > best_iou:
                best, best_iou = raster, iou
        if best is None or best_iou < .40:
            raise ValueError(f"Unreliable ROI nail prediction for {spec['finger_id']}: IoU {best_iou:.3f}")
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        best = cv2.morphologyEx(best.astype(np.uint8), cv2.MORPH_CLOSE, kernel) > 0
        # Coarse mask anchors finger identity. ROI raster adjusts the boundary.
        def sdf(array):
            positive = cv2.distanceTransform(array.astype(np.uint8), cv2.DIST_L2, 3)
            negative = cv2.distanceTransform((~array).astype(np.uint8), cv2.DIST_L2, 3)
            return positive - negative
        refined = (.75 * sdf(coarse) + .25 * sdf(best)) > 1.0
        count = int(refined.sum())
        ratio = count / max(1, int(coarse.sum()))
        overlap = int(np.count_nonzero(refined & coarse)) / max(1, count)
        if not .60 <= ratio <= 1.25 or overlap < .75:
            raise ValueError(f"Unreliable refined plate for {spec['finger_id']}: "
                             f"area ratio {ratio:.3f}, overlap {overlap:.3f}")
        ys, xs = np.nonzero(refined)
        width, height = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
        aspect = width / height
        components, _, sizes, _ = cv2.connectedComponentsWithStats(
            refined.astype(np.uint8), 8)
        large_islands = sum(sizes[i, cv2.CC_STAT_AREA] > count * .03
                            for i in range(1, components))
        if count < 80 or not .20 <= aspect <= 5.0 or large_islands != 1:
            raise ValueError(f"Implausible refined plate for {spec['finger_id']}")
        path = output / f"{spec['finger_id']}.png"
        Image.fromarray((refined * 255).astype(np.uint8), "L").save(path)
        records.append({"finger_id": spec["finger_id"], "roi_iou": round(best_iou, 4),
                        "area_ratio": round(ratio, 4), "pixels": count})
    (output / "metrics.json").write_text(json.dumps(records, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--roi-manifest", type=Path)
    parser.add_argument("--roi-output", type=Path)
    args = parser.parse_args()
    from ultralytics import YOLO

    model = YOLO(str(args.checkpoint))
    if args.roi_manifest:
        if not args.roi_output:
            parser.error("--roi-output is required with --roi-manifest")
        _roi_batch(model, args.roi_manifest, args.roi_output)
        return
    if not args.image or not args.mask:
        parser.error("--image and --mask are required for coarse segmentation")
    with Image.open(args.image) as opened:
        rgb = opened.convert("RGB")
    result = _predict(model, rgb)
    mask = np.zeros((rgb.height, rgb.width), dtype=np.uint8)
    for polygon in result.masks.xy if result.masks is not None else []:
        if len(polygon) >= 3:
            cv2.fillPoly(mask, [np.rint(polygon).astype(np.int32)], 255)
    Image.fromarray(mask, "L").save(args.mask)


if __name__ == "__main__":
    main()
