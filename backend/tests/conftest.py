"""Keep backend tests independent of the developer's local .env."""

import os
from pathlib import Path


def pytest_configure() -> None:
    os.environ["GENERATION_ENGINE"] = "mock"
    os.environ["MAKEUP_GENERATION_ENGINE"] = "mock"
    os.environ["NAILS_PREVIEW_MODE"] = "mock"
    os.environ["HAIRCAPSTONE_STYLE_REGISTRY_PATH"] = str(
        Path(__file__).resolve().parents[1] / "app" / "style_registry.json")
