"""Record the exact localized pairs delivered to each AI Toolkit train step.

This module is copied beside the pinned AI Toolkit entrypoint. A single guarded
call in its trainer invokes trace_batch immediately after fetching each batch.
"""

import json
import os
from pathlib import Path


_ROWS = None


def trace_batch(step, accumulation_index, batch):
    global _ROWS
    if batch is None:
        raise RuntimeError("NAILS-001-LOCAL received an empty training batch")
    if _ROWS is None:
        manifest = Path(os.environ["NAILS001_LOCAL_MANIFEST"])
        rows = json.loads(manifest.read_text(encoding="utf-8"))
        _ROWS = {row["pair_id"]: row for row in rows if row["split"] == "train"}
    output = Path(os.environ["NAILS001_LOCAL_TRACE"])
    target_root = Path(os.environ["NAILS001_LOCAL_TARGET_ROOT"]).resolve()
    for batch_position, item in enumerate(batch.file_items):
        path = Path(item.path).resolve()
        if path.parent != target_root or path.suffix.lower() != ".png":
            raise RuntimeError(f"Unexpected training target path: {path}")
        row = _ROWS.get(path.stem)
        if row is None:
            raise RuntimeError(f"Unlisted localized training pair: {path.stem}")
        record = {"step": step, "accumulation_index": accumulation_index,
                  "batch_position": batch_position, "pair_id": row["pair_id"],
                  "identity_id": row["identity_id"], "finger_id": row["finger_id"],
                  "style_id": row["style_id"], "target_path": str(path)}
        with output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
