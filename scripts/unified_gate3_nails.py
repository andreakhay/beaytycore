"""Nails step comparison on the shared foundation; original 20-step path retained."""

import base64
from io import BytesIO
import time

from scripts.nails001_local_inference_server import NailsRuntime as EvaluatedNailsRuntime
from app.nails.contract import (ADAPTER_ID, ADAPTER_SHA256, GENERATOR, GUIDANCE,
                                MODEL_ID, MODEL_REVISION, PROMPTS, SEED, STEPS)
from app.nails.inference_options import validate_steps


class NailsRuntime(EvaluatedNailsRuntime):
    def generate(self, reference, style_id, inference_steps=STEPS):
        steps = validate_steps(inference_steps)
        if steps == STEPS:
            return super().generate(reference, style_id)
        started = time.monotonic()
        result = self.pipe(prompt=PROMPTS[style_id], image=reference, width=512, height=512,
                           num_inference_steps=steps, guidance_scale=GUIDANCE,
                           generator=self.torch.Generator(device="cuda").manual_seed(SEED)).images[0]
        stream = BytesIO()
        result.convert("RGB").save(stream, "PNG")
        return {"status": "completed", "generator": GENERATOR,
                "image": {"data_url": "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode(),
                          "content_type": "image/png", "width": 512, "height": 512},
                "metadata": {"feature": "nails", "style_id": style_id, "adapter_id": ADAPTER_ID,
                             "adapter_sha256": ADAPTER_SHA256, "adapter_steps": 50,
                             "base_model_id": MODEL_ID, "base_model_revision": MODEL_REVISION,
                             "lora_active": True, "seed": SEED, "steps": steps,
                             "guidance": GUIDANCE, "prompt": PROMPTS[style_id],
                             "runtime_seconds": round(time.monotonic() - started, 2)}}
