"""Package the frozen two-identity, four-style source-anchored Makeup pilot.

Uses source semantic labels and region fields saved by the DATA-M001 V4 CPU
pass. It does not use V4 targets, raw FLUX images, or any Hair asset.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

import cv2
import numpy as np
from PIL import Image


IDS = ("003025", "054109")
STYLES = ("natural_makeup", "soft_glam", "smoky_glam", "classic_red_lip")
REGION_WEIGHTS = {
    "natural_makeup": (0.12, 0.48, 0.45, 0.55, 0.15),
    "soft_glam": (0.15, 0.75, 0.65, 0.75, 0.25),
    "smoky_glam": (0.10, 0.98, 0.35, 0.55, 0.25),
    "classic_red_lip": (0.06, 0.30, 0.30, 1.00, 0.10),
}
REGION_WEIGHTS_V2 = {
    "natural_makeup": (0.16, 0.70, 0.65, 0.70, 0.18),
    "soft_glam": (0.19, 0.90, 0.80, 0.82, 0.28),
    "smoky_glam": (0.12, 1.00, 0.38, 0.55, 0.28),
    "classic_red_lip": (0.06, 0.26, 0.27, 0.78, 0.10),
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def soft_mask(labels, eye, cheek, lip, brow, weights, style_id):
    if labels.shape != (512, 512):
        raise ValueError("Expected 512x512 source parser labels")
    skin = labels == 1
    lips = np.isin(labels, (11, 12))
    brows = np.isin(labels, (6, 7))
    if skin.sum() < 15000 or lips.sum() < 150:
        raise ValueError("Implausible source face parsing")
    # White edits; black protects. Preserve a continuous feathered alpha rather
    # than letting the inpaint processor threshold it to a binary face mask.
    edge = cv2.GaussianBlur(skin.astype(np.float32), (0, 0), 3) * skin
    yy = np.arange(512)[:, None]
    eyelid_zone = np.zeros_like(eye)
    for label in (4, 5):
        ey, ex = np.where(labels == label)
        if len(ex) < 35:
            raise ValueError("Parser did not resolve eye")
        upper_limit = ey.min() - 22
        lower_limit = ey.max() + (6 if style_id == "smoky_glam" else 2)
        side = (np.arange(512)[None, :] >= ex.min() - 8) & (np.arange(512)[None, :] <= ex.max() + 8)
        vertical = np.clip((yy - upper_limit) / 5, 0, 1) * np.clip((lower_limit - yy) / 5, 0, 1)
        eyelid_zone = np.maximum(eyelid_zone, vertical * side)
    eye = eye * eyelid_zone * skin
    components = [edge * weights[0], eye * weights[1], cheek * weights[2],
                  lip * weights[3], brow * weights[4]]
    mask = np.maximum.reduce(components)
    mask *= (skin | lips | brows)
    return np.uint8(np.round(np.clip(mask, 0, 1) * 255))


def soft_mask_v2(labels, fields, previous_strengths, style_id):
    """Undo V4 strength baked into saved fields before setting inpaint opacity."""
    names = ("eye", "cheek", "lip", "brow")
    normalized = []
    for name, field in zip(names, fields):
        prior = previous_strengths[name]
        if prior <= 0 or prior > 1:
            raise ValueError(f"Invalid V4 field strength: {name}={prior}")
        normalized.append(np.clip(field / prior, 0, 1))
    eye, cheek, lip, brow = normalized
    # Expand weak gradients inside their existing source anatomy, not across
    # protected labels. The first run had no Natural/Soft high opacity cells.
    eye = eye ** (0.65 if style_id == "smoky_glam" else 0.8)
    cheek = cheek ** 0.8
    if style_id == "classic_red_lip":
        # In the open-mouth source, V1 repainted the full outer and inner lip
        # boundary at high opacity. Keep red in original lip tissue, fade both
        # edges inward, and leave mouth opening/teeth at zero.
        lips = np.isin(labels, (11, 12)).astype(np.uint8)
        distance = cv2.distanceTransform(lips, cv2.DIST_L2, 3)
        lip *= np.clip(distance / 6, 0, 1)
    return soft_mask(labels, eye, cheek, lip, brow, REGION_WEIGHTS_V2[style_id], style_id)


def prepare(pilot, preserved, output, mask_version="v1"):
    if mask_version not in ("v1", "v2"):
        raise ValueError("Unknown inpaint mask version")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Refusing to overwrite {output}")
    config = json.loads((pilot / "config.json").read_text(encoding="utf-8"))
    source_manifest = json.loads((pilot / "source_manifest.json").read_text(encoding="utf-8"))
    if config["model_id"] != "black-forest-labs/FLUX.2-klein-base-4B":
        raise ValueError("Unexpected model")
    if config["inference"]["lora_active"] is not False or config["inference"]["adapter_id"] is not None:
        raise ValueError("LoRA configuration is forbidden")
    by_id = {x["identity_id"]: x for x in source_manifest["identities"]}
    by_style = {x["id"]: x for x in config["styles"]}
    if not set(IDS) <= by_id.keys() or not set(STYLES) <= by_style.keys():
        raise ValueError("Frozen pilot identity/style mismatch")
    output.mkdir(parents=True)
    jobs = []
    for identity in IDS:
        source_row = by_id[identity]
        if source_row["split"] != "TRAIN":
            raise ValueError("Inpaint pilot must use the two existing TRAIN identities")
        source = pilot / source_row["source_path"]
        if digest(source) != source_row["source_sha256"]:
            raise ValueError(f"Source hash mismatch: {identity}")
        target_source = output / "sources" / f"{identity}.jpg"
        target_source.parent.mkdir(exist_ok=True)
        target_source.write_bytes(source.read_bytes())
        for style_id in STYLES:
            folder = preserved / "targets" / identity / style_id
            sidecar = json.loads((folder / "preservation_v4.json").read_text(encoding="utf-8"))
            if sidecar["source_sha256"] != source_row["source_sha256"]:
                raise ValueError("Parser/source provenance mismatch")
            labels_path = folder / "source_semantics.png"
            if digest(labels_path) != sidecar["source_semantics_sha256"]:
                raise ValueError("Parser label hash mismatch")
            labels = np.asarray(Image.open(labels_path).convert("L"))
            fields = []
            for field_name in ("eye", "cheek", "lip", "brow"):
                field = np.asarray(Image.open(folder / f"{field_name}_mask.png").convert("L"), np.float32) / 255
                fields.append(field)
            if mask_version == "v2":
                mask = soft_mask_v2(labels, fields, sidecar["style_strength"], style_id)
            else:
                mask = soft_mask(labels, *fields, REGION_WEIGHTS[style_id], style_id)
            mask_path = output / "masks" / identity / f"{style_id}.png"
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(mask, "L").save(mask_path)
            protected = np.isin(labels, (2, 4, 5, 10, 13))
            if np.any(mask[protected]):
                raise AssertionError("Mask touches source nose, eyes, mouth, or hair")
            weights = REGION_WEIGHTS_V2[style_id] if mask_version == "v2" else REGION_WEIGHTS[style_id]
            jobs.append({"identity_id": identity, "split": "TRAIN", "style_id": style_id,
                         "style_name": by_style[style_id]["name"],
                         "prompt": by_style[style_id]["instruction"] + " " + config["preservation_instruction"],
                         "source_path": f"sources/{identity}.jpg", "source_sha256": digest(target_source),
                         "mask_path": f"masks/{identity}/{style_id}.png", "mask_sha256": digest(mask_path),
                         "parser_labels_sha256": digest(labels_path),
                         "mask_nonzero_pixels": int(np.count_nonzero(mask)),
                         "mask_soft_pixels": int(np.count_nonzero((mask > 0) & (mask < 255))),
                         "mask_region_weights": dict(zip(("complexion", "eye", "cheek", "lip", "brow"), weights)),
                         **({"mask_v2_previous_v4_strength": sidecar["style_strength"]} if mask_version == "v2" else {})})
    plan = {"experiment": "DATA-M001-INPAINT-PILOT" + ("-V2" if mask_version == "v2" else ""),
            "mask_version": mask_version, "status": "PREPARED_NOT_GENERATED",
            "model_id": config["model_id"], "model_revision": config["model_revision"],
            "pipeline_class": "Flux2KleinInpaintPipeline", "diffusers_version": "0.40.0",
            "inference": {**config["inference"], "strength": 0.70,
                          "mask_processor_do_binarize": False, "padding_mask_crop": None},
            "parser_id": "jonathandinu/face-parsing",
            "parser_revision": "758b82e15a0178c9db39c1ff666a8b56e3a550c8",
            "mask_source": "DATA-M001 V4 source_semantics and makeup region fields; raw/V4 output pixels excluded",
            "jobs": jobs}
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    runner = Path(__file__).resolve().parents[1] / "notebooks" / "data_m001_inpaint_kaggle.py"
    shutil.copyfile(runner, output / runner.name)
    bundle_name = "data_m001_inpaint_pilot_v2_input.zip" if mask_version == "v2" else "data_m001_inpaint_pilot_input.zip"
    bundle = output.parent / bundle_name
    if bundle.exists():
        raise ValueError(f"Refusing to overwrite existing input bundle: {bundle}")
    with ZipFile(bundle, "w", ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output).as_posix())
    return bundle, plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--preserved", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mask-version", choices=("v1", "v2"), default="v1")
    args = parser.parse_args()
    bundle, plan = prepare(args.pilot, args.preserved, args.output, args.mask_version)
    print(json.dumps({"bundle": str(bundle), "jobs": len(plan["jobs"]),
                      "styles": list(STYLES), "identities": list(IDS)}, indent=2))
