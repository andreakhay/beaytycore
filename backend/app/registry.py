"""Shared, fail-closed contract for real hairstyle and adapter routing."""

import json
import os
from pathlib import Path


REGISTRY_PATH = Path(__file__).with_name("style_registry.json")


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    if path == REGISTRY_PATH and os.environ.get("HAIRCAPSTONE_STYLE_REGISTRY_PATH"):
        path = Path(os.environ["HAIRCAPSTONE_STYLE_REGISTRY_PATH"])
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not data.get("base_model_id") or not data.get("base_model_revision"):
        raise ValueError("Invalid hairstyle registry header")
    adapters = data.get("adapters")
    styles = data.get("styles")
    if not isinstance(adapters, dict) or not isinstance(styles, list):
        raise ValueError("Invalid hairstyle registry entries")
    for adapter_id, adapter in adapters.items():
        if (not adapter_id or not isinstance(adapter, dict)
                or adapter.get("status") not in {"enabled", "disabled"}
                or not isinstance(adapter.get("checkpoint_sha256"), str)
                or len(adapter["checkpoint_sha256"]) != 64
                or not isinstance(adapter.get("training_steps"), int)
                or adapter["training_steps"] <= 0
                or not adapter.get("experiment") or not adapter.get("dataset_version")):
            raise ValueError(f"Invalid adapter registry entry: {adapter_id}")
    seen = set()
    for style in styles:
        if not isinstance(style, dict):
            raise ValueError("Invalid hairstyle registry record")
        style_id = style.get("style_id")
        if (not isinstance(style_id, str) or not style_id or style_id in seen
                or style.get("adapter_id") not in adapters
                or style.get("support_status") not in {"experimental", "verified", "disabled"}
                or any(not style.get(key) for key in ("display_name", "description", "prompt", "training_label"))):
            raise ValueError(f"Invalid hairstyle registry record: {style_id}")
        seen.add(style_id)
    return data


def enabled_styles(registry: dict) -> list[dict]:
    return [style for style in registry["styles"]
            if style["support_status"] in {"experimental", "verified"}
            and registry["adapters"][style["adapter_id"]]["status"] == "enabled"]


def styles_by_id(registry: dict) -> dict[str, dict]:
    return {style["style_id"]: style for style in enabled_styles(registry)}


def styles_for_adapter(registry: dict, adapter_id: str) -> set[str]:
    return {style["style_id"] for style in enabled_styles(registry) if style["adapter_id"] == adapter_id}
