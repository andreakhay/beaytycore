"""Gate 3 candidate: one authenticated HTTP service and one verified FLUX foundation."""

import asyncio
from contextlib import asynccontextmanager
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))
from scripts import unified_gate1 as gate
from scripts.unified_gate2 import SharedExperiment, SwitchFailure, inspect_adapter
from scripts.kaggle_inference_server import FluxRuntime, read_adapter_metadata, validated_image as portrait_image
from scripts.makeup_inference_server import MakeupRuntime, validated_portrait
from scripts.unified_gate3_nails import NailsRuntime
from app.nails.inference_options import SUPPORTED_STEPS
from app.generation.diagnostics import RequestDiagnostics, current, emit
from app.styles import REGISTRY
from app.registry import styles_by_id
from app.makeup_contract import (ADAPTER_ID as MAKEUP_ID, ADAPTER_SHA256 as MAKEUP_SHA,
                                 GENERATOR as MAKEUP_GENERATOR, PRESETS_SHA256, PROMPTS as MAKEUP_PROMPTS,
                                 verify_adapter as verify_makeup)
from app.nails.contract import (ADAPTER_ID as NAILS_ID, ADAPTER_SHA256 as NAILS_SHA,
                                GENERATOR as NAILS_GENERATOR, MODEL_STYLES, PROMPTS as NAILS_PROMPTS,
                                verify_adapter as verify_nails)

LOGGER = logging.getLogger('unified_gate3')
HAIR_STYLES = styles_by_id(REGISTRY)
FEATURES = ('hairstyle', 'makeup', 'nails')


def adapter_configuration(root=ROOT):
    """All enabled Hair adapters must have an approved artifact; no silent fallback."""
    configured = json.loads(os.getenv('AI_HAIR_ADAPTER_DIRS', '{}'))
    if not configured:
        configured = {'train001': str(root / 'gate1/adapters/hairstyle')}
    enabled = {name for name, info in REGISTRY['adapters'].items() if info['status'] == 'enabled'}
    if set(configured) != enabled:
        raise ValueError('Enabled Hairstyle adapters do not match attached assets')
    result = {}
    for name, directory in configured.items():
        path = Path(directory)
        metadata = read_adapter_metadata(path, name)
        result[name] = (path, metadata)
    return result


def expected_contract(feature, style_id, adapter_id=None, adapter_meta=None):
    if feature == 'hairstyle':
        return {'style_id': style_id, 'adapter_id': adapter_id,
                'adapter_sha256': adapter_meta['checkpoint_sha256'],
                'adapter_steps': adapter_meta['training_steps'],
                'generator': f'flux2_klein_base_{adapter_id}',
                'prompt': HAIR_STYLES[style_id]['prompt']}
    if feature == 'makeup':
        return {'feature': 'makeup', 'style_id': style_id, 'adapter_id': MAKEUP_ID,
                'adapter_sha256': MAKEUP_SHA, 'adapter_steps': 250,
                'generator': MAKEUP_GENERATOR, 'prompt': MAKEUP_PROMPTS[style_id],
                'prompt_presets_sha256': PRESETS_SHA256, 'lora_active': True}
    return {'feature': 'nails', 'style_id': style_id, 'adapter_id': NAILS_ID,
            'adapter_sha256': NAILS_SHA, 'adapter_steps': 50,
            'generator': NAILS_GENERATOR, 'prompt': NAILS_PROMPTS[style_id],
            'lora_active': True}


def selected_adapter(feature, style_id):
    if feature == 'hairstyle':
        if style_id not in HAIR_STYLES:
            raise ValueError('Unsupported Hairstyle style')
        return 'hairstyle:' + HAIR_STYLES[style_id]['adapter_id']
    if feature == 'makeup' and style_id in MAKEUP_PROMPTS:
        return 'makeup'
    if feature == 'nails' and style_id in MODEL_STYLES:
        return 'nails'
    raise ValueError('Unsupported feature style')


def validate_result(payload, expected, inference_steps):
    # Gate 1's unchanged validator pins 20. Check actual steps first, then reuse
    # its checks for every other field and PNG through a temporary metadata copy.
    if payload.get('metadata', {}).get('steps') != inference_steps:
        raise ValueError('Wrong inference step provenance')
    gate.validate_result({**payload, 'metadata': {**payload['metadata'], 'steps': 20}}, expected)


