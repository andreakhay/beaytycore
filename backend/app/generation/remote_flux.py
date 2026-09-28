"""Local HTTP adapter for the temporary Kaggle GPU service."""

import base64
from io import BytesIO
import os

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from app.generation.base import GeneratedImage
from app.styles import Style
from app.styles import REAL_STYLE_BY_ID


class RemoteGenerationError(Exception):
    pass


class RemoteFluxEngine:
    name = "remote_flux"

    def __init__(self, url: str, api_key: str, timeout_seconds: float = 180):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        if not self.url.startswith("https://") or not self.api_key:
            raise RuntimeError("Remote FLUX needs an HTTPS FLUX_REMOTE_URL and FLUX_REMOTE_API_KEY.")

    async def generate(self, image: Image.Image, style: Style) -> GeneratedImage:
        if style.id not in REAL_STYLE_BY_ID:
            raise RemoteGenerationError("This hairstyle is not supported by the trained adapter.")
        buffer = BytesIO()
        normalized = ImageOps.pad(image, (512, 512), method=Image.Resampling.LANCZOS,
                                  color=(245, 245, 245), centering=(0.5, 0.5))
        normalized.save(buffer, format="PNG")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = await client.post(
                    f"{self.url}/generate",
                    data={"style_id": style.id},
                    files={"image": ("portrait.png", buffer.getvalue(), "image/png")},
                    headers={"X-API-Key": self.api_key},
                )
        except httpx.RequestError as exc:
            raise RemoteGenerationError("The Kaggle GPU endpoint is unavailable or timed out. Check the active session and tunnel URL.") from exc
        if response.status_code == 401:
            raise RemoteGenerationError("The Kaggle GPU API key does not match.")
        if response.status_code == 503:
            raise RemoteGenerationError("The Kaggle GPU model is not ready. Check its server log.")
        if response.status_code == 429:
            raise RemoteGenerationError("The Kaggle GPU is busy. Wait for the current request to finish.")
        if response.status_code != 200:
            raise RemoteGenerationError(f"Kaggle generation failed (HTTP {response.status_code}). Check its server log.")
        try:
            payload = response.json()
            item = payload["image"]
            metadata = payload.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValueError("invalid remote metadata")
            if item["content_type"] != "image/png":
                raise ValueError("unexpected content type")
            data_url = item["data_url"]
            if not data_url.startswith("data:image/png;base64,"):
                raise ValueError("invalid image data URL")
            content = base64.b64decode(data_url.split(",", 1)[1], validate=True)
            if len(content) > 16 * 1024 * 1024:
                raise ValueError("remote image too large")
            with Image.open(BytesIO(content)) as decoded:
                decoded.verify()
            with Image.open(BytesIO(content)) as decoded:
                if decoded.format != "PNG" or decoded.size != (item["width"], item["height"]):
                    raise ValueError("remote image metadata mismatch")
            return GeneratedImage(content, "image/png", item["width"], item["height"], metadata)
        except (KeyError, AttributeError, TypeError, ValueError, UnidentifiedImageError, OSError) as exc:
            raise RemoteGenerationError("The Kaggle GPU endpoint returned an invalid image response.") from exc


def from_environment() -> RemoteFluxEngine:
    from app.generation.remote_destination import destination

    return RemoteFluxEngine(*destination("hairstyle", "FLUX_REMOTE_URL", "FLUX_REMOTE_API_KEY"))
