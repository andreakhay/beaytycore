"""Run exactly three sequential localhost requests to verify adapter restoration."""

import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import time
from zipfile import ZipFile

import httpx
from PIL import Image


BASE = "http://127.0.0.1:8765"
OUTPUT = Path("/kaggle/working/train002_switch_smoke")
PORTRAIT = Path(__file__).resolve().parents[1] / "frontend/e2e/fixtures/portrait.png"
EXPECTED = {
    "train001": "7e3991f8a4e502573d3e82e9ac34c89fdf3f0b66fb337abb026a5b4c9ad080ff",
    "train002": "59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b",
}
REQUESTS = (("crew_cut", "train001"), ("pixie_cut", "train002"), ("crew_cut", "train001"))


def api_key() -> str:
    key = os.environ.get("HAIRCAPSTONE_API_KEY", "")
    if not key:
        from kaggle_secrets import UserSecretsClient
        key = UserSecretsClient().get_secret("HAIRCAPSTONE_API_KEY") or ""
    if len(key) < 24:
        raise RuntimeError("Enable the existing HAIRCAPSTONE_API_KEY Kaggle Secret")
    return key


def main() -> None:
    if not PORTRAIT.is_file():
        raise RuntimeError(f"Smoke portrait is missing: {PORTRAIT}")
    key = api_key()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = []
    with httpx.Client(timeout=240, follow_redirects=False) as client:
        initial = client.get(BASE + "/health")
        initial.raise_for_status()
        health = initial.json()
        if health.get("status") != "ready" or health.get("available_adapters") != EXPECTED:
            raise RuntimeError(f"Both verified adapters are not ready: {health}")
        if health.get("active_adapter") != "train001":
            raise RuntimeError("Smoke must start on the TRAIN-001 fallback")
        for index, (style, adapter) in enumerate(REQUESTS, 1):
            started = time.monotonic()
            with PORTRAIT.open("rb") as image:
                response = client.post(BASE + "/generate", data={"style_id": style},
                                       files={"image": (PORTRAIT.name, image, "image/png")},
                                       headers={"X-API-Key": key})
            if response.status_code != 200:
                raise RuntimeError(f"Request {index} failed ({response.status_code}); inspect GPU server.log")
            payload = response.json()
            metadata = payload.get("metadata") or {}
            if (metadata.get("adapter_id") != adapter or metadata.get("style_id") != style
                    or metadata.get("adapter_sha256") != EXPECTED[adapter]):
                raise RuntimeError(f"Request {index} used the wrong adapter or style: {metadata}")
            data_url = payload["image"]["data_url"]
            if not data_url.startswith("data:image/png;base64,"):
                raise RuntimeError(f"Request {index} did not return a PNG")
            content = base64.b64decode(data_url.split(",", 1)[1], validate=True)
            with Image.open(BytesIO(content)) as result:
                result.load()
                if result.size != (512, 512) or result.mode != "RGB":
                    raise RuntimeError(f"Request {index} image is not 512×512 RGB")
            dest = OUTPUT / f"{index}_{adapter}_{style}.png"
            dest.write_bytes(content)
            check = client.get(BASE + "/health")
            check.raise_for_status()
            after = check.json()
            if after.get("active_adapter") != adapter or after.get("status") != "ready":
                raise RuntimeError(f"Request {index} did not leave the expected active adapter: {after}")
            record = {"request": index, "style_id": style, "adapter_id": adapter,
                      "adapter_sha256": EXPECTED[adapter], "seconds": round(time.monotonic() - started, 2),
                      "image_sha256": hashlib.sha256(content).hexdigest(), "image": str(dest),
                      "peak_gpu_mib": metadata.get("peak_gpu_mib")}
            results.append(record)
            print(json.dumps(record), flush=True)
    report = {"status": "PASS", "sequence": "TRAIN-001 -> TRAIN-002 -> TRAIN-001",
              "final_active_adapter": "train001", "results": results}
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    archive = OUTPUT.with_suffix(".zip")
    with ZipFile(archive, "w") as bundle:
        for path in sorted(OUTPUT.iterdir()):
            if path.is_file():
                bundle.write(path, path.name)
    print("TRAIN-002 SWITCH SMOKE PASS", OUTPUT / "report.json", flush=True)
    print("DOWNLOAD", archive, flush=True)


if __name__ == "__main__":
    main()
