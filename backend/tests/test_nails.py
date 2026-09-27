import base64
from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app
from app.nails.geometry import HandGeometry, UnusableHand, crop_nails, composite_nails, prepare_model_crop, restore_model_crop
from app.nails.render import render_target
from app.nails.styles import NAIL_STYLES
from app.nails.pipeline import NailsPipeline
from app.nails.geometry import ReviewedMaskSegmenter


client = TestClient(app)


def photo_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (128, 128), "#aabbcc").save(output, "PNG")
    return output.getvalue()


def test_nail_catalog_and_placeholder_are_isolated():
    catalog = client.get("/nails/styles")
    assert catalog.status_code == 200
    assert [row["id"] for row in catalog.json()] == [style.id for style in NAIL_STYLES]
    assert {row["status"] for row in catalog.json()} == {"prototype"}
    response = client.post("/nails/generate", data={"style_id": "classic_red"},
                           files={"image": ("hand.png", photo_bytes(), "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "placeholder"
    assert body["metadata"]["model_status"] == "not_connected"
    assert body["metadata"]["adapter_id"] == "NAILS-001-LOCAL-v1"
    assert client.post("/generate", data={"style_id": "classic_red"},
                       files={"image": ("hand.png", photo_bytes(), "image/png")}).status_code == 400
    assert client.post("/nails/generate", data={"style_id": "crew-cut"},
                       files={"image": ("hand.png", photo_bytes(), "image/png")}).status_code == 400


def test_nails_shared_validation():
    response = client.post("/nails/generate", data={"style_id": "classic_red"},
                           files={"image": ("bad.png", b"bad", "image/png")})
    assert response.status_code == 400


def fixture_hand():
    source = Image.new("RGB", (256, 256), (145, 110, 90))
    mask = Image.new("L", source.size)
    draw = ImageDraw.Draw(mask)
    points = [(0.5, 0.8)] * 21
    for tip, base, x in ((4, 3, 55), (8, 7, 90), (12, 11, 125), (16, 15, 160), (20, 19, 195)):
        points[tip] = (x / 256, 65 / 256)
        points[base] = (x / 256, 125 / 256)
        draw.ellipse((x - 10, 65, x + 10, 95), fill=255)
    return source, mask, HandGeometry(tuple(points), 256, 256)


def test_crop_render_and_composite_preserve_every_outside_pixel():
    source, mask, hand = fixture_hand()
    crop = crop_nails(source, mask, hand)
    assert crop.image.size[0] < source.width
    model_input, content_box = prepare_model_crop(crop)
    assert model_input.size == (512, 512)
    assert restore_model_crop(model_input, crop, content_box).size == crop.image.size
    for style in NAIL_STYLES:
        rendered = render_target(source, mask, style.id, hand)
        result = composite_nails(source, rendered.crop(crop.box), crop)
        original = np.asarray(source)
        changed = np.asarray(result)
        outside = np.asarray(mask) == 0
        assert np.array_equal(changed[outside], original[outside])
        assert np.any(changed[~outside] != original[~outside])


def test_pipeline_discards_all_non_nail_generated_pixels():
    source, mask, hand = fixture_hand()

    class Localizer:
        def locate(self, image): return hand

    class Generator:
        async def generate(self, image, style):
            assert image.size == (512, 512)
            return Image.new("RGB", image.size, "blue")

    import asyncio
    result = asyncio.run(NailsPipeline(Localizer(), ReviewedMaskSegmenter(mask), Generator()).run(source, NAIL_STYLES[0]))
    outside = np.asarray(mask) == 0
    assert np.array_equal(np.asarray(result.image)[outside], np.asarray(source)[outside])
    assert result.model_output.size == (512, 512)


def test_unusable_nail_masks_fail_closed():
    source, _, hand = fixture_hand()
    with pytest.raises(UnusableHand, match="could not be located"):
        crop_nails(source, Image.new("L", source.size), hand)
    with pytest.raises(UnusableHand):
        one_nail = Image.new("L", source.size)
        ImageDraw.Draw(one_nail).ellipse((110, 65, 140, 95), fill=255)
        crop_nails(source, one_nail, hand)
