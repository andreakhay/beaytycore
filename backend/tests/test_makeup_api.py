import base64
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.makeup_styles import MAKEUP_STYLES


client = TestClient(app)


def portrait() -> bytes:
    output = BytesIO()
    Image.new("RGB", (128, 96), "#8aafbb").save(output, format="PNG")
    return output.getvalue()


def post(route: str, style_id: str):
    return client.post(route, data={"style_id": style_id},
                       files={"image": ("portrait.png", portrait(), "image/png")})


def test_makeup_catalog_has_ten_distinct_prototype_styles():
    result = client.get("/makeup/styles")
    assert result.status_code == 200
    assert len(result.json()) == 10
    assert len({item["id"] for item in result.json()}) == 10
    assert {item["status"] for item in result.json()} == {"prototype"}
    assert {item["id"] for item in result.json()} == {style.id for style in MAKEUP_STYLES}


def test_makeup_preview_returns_normalized_original_and_placeholder_metadata():
    result = post("/makeup/generate", "soft_glam")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "placeholder"
    assert body["generator"] == "makeup_mock"
    assert body["metadata"] == {"feature": "makeup", "model_status": "not_connected"}
    assert body["style"]["id"] == "soft_glam"
    with Image.open(BytesIO(base64.b64decode(body["image"]["data_url"].split(",", 1)[1]))) as image:
        assert image.size == (128, 96)
        assert image.mode == "RGB"


def test_hair_and_makeup_style_namespaces_are_isolated():
    assert post("/makeup/generate", "crew_cut").status_code == 400
    assert post("/makeup/generate", "bob").status_code == 400
    assert post("/generate", "soft_glam").status_code == 400
    assert post("/generate", "classic_red_lip").status_code == 400


def test_makeup_preview_uses_shared_image_validation():
    invalid = client.post("/makeup/generate", data={"style_id": "soft_glam"},
                          files={"image": ("bad.png", b"not an image", "image/png")})
    assert invalid.status_code == 400
    assert client.post("/makeup/generate", data={"style_id": "soft_glam"}).status_code == 422