class ServingOwner(SharedExperiment):
    """Gate 2 switch/lock/cancellation behavior with dynamic image and style inputs."""

    def __init__(self, pipe, torch, specs, views, hair_adapters):
        super().__init__(pipe, specs, lambda _: None, lambda: torch.cuda.synchronize(0),
                         inspect_adapter, lambda: gate.memory(torch))
        self.torch, self.views, self.hair_adapters = torch, views, hair_adapters
        self.foundation_load_count = 1
        self.audit = []

    def operate(self, adapter_key, label, image, style_id, inference_steps=20):
        self.sequence += 1
        self.event('ownership_start', label=label, sequence=self.sequence)
        feature = adapter_key.split(':')[0]
        try:
            self.switch(adapter_key)
            self.assert_active(adapter_key)
            if feature == 'hairstyle':
                name = adapter_key.split(':', 1)[1]
                directory, metadata = self.hair_adapters[name]
                view = self.views[feature]
                view.adapters = {name: (directory, metadata)}
                view.active_adapter = name  # Original activation returns; the owner verified actual state.
                view.metadata = metadata
                expected = expected_contract(feature, style_id, name, metadata)
            else:
                expected = expected_contract(feature, style_id)
            started = time.monotonic()
            self.event('inference_start', feature=feature, label=label)
            emit('worker_inference_start', feature=feature, style_id=style_id)
            try:
                with gate.optional_runtime_telemetry(self.torch, []):
                    if feature == 'nails' and inference_steps != 20:
                        payload = self.views[feature].generate(image, style_id, inference_steps=inference_steps)
                    else:
                        payload = self.views[feature].generate(image, style_id)
                self.synchronize()
                validate_result(payload, expected, inference_steps)
                self.assert_active(adapter_key)
            except Exception:
                self.ready, self.active, self.active_state = False, None, None
                try:
                    self.synchronize()
                except Exception as exc:
                    emit('worker_error', category='gpu_drain', exception_type=type(exc).__name__, ready=False)
                raise
            self.event('inference_end', feature=feature, label=label,
                       seconds=time.monotonic() - started)
            LOGGER.info('Completed %s/%s with %s in %.2f seconds', feature, style_id,
                        expected['adapter_id'], time.monotonic() - started)
            self.audit.append({'feature': feature, 'style_id': style_id,
                **current(),
                'inference_steps': inference_steps,
                'adapter_id': expected['adapter_id'], 'adapter_sha256': expected['adapter_sha256'],
                'base_revision': gate.REVISION, 'inference_seconds': round(time.monotonic() - started, 3),
                'http_status': 200, 'memory_after': self.measure()})
            del self.audit[:-30]
            emit('worker_inference_end', feature=feature, style_id=style_id,
                 adapter_id=expected['adapter_id'], inference_seconds=round(time.monotonic() - started, 3))
            return payload
        finally:
            self.event('ownership_end', label=label)


class UnifiedRuntime:
    def __init__(self):
        self.owner = None
        self.ready = False
        self.base_loaded = False
        self.foundation_load_count = 0
        self.load_seconds = None
        self.init_error = None

    def load(self):
        import torch
        from diffusers import Flux2KleinPipeline
        from app.nails.contract import verify_adapter as nails_verify
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable')
        if len(os.environ.get('AI_REMOTE_API_KEY', '')) < 24:
            raise RuntimeError('Unified API key is missing')
        model = Path(os.environ['AI_MODEL_DIR'])
        if model.name != gate.REVISION or gate.digest(model / 'model_index.json') != json.loads(
                (ROOT / 'docs/experiments/unified-kaggle-gate1-review.json').read_text())['base_model_index_sha256']:
            raise ValueError('Pinned Base revision/index mismatch')
        hair_adapters = adapter_configuration()
        makeup = ROOT / 'gate1/adapters/makeup'
        nails = ROOT / 'gate1/adapters/nails/nails001_local_v1.safetensors'
        verify_makeup(makeup)
        nails_verify(nails)
        specs = {}
        for name, (directory, metadata) in hair_adapters.items():
            specs['hairstyle:' + name] = {'path': directory / 'adapter.safetensors',
                'verify': lambda directory=directory, name=name: read_adapter_metadata(directory, name),
                'expected': {'adapter_sha256': metadata['checkpoint_sha256']}}
        specs['makeup'] = {'path': makeup / 'adapter.safetensors', 'verify': lambda: verify_makeup(makeup),
                           'expected': {'adapter_sha256': MAKEUP_SHA}}
        specs['nails'] = {'path': nails, 'verify': lambda: nails_verify(nails),
                          'expected': {'adapter_sha256': NAILS_SHA}}
        started = time.monotonic()
        pipe = Flux2KleinPipeline.from_pretrained(str(model), torch_dtype=torch.float16, local_files_only=True)
        self.foundation_load_count += 1
        pipe.enable_model_cpu_offload(gpu_id=0)
        self.base_loaded = True
        views = {'hairstyle': FluxRuntime(), 'makeup': MakeupRuntime(), 'nails': NailsRuntime()}
        for view in views.values():
            view.pipe, view.torch, view.ready = pipe, torch, True
        owner = ServingOwner(pipe, torch, specs, views, hair_adapters)
        owner.load_verified('hairstyle:train001')
        owner.assert_active('hairstyle:train001')
        self.owner = owner
        self.ready = True
        self.load_seconds = round(time.monotonic() - started, 3)
        LOGGER.info('Unified Base and first adapter ready in %.2f seconds', self.load_seconds)

    def health(self):
        owner = self.owner
        active = owner.active if owner and owner.ready else None
        return {'status': 'ready' if self.ready and owner and owner.ready else 'unready',
                'process_alive': True, 'gpu_runtime_ready': bool(self.ready and owner and owner.ready),
                'base_model_loaded': self.base_loaded,
                'foundation_load_count': self.foundation_load_count,
                'base_model_id': gate.MODEL_ID, 'base_model_revision': gate.REVISION,
                'active_feature': active.split(':')[0] if active else None,
                'active_adapter': active.split(':')[-1] if active else None,
                'supported_features': list(FEATURES), 'load_seconds': self.load_seconds,
                'nails_inference_steps': list(SUPPORTED_STEPS),
                'gpu_busy': bool(owner and owner.owner.locked()),
                'diagnostics_version': 'deployment-01'}

    def status(self):
        return {**self.health(), 'requests': list(self.owner.audit) if self.owner else [],
                'http_requests': list(HTTP_RECORDS),
                'switch_events': sum(event['event'] == 'switch_end' for event in self.owner.events)
                    if self.owner else 0}


