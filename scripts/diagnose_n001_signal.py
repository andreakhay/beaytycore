"""Measure the immutable DATA-N001 training edit signal without extracting it."""

import argparse
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from statistics import mean, median
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


EXPECTED_SHA256 = "d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb"


def summary(values):
    return {"mean": mean(values), "median": median(values), "min": min(values), "max": max(values)}


def load_image(archive, name, mode):
    with Image.open(BytesIO(archive.read(name))) as image:
        return image.convert(mode)


def run(archive_path: Path, output_dir: Path) -> dict:
    if sha256(archive_path.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError("DATA-N001 hash differs from the approved archive")
    output_dir.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("DATA-N001 CRC failure")
        manifest = json.loads(archive.read("manifests/pairs.json"))
        train = [row for row in manifest if row["split"] == "train"]
        if len(train) != 80:
            raise ValueError("Expected 80 frozen train pairs")
        rows = []
        by_style = defaultdict(list)
        for row in train:
            pair = row["pair_id"]
            source = np.asarray(load_image(archive, f"train/reference/{pair}.png", "RGB"))
            target = np.asarray(load_image(archive, f"train/target/{pair}.png", "RGB"))
            mask = np.asarray(load_image(archive, f"train/masks/{pair}.png", "L")) > 127
            if source.shape != (512, 512, 3) or target.shape != source.shape or mask.shape != source.shape[:2]:
                raise ValueError(f"Unexpected shape: {pair}")
            changed = np.any(source != target, axis=2)
            if np.any(changed & ~mask):
                raise ValueError(f"Target changed pixels outside mask: {pair}")
            label, count = ndimage.label(mask)
            components = []
            tip_core_pixels = 0
            for index in range(1, count + 1):
                points = np.argwhere(label == index)
                if len(points) < 20:
                    continue
                y0, x0 = points.min(axis=0)
                y1, x1 = points.max(axis=0) + 1
                components.append({"width": int(x1 - x0), "height": int(y1 - y0), "pixels": len(points)})
                if row["style_id"] == "french_tip":
                    xy = points[:, ::-1].astype(float)
                    center = xy.mean(axis=0)
                    finger = min(((4, 3), (8, 7), (12, 11), (16, 15), (20, 19)),
                                 key=lambda pair: np.linalg.norm(center -
                                     np.asarray(row["landmarks"][pair[0]]) * 512))
                    direction = (np.asarray(row["landmarks"][finger[0]]) -
                                 np.asarray(row["landmarks"][finger[1]]))
                    direction /= np.linalg.norm(direction)
                    projection = xy @ direction
                    relative = (projection - projection.min()) / max(1e-6, np.ptp(projection))
                    tip_core_pixels += int(np.count_nonzero(relative >= 0.77))
            ys, xs = np.nonzero(mask)
            box = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
            pad = max(24, int(max(box[2] - box[0], box[3] - box[1]) * 0.2))
            crop = [max(0, box[0] - pad), max(0, box[1] - pad), min(512, box[2] + pad), min(512, box[3] + pad)]
            crop_area = (crop[2] - crop[0]) * (crop[3] - crop[1])
            record = {"pair_id": pair, "identity_id": row["identity_id"], "style_id": row["style_id"],
                      "mask_pixels": int(mask.sum()), "mask_pct": float(mask.mean() * 100),
                      "changed_pixels": int(changed.sum()), "changed_pct": float(changed.mean() * 100),
                      "changed_of_mask_pct": float(changed.sum() / mask.sum() * 100),
                      "nail_components": components, "nail_union_box": box, "possible_crop_box": crop,
                      "possible_crop_area_pct": crop_area / (512 * 512) * 100,
                      "possible_crop_mask_pct": float(mask.sum() / crop_area * 100),
                      "possible_crop_upscale": float(512 / max(crop[2] - crop[0], crop[3] - crop[1]))}
            if row["style_id"] == "french_tip":
                record["french_tip_core_pixels"] = tip_core_pixels
                record["french_tip_core_pct"] = tip_core_pixels / (512 * 512) * 100
            rows.append(record)
            by_style[row["style_id"]].append(record)
        report = {"archive_sha256": EXPECTED_SHA256, "train_pairs": len(rows),
                  "all": {key: summary([item[key] for item in rows]) for key in
                          ("mask_pct", "changed_pct", "changed_of_mask_pct", "possible_crop_area_pct",
                           "possible_crop_mask_pct", "possible_crop_upscale")},
                  "by_style": {style: {key: summary([item[key] for item in group]) for key in
                               ("mask_pct", "changed_pct", "changed_of_mask_pct")} for style, group in sorted(by_style.items())},
                  "component_dimensions": {axis: summary([component[axis] for row in rows for component in row["nail_components"]])
                                           for axis in ("width", "height", "pixels")},
                  "french_tip_core_pct": summary([item["french_tip_core_pct"] for item in by_style["french_tip"]]),
                  "rows": rows}
        (output_dir / "signal.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        for identity in (sorted({row["identity_id"] for row in rows})[0],
                         sorted({row["identity_id"] for row in rows})[-1]):
            row = next(item for item in rows if item["identity_id"] == identity and item["style_id"] == "french_tip")
            image = load_image(archive, f"train/reference/{row['pair_id']}.png", "RGB")
            mask = load_image(archive, f"train/masks/{row['pair_id']}.png", "L")
            overlay = image.copy()
            drawing = ImageDraw.Draw(overlay)
            drawing.rectangle(row["possible_crop_box"], outline="red", width=3)
            crop = image.crop(tuple(row["possible_crop_box"]))
            crop.thumbnail((512, 512))
            sheet = Image.new("RGB", (1024, 550), "white")
            sheet.paste(overlay, (0, 25))
            sheet.paste(crop.resize((512, 512)), (512, 25))
            pen = ImageDraw.Draw(sheet)
            pen.text((5, 5), f"DATA-N001 reference {identity} (red = existing crop box)", fill="black")
            pen.text((520, 5), "Possible nail-focused crop (diagnostic only)", fill="black")
            sheet.save(output_dir / f"crop-{identity}.png")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("data/nails/work/DATA-N001-final.zip"))
    parser.add_argument("--output", type=Path, default=Path("data/nails/work/NAILS-001-step025-diagnostic"))
    args = parser.parse_args()
    result = run(args.archive, args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
