"""Isolated single-adapter MAKEUP-001 GPU service, never imports Hair runtime."""

import asyncio
import base64
from contextlib import asynccontextmanager
from io import BytesIO
import logging
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Annotated
import warnings

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.makeup_contract import (ADAPTER_ID, ADAPTER_SHA256, GENERATOR, INFERENCE, MODEL_ID,
                                 MODEL_REVISION, PRESETS_SHA256, PROMPTS, verify_adapter)

LOGGER = logging.getLogger("makeup001.inference")
Image.MAX_IMAGE_PIXELS = 16_777_216


class MakeupRuntime:
    def __init__(self):
        self.ready = False
        self.pipe = None
        self.torch = None
        self.lock = asyncio.Lock()
        self.load_seconds = None

    def load(self):
        import torch
        from diffusers import Flux2KleinPipeline
        if not torch.cuda.is_available():
            raise RuntimeError("Select a Kaggle GPU accelerator")
        adapter = Path(os.environ["MAKEUP001_ADAPTER_DIR"])
        model = Path(os.environ["MAKEUP001_MODEL_DIR"])
        verify_adapter(adapter)
        if model.name != MODEL_REVISION:
            raise RuntimeError("Makeup Base snapshot is not the pinned revision")
        if len(os.environ.get("MAKEUP001_API_KEY", "")) < 24:
            raise RuntimeError("MAKEUP001_API_KEY must contain at least 24 characters")
        started = time.monotonic()
        pipe = Flux2KleinPipeline.from_pretrained(str(model), torch_dtype=torch.float16, local_files_only=True)
        pipe.enable_model_cpu_offload(gpu_id=0)
        pipe.load_lora_weights(str(adapter), weight_name="adapter.safetensors")
        self.pipe, self.torch = pipe, torch
        self.load_seconds = round(time.monotonic() - started, 2)
        self.ready = True
        LOGGER.info("Verified MAKEUP-001 loaded in %.1f seconds", self.load_seconds)

    def generate(self, portrait: Image.Image, style_id: str) -> dict:
        source = ImageOps.pad(portrait, (512, 512), method=Image.Resampling.LANCZOS, color=(245, 245, 245))
        started = time.monotonic()
        try:
            self.torch.cuda.reset_peak_memory_stats(0)
        except RuntimeError:
            LOGGER.warning("CUDA peak memory reset unavailable; continuing Makeup generation")
        result = self.pipe(prompt=PROMPTS[style_id], image=source, width=512, height=512,
                           num_inference_steps=20, guidance_scale=4.0,
                           generator=self.torch.Generator(device="cuda").manual_seed(1977)).images[0]
        try:
            peak_gpu_mib = round(self.torch.cuda.max_memory_allocated(0) / 1024**2, 1)
        except RuntimeError:
            peak_gpu_mib = None
        stream = BytesIO()
        result.convert("RGB").save(stream, format="PNG")
        return {"status": "completed", "generator": GENERATOR,
                "image": {"data_url": "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii"),
                          "content_type": "image/png", "width": result.width, "height": result.height},
                "metadata": {"feature": "makeup", "style_id": style_id, "adapter_id": ADAPTER_ID,
                             "adapter_sha256": ADAPTER_SHA256, "adapter_steps": 250, "lora_active": True,
                             "base_model_id": MODEL_ID, "base_model_revision": MODEL_REVISION,
                             "prompt_presets_sha256": PRESETS_SHA256, "prompt": PROMPTS[style_id],
                             "seed": 1977, "steps": 20, "guidance": 4.0,
                             "preprocessing": "aspect-preserving pad to 512x512",
                             "runtime_seconds": round(time.monotonic() - started, 2),
                             "peak_gpu_mib": peak_gpu_mib}}


runtime = MakeupRuntime()


@asynccontextmanager
async def lifespan(_app):
    runtime.load()
    yield
    runtime.ready = False


app = FastAPI(title="MAKEUP-001 isolated inference", docs_url=None, redoc_url=None,
              openapi_url=None, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ready" if runtime.ready else "starting", "feature": "makeup",
            "generator": GENERATOR, "adapter_id": ADAPTER_ID,
            "adapter_sha256": ADAPTER_SHA256 if runtime.ready else None,
            "base_model_id": MODEL_ID, "base_model_revision": MODEL_REVISION,
            "lora_active": runtime.ready, "adapter_steps": 250,
            "prompt_presets_sha256": PRESETS_SHA256, "supported_styles": list(PROMPTS),
            "load_seconds": runtime.load_seconds}


async def validated_portrait(upload: UploadFile):
    expected = {"JPEG": "image/jpeg", "PNG": "image/png"}
    if upload.content_type not in expected.values():
        raise HTTPException(415, "Upload a JPG or PNG portrait.")
    data = await upload.read(8 * 1024 * 1024 + 1)
    if not data:
        raise HTTPException(400, "Image is empty.")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Image must be 8 MB or smaller.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if expected.get(source.format) != upload.content_type:
                    raise HTTPException(415, "Image type does not match its content.")
                if not (64 <= source.width <= 4096 and 64 <= source.height <= 4096):
                    raise HTTPException(422, "Image dimensions must be 64 to 4096 pixels.")
                source.load()
                return ImageOps.exif_transpose(source).convert("RGB")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(400, "The uploaded portrait cannot be read.") from None


@app.post("/generate")
async def generate(image: Annotated[UploadFile, File()], style_id: Annotated[str, Form()],
                   x_api_key: Annotated[str | None, Header()] = None):
    key = os.environ.get("MAKEUP001_API_KEY", "")
    if len(key) < 24 or not x_api_key or not secrets.compare_digest(key, x_api_key):
        raise HTTPException(401, "Invalid Makeup API key.")
    if style_id not in PROMPTS:
        raise HTTPException(400, "Unsupported Makeup preset.")
    if not runtime.ready:
        raise HTTPException(503, "Makeup GPU is not ready.")
    portrait = await validated_portrait(image)
    if runtime.lock.locked():
        raise HTTPException(429, "Makeup GPU is busy. Try again after the current request finishes.")
    async with runtime.lock:
        task = asyncio.create_task(asyncio.to_thread(runtime.generate, portrait, style_id))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # Do not release the GPU lock while a disconnected request is still computing.
            try:
                await task
            finally:
                raise
        except Exception:
            LOGGER.exception("Makeup inference failed")
            raise HTTPException(500, "Makeup inference failed. Check its Kaggle log.") from None
