"""Makeup HTTP client. No Hair registry, adapter selection or switching."""

import base64
from io import BytesIO
import os

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from app.generation.base import GeneratedImage
from app.makeup_contract import ADAPTER_ID, ADAPTER_SHA256, GENERATOR, MODEL_ID, MODEL_REVISION, PRESETS_SHA256, PROMPTS
from app.makeup_styles import MakeupStyle


class MakeupGenerationError(Exception):
    pass


class RemoteMakeupEngine:
    name = GENERATOR

    def __init__(self, url: str, api_key: str, timeout_seconds: float = 180):
        self.url, self.api_key, self.timeout_seconds = url.rstrip("/"), api_key, timeout_seconds
        if not self.url.startswith("https://") or len(api_key) < 24:
            raise RuntimeError("Remote Makeup requires MAKEUP_REMOTE_URL (HTTPS) and MAKEUP_REMOTE_API_KEY (at least 24 characters).")

    async def generate(self, image: Image.Image, style: MakeupStyle) -> GeneratedImage:
        if style.id not in PROMPTS:
            raise MakeupGenerationError("This style is not a Makeup inference preset.")
        buffer = BytesIO()
        ImageOps.pad(image, (512, 512), method=Image.Resampling.LANCZOS,
                     color=(245, 245, 245)).save(buffer, format="PNG")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = await client.post(
                    f"{self.url}/generate", data={"style_id": style.id},
                    files={"image": ("portrait.png", buffer.getvalue(), "image/png")},
                    headers={"X-API-Key": self.api_key},
                )
        except httpx.RequestError as exc:
            raise MakeupGenerationError("The Makeup GPU service is unavailable or timed out. Check its active Kaggle session and tunnel URL.") from exc
        messages = {401: "The Makeup GPU API key does not match.",
                    429: "The Makeup GPU is busy. Wait for the current request to finish.",
                    503: "The Makeup GPU model is not ready. Check its server log."}
        if response.status_code != 200:
            raise MakeupGenerationError(messages.get(response.status_code, f"Makeup GPU generation failed (HTTP {response.status_code})."))
        try:
            payload = response.json()
            item, metadata = payload["image"], payload["metadata"]
            required = {"feature": "makeup", "adapter_id": ADAPTER_ID, "adapter_sha256": ADAPTER_SHA256,
                        "base_model_id": MODEL_ID, "base_model_revision": MODEL_REVISION,
                        "prompt_presets_sha256": PRESETS_SHA256, "style_id": style.id,
                        "lora_active": True}
            if (payload.get("status") != "completed" or payload.get("generator") != GENERATOR
                    or any(metadata.get(key) != value for key, value in required.items())):
                raise ValueError("Wrong Makeup model or preset")
            data_url = item["data_url"]
            if (item["content_type"] != "image/png" or (item["width"], item["height"]) != (512, 512)
                    or not data_url.startswith("data:image/png;base64,") or len(data_url) > 24 * 1024 * 1024):
                raise ValueError("Invalid remote image metadata")
            content = base64.b64decode(data_url.split(",", 1)[1], validate=True)
            if len(content) > 16 * 1024 * 1024:
                raise ValueError("Remote image too large")
            with Image.open(BytesIO(content)) as decoded:
                if decoded.format != "PNG" or decoded.size != (512, 512):
                    raise ValueError("Remote image mismatch")
                decoded.verify()
            return GeneratedImage(content, "image/png", 512, 512, metadata)
        except (KeyError, AttributeError, TypeError, ValueError, UnidentifiedImageError, OSError) as exc:
            raise MakeupGenerationError("The Makeup GPU returned an invalid image or model response.") from exc


def configured_makeup_engine():
    from app.generation.mock import MockEngine
    mode = os.getenv("MAKEUP_GENERATION_ENGINE", "mock").strip().lower()
    if mode == "mock":
        return MockEngine()
    if mode == "remote_makeup":
        from app.generation.remote_destination import destination

        return RemoteMakeupEngine(*destination("makeup", "MAKEUP_REMOTE_URL", "MAKEUP_REMOTE_API_KEY"))
    raise RuntimeError(f"Unsupported MAKEUP_GENERATION_ENGINE: {mode}")
