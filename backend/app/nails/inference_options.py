"""Bounded Nails latency comparison; the evaluated default remains 20 steps."""

import os

from app.nails.contract import STEPS

SUPPORTED_STEPS = (8, 12, STEPS)


def validate_steps(value: int | str) -> int:
    if str(value).strip() not in {str(step) for step in SUPPORTED_STEPS}:
        raise ValueError("Nails inference steps must be 8, 12 or 20")
    return int(str(value).strip())


def configured_steps() -> int:
    try:
        return validate_steps(os.getenv("NAILS_INFERENCE_STEPS", str(STEPS)))
    except ValueError:
        raise RuntimeError("NAILS_INFERENCE_STEPS must be 8, 12 or 20") from None
