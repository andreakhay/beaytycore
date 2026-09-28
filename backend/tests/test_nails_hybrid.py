"""Hybrid routing and preservation without claiming GPU model quality."""

import asyncio
import base64
from io import BytesIO

import httpx
import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.nails.geometry import (HandGeometry, ReviewedMaskSegmenter, UnusableHand,
                                NailCrop, composite_nails, nail_components)
from app.nails.hybrid import HybridNailsPipeline, normalized_hand
from app.nails.localized import localized_nails, restore_crop, single_nail_mask
from app.nails.contract import (ADAPTER_ID, ADAPTER_SHA256, GENERATOR, GUIDANCE,
                                MODEL_ID, MODEL_REVISION, SEED, STEPS)
from app.nails.remote import NailsGenerationError, RemoteLocalizedNails
from app.nails.styles import NAIL_STYLE_BY_ID


def hand_fixture():
    source = Image.new("RGB", (512, 512), (145, 110, 90))
    mask = Image.new("L", source.size)
    draw = ImageDraw.Draw(mask)
    points = [(.5, .8)] * 21
    for tip, base, x in ((4, 3, 90), (8, 7, 170), (12, 11, 250),
                         (16, 15, 330), (20, 19, 410)):
        points[tip] = (x / 512, 130 / 512)
        points[base] = (x / 512, 220 / 512)
        draw.ellipse((x - 12, 130, x + 12, 160), fill=255)
    return source, mask, HandGeometry(tuple(points), 512, 512)


@pytest.mark.parametrize("style_id,path", [
    ("classic_red", "model"), ("glossy_black", "model"),
    ("nude_pink", "renderer"), ("french_tip", "renderer"),
    ("pink_ombre", "renderer")])
def test_hybrid_routes_each_style_and_preserves_outside_masks(style_id, path):
    source, mask, hand = hand_fixture()
    calls = []

    class Localizer:
        def locate(self, image):
            return hand

    class Model:
        async def generate(self, image, style):
            calls.append((image.size, style.id))
            return Image.new("RGB", (512, 512), (180, 20, 20))

    result = asyncio.run(HybridNailsPipeline(
        Localizer(), ReviewedMaskSegmenter(mask), Model()).run(source, NAIL_STYLE_BY_ID[style_id]))
    assert result.path == path and result.nail_count == 5
    assert len(calls) == (5 if path == "model" else 0)
    assert all(size == (512, 512) and selected == style_id for size, selected in calls)
    outside = np.asarray(mask) == 0
    assert np.array_equal(np.asarray(result.image)[outside], np.asarray(source)[outside])
    assert np.any(np.asarray(result.image)[~outside] != np.asarray(source)[~outside])
    assert result.phase_seconds["hand_localization"] >= 0
    assert result.phase_seconds["nail_segmentation"] >= 0
    if path == "model":
        assert result.phase_seconds["gpu_request"] >= 0
        assert result.phase_seconds["result_reconstruction"] >= 0
    else:
        assert result.phase_seconds["style_rendering"] >= 0


def test_hybrid_rejects_missing_masks_before_model_calls():
    source, _, hand = hand_fixture()

    class Localizer:
        def locate(self, image):
            return hand

    class Model:
        async def generate(self, image, style):
            raise AssertionError("Invalid mask reached the GPU model")

    pipeline = HybridNailsPipeline(Localizer(), ReviewedMaskSegmenter(Image.new("L", source.size)), Model())
    with pytest.raises(UnusableHand, match="could not be located"):
        asyncio.run(pipeline.run(source, NAIL_STYLE_BY_ID["classic_red"]))


