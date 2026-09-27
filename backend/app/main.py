"""Application API for Hairstyle, Makeup, and Nails."""

import base64
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
import os
import time
from pathlib import Path
import warnings
from io import BytesIO
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.generation.base import GenerationEngine
from app.generation.mock import MockEngine
from app.generation.remote_flux import RemoteFluxEngine, RemoteGenerationError, from_environment
from app.styles import STYLE_BY_ID, STYLES, REAL_STYLE_BY_ID, REAL_STYLES, Style
from app.makeup_styles import MAKEUP_STYLE_BY_ID, MAKEUP_STYLES
from app.generation.remote_makeup import MakeupGenerationError, RemoteMakeupEngine, configured_makeup_engine
from app.nails.styles import NAIL_STYLE_BY_ID, NAIL_STYLES
from app.nails.contract import MODEL_STYLES
from app.nails.geometry import MediaPipeHandLocalizer, UnusableHand
from app.nails.hybrid import HybridNailsPipeline
from app.nails.remote import NailsGenerationError, RemoteLocalizedNails
from app.nails.segmentation import IsolatedYoloNailSegmenter


MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_777_216
MIN_DIMENSION = 64
MAX_DIMENSION = 4096
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png"}
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def configured_engine() -> GenerationEngine:
    mode = os.getenv("GENERATION_ENGINE", os.getenv("GENERATOR_MODE", "mock")).strip().lower()
    if mode == "mock":
        return MockEngine()
    if mode == "remote_flux":
        return from_environment()
    raise RuntimeError(f"Unsupported GENERATION_ENGINE: {mode}.")


