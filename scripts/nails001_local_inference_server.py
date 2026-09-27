"""Isolated single-adapter GPU service for two selected NAILS-001 styles."""

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

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.nails.contract import (ADAPTER_ID, ADAPTER_SHA256, GENERATOR, GUIDANCE, MODEL_ID,
                                MODEL_REVISION, MODEL_STYLES, PROMPTS, SEED, STEPS, verify_adapter)

LOGGER = logging.getLogger("nails001.local.inference")


class NailsRuntime:
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
        adapter = Path(os.environ["NAILS001_ADAPTER_PATH"])
        model = Path(os.environ["NAILS001_MODEL_DIR"])
        verify_adapter(adapter)
        if model.name != MODEL_REVISION or not (model / "model_index.json").is_file():
            raise RuntimeError("Nails Base snapshot is not the pinned revision")
        if len(os.environ.get("NAILS001_API_KEY", "")) < 24:
            raise RuntimeError("NAILS001_API_KEY must be at least 24 characters")
        started = time.monotonic()
        pipe = Flux2KleinPipeline.from_pretrained(
            str(model), torch_dtype=torch.float16, local_files_only=True)
        pipe.enable_model_cpu_offload(gpu_id=0)
        pipe.load_lora_weights(str(adapter.parent), weight_name=adapter.name)
        self.pipe, self.torch = pipe, torch
        self.load_seconds = round(time.monotonic() - started, 2)
        self.ready = True
        LOGGER.info("Verified Nails step-50 adapter loaded in %.1f seconds", self.load_seconds)

    def generate(self, reference: Image.Image, style_id: str):
        started = time.monotonic()
        result = self.pipe(prompt=PROMPTS[style_id], image=reference, width=512, height=512,
                           num_inference_steps=STEPS, guidance_scale=GUIDANCE,
                           generator=self.torch.Generator(device="cuda").manual_seed(SEED)).images[0]
        output = BytesIO()
        result.convert("RGB").save(output, "PNG")
        return {"status": "completed", "generator": GENERATOR,
                "image": {"data_url": "data:image/png;base64," + base64.b64encode(output.getvalue()).decode(),
                          "content_type": "image/png", "width": 512, "height": 512},
                "metadata": {"feature": "nails", "style_id": style_id, "adapter_id": ADAPTER_ID,
                             "adapter_sha256": ADAPTER_SHA256, "adapter_steps": 50,
                             "base_model_id": MODEL_ID, "base_model_revision": MODEL_REVISION,
                             "lora_active": True, "seed": SEED, "steps": STEPS,
                             "guidance": GUIDANCE, "prompt": PROMPTS[style_id],
                             "runtime_seconds": round(time.monotonic() - started, 2)}}


runtime = NailsRuntime()


@asynccontextmanager
async def lifespan(_app):
    runtime.load()
    yield
    runtime.ready = False


app = FastAPI(title="NAILS-001 localized inference", docs_url=None,
              redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ready" if runtime.ready else "starting", "feature": "nails",
            "generator": GENERATOR, "adapter_id": ADAPTER_ID,
            "adapter_sha256": ADAPTER_SHA256 if runtime.ready else None,
            "base_model_id": MODEL_ID, "base_model_revision": MODEL_REVISION,
            "lora_active": runtime.ready, "adapter_steps": 50,
            "supported_styles": sorted(MODEL_STYLES), "load_seconds": runtime.load_seconds}


@app.post("/generate")
async def generate(image: Annotated[UploadFile, File()], style_id: Annotated[str, Form()],
                   x_api_key: Annotated[str | None, Header()] = None):
    key = os.environ.get("NAILS001_API_KEY", "")
    if len(key) < 24 or not x_api_key or not secrets.compare_digest(key, x_api_key):
        raise HTTPException(401, "Invalid Nails API key")
    if style_id not in MODEL_STYLES:
        raise HTTPException(400, "Unsupported Nails model style")
    if not runtime.ready:
        raise HTTPException(503, "Nails GPU model is not ready")
    if image.content_type != "image/png":
        raise HTTPException(415, "Expected a localized PNG")
    content = await image.read(8 * 1024 * 1024 + 1)
    if not content or len(content) > 8 * 1024 * 1024:
        raise HTTPException(413, "Localized image is empty or too large")
    try:
        with Image.open(BytesIO(content)) as opened:
            if opened.format != "PNG" or opened.size != (512, 512):
                raise ValueError("Wrong localized crop")
            reference = opened.convert("RGB")
    except (OSError, ValueError):
        raise HTTPException(400, "Invalid localized crop") from None
    if runtime.lock.locked():
        raise HTTPException(429, "Nails GPU is busy")
    async with runtime.lock:
        task = asyncio.create_task(asyncio.to_thread(runtime.generate, reference, style_id))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            try:
                await task
            finally:
                raise
        except Exception:
            LOGGER.exception("Nails inference failed")
            raise HTTPException(500, "Nails inference failed. Check its GPU log") from None
