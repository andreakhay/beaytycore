"""Synthetic boundaries for central API tests, never a GPU or quality check.

Keep the real handlers, HTTP clients and Nails hybrid pipeline. Replace only
remote HTTP, hand localization and segmentation with deterministic fixtures.
"""

import base64
from contextlib import contextmanager
from email.parser import BytesParser
from email.policy import default
from io import BytesIO
import os
from unittest.mock import patch

import httpx
from PIL import Image, ImageDraw

from app import main
from app import makeup_contract as makeup
from app.generation.remote_flux import RemoteFluxEngine
from app.generation.remote_makeup import RemoteMakeupEngine
from app.nails import contract as nails
from app.nails.geometry import HandGeometry, ReviewedMaskSegmenter
from app.nails.hybrid import HybridNailsPipeline
from app.nails.remote import RemoteLocalizedNails


STYLES = {"hairstyle": "crew_cut", "makeup": "soft_glam", "nails": "classic_red"}
HOSTS = {f"{feature}.inference.invalid": feature for feature in STYLES}
TEST_KEY = "synthetic-test-key-never-a-secret"


def png(image):
    stream = BytesIO()
    image.save(stream, "PNG")
    return stream.getvalue()


class CentralRemoteScenario:
    def __init__(self):
        self.failures = {}
        self.calls = []
        self.source = Image.new("RGB", (512, 512), (145, 110, 90))
        self.mask = Image.new("L", self.source.size)
        self.refined = Image.new("L", self.source.size)
        self.finger_masks = {}
        points = [(.5, .8)] * 21
        for finger, (tip, base, x) in zip(
                ("thumb", "index", "middle", "ring", "little"),
                ((4, 3, 90), (8, 7, 170), (12, 11, 250), (16, 15, 330), (20, 19, 410))):
            points[tip], points[base] = (x / 512, 130 / 512), (x / 512, 220 / 512)
            ImageDraw.Draw(self.mask).ellipse((x - 12, 130, x + 12, 160), fill=255)
            part = Image.new("L", self.source.size)
            ImageDraw.Draw(part).ellipse((x - 8, 134, x + 8, 155), fill=255)
            self.finger_masks[finger] = part
            ImageDraw.Draw(self.refined).ellipse((x - 8, 134, x + 8, 155), fill=255)
        self.hand = HandGeometry(tuple(points), 512, 512)

    def response(self, feature, style_id):
        metadata = {"feature": feature, "style_id": style_id}
        generator = "remote_flux"
        if feature == "makeup":
            generator = makeup.GENERATOR
            metadata.update(adapter_id=makeup.ADAPTER_ID, adapter_sha256=makeup.ADAPTER_SHA256,
                            base_model_id=makeup.MODEL_ID, base_model_revision=makeup.MODEL_REVISION,
                            prompt_presets_sha256=makeup.PRESETS_SHA256, lora_active=True)
        elif feature == "nails":
            generator = nails.GENERATOR
            metadata.update(adapter_id=nails.ADAPTER_ID, adapter_sha256=nails.ADAPTER_SHA256,
                            adapter_steps=50, base_model_id=nails.MODEL_ID,
                            base_model_revision=nails.MODEL_REVISION, lora_active=True,
                            seed=nails.SEED, steps=nails.STEPS, guidance=nails.GUIDANCE)
        return {"status": "completed", "generator": generator, "metadata": metadata,
                "image": {"content_type": "image/png", "width": 512, "height": 512,
                          "data_url": "data:image/png;base64," + base64.b64encode(
                              png(Image.new("RGB", (512, 512), (180, 20, 20)))).decode()}}

    def transport(self, request):
        # Assert what the real remote client sends, not an invented model interface.
        feature = HOSTS[request.url.host]
        assert request.method == "POST" and request.url.path == "/generate"
        assert request.headers["X-API-Key"] == TEST_KEY
        envelope = BytesParser(policy=default).parsebytes(
            b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.content)
        fields = {part.get_param("name", header="content-disposition"): part.get_payload(decode=True)
                  for part in envelope.iter_parts()}
        style_id = fields["style_id"].decode()
        with Image.open(BytesIO(fields["image"])) as image:
            assert image.format == "PNG" and image.size == (512, 512)
        self.calls.append((feature, style_id))
        failure = self.failures.get(feature)
        if failure == "unavailable":
            raise httpx.ConnectError("synthetic outage", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        if failure == "inference_error":
            return httpx.Response(500, text="private internal traceback must not reach the user")
        if failure == "not_ready":
            return httpx.Response(503)
        if failure == "invalid_json":
            return httpx.Response(200, text="not JSON")
        payload = self.response(feature, style_id)
        if failure == "invalid_image":
            payload["image"]["data_url"] = None
        if failure == "invalid_metadata":
            payload["metadata"] = None
        if failure == "wrong_provenance":
            payload["metadata"]["adapter_sha256"] = "wrong"
        return httpx.Response(200, json=payload)

    @contextmanager
    def installed(self):
        scenario = self

        class Localizer:
            def locate(self, image):
                assert image.size == (512, 512)
                return scenario.hand

        class Segmenter(ReviewedMaskSegmenter):
            def segment_fingertips(self, original, mask, geometry, content_box):
                assert original.size == scenario.source.size and mask.size == (512, 512)
                return scenario.refined, scenario.finger_masks

        real_client = httpx.AsyncClient
        transport = httpx.MockTransport(self.transport)

        def client(*args, **kwargs):
            return real_client(*args, **kwargs, transport=transport)

        pipeline = HybridNailsPipeline(Localizer(), Segmenter(self.mask),
                                      RemoteLocalizedNails("https://nails.inference.invalid", TEST_KEY))
        with (patch.object(main, "engine", RemoteFluxEngine("https://hairstyle.inference.invalid", TEST_KEY)),
              patch.object(main, "makeup_engine", RemoteMakeupEngine("https://makeup.inference.invalid", TEST_KEY)),
              patch.object(main, "_nails_pipeline", pipeline),
              patch.dict(os.environ, {"NAILS_PREVIEW_MODE": "hybrid"}),
              patch.object(httpx, "AsyncClient", client)):
            yield self
