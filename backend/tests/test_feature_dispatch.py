"""The additive feature API delegates to the existing independent routes."""

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app import main
from app.nails.hybrid import HybridResult


client = TestClient(main.app)
LEGACY = {"hairstyle": ("/styles", "/generate", "bob"),
          "makeup": ("/makeup/styles", "/makeup/generate", "soft_glam"),
          "nails": ("/nails/styles", "/nails/generate", "classic_red")}


def portrait() -> bytes:
    output = BytesIO()
    Image.new("RGB", (128, 96), "#8aafbb").save(output, format="PNG")
    return output.getvalue()


def post(route: str, style_id: str, image: bytes | None = None):
    return client.post(route, data={"style_id": style_id},
                       files={"image": ("portrait.png", portrait() if image is None else image, "image/png")})


def test_feature_registration_and_style_discovery_use_existing_catalogs():
    features = client.get("/features")
    assert features.status_code == 200
    assert [item["id"] for item in features.json()] == list(LEGACY)
    assert all(item["name"] and item["description"] for item in features.json())
    for feature, (styles_route, _, _) in LEGACY.items():
        central = client.get(f"/features/{feature}/styles")
        legacy = client.get(styles_route)
        assert central.status_code == legacy.status_code == 200
        assert central.json() == legacy.json()


def test_central_generation_dispatches_only_to_selected_existing_handler(monkeypatch):
    called = []
    for feature, route in list(main.FEATURE_ROUTES.items()):
        original = route.generate

        async def spy(image, style_id, *, selected=feature, handler=original):
            called.append(selected)
            return await handler(image, style_id)

        monkeypatch.setitem(main.FEATURE_ROUTES, feature,
                            main.FeatureRoute(route.info, route.styles, spy))

    for feature, (_, legacy_route, style_id) in LEGACY.items():
        called.clear()
        central = post(f"/features/{feature}/generate", style_id)
        legacy = post(legacy_route, style_id)
        assert central.status_code == legacy.status_code == 200
        assert called == [feature]
        central_body, legacy_body = central.json(), legacy.json()
        for field in ("status", "generator", "style", "image"):
            assert central_body[field] == legacy_body[field]
        if feature != "nails":
            assert central_body["metadata"] == legacy_body["metadata"]
        else:
            assert central_body["metadata"]["feature"] == legacy_body["metadata"]["feature"]


@pytest.mark.parametrize("feature,style_id", [
    ("hairstyle", "soft_glam"), ("hairstyle", "classic_red"),
    ("makeup", "bob"), ("makeup", "classic_red"),
    ("nails", "bob"), ("nails", "soft_glam"),
])
def test_feature_style_namespaces_remain_isolated(feature, style_id):
    assert post(f"/features/{feature}/generate", style_id).status_code == 400


def test_unknown_feature_and_existing_request_validation():
    assert client.get("/features/unknown/styles").status_code == 404
    assert post("/features/unknown/generate", "bob").status_code == 404
    assert client.post("/features/hairstyle/generate", data={"style_id": "bob"}).status_code == 422
    central = post("/features/hairstyle/generate", "bob", b"not a valid image")
    legacy = post("/generate", "bob", b"not a valid image")
    assert (central.status_code, central.json()) == (legacy.status_code, legacy.json())


def test_central_nails_route_reaches_existing_hybrid_pipeline(monkeypatch):
    called = []

    class Pipeline:
        async def run(self, photo, style):
            called.append((photo.size, style.id))
            return HybridResult(photo, "renderer", 5, None, 0.2, {"style_rendering": 0.1})

    monkeypatch.setenv("NAILS_PREVIEW_MODE", "hybrid")
    monkeypatch.setattr(main, "nails_pipeline", lambda: Pipeline())
    response = post("/features/nails/generate", "french_tip")
    assert response.status_code == 200
    assert called == [((128, 96), "french_tip")]
    body = response.json()
    assert body["status"] == "completed"
    assert body["generator"] == "nails_hybrid"
    assert body["metadata"]["inference_path"] == "renderer"
    assert body["metadata"]["nails_edited"] == 5
