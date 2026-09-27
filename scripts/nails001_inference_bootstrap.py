"""Start the pinned Nails GPU service and temporary authenticated tunnel."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("/kaggle/working/nails001_runtime")
PORT = 8767
sys.path.insert(0, str(ROOT / "backend"))
from app.nails.contract import ADAPTER_ID, ADAPTER_SHA256, MODEL_ID, MODEL_REVISION, MODEL_STYLES, verify_adapter


def save(name: str, value: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def stage(name: str) -> None:
    save("progress.json", {"stage": name, "utc": datetime.now(timezone.utc).isoformat()})
    print("Nails inference stage:", name, flush=True)


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_bundle() -> None:
    manifest = json.loads((ROOT / "bundle.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "NAILS-001-LOCAL-v1-runtime-v1":
        raise RuntimeError("Unexpected Nails runtime bundle")
    if (manifest.get("adapter_id") != ADAPTER_ID or manifest.get("adapter_sha256") != ADAPTER_SHA256
            or manifest.get("base_revision") != MODEL_REVISION):
        raise RuntimeError("Wrong Nails model selection")
    for name, expected in manifest["files"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or digest(path) != expected:
            raise RuntimeError(f"Nails bundle member failed verification: {name}")
    verify_adapter(ROOT / "adapter/nails001_local_v1.safetensors")


def health(url: str) -> dict | None:
    try:
        with urlopen(url + "/health", timeout=5) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def expected_health(value: dict | None) -> bool:
    return bool(value and value.get("status") == "ready" and value.get("feature") == "nails"
                and value.get("adapter_id") == ADAPTER_ID
                and value.get("adapter_sha256") == ADAPTER_SHA256
                and value.get("base_model_id") == MODEL_ID
                and value.get("base_model_revision") == MODEL_REVISION
                and value.get("adapter_steps") == 50 and value.get("lora_active") is True
                and set(value.get("supported_styles", [])) == MODEL_STYLES)


def install_dependencies(torch_version: str) -> None:
    from importlib import metadata
    constraints = OUT / "constraints.txt"
    pins = [f"torch=={torch_version}"]
    for name in ("torchvision", "torchaudio"):
        try:
            pins.append(f"{name}=={metadata.version(name)}")
        except metadata.PackageNotFoundError:
            pass
    constraints.write_text("\n".join(pins) + "\n", encoding="utf-8")
    with (OUT / "dependency_install.log").open("w", encoding="utf-8") as log:
        subprocess.run([sys.executable, "-m", "pip", "install", "--constraint", str(constraints),
                        "-r", str(ROOT / "scripts/nails001_inference_requirements.txt")],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    check = subprocess.run([sys.executable, "-c",
                            "import json,numpy,torch,diffusers,transformers; "
                            "from diffusers import Flux2KleinPipeline; "
                            "print(json.dumps({'numpy':numpy.__version__,'torch':torch.__version__,"
                            "'diffusers':diffusers.__version__,'transformers':transformers.__version__,"
                            "'cuda':torch.version.cuda,'gpu':torch.cuda.is_available()}))"],
                           capture_output=True, text=True, timeout=600)
    (OUT / "dependency_check.log").write_text(check.stdout + check.stderr, encoding="utf-8")
    if check.returncode:
        raise RuntimeError("Nails inference dependency imports failed")
    runtime = json.loads(check.stdout.strip().splitlines()[-1])
    if (runtime["torch"] != torch_version or runtime["diffusers"] != "0.39.0.dev0"
            or runtime["transformers"] != "5.5.3" or not runtime["gpu"]):
        raise RuntimeError("Nails inference runtime differs from evaluated versions")
    save("environment.json", runtime)


def model_snapshot() -> Path:
    from huggingface_hub import snapshot_download
    if not os.environ.get("HF_TOKEN"):
        try:
            from kaggle_secrets import UserSecretsClient
            token = UserSecretsClient().get_secret("HF_TOKEN")
            if token:
                os.environ["HF_TOKEN"] = token
        except Exception:
            pass
    if shutil.disk_usage("/tmp").free < 30 * 1024**3:
        raise RuntimeError("Insufficient scratch for the pinned FLUX Base")
    path = Path(snapshot_download(repo_id=MODEL_ID, revision=MODEL_REVISION,
                cache_dir="/tmp/hf-cache/hub", allow_patterns=[
                    "model_index.json", "scheduler/*", "tokenizer/*", "text_encoder/*",
                    "transformer/*", "vae/*"])).resolve()
    if path.name != MODEL_REVISION or not (path / "model_index.json").is_file():
        raise RuntimeError("Wrong or incomplete pinned FLUX Base snapshot")
    save("model.json", {"model_id": MODEL_ID, "revision": MODEL_REVISION, "snapshot": str(path)})
    return path


def start_server(model: Path, key: str) -> None:
    local = f"http://127.0.0.1:{PORT}"
    if expected_health(health(local)):
        return
    if health(local) is not None:
        raise RuntimeError("Nails port is occupied by another service")
    env = os.environ.copy()
    env.update({"NAILS001_MODEL_DIR": str(model),
                "NAILS001_ADAPTER_PATH": str(ROOT / "adapter/nails001_local_v1.safetensors"),
                "NAILS001_API_KEY": key, "PYTHONUNBUFFERED": "1"})
    with (OUT / "server.log").open("a", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn",
                                    "scripts.nails001_local_inference_server:app", "--host", "127.0.0.1",
                                    "--port", str(PORT), "--workers", "1"],
                                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    save("server_process.json", {"pid": process.pid, "port": PORT})
    started = time.monotonic()
    while time.monotonic() - started < 900:
        if process.poll() is not None:
            raise RuntimeError(f"Nails server exited {process.returncode}; inspect server.log")
        if expected_health(health(local)):
            return
        time.sleep(3)
    raise RuntimeError("Nails model load timed out; inspect server.log")


def start_tunnel() -> str:
    binary = OUT / "cloudflared"
    if not binary.exists():
        with urlopen("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
                     timeout=90) as source, binary.open("wb") as target:
            shutil.copyfileobj(source, target)
        binary.chmod(0o700)
    with (OUT / "tunnel.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([str(binary), "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    started = time.monotonic()
    while time.monotonic() - started < 180:
        if process.poll() is not None:
            raise RuntimeError("Nails tunnel exited; inspect tunnel.log")
        log = (OUT / "tunnel.log").read_text(encoding="utf-8", errors="replace")
        match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", log)
        if match and expected_health(health(match.group(0))):
            save("endpoint.json", {"url": match.group(0), "pid": process.pid})
            return match.group(0)
        time.sleep(3)
    raise RuntimeError("Nails public health failed; inspect tunnel.log")


def main() -> None:
    stage("VERIFYING_BUNDLE")
    verify_bundle()
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["HF_HOME"] = "/tmp/hf-cache"
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("Select a Kaggle T4 GPU")
    key = os.environ.get("NAILS001_API_KEY", "")
    if not key:
        from kaggle_secrets import UserSecretsClient
        key = UserSecretsClient().get_secret("NAILS001_API_KEY")
    if len(key) < 24:
        raise RuntimeError("Enable a private NAILS001_API_KEY Kaggle Secret of at least 24 characters")
    stage("INSTALLING_PINNED_DEPENDENCIES")
    install_dependencies(torch.__version__)
    stage("DOWNLOADING_PINNED_BASE")
    model = model_snapshot()
    stage("LOADING_STEP050_ADAPTER")
    start_server(model, key)
    stage("STARTING_TUNNEL")
    url = start_tunnel()
    save("health.json", health(url))
    stage("READY")
    print("NAILS_REMOTE_URL=" + url, flush=True)
    print("NAILS_REMOTE_API_KEY=<same value as the NAILS001_API_KEY Kaggle Secret>", flush=True)
    print("No training was run.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        stage("FAILED")
        print(f"NAILS SETUP FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