@pytest.mark.parametrize("xs,reason", [((12, 170, 250, 330, 410), "image_boundary")])
def test_rejected_crop_logs_reason_without_calling_model(xs, reason, caplog):
    source, _, hand = hand_fixture()
    mask = Image.new("L", source.size)
    draw = ImageDraw.Draw(mask)
    points = list(hand.points)
    for tip, base, x in zip((4, 8, 12, 16, 20), (3, 7, 11, 15, 19), xs):
        points[tip], points[base] = (x / 512, 130 / 512), (x / 512, 220 / 512)
        draw.ellipse((x - 12, 130, x + 12, 160), fill=255)
    geometry = HandGeometry(tuple(points), 512, 512)

    class Localizer:
        def locate(self, image):
            return geometry

    class Model:
        async def generate(self, image, style):
            raise AssertionError("Rejected crop reached GPU")

    with pytest.raises(UnusableHand, match="full nail"):
        asyncio.run(HybridNailsPipeline(Localizer(), ReviewedMaskSegmenter(mask), Model())
                    .run(source, NAIL_STYLE_BY_ID["classic_red"]))
    records = [r for r in caplog.records if "Nails crop rejected before GPU" in r.message]
    assert len(records) == 1
    counts = dict(field.split("=", 1) for field in records[0].message.split() if "=" in field)
    assert int(counts[reason]) > 0


@pytest.mark.parametrize("style_id", ["classic_red", "glossy_black"])
def test_close_fingers_generate_all_nails_and_preserve_surroundings(style_id):
    source, _, hand = hand_fixture()
    mask = Image.new("L", source.size)
    draw = ImageDraw.Draw(mask)
    points = list(hand.points)
    for tip, base, x in zip((4, 8, 12, 16, 20), (3, 7, 11, 15, 19), (90, 125, 160, 195, 230)):
        points[tip], points[base] = (x / 512, 130 / 512), (x / 512, 220 / 512)
        draw.ellipse((x - 12, 130, x + 12, 160), fill=255)
    geometry = HandGeometry(tuple(points), 512, 512)
    mappings = localized_nails(mask, geometry)
    assert len(mappings) == 5
    assert any(m.get("neighbor_context_pixels", 0) > 0 for m in mappings)
    selected = next(m for m in mappings if m.get("neighbor_context_pixels", 0) > 0)
    single = single_nail_mask(mask, selected)
    restored = restore_crop(Image.new("RGB", (512, 512), (180, 20, 20)), selected)
    one_result = composite_nails(source, restored, NailCrop((0, 0, 512, 512), source, single))
    untouched = np.asarray(single) == 0
    # Even a crop that paints all neighboring context cannot paste onto other nails.
    assert np.array_equal(np.asarray(one_result)[untouched], np.asarray(source)[untouched])
    calls = []

    class Localizer:
        def locate(self, image):
            return geometry

    class Model:
        async def generate(self, image, style):
            calls.append(style.id)
            # Paint the whole crop, including any neighbor, to challenge compositing.
            return Image.new("RGB", (512, 512), (180, 20, 20))

    result = asyncio.run(HybridNailsPipeline(Localizer(), ReviewedMaskSegmenter(mask), Model())
                         .run(source, NAIL_STYLE_BY_ID[style_id]))
    assert result.path == "model" and result.nail_count == 5
    assert calls == [style_id] * 5
    outside = np.asarray(mask) == 0
    assert np.array_equal(np.asarray(result.image)[outside], np.asarray(source)[outside])
    for group in nail_components(~outside):
        assert np.any(np.asarray(result.image)[group[:, 0], group[:, 1]] !=
                      np.asarray(source)[group[:, 0], group[:, 1]])


def test_accepted_crop_has_no_rejection_log(caplog):
    _, mask, hand = hand_fixture()
    mappings = localized_nails(mask, hand)
    assert len(mappings) == 5
    assert [m["crop_side_px"] for m in mappings] == [74] * 5
    assert not any("Nails crop rejected" in r.message for r in caplog.records)


