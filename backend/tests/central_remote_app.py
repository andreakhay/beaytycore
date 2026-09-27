"""Local browser harness. Run only with uvicorn --app-dir tests.

All GPU HTTP traffic is intercepted in memory. This is NOT a deployable app.
"""

import os
from pathlib import Path

os.environ.update(GENERATION_ENGINE="mock", MAKEUP_GENERATION_ENGINE="mock", NAILS_PREVIEW_MODE="mock",
                  HAIRCAPSTONE_STYLE_REGISTRY_PATH=str(Path(__file__).resolve().parents[1] / "app/style_registry.json"))

from fastapi.responses import Response
from app.main import app
from central_remote_fixture import CentralRemoteScenario, png

scenario = CentralRemoteScenario()
# Hold patches for the lifetime of this test server.
boundaries = scenario.installed()
boundaries.__enter__()


@app.get("/_test/image")
async def synthetic_image():
    return Response(png(scenario.source), media_type="image/png")
