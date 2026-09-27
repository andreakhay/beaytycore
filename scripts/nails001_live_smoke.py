"""Call the real /nails API for two hands and save a visual/timing review pack.

The script never calls the GPU service directly. Run it while the local backend
and the approved Kaggle Nails service are both running.
"""

import argparse
import base64
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
import time

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import configured_nails_pipeline  # noqa: E402
from app.nails.contract import ADAPTER_SHA256, MODEL_STYLES  # noqa: E402
from app.nails.hybrid import _to_original, normalized_hand  # noqa: E402


STYLES = ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def nail_mask(image: Image.Image, pipeline) -> Image.Image:
    normalized, content_box = normalized_hand(image)
    hand = pipeline.localizer.locate(normalized)
    mask = pipeline.segmenter.segment(normalized, hand)
    return _to_original(mask, content_box, image.size, mask=True)


def review_sheet(images: dict[str, dict[str, Image.Image]], path: Path) -> None:
    cell = 260
    sheet = Image.new("RGB", (cell * 6, (cell + 30) * 2), "white")
    draw = ImageDraw.Draw(sheet)
    for row, (name, results) in enumerate(images.items()):
        for col, style in enumerate(("original", *STYLES)):
            item = results.get(style)
            if item is None:
                continue
            thumb = ImageOps.contain(item.convert("RGB"), (cell - 12, cell - 12))
            x = col * cell + (cell - thumb.width) // 2
            y = row * (cell + 30) + 26 + (cell - thumb.height) // 2
            sheet.paste(thumb, (x, y))
            draw.text((col * cell + 5, row * (cell + 30) + 5),
                      f"{name}: {style}", fill="black")
    sheet.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--hand-a", type=Path, default=ROOT / "data/nails/work/source-frozen-v4/source/0000000.png")
    parser.add_argument("--hand-b", type=Path, default=ROOT / "data/nails/work/source-frozen-v4/source/0000088.png")
    parser.add_argument("--out", type=Path, default=ROOT / "data/nails/work/live-smoke")
    parser.add_argument("--resume", action="store_true", help="Reuse verified saved requests and run only missing ones")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    images: dict[str, dict[str, Image.Image]] = {}
    report_path = args.out / "report.json"
    report: dict = (json.loads(report_path.read_text(encoding="utf-8"))
                    if args.resume and report_path.is_file()
                    else {"checkpoint_sha256_expected": ADAPTER_SHA256, "requests": []})
    if report.get("checkpoint_sha256_expected") != ADAPTER_SHA256:
        raise RuntimeError("Saved report belongs to a different checkpoint")
    saved = {(item["hand"], item["style_id"]): item for item in report["requests"]}
    if len(saved) != len(report["requests"]):
        raise RuntimeError("Saved report has duplicate request records")
    sources = (("hand_a", args.hand_a, STYLES),
               ("hand_b", args.hand_b, ("classic_red", "glossy_black")))
    with httpx.Client(timeout=1800) as client:
        for name, source_path, styles in sources:
            source = Image.open(source_path).convert("RGB")
            images[name] = {"original": source}
            source_hash = sha256_file(source_path)
            if name in report and report[name].get("source_sha256") != source_hash:
                raise RuntimeError(f"Saved report uses a different {name} source image")
            report[name] = {"source": str(source_path.resolve()),
                            "source_sha256": source_hash}
            for style in styles:
                output_path = args.out / f"{name}-{style}.png"
                if args.resume and (name, style) in saved:
                    record = saved[name, style]
                    if (record.get("result") != output_path.name or not output_path.is_file()
                            or sha256_file(output_path) != record.get("result_sha256")):
                        raise RuntimeError(f"{name}/{style}: saved result hash does not match report")
                    with Image.open(output_path) as opened:
                        images[name][style] = opened.convert("RGB")
                    if images[name][style].size != source.size:
                        raise RuntimeError(f"{name}/{style}: saved result framing changed")
                    print(f"{name} {style}: verified saved result; skipping GPU request", flush=True)
                    continue
                started = time.monotonic()
                try:
                    response = client.post(f"{args.base_url.rstrip('/')}/nails/generate",
                        data={"style_id": style},
                        files={"image": (source_path.name, source_path.read_bytes(), "image/png")})
                except httpx.RequestError:
                    raise RuntimeError(f"{name}/{style}: local backend is unreachable; start it and rerun with --resume") from None
                elapsed = time.monotonic() - started
                if response.status_code != 200:
                    raise RuntimeError(f"{name}/{style}: HTTP {response.status_code}: {response.text[:500]}")
                body = response.json()
                metadata = body["metadata"]
                expected_path = "model" if style in MODEL_STYLES else "renderer"
                if body["status"] != "completed" or metadata["inference_path"] != expected_path:
                    raise RuntimeError(f"{name}/{style}: wrong API inference path")
                if style in MODEL_STYLES and metadata.get("adapter_sha256") != ADAPTER_SHA256:
                    raise RuntimeError(f"{name}/{style}: wrong adapter hash")
                if not 3 <= metadata.get("nails_edited", 0) <= 5:
                    raise RuntimeError(f"{name}/{style}: unexpected nail count")
                if style in MODEL_STYLES and not all(
                    key in metadata.get("timing_seconds", {}) for key in
                    ("image_validation", "hand_localization", "nail_segmentation",
                     "crop_preparation", "gpu_request", "model_generation",
                     "result_reconstruction", "compositing", "total_request")
                ):
                    raise RuntimeError(f"{name}/{style}: missing stage timings")
                content = base64.b64decode(body["image"]["data_url"].split(",", 1)[1], validate=True)
                with Image.open(BytesIO(content)) as decoded:
                    result = decoded.convert("RGB")
                if result.size != source.size:
                    raise RuntimeError(f"{name}/{style}: original framing changed")
                images[name][style] = result
                output_path.write_bytes(content)
                record = {"hand": name, "style_id": style, "inference_path": expected_path,
                          "nails_edited": metadata["nails_edited"],
                          "wall_seconds": round(elapsed, 3),
                          "timing_seconds": metadata.get("timing_seconds"),
                          "result": output_path.name,
                          "result_sha256": sha256(content).hexdigest()}
                report["requests"].append(record)
                report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(f"{name} {style}: {elapsed:.1f}s, {metadata['nails_edited']} nails, {expected_path}", flush=True)

        invalid = client.post(f"{args.base_url.rstrip('/')}/nails/generate",
            data={"style_id": "classic_red"},
            files={"image": ("invalid.png", b"not an image", "image/png")})
        report["invalid_image"] = {"status_code": invalid.status_code,
                                   "detail": invalid.json().get("detail")}
        if invalid.status_code not in (400, 415, 422):
            raise RuntimeError(f"Invalid image was not rejected: HTTP {invalid.status_code}")

    # Independent QA of the unchanged-pixel guarantee. The requests above
    # have already gone through the real API and GPU route.
    pipeline = configured_nails_pipeline()
    for name, _, _ in sources:
        mask = nail_mask(images[name]["original"], pipeline)
        mask.save(args.out / f"{name}-nail-mask.png")
        outside = np.asarray(mask) <= 127
        original = np.asarray(images[name]["original"])
        for record in report["requests"]:
            if record["hand"] == name:
                result = np.asarray(images[name][record["style_id"]])
                record["changed_outside_mask_pixels"] = int(np.any(result != original, axis=2)[outside].sum())
                if record["changed_outside_mask_pixels"]:
                    raise RuntimeError(f"{name}/{record['style_id']}: outside-mask pixels changed")
    review_sheet(images, args.out / "review-sheet.png")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Saved review sheet and timing report to", args.out, flush=True)


if __name__ == "__main__":
    main()
