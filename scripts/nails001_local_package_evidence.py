"""Retain step-50 checkpoint, exact sample trace, logs and held-out images."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from nails001_local_kaggle import LOCAL_NAME, DATA_SHA, digest


def package(root: Path) -> dict:
    output = root / "NAILS-001-LOCAL-v1-step050-evidence.zip"
    if output.exists():
        raise ValueError("Evidence ZIP exists; refusing to overwrite")
    out = root / "nails001_local"
    summary = json.loads((out / "training_summary.json").read_text(encoding="utf-8"))
    evaluation_zip = root / "NAILS-001-LOCAL-v1-step050-evaluation.zip"
    checkpoint = out / "checkpoints" / LOCAL_NAME / f"{LOCAL_NAME}.safetensors"
    optimizer = checkpoint.parent / "optimizer.pt"
    if summary["status"] != "CHECKPOINT_READY_REVIEW_REQUIRED":
        raise ValueError("Training has not finished its first bounded stage")
    if digest(checkpoint) != summary["checkpoint_sha256"] or digest(optimizer) != summary["optimizer_sha256"]:
        raise ValueError("Checkpoint or optimizer hash mismatch")
    if not evaluation_zip.is_file():
        raise ValueError("Held-out evaluation ZIP missing")
    with ZipFile(evaluation_zip) as evaluated:
        if evaluated.testzip() is not None:
            raise ValueError("Evaluation ZIP CRC failure")
        meta = json.loads(evaluated.read("metadata.json"))
        if meta["status"] != "PENDING_VISUAL_REVIEW" or len(meta["pairs"]) != 20:
            raise ValueError("Held-out evaluation incomplete")
        if meta["checkpoint_sha256"] != summary["checkpoint_sha256"]:
            raise ValueError("Evaluation used a different checkpoint")
    trace = [json.loads(line) for line in (out / "sample_trace.jsonl").read_text(encoding="utf-8").splitlines()]
    if [line["step"] for line in trace] != list(range(1, 51)):
        raise ValueError("Exact sample exposure trace incomplete")
    required = [root / "train_config.yaml", root / "local_bundle_evidence.json", checkpoint, optimizer,
        evaluation_zip] + [out / name for name in ("preflight.json", "runtime.json",
        "training_command.json", "training_summary.json", "sample_trace.jsonl", "train.log")]
    if any(not path.is_file() for path in required):
        raise ValueError("Required training evidence missing")
    hashes = {path.name: digest(path) for path in required}
    manifest = {"status": "PENDING_VISUAL_REVIEW", "approved_data_sha256": DATA_SHA,
        "localized_data_sha256": digest(root / "DATA-N001-LOCAL-v1.zip"),
        "checkpoint_step": 50, "checkpoint_sha256": summary["checkpoint_sha256"],
        "evaluation_sha256": digest(evaluation_zip), "sample_trace_count": len(trace),
        "evidence_file_hashes": hashes}
    with ZipFile(output, "w", ZIP_DEFLATED) as artifact:
        for path in required:
            if path == checkpoint or path == optimizer:
                name = f"checkpoint/{path.name}"
            elif path == evaluation_zip:
                name = "evaluation/NAILS-001-LOCAL-v1-step050-evaluation.zip"
            elif path.parent == out:
                name = f"logs/{path.name}"
            else:
                name = path.name
            artifact.write(path, name)
        artifact.writestr("evidence_manifest.json", json.dumps(manifest, indent=2) + "\n")
    with ZipFile(output) as check:
        if check.testzip() is not None:
            raise ValueError("Evidence ZIP CRC failure")
    return {"status": "PENDING_VISUAL_REVIEW", "evidence_zip": str(output),
            "evidence_sha256": digest(output), "checkpoint_sha256": summary["checkpoint_sha256"],
            "held_out_pairs": 20, "sample_trace_count": 50}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/kaggle/working"))
    args = parser.parse_args()
    print(json.dumps(package(args.root), indent=2))


if __name__ == "__main__":
    main()