engine = configured_engine()
makeup_engine = configured_makeup_engine()
app = FastAPI(title="HAIR CAPSTONE API", version="0.1.0", openapi_url=None, docs_url=None, redoc_url=None)
origins = [origin.strip() for origin in os.getenv(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class StyleResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str


class ImageResponse(BaseModel):
    data_url: str
    content_type: str
    width: int
    height: int


class GenerateResponse(BaseModel):
    status: str
    generator: str
    style: StyleResponse
    image: ImageResponse
    metadata: dict = Field(default_factory=dict)


class FeatureResponse(BaseModel):
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class FeatureRoute:
    info: FeatureResponse
    styles: Callable[[], Awaitable[list[StyleResponse]]]
    generate: Callable[[UploadFile, str], Awaitable[GenerateResponse]]


def style_response(style: Style) -> StyleResponse:
    return StyleResponse(**vars(style))


async def validated_image(upload: UploadFile) -> Image.Image:
    if upload.content_type not in ALLOWED_FORMATS.values():
        raise HTTPException(status_code=415, detail="Please upload a JPG or PNG image.")

    content = await upload.read(MAX_FILE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The image file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format not in ALLOWED_FORMATS:
                    raise HTTPException(status_code=415, detail="Please upload a JPG or PNG image.")
                if ALLOWED_FORMATS[source.format] != upload.content_type:
                    raise HTTPException(status_code=415, detail="The image type does not match the file.")
                width, height = source.size
                if not (MIN_DIMENSION <= width <= MAX_DIMENSION and MIN_DIMENSION <= height <= MAX_DIMENSION):
                    raise HTTPException(
                        status_code=422,
                        detail="Image width and height must each be between 64 and 4096 pixels.",
                    )
                if width * height > MAX_IMAGE_PIXELS:
                    raise HTTPException(status_code=422, detail="Image dimensions are too large.")
                source.load()
                return ImageOps.exif_transpose(source).convert("RGB")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a readable image.") from None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "generator": engine.name}


@app.get("/styles", response_model=list[StyleResponse])
async def styles() -> list[StyleResponse]:
    catalog = REAL_STYLES if isinstance(engine, RemoteFluxEngine) else STYLES
    return [style_response(style) for style in catalog]


@app.get("/makeup/styles", response_model=list[StyleResponse])
async def makeup_styles() -> list[StyleResponse]:
    return [StyleResponse(id=style.id, name=style.name, description=style.description,
                          status="trained_preset" if isinstance(makeup_engine, RemoteMakeupEngine) else style.status)
            for style in MAKEUP_STYLES]


@app.get("/makeup/health")
async def makeup_health() -> dict:
    return {"status": "configured" if isinstance(makeup_engine, RemoteMakeupEngine) else "mock",
            "generator": makeup_engine.name, "feature": "makeup"}


@app.post("/makeup/generate", response_model=GenerateResponse)
async def generate_makeup(
    image: Annotated[UploadFile, File()],
    style_id: Annotated[str, Form()],
) -> GenerateResponse:
    style = MAKEUP_STYLE_BY_ID.get(style_id)
    if style is None:
        raise HTTPException(status_code=400, detail="Please choose a valid makeup style.")
    portrait = await validated_image(image)
    try:
        preview = await makeup_engine.generate(portrait, style)
    except MakeupGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except Exception:
        raise HTTPException(status_code=500, detail="Makeup generation failed. Please try again.") from None
    live = isinstance(makeup_engine, RemoteMakeupEngine)
    encoded = base64.b64encode(preview.content).decode("ascii")
    return GenerateResponse(
        status="completed" if live else "placeholder", generator=makeup_engine.name if live else "makeup_mock",
        style=StyleResponse(id=style.id, name=style.name, description=style.description,
                            status="trained_preset" if live else style.status),
        image=ImageResponse(data_url=f"data:{preview.content_type};base64,{encoded}",
                            content_type=preview.content_type, width=preview.width, height=preview.height),
        metadata=preview.metadata if live else {"feature": "makeup", "model_status": "not_connected"},
    )


@app.get("/nails/styles", response_model=list[StyleResponse])
async def nail_styles() -> list[StyleResponse]:
    live = os.getenv("NAILS_PREVIEW_MODE", "mock").strip().lower() == "hybrid"
    return [StyleResponse(id=style.id, name=style.name, description=style.description,
                          status="available" if live else style.status) for style in NAIL_STYLES]


def configured_nails_pipeline() -> HybridNailsPipeline:
    root = Path(__file__).resolve().parents[2]
    landmark = Path(os.getenv("NAILS_HAND_LANDMARKER_PATH", str(
        root / "data/nails/checkpoints/mediapipe/hand_landmarker.task")))
    segment_python = Path(os.getenv("NAILS_SEGMENT_PYTHON", str(
        root / "data/nails/work/seg-venv/Scripts/python.exe")))
    segment_checkpoint = Path(os.getenv("NAILS_SEGMENT_CHECKPOINT", str(
        root / "data/nails/checkpoints/mnemic/nails_seg_s_yolov8_v1.pt")))
    segment_script = root / "scripts/nails_segment_once.py"
    localizer = MediaPipeHandLocalizer(landmark)
    segmenter = IsolatedYoloNailSegmenter(segment_python, segment_checkpoint, segment_script)
    url, key = os.getenv("NAILS_REMOTE_URL", ""), os.getenv("NAILS_REMOTE_API_KEY", "")
    model = RemoteLocalizedNails(url, key) if url or key else None
    return HybridNailsPipeline(localizer, segmenter, model)


_nails_pipeline: HybridNailsPipeline | None = None


def nails_pipeline() -> HybridNailsPipeline:
    global _nails_pipeline
    if _nails_pipeline is None:
        _nails_pipeline = configured_nails_pipeline()
    return _nails_pipeline


@app.post("/nails/generate", response_model=GenerateResponse)
async def generate_nails(
    image: Annotated[UploadFile, File()],
    style_id: Annotated[str, Form()],
) -> GenerateResponse:
    request_started = time.monotonic()
    style = NAIL_STYLE_BY_ID.get(style_id)
    if style is None:
        raise HTTPException(status_code=400, detail="Please choose a valid nail style.")
    photo = await validated_image(image)
    validation_seconds = time.monotonic() - request_started
    mode = os.getenv("NAILS_PREVIEW_MODE", "mock").strip().lower()
    if mode == "hybrid":
        try:
            result = await nails_pipeline().run(photo, style)
        except UnusableHand as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        except NailsGenerationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from None
        except (FileNotFoundError, RuntimeError):
            logging.getLogger(__name__).exception("Nails service is unavailable")
            raise HTTPException(status_code=503, detail="Nails service is unavailable. Please try again later.") from None
        except Exception:
            raise HTTPException(status_code=500, detail="Nails generation failed. Please try again.") from None
        output = BytesIO()
        result.image.save(output, format="PNG")
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        metadata = {"feature": "nails", "inference_path": result.path,
                    "nails_edited": result.nail_count,
                    "model_seconds": result.model_seconds,
                    "renderer_seconds": result.renderer_seconds,
                    "compositing": "original_nail_mask"}
        metadata["timing_seconds"] = {"image_validation": round(validation_seconds, 3),
                                      **(result.phase_seconds or {})}
        if style.id in MODEL_STYLES:
            from app.nails.contract import ADAPTER_ID, ADAPTER_SHA256
            metadata.update({"adapter_id": ADAPTER_ID, "adapter_sha256": ADAPTER_SHA256})
        metadata["timing_seconds"]["total_request"] = round(time.monotonic() - request_started, 3)
        return GenerateResponse(
            status="completed", generator="nails_hybrid",
            style=StyleResponse(id=style.id, name=style.name, description=style.description,
                                status="available"),
            image=ImageResponse(data_url=f"data:image/png;base64,{encoded}", content_type="image/png",
                                width=result.image.width, height=result.image.height),
            metadata=metadata)
    if mode != "mock":
        raise HTTPException(status_code=503, detail="Nails service mode is not configured.")
    preview = await MockEngine().generate(photo, style)
    encoded = base64.b64encode(preview.content).decode("ascii")
    return GenerateResponse(
        status="placeholder", generator="nails_mock",
        style=StyleResponse(id=style.id, name=style.name, description=style.description, status=style.status),
        image=ImageResponse(data_url=f"data:{preview.content_type};base64,{encoded}",
                            content_type=preview.content_type, width=preview.width, height=preview.height),
        metadata={"feature": "nails", "model_status": "not_connected", "adapter_id": style.adapter_id},
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(
    image: Annotated[UploadFile, File()],
    style_id: Annotated[str, Form()],
) -> GenerateResponse:
    catalog = REAL_STYLE_BY_ID if isinstance(engine, RemoteFluxEngine) else STYLE_BY_ID
    style = catalog.get(style_id)
    if style is None:
        raise HTTPException(status_code=400, detail="Please choose a valid hairstyle.")

    portrait = await validated_image(image)
    try:
        generated = await engine.generate(portrait, style)
    except RemoteGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except Exception:
        raise HTTPException(status_code=500, detail="Generation failed. Please try again.") from None
    encoded = base64.b64encode(generated.content).decode("ascii")
    return GenerateResponse(
        status="completed",
        generator=engine.name,
        style=style_response(style),
        image=ImageResponse(
            data_url=f"data:{generated.content_type};base64,{encoded}",
            content_type=generated.content_type,
            width=generated.width,
            height=generated.height,
        ),
        metadata=generated.metadata,
    )


# The feature catalog coordinates existing handlers. Each handler retains its own
# style validation, image processing, inference client, and result semantics.
FEATURE_ROUTES: dict[str, FeatureRoute] = {
    "hairstyle": FeatureRoute(
        FeatureResponse(id="hairstyle", name="Hairstyle", description="Try a hairstyle on a portrait."),
        styles, generate,
    ),
    "makeup": FeatureRoute(
        FeatureResponse(id="makeup", name="Makeup", description="Try a makeup look on a portrait."),
        makeup_styles, generate_makeup,
    ),
    "nails": FeatureRoute(
        FeatureResponse(id="nails", name="Nails", description="Try a nail style on a hand photo."),
        nail_styles, generate_nails,
    ),
}


def feature_route(feature_id: str) -> FeatureRoute:
    feature = FEATURE_ROUTES.get(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Unknown feature.")
    return feature


@app.get("/features", response_model=list[FeatureResponse])
async def features() -> list[FeatureResponse]:
    return [feature.info for feature in FEATURE_ROUTES.values()]


@app.get("/features/{feature_id}/styles", response_model=list[StyleResponse])
async def feature_styles(feature_id: str) -> list[StyleResponse]:
    return await feature_route(feature_id).styles()


@app.post("/features/{feature_id}/generate", response_model=GenerateResponse)
async def generate_feature(
    feature_id: str,
    image: Annotated[UploadFile, File()],
    style_id: Annotated[str, Form()],
) -> GenerateResponse:
    return await feature_route(feature_id).generate(image, style_id)
