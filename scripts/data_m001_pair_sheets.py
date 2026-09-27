"""Make small, deterministic FFHQ Makeup pair sheets for human selection."""

import argparse
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageOps


def make_sheets(archive_path: Path, ids: list[str], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path) as archive:
        for page_start in range(0, len(ids), 4):
            page_ids = ids[page_start:page_start + 4]
            sheet = Image.new("RGB", (6 * 220, len(page_ids) * 244), "white")
            draw = ImageDraw.Draw(sheet)
            for row, identity in enumerate(page_ids):
                for col, variant in enumerate(["bare", *(f"makeup_{n:02d}" for n in range(1, 6))]):
                    member = f"{identity}/{variant}.jpg"
                    with Image.open(BytesIO(archive.read(member))) as image:
                        image.load()
                        if image.size != (512, 512) or image.format != "JPEG":
                            raise ValueError(f"Unexpected image: {member}")
                        thumbnail = ImageOps.contain(image.convert("RGB"), (214, 214))
                    x, y = col * 220, row * 244
                    draw.text((x + 5, y + 3), f"{identity} {variant}", fill="black")
                    sheet.paste(thumbnail, (x + 3, y + 24))
            sheet.save(output / f"pairs_{page_start // 4 + 1:02d}.jpg", quality=94)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--ids-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.ids_json.read_text(encoding="utf-8"))
    ids = data if isinstance(data, list) else [row["identity_id"] for row in data["identities"]]
    make_sheets(args.archive, ids, args.output)


if __name__ == "__main__":
    main()
