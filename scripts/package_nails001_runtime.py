"""Package the immutable step-50 checkpoint for inference only."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "backend"))
from app.nails.contract import ADAPTER_ID, ADAPTER_SHA256, MODEL_ID, MODEL_REVISION

SOURCES = (
    "backend/app/__init__.py", "backend/app/nails/__init__.py",
    "backend/app/nails/contract.py", "scripts/nails001_local_inference_server.py",
    "scripts/nails001_inference_bootstrap.py", "scripts/nails001_inference_requirements.txt",
)
CHECKPOINT_MEMBER = "checkpoint/nails001_local_v1.safetensors"


def digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def build(evidence: Path, destination: Path) -> dict:
    if destination.exists():
        raise ValueError("Refusing to replace an existing Nails runtime bundle")
    files = {name: (ROOT / name).read_bytes() for name in SOURCES}
    with ZipFile(evidence) as source:
        if source.testzip() is not None:
            raise ValueError("Step-50 evidence archive failed CRC")
        checkpoint = source.read(CHECKPOINT_MEMBER)
        if len(checkpoint) != 46223600 or digest(checkpoint) != ADAPTER_SHA256:
            raise ValueError("Step-50 adapter hash mismatch")
        summary = json.loads(source.read("logs/training_summary.json"))
        if summary["steps_planned"] != 50 or summary["checkpoint_sha256"] != ADAPTER_SHA256:
            raise ValueError("Step-50 training evidence mismatch")
    files["adapter/nails001_local_v1.safetensors"] = checkpoint
    manifest = {"schema": "NAILS-001-LOCAL-v1-runtime-v1", "adapter_id": ADAPTER_ID,
                "adapter_sha256": ADAPTER_SHA256, "training_steps": 50,
                "base_model_id": MODEL_ID, "base_revision": MODEL_REVISION,
                "files": {name: digest(content) for name, content in files.items()}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr("bundle.json", json.dumps(manifest, indent=2) + "\n")
    return {"runtime_bundle": str(destination), "bytes": destination.stat().st_size,
            "sha256": digest(destination.read_bytes()), "checkpoint_sha256": ADAPTER_SHA256}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path,
                        default=Path("D:/Downloads/NAILS-001-LOCAL-v1-step050-evidence.zip"))
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/nails/work/NAILS-001-LOCAL-v1-runtime-v2.bin")
    args = parser.parse_args()
    print(json.dumps(build(args.evidence, args.output), indent=2))


if __name__ == "__main__":
    main()
