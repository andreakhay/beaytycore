"""Recover DATA-002 in one Kaggle Save & Run All version.

This is a Supervisor-run GPU job. It never trains a model or touches TRAIN-001.
The notebook version, not the interactive session, is the durable artifact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from urllib.request import Request, urlopen
from zipfile import ZIP_STORED, ZipFile


REPO = Path("/kaggle/working/CometicsAI")
OUT = Path("/kaggle/working/data002")
ARCHIVE = Path("/kaggle/working/data002_final.zip")
COMMIT = "ddf1681"
MANIFEST_SHA256 = "25a3200c9a79be85ce19f690ba81f564d57d55d86d36e6383b0cacd1188ec5ab"
FILES = {
    "docs/data/DATA-002-manifest.json": MANIFEST_SHA256,
    "scripts/paired_dataset.py": "1c657ea982dbe0743fbc4b6dc0859a7cee9374c6ede19e0d864a54a588fd999e",
    "notebooks/data002_generate_kaggle.py": "8104c3a672bf839cf83e3f644a9ee0a55185fb2a9fb26bc59936eed6752abfd6",
}
REQUIREMENTS = """diffusers==0.40.0
transformers==5.0.0
accelerate>=1.10,<2
peft>=0.17,<1
huggingface-hub>=1.23,<2
safetensors>=0.8,<1
Pillow>=10.1,<13
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_status(stage: str, detail: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "recovery_status.json").write_text(
        json.dumps({"stage": stage, "detail": detail, "manifest_sha256": MANIFEST_SHA256}, indent=2) + "\n",
        encoding="utf-8",
    )


def fetch_pinned_sources() -> None:
    for relative, expected in FILES.items():
        url = f"https://raw.githubusercontent.com/mark-juswa/CometicsAI/{COMMIT}/{relative}"
        print("Fetching", relative, flush=True)
        with urlopen(Request(url, headers={"User-Agent": "haircapstone-data002-recovery/1"}), timeout=45) as response:
            data = response.read()
        actual = sha256(data)
        if actual != expected:
            raise RuntimeError(f"Pinned source SHA-256 mismatch for {relative}: {actual}")
        target = REPO / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (REPO / "docs/data/DATA-002-manifest.sha256").write_text(MANIFEST_SHA256 + "\n", encoding="utf-8")


def wait_for(command: list[str], log_path: Path, label: str, every_seconds: int = 60) -> None:
    print(label, flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        while True:
            try:
                process.wait(timeout=every_seconds)
                break
            except subprocess.TimeoutExpired:
                completed = len(list((OUT / "generated").glob("*/generated.png")))
                print(f"{label}: still running; generated images: {completed}; log: {log_path}", flush=True)
    if process.returncode:
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:])
        raise RuntimeError(f"{label} exited {process.returncode}. Last log lines:\n{tail}")
    print(f"{label}: complete", flush=True)


def install_dependencies(torch_version: str) -> None:
    requirements = OUT / "recovery_requirements.txt"
    constraints = OUT / "torch_constraints.txt"
    requirements.write_text(REQUIREMENTS, encoding="utf-8")
    constraints.write_text(f"torch=={torch_version}\n", encoding="utf-8")
    wait_for(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
         "--upgrade-strategy", "only-if-needed", "--constraint", str(constraints), "-r", str(requirements)],
        OUT / "dependency_install.log", "Dependency setup", every_seconds=30,
    )
    wait_for(
        [sys.executable, "-c", "import torch; from diffusers import Flux2KleinPipeline; "
         f"assert torch.__version__ == {torch_version!r} and torch.cuda.is_available(); "
         "print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"],
        OUT / "dependency_check.log", "CUDA and FLUX import check", every_seconds=30,
    )


def run_dataset() -> None:
    generator = REPO / "notebooks/data002_generate_kaggle.py"
    finalizer = REPO / "scripts/paired_dataset.py"
    manifest = REPO / "docs/data/DATA-002-manifest.json"
    wait_for(
        [sys.executable, "-u", str(generator), "--all",
         "--approved-manifest-sha256", MANIFEST_SHA256],
        OUT / "generation_run.log", "FLUX counterpart generation",
    )
    audit_path = OUT / "generation_audit.json"
    wait_for(
        [sys.executable, "-u", str(finalizer), "audit", "--manifest", str(manifest),
         "--generation-dir", str(OUT / "generated"), "--approved-manifest-sha256", MANIFEST_SHA256,
         "--output", str(audit_path)],
        OUT / "generation_audit.log", "Structural audit", every_seconds=15,
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (audit["valid_generation_count"] != 120 or audit["issues"]
            or audit["severely_underrepresented"] or audit["exact_hash_split_leakage"]):
        raise RuntimeError("Structural audit failed or has exclusions; inspect generation_audit.json")
    wait_for(
        [sys.executable, "-u", str(finalizer), "finalize", "--manifest", str(manifest),
         "--generation-dir", str(OUT / "generated"), "--output", str(OUT / "final"),
         "--review-mode", "automated_unreviewed", "--approved-manifest-sha256", MANIFEST_SHA256],
        OUT / "finalization.log", "Paired-dataset finalization", every_seconds=15,
    )
    qa = json.loads((OUT / "final/reports/qa.json").read_text(encoding="utf-8"))
    if (qa["identity_counts"] != {"train": 100, "val": 20}
            or qa["pair_counts"] != {"train": 200, "val": 40}
            or qa["review_mode"] != "automated_unreviewed"
            or qa["split_leakage"] is not False or qa["excluded_generations"]):
        raise RuntimeError("Final DATA-002 QA differs from the approved structural target")


def package_final() -> None:
    final = OUT / "final"
    files = sorted(path for path in final.rglob("*") if path.is_file())
    with ZipFile(ARCHIVE, "w", compression=ZIP_STORED) as archive:
        for index, path in enumerate(files, 1):
            archive.write(path, path.relative_to(OUT))
            if index % 100 == 0:
                print(f"Archived {index}/{len(files)} files", flush=True)
    with ZipFile(ARCHIVE) as archive:
        bad = archive.testzip()
    if bad:
        raise RuntimeError(f"Final archive failed CRC check: {bad}")
    print("DATA-002 READY", ARCHIVE, "bytes:", ARCHIVE.stat().st_size, flush=True)


def main() -> None:
    import torch

    if not torch.cuda.is_available() or not torch.version.cuda:
        raise RuntimeError("Select a Kaggle T4 GPU and enable Internet before Save & Run All")
    if shutil.disk_usage("/kaggle/working").free < 2 * 1024**3:
        raise RuntimeError("Less than 2 GiB free in /kaggle/working")
    if shutil.disk_usage("/tmp").free < 40 * 1024**3:
        raise RuntimeError("Less than 40 GiB free in /tmp for Base cache")
    print("GPU:", torch.cuda.get_device_name(0), "Torch:", torch.__version__, flush=True)
    save_status("STARTED", "Pinned DATA-002 recovery run started")
    fetch_pinned_sources()
    install_dependencies(torch.__version__)
    run_dataset()
    package_final()
    save_status("READY", "120 generated identities; 200 train and 40 validation pairs; ZIP verified")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        save_status("FAILED", f"{type(error).__name__}: {error}")
        print("DATA-002 RECOVERY FAILED. Saved outputs and logs require inspection; no TRAIN-002 run started.", flush=True)
        traceback.print_exc()