runtime = UnifiedRuntime()
HTTP_RECORDS = []


@asynccontextmanager
async def lifespan(_app):
    try:
        runtime.load()
    except Exception as exc:
        runtime.ready = False
        emit('worker_error', category='base_initialization', exception_type=type(exc).__name__, ready=False)
    yield
    runtime.ready = False


app = FastAPI(title='Unified Kaggle inference candidate', lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(RequestDiagnostics, layer='worker', records=HTTP_RECORDS)


@app.get('/health')
async def health():
    return runtime.health()


@app.get('/status')
async def status(x_api_key: Annotated[str | None, Header()] = None):
    key = os.environ.get('AI_REMOTE_API_KEY', '')
    if len(key) < 24 or not x_api_key or not secrets.compare_digest(key, x_api_key):
        raise HTTPException(401, 'Invalid API key')
    return runtime.status()


async def read_image(feature, upload):
    if feature == 'hairstyle':
        return await portrait_image(upload)
    if feature == 'makeup':
        return await validated_portrait(upload)
    if upload.content_type != 'image/png':
        raise HTTPException(415, 'Expected a localized PNG')
    content = await upload.read(8 * 1024 * 1024 + 1)
    if not content or len(content) > 8 * 1024 * 1024:
        raise HTTPException(413, 'Localized image is empty or too large')
    try:
        with Image.open(BytesIO(content)) as opened:
            if opened.format != 'PNG' or opened.size != (512, 512):
                raise ValueError('Wrong localized crop')
            opened.load()
            return opened.convert('RGB')
    except (OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(400, 'Invalid localized crop') from None


@app.post('/{feature}/generate')
async def generate(feature: str, image: Annotated[UploadFile, File()], style_id: Annotated[str, Form()],
                   x_api_key: Annotated[str | None, Header()] = None,
                   inference_steps: Annotated[int, Form()] = 20):
    key = os.environ.get('AI_REMOTE_API_KEY', '')
    if len(key) < 24 or not x_api_key or not secrets.compare_digest(key, x_api_key):
        raise HTTPException(401, 'Invalid API key')
    if feature not in FEATURES:
        raise HTTPException(404, 'Unknown feature')
    if inference_steps not in SUPPORTED_STEPS or (feature != 'nails' and inference_steps != 20):
        raise HTTPException(400, 'Unsupported inference steps for this feature')
    try:
        adapter_key = selected_adapter(feature, style_id)
    except ValueError:
        raise HTTPException(400, 'Unsupported style') from None
    if not runtime.ready or not runtime.owner or not runtime.owner.ready:
        raise HTTPException(503, 'GPU runtime is not ready')
    source = await read_image(feature, image)
    owner = runtime.owner
    if owner.owner.locked():
        raise HTTPException(429, 'GPU is busy')
    label = f'{feature}:{style_id}:{time.monotonic_ns()}'
    try:
        return await owner.generate(adapter_key, label, image=source, style_id=style_id,
                                    inference_steps=inference_steps)
    except asyncio.CancelledError:
        raise
    except SwitchFailure as exc:
        emit('worker_error', category='adapter_switch', exception_type=type(exc).__name__, ready=owner.ready)
        raise HTTPException(503, 'GPU adapter switch failed. Please try again.') from None
    except Exception as exc:
        emit('worker_error', category='inference', exception_type=type(exc).__name__, ready=owner.ready)
        raise HTTPException(500, 'GPU inference failed. Please try again.') from None
