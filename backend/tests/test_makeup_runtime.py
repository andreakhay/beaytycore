"""Isolated Makeup runtime contract tests, no GPU or live network required."""

import asyncio
import base64
from io import BytesIO
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
import httpx
from PIL import Image
import pytest

from app import main
from app.generation.remote_makeup import RemoteMakeupEngine, configured_makeup_engine
from app.makeup_contract import ADAPTER_ID, ADAPTER_SHA256, GENERATOR, MODEL_ID, MODEL_REVISION, PRESETS_SHA256, PROMPTS, load_prompts

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import makeup_inference_server as server
from scripts import makeup_inference_bootstrap as bootstrap

KEY = "makeup-test-key-with-32-characters"


def png(size=(512, 512)):
    stream = BytesIO()
    Image.new("RGB", size, "#af8a99").save(stream, format="PNG")
    return stream.getvalue()


def payload(style="soft_glam"):
    return {"status": "completed", "generator": GENERATOR,
            "image": {"data_url": "data:image/png;base64," + base64.b64encode(png()).decode(),
                      "content_type": "image/png", "width": 512, "height": 512},
            "metadata": {"feature": "makeup", "style_id": style, "adapter_id": ADAPTER_ID,
                         "adapter_sha256": ADAPTER_SHA256, "base_model_id": MODEL_ID,
                         "base_model_revision": MODEL_REVISION, "prompt_presets_sha256": PRESETS_SHA256,
                         "lora_active": True}}


