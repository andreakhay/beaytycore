"""Make deterministic bare portrait sheets for DATA-M001 source selection.

This CPU-only utility reads the verified FFHQ-Makeup ZIP. It does not infer or
store demographic labels and does not load an image generation model.
"""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageOps


def candidate_ids(archive: ZipFile, count: int) -> list[tuple[str, str]]:
    entries = []
    for name in archive.namelist():
        path = PurePosixPath(name)
        if path.name == "bare.jpg" and path.parent.name.isdigit():
            entries.append((path.parent.name, name))
    entries.sort()
    if not entries or count < 1:
        raise ValueError("No nested bare portraits or invalid count")
    take = min(count, len(entries))
    return [entries[(index * (len(entries) - 1)) // max(1, take - 1)] for index in range(take)]


def make_sheets(source: Path, output: Path, count: int = 80) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with ZipFile(source) as archive:
        chosen = candidate_ids(archive, count)
        for page_index in range((len(chosen) + 19) // 20):
            page_entries = chosen[page_index * 20:(page_index + 1) * 20]
            sheet = Image.new("RGB", (5 * 192, 4 * 216), "white")
            draw = ImageDraw.Draw(sheet)
            for position, (identity, member) in enumerate(page_entries):
                raw = archive.read(member)
                with Image.open(BytesIO(raw)) as image:
                    image.load()
                    if image.format != "JPEG" or image.size != (512, 512):
                        raise ValueError(f"Unexpected source image: {member}")
                    thumbnail = ImageOps.contain(image.convert("RGB"), (184, 184))
                x, y = (position % 5) * 192, (position // 5) * 216
                draw.text((x + 6, y + 3), identity, fill="black")
                sheet.paste(thumbnail, (x + (192 - thumbnail.width) // 2, y + 24))
                records.append({"identity_id": identity, "source_member": member,
                                "source_sha256": sha256(raw).hexdigest(),
                                "sheet_page": page_index + 1})
            sheet.save(output / f"bare_candidates_{page_index + 1:02d}.jpg", quality=92)
    report = {"source_archive": str(source), "selection_rule": "evenly spaced sorted bare identity IDs",
              "candidate_count": len(records), "candidates": records}
    (output / "bare_candidates.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=80)
    args = parser.parse_args()
    print(json.dumps({key: value for key, value in make_sheets(args.archive, args.output, args.count).items()
                      if key != "candidates"}, indent=2))


if __name__ == "__main__":
    main()
