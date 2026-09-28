"""Select the additive unified GPU endpoint or the original per-feature endpoint."""

import os


def destination(feature: str, legacy_url: str, legacy_key: str) -> tuple[str, str]:
    shared_url = os.getenv("AI_REMOTE_URL", "").strip()
    shared_key = os.getenv("AI_REMOTE_API_KEY", "").strip()
    if shared_url or shared_key:
        if not shared_url or not shared_key:
            raise RuntimeError("Set both AI_REMOTE_URL and AI_REMOTE_API_KEY for the unified GPU service.")
        return f"{shared_url.rstrip('/')}/{feature}", shared_key
    return os.getenv(legacy_url, ""), os.getenv(legacy_key, "")