def connect(monkeypatch, handler):
    client_type = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_type(
        transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setattr(main, "makeup_engine", RemoteMakeupEngine("https://makeup.example", KEY))


def post(client, style="soft_glam", headers=None):
    return client.post("/generate" if client.app is server.app else "/makeup/generate",
                       data={"style_id": style}, files={"image": ("portrait.png", png(), "image/png")},
                       headers=headers or {})


def test_makeup_forwarding_preserves_hair_engine_and_returns_verified_model(monkeypatch):
    hair_engine = main.engine

    def handler(request):
        assert request.url == "https://makeup.example/generate"
        assert request.headers["X-API-Key"] == KEY
        assert b"soft_glam" in request.content
        return httpx.Response(200, json=payload())

    connect(monkeypatch, handler)
    client = TestClient(main.app)
    result = post(client)
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
    assert result.json()["generator"] == GENERATOR
    assert result.json()["metadata"]["adapter_id"] == ADAPTER_ID
    assert {style["status"] for style in client.get("/makeup/styles").json()} == {"trained_preset"}
    assert main.engine is hair_engine
    assert client.get("/health").json()["generator"] == hair_engine.name


@pytest.mark.parametrize("status", [401, 429, 503, 500])
def test_remote_makeup_errors_are_visible_without_falling_back_to_mock(monkeypatch, status):
    connect(monkeypatch, lambda request: httpx.Response(status))
    result = post(TestClient(main.app))
    assert result.status_code == 502
    assert "Makeup" in result.json()["detail"]
    assert KEY not in result.text


def test_makeup_timeout_is_a_recoverable_error(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)
    connect(monkeypatch, handler)
    result = post(TestClient(main.app))
    assert result.status_code == 502
    assert "timed out" in result.json()["detail"]


@pytest.mark.parametrize("field,value", [("adapter_id", "TRAIN-001"), ("adapter_sha256", "wrong"),
                                        ("style_id", "classic_red_lip"), ("lora_active", False),
                                        ("base_model_revision", "wrong"), ("prompt_presets_sha256", "wrong")])
def test_makeup_rejects_wrong_adapter_or_preset_response(monkeypatch, field, value):
    body = payload()
    body["metadata"][field] = value
    connect(monkeypatch, lambda request: httpx.Response(200, json=body))
    assert post(TestClient(main.app)).status_code == 502


def test_makeup_rejects_corrupt_remote_png(monkeypatch):
    body = payload()
    body["image"]["data_url"] = "data:image/png;base64,bm90YW5pbWFnZQ=="
    connect(monkeypatch, lambda request: httpx.Response(200, json=body))
    assert post(TestClient(main.app)).status_code == 502


def test_remote_makeup_rejects_hair_styles_before_network_call(monkeypatch):
    def forbidden(request):
        pytest.fail("Hair style reached Makeup service")
    connect(monkeypatch, forbidden)
    assert post(TestClient(main.app), "crew_cut").status_code == 400
    with pytest.raises(Exception, match="not a Makeup"):
        asyncio.run(main.makeup_engine.generate(Image.new("RGB", (512, 512)), SimpleNamespace(id="crew_cut")))


def test_makeup_config_requires_its_own_url_and_key(monkeypatch):
    monkeypatch.setenv("MAKEUP_GENERATION_ENGINE", "remote_makeup")
    monkeypatch.delenv("MAKEUP_REMOTE_URL", raising=False)
    monkeypatch.delenv("MAKEUP_REMOTE_API_KEY", raising=False)
    monkeypatch.setenv("FLUX_REMOTE_URL", "https://hair.example")
    monkeypatch.setenv("FLUX_REMOTE_API_KEY", KEY)
    with pytest.raises(RuntimeError, match="MAKEUP_REMOTE_URL"):
        configured_makeup_engine()


def test_reviewed_prompts_cannot_silently_change(tmp_path):
    presets = tmp_path / "prompts.json"
    presets.write_text('{"styles": []}')
    with pytest.raises(ValueError, match="differ"):
        load_prompts(presets)
    assert len(PROMPTS) == 10 and all("Change makeup only" in value for value in PROMPTS.values())


def test_gpu_makeup_auth_style_readiness_and_busy_checks(monkeypatch):
    monkeypatch.setenv("MAKEUP001_API_KEY", KEY)
    monkeypatch.setattr(server.runtime, "ready", True)
    monkeypatch.setattr(server.runtime, "generate", lambda image, style: payload(style))
    lock = asyncio.Lock()
    monkeypatch.setattr(server.runtime, "lock", lock)
    client = TestClient(server.app)
    auth = {"X-API-Key": KEY}
    assert post(client).status_code == 401
    assert post(client, "crew_cut", auth).status_code == 400
    assert post(client, headers=auth).status_code == 200
    asyncio.run(lock.acquire())
    try:
        assert post(client, headers=auth).status_code == 429
    finally:
        lock.release()
    monkeypatch.setattr(server.runtime, "ready", False)
    assert post(client, headers=auth).status_code == 503


def test_gpu_makeup_validates_image_before_inference(monkeypatch):
    monkeypatch.setenv("MAKEUP001_API_KEY", KEY)
    monkeypatch.setattr(server.runtime, "ready", True)
    client = TestClient(server.app)
    for content, mime, expected in [(b"bad", "image/png", 400), (png((32, 32)), "image/png", 422),
                                    (png(), "image/jpeg", 415), (b"", "image/png", 400)]:
        result = client.post("/generate", headers={"X-API-Key": KEY}, data={"style_id": "soft_glam"},
                             files={"image": ("photo", content, mime)})
        assert result.status_code == expected


def test_gpu_makeup_loads_only_approved_adapter_once(monkeypatch, tmp_path):
    model = tmp_path / MODEL_REVISION
    model.mkdir()
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    calls = []
    pipe = SimpleNamespace(enable_model_cpu_offload=lambda **kwargs: calls.append(("offload", kwargs)),
                           load_lora_weights=lambda path, **kwargs: calls.append(("adapter", path, kwargs)))
    pipeline = SimpleNamespace(from_pretrained=lambda path, **kwargs: (calls.append(("model", path, kwargs)), pipe)[1])
    monkeypatch.setitem(sys.modules, "diffusers", SimpleNamespace(Flux2KleinPipeline=pipeline))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(float16="float16", cuda=SimpleNamespace(is_available=lambda: True)))
    monkeypatch.setattr(server, "verify_adapter", lambda directory: {})
    monkeypatch.setenv("MAKEUP001_MODEL_DIR", str(model))
    monkeypatch.setenv("MAKEUP001_ADAPTER_DIR", str(adapter))
    monkeypatch.setenv("MAKEUP001_API_KEY", KEY)
    runtime = server.MakeupRuntime()
    runtime.load()
    assert runtime.ready
    assert calls == [("model", str(model), {"torch_dtype": "float16", "local_files_only": True}),
                     ("offload", {"gpu_id": 0}), ("adapter", str(adapter), {"weight_name": "adapter.safetensors"})]


def test_gpu_generation_survives_unavailable_cuda_memory_stats():
    class FailingCudaStats:
        def reset_peak_memory_stats(self, device):
            raise RuntimeError("Invalid device argument")

        def max_memory_allocated(self, device):
            raise RuntimeError("Invalid device argument")

    calls = []
    runtime = server.MakeupRuntime()
    runtime.torch = SimpleNamespace(
        cuda=FailingCudaStats(),
        Generator=lambda **kwargs: SimpleNamespace(manual_seed=lambda seed: seed),
    )
    runtime.pipe = lambda **kwargs: (
        calls.append(kwargs), SimpleNamespace(images=[Image.new("RGB", (512, 512), "pink")])
    )[1]
    result = runtime.generate(Image.new("RGB", (512, 512), "white"), "soft_glam")
    assert result["status"] == "completed"
    assert calls[0]["prompt"] == PROMPTS["soft_glam"]
    assert result["metadata"]["peak_gpu_mib"] is None


def test_health_gate_rejects_wrong_feature_and_checkpoint(monkeypatch):
    monkeypatch.setattr(server.runtime, "ready", True)
    health = TestClient(server.app).get("/health").json()
    assert bootstrap.expected_health(health)
    assert not bootstrap.expected_health({**health, "adapter_sha256": "wrong"})
    assert not bootstrap.expected_health({**health, "feature": "hair"})
    assert KEY not in json.dumps(health)