def test_renderer_preserves_non_square_original_outside_mapped_mask():
    _, mask, hand = hand_fixture()
    source = Image.new("RGB", (768, 512), (145, 110, 90))
    _, box = normalized_hand(source)
    assert box[1] > 0

    class Localizer:
        def locate(self, image):
            return hand

    result = asyncio.run(HybridNailsPipeline(Localizer(), ReviewedMaskSegmenter(mask), None)
                         .run(source, NAIL_STYLE_BY_ID["french_tip"]))
    mapped_mask = mask.crop(box).resize(source.size, Image.Resampling.NEAREST)
    outside = np.asarray(mapped_mask) == 0
    assert np.array_equal(np.asarray(result.image)[outside], np.asarray(source)[outside])


@pytest.mark.parametrize("style_id", ["classic_red", "nude_pink"])
def test_source_resolution_refined_mask_controls_final_boundary(style_id):
    source, coarse, hand = hand_fixture()
    refined = Image.new("L", source.size)
    draw = ImageDraw.Draw(refined)
    for x in (90, 170, 250, 330, 410):
        draw.ellipse((x - 8, 134, x + 8, 155), fill=255)

    class Localizer:
        def locate(self, image):
            return hand

    class Segmenter(ReviewedMaskSegmenter):
        def segment_fingertips(self, original, mask, geometry, content_box):
            assert original.size == source.size and mask.size == (512, 512)
            parts = {}
            for finger, x in zip(("thumb", "index", "middle", "ring", "little"),
                                 (90, 170, 250, 330, 410)):
                part = Image.new("L", source.size)
                ImageDraw.Draw(part).ellipse((x - 8, 134, x + 8, 155), fill=255)
                parts[finger] = part
            return refined, parts

    class Model:
        async def generate(self, image, style):
            return Image.new("RGB", (512, 512), (180, 20, 20))

    result = asyncio.run(HybridNailsPipeline(Localizer(), Segmenter(coarse), Model())
                         .run(source, NAIL_STYLE_BY_ID[style_id]))
    outside = np.asarray(refined) == 0
    assert np.array_equal(np.asarray(result.image)[outside], np.asarray(source)[outside])
    assert np.any(np.asarray(result.image)[~outside] != np.asarray(source)[~outside])
    assert result.phase_seconds["mask_refinement"] >= 0


def test_model_style_never_falls_back_to_renderer_when_gpu_is_missing():
    source, mask, hand = hand_fixture()

    class Localizer:
        def locate(self, image):
            return hand

    pipeline = HybridNailsPipeline(Localizer(), ReviewedMaskSegmenter(mask), None)
    with pytest.raises(RuntimeError, match="GPU model is not configured"):
        asyncio.run(pipeline.run(source, NAIL_STYLE_BY_ID["classic_red"]))


def test_remote_client_rejects_wrong_checkpoint_metadata(monkeypatch):
    image = Image.new("RGB", (512, 512), "pink")
    stream = BytesIO()
    image.save(stream, "PNG")
    metadata = {"feature": "nails", "style_id": "classic_red", "adapter_id": ADAPTER_ID,
                "adapter_sha256": ADAPTER_SHA256, "adapter_steps": 50,
                "base_model_id": MODEL_ID, "base_model_revision": MODEL_REVISION,
                "lora_active": True, "seed": SEED, "steps": STEPS, "guidance": GUIDANCE,
                "runtime_seconds": 1.23}
    payload = {"status": "completed", "generator": GENERATOR, "metadata": metadata,
               "image": {"data_url": "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode(),
                         "content_type": "image/png", "width": 512, "height": 512}}
    client_class = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        return client_class(transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    remote = RemoteLocalizedNails("https://nails.example", "k" * 24)
    generated = asyncio.run(remote.generate(image, NAIL_STYLE_BY_ID["classic_red"]))
    assert generated.size == (512, 512)
    assert generated.info["runtime_seconds"] == 1.23
    metadata["adapter_sha256"] = "wrong"
    with pytest.raises(NailsGenerationError, match="invalid image or model response"):
        asyncio.run(remote.generate(image, NAIL_STYLE_BY_ID["classic_red"]))
