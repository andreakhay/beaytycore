"""Start an isolated MAKEUP-001 inference session, no training or Hair runtime."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("/kaggle/working/makeup001_runtime")
CACHE = Path("/tmp/hf-cache/hub")
PORT = 8766
sys.path.insert(0, str(ROOT / "backend"))
from app.makeup_contract import (ADAPTER_ID, ADAPTER_SHA256, MODEL_ID, MODEL_REVISION,
                                 PRESETS_SHA256, PROMPTS, digest, verify_adapter)


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def stage(name):
    save("progress.json", {"stage": name, "utc": datetime.now(timezone.utc).isoformat()})
    print("MAKEUP-001 stage:", name, flush=True)


def health(url):
    try:
        with urlopen(url + "/health", timeout=5) as response:
            return json.load(response)
    except (OSError, URLError, ValueError):
        return None


def expected_health(payload):
    return bool(payload and payload.get("status") == "ready" and payload.get("feature") == "makeup"
                and payload.get("adapter_id") == ADAPTER_ID and payload.get("adapter_sha256") == ADAPTER_SHA256
                and payload.get("base_model_id") == MODEL_ID and payload.get("base_model_revision") == MODEL_REVISION
                and payload.get("lora_active") is True and payload.get("adapter_steps") == 250
                and payload.get("prompt_presets_sha256") == PRESETS_SHA256
                and set(payload.get("supported_styles", [])) == set(PROMPTS))


def verify_bundle():
    manifest = json.loads((ROOT / "bundle.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "MAKEUP-001-runtime-bundle-v1" or manifest.get("adapter_id") != ADAPTER_ID:
        raise RuntimeError("Not a MAKEUP-001 inference bundle")
    for name, expected in manifest["files"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or digest(path) != expected:
            raise RuntimeError(f"Runtime bundle file failed verification: {name}")
    return verify_adapter(ROOT / "adapter")


def dependencies(torch_version):
    from packaging.requirements import Requirement
    requirements = ROOT / "scripts/kaggle_inference_requirements.txt"
    missing = False
    for line in requirements.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        requirement = Requirement(line)
        try:
            missing |= importlib.metadata.version(requirement.name) not in requirement.specifier
        except importlib.metadata.PackageNotFoundError:
            missing = True
    if missing:
        constraints = OUT / "torch_constraints.txt"
        pins = [f"torch=={torch_version}"]
        for name in ("torchvision", "torchaudio"):
            try:
                pins.append(f"{name}=={importlib.metadata.version(name)}")
            except importlib.metadata.PackageNotFoundError:
                pass
        constraints.write_text("\n".join(pins) + "\n", encoding="utf-8")
        with (OUT / "dependency_install.log").open("w", encoding="utf-8") as log:
            subprocess.run([sys.executable, "-m", "pip", "install", "--constraint", str(constraints),
                            "-r", str(requirements)], stdout=log, stderr=subprocess.STDOUT, check=True)
    # Optional old torchao can break PEFT imports; it is not used by FP16 inference.
    from packaging.version import Version
    try:
        old_torchao = Version(importlib.metadata.version("torchao")) < Version("0.16.0")
    except importlib.metadata.PackageNotFoundError:
        old_torchao = False
    if old_torchao:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], check=True)
    check = subprocess.run([sys.executable, "-c", "import torch; from diffusers import Flux2KleinPipeline; "
                            "print(torch.__version__); assert torch.cuda.is_available()"],
                           capture_output=True, text=True, timeout=600)
    (OUT / "dependency_check.log").write_text(check.stdout + check.stderr, encoding="utf-8")
    if check.returncode or check.stdout.strip().splitlines()[-1] != torch_version:
        raise RuntimeError("Inference imports failed or CUDA Torch changed; inspect dependency_check.log")


def model_snapshot():
    from huggingface_hub import snapshot_download
    if shutil.disk_usage("/tmp").free < 30 * 1024**3:
        raise RuntimeError("Insufficient scratch space for pinned FLUX Base")
    path = Path(snapshot_download(repo_id=MODEL_ID, revision=MODEL_REVISION, cache_dir=str(CACHE),
                                 allow_patterns=["model_index.json", "scheduler/*", "tokenizer/*",
                                                 "text_encoder/*", "transformer/*", "vae/*"]))
    if path.name != MODEL_REVISION or not (path / "model_index.json").is_file():
        raise RuntimeError("Wrong or incomplete Base snapshot")
    save("model.json", {"model_id": MODEL_ID, "revision": MODEL_REVISION, "snapshot": str(path)})
    return path


def start_server(model, key):
    local = f"http://127.0.0.1:{PORT}"
    if expected_health(health(local)):
        return
    if health(local) is not None:
        raise RuntimeError("Makeup port is occupied by an unexpected service; do not stop another feature")
    process_file = OUT / "server_process.json"
    if process_file.exists():
        pid = json.loads(process_file.read_text())["pid"]
        proc = Path(f"/proc/{pid}/cmdline")
        if proc.exists() and proc.read_bytes():
            raise RuntimeError("An earlier Makeup server process exists; inspect its log instead of starting another")
    env = os.environ.copy()
    env.update({"MAKEUP001_API_KEY": key, "MAKEUP001_MODEL_DIR": str(model),
                "MAKEUP001_ADAPTER_DIR": str(ROOT / "adapter"), "PYTHONUNBUFFERED": "1"})
    with (OUT / "server.log").open("a", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "scripts.makeup_inference_server:app",
                                    "--host", "127.0.0.1", "--port", str(PORT), "--workers", "1"],
                                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    save("server_process.json", {"pid": process.pid, "port": PORT})
    started, next_update = time.monotonic(), time.monotonic() + 30
    while time.monotonic() - started < 900:
        if process.poll() is not None:
            raise RuntimeError(f"Makeup server exited {process.returncode}; inspect server.log")
        if expected_health(health(local)):
            return
        if time.monotonic() >= next_update:
            print("Loading Makeup model; server.log bytes:", (OUT / "server.log").stat().st_size, flush=True)
            next_update = time.monotonic() + 30
        time.sleep(3)
    raise RuntimeError("Makeup load exceeded 15 minutes; inspect server.log before rerunning")


def tunnel():
    prior = OUT / "endpoint.json"
    if prior.exists():
        url = json.loads(prior.read_text())["url"]
        if expected_health(health(url)):
            return url
    binary = OUT / "cloudflared"
    if not binary.exists():
        with urlopen("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
                     timeout=90) as source, binary.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        binary.chmod(0o700)
    with (OUT / "tunnel.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([str(binary), "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    started = time.monotonic()
    while time.monotonic() - started < 180:
        if process.poll() is not None:
            raise RuntimeError("Makeup tunnel exited; inspect tunnel.log")
        text = (OUT / "tunnel.log").read_text(encoding="utf-8", errors="replace")
        match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", text)
        if match and expected_health(health(match.group(0))):
            url = match.group(0)
            save("endpoint.json", {"url": url, "pid": process.pid})
            return url
        time.sleep(3)
    raise RuntimeError("Public Makeup health did not pass; inspect tunnel.log")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true")
    args = parser.parse_args()
    stage("VERIFYING_BUNDLE")
    verify_bundle()
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["HF_HOME"] = "/tmp/hf-cache"
    os.environ["HF_HUB_CACHE"] = str(CACHE)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("Select a Kaggle T4 GPU")
    key = os.environ.get("MAKEUP001_API_KEY", "")
    if not key:
        from kaggle_secrets import UserSecretsClient
        key = UserSecretsClient().get_secret("MAKEUP001_API_KEY")
    if len(key) < 24:
        raise RuntimeError("Enable a MAKEUP001_API_KEY Kaggle Secret of at least 24 characters")
    save("environment.json", {"python": sys.version, "torch": torch.__version__, "cuda": torch.version.cuda,
                              "gpu": torch.cuda.get_device_name(0), "hair_adapter_loaded": False})
    stage("INSTALLING_DEPENDENCIES")
    dependencies(torch.__version__)
    stage("DOWNLOADING_PINNED_BASE")
    model = model_snapshot()
    stage("LOADING_MAKEUP001")
    start_server(model, key)
    stage("STARTING_TUNNEL")
    url = f"http://127.0.0.1:{PORT}" if args.local_only else tunnel()
    save("health.json", health(url))
    stage("READY")
    print("MAKEUP_GENERATION_ENGINE=remote_makeup\nMAKEUP_REMOTE_URL=" + url, flush=True)
    print("MAKEUP_REMOTE_API_KEY=<same value as your Kaggle MAKEUP001_API_KEY Secret>", flush=True)
    print("Keep this inference session running while using the Makeup page. No training was run.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        stage("FAILED")
        print(f"MAKEUP SETUP FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
