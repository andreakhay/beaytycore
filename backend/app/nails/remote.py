"""Authenticated client for the isolated step-50 Nails GPU service."""

import base64
import binascii
from io import BytesIO

import httpx
from PIL import Image, UnidentifiedImageError

from app.nails.contract import (ADAPTER_ID, ADAPTER_SHA256, GENERATOR, GUIDANCE,
                                MODEL_ID, MODEL_REVISION, MODEL_STYLES, SEED, STEPS)
from app.nails.styles import NailStyle
from app.nails.inference_options import validate_steps


class NailsGenerationError(Exception):
    pass


class RemoteLocalizedNails:
    def __init__(self, url: str, api_key: str, timeout_seconds: float = 300, inference_steps: int = STEPS):
        self.url, self.api_key, self.timeout_seconds = url.rstrip("/"), api_key, timeout_seconds
        self.inference_steps = validate_steps(inference_steps)
        self._steps_verified = self.inference_steps == STEPS
        if not self.url.startswith("https://") or len(api_key) < 24:
            raise RuntimeError("Nails GPU needs an HTTPS URL and a shared key of at least 24 characters")

    async def _verify_step_support(self, client):
        if self._steps_verified:
            return
        root = self.url.removesuffix("/nails")
        response = await client.get(f"{root}/health", timeout=min(10, self.timeout_seconds))
        try:
            supported = response.json().get("nails_inference_steps")
            if response.status_code != 200 or not isinstance(supported, list) or self.inference_steps not in supported:
                raise ValueError("Unsupported steps")
        except (ValueError, TypeError, AttributeError):
            raise NailsGenerationError("Update the unified Kaggle worker for faster Nails inference, or use 20 steps.") from None
        self._steps_verified = True

    async def generate(self, image: Image.Image, style: NailStyle) -> Image.Image:
        if style.id not in MODEL_STYLES or image.size != (512, 512):
            raise NailsGenerationError("Unsupported localized Nails inference request")
        stream = BytesIO()
        image.convert("RGB").save(stream, "PNG")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
                await self._verify_step_support(client)
                fields = {"style_id": style.id}
                if self.inference_steps != STEPS:
                    fields["inference_steps"] = str(self.inference_steps)
                response = await client.post(
                    f"{self.url}/generate", data=fields,
                    files={"image": ("nail.png", stream.getvalue(), "image/png")},
                    headers={"X-API-Key": self.api_key})
        except httpx.RequestError as exc:
            raise NailsGenerationError("The Nails GPU service is unavailable or timed out. Please try again.") from exc
        if response.status_code != 200:
            messages = {401: "The Nails GPU key does not match.",
                        429: "The Nails GPU is busy. Please try again.",
                        503: "The Nails GPU model is not ready. Please try again."}
            raise NailsGenerationError(messages.get(response.status_code,
                                       f"Nails GPU inference failed (HTTP {response.status_code})."))
        try:
            payload = response.json()
            metadata, item = payload["metadata"], payload["image"]
            expected = {"feature": "nails", "style_id": style.id, "adapter_id": ADAPTER_ID,
                        "adapter_sha256": ADAPTER_SHA256, "adapter_steps": 50,
                        "base_model_id": MODEL_ID, "base_model_revision": MODEL_REVISION,
                        "lora_active": True, "seed": SEED, "steps": self.inference_steps, "guidance": GUIDANCE}
            if payload.get("status") != "completed" or payload.get("generator") != GENERATOR:
                raise ValueError("Wrong Nails GPU response")
            if any(metadata.get(key) != value for key, value in expected.items()):
                raise ValueError("Wrong Nails model or inference settings")
            if (item["content_type"] != "image/png" or (item["width"], item["height"]) != (512, 512)
                    or not item["data_url"].startswith("data:image/png;base64,")
                    or len(item["data_url"]) > 24 * 1024 * 1024):
                raise ValueError("Invalid Nails image metadata")
            content = base64.b64decode(item["data_url"].split(",", 1)[1], validate=True)
            if len(content) > 16 * 1024 * 1024:
                raise ValueError("Nails result too large")
            with Image.open(BytesIO(content)) as decoded:
                if decoded.format != "PNG" or decoded.size != (512, 512):
                    raise ValueError("Nails result dimensions differ")
                decoded.load()
                result = decoded.convert("RGB")
                result.info["inference_steps"] = self.inference_steps
                runtime = metadata.get("runtime_seconds")
                if isinstance(runtime, (int, float)) and runtime >= 0:
                    result.info["runtime_seconds"] = runtime
                return result
        except (KeyError, AttributeError, TypeError, ValueError, binascii.Error, UnidentifiedImageError, OSError) as exc:
            raise NailsGenerationError("The Nails GPU returned an invalid image or model response.") from exc
