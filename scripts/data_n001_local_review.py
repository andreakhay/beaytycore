"""Create identity-level visual review sheets from a derived DATA-N001 archive."""

import argparse
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw


STYLES = ("classic_red", "nude_pink", "glossy_black", "french_tip", "pink_ombre")
FINGERS = ("thumb", "index", "middle", "ring", "little")


def build(archive_path: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Localized archive CRC failure")
        rows = json.loads(archive.read("manifests/pairs.json"))
        identities = defaultdict(dict)
        for row in rows:
            identities[row["identity_id"]][(row["style_id"], row["finger_id"])] = row
        hashes = {}
        for identity, pairs in sorted(identities.items()):
            sheet = Image.new("RGB", (5 * 260, 5 * 276), "white")
            draw = ImageDraw.Draw(sheet)
            for row_index, style in enumerate(STYLES):
                for column, finger in enumerate(FINGERS):
                    x, y = column * 260, row_index * 276
                    entry = pairs.get((style, finger))
                    draw.text((x + 4, y + 2), f"{identity} {style} {finger}", fill="black")
                    if entry is None:
                        draw.text((x + 45, y + 110), "EXCLUDED", fill="red")
                        continue
                    for index, role in enumerate(("reference", "target")):
                        member = f"{entry['split']}/{role}/{entry['pair_id']}.png"
                        content = archive.read(member)
                        if sha256(content).hexdigest() != entry[f"{role}_sha256"]:
                            raise ValueError(f"Member hash mismatch: {member}")
                        with Image.open(BytesIO(content)) as source:
                            tile = source.convert("RGB").resize((128, 128), Image.Resampling.BICUBIC)
                        sheet.paste(tile, (x + 2 + index * 130, y + 20))
                        if index == 1:
                            # Enlarged target reveals nail boundary quality.
                            sheet.paste(tile, (x + 65, y + 150))
            path = output / f"{identity}.jpg"
            sheet.save(path, quality=94)
            hashes[identity] = sha256(path.read_bytes()).hexdigest()
    return hashes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.archive, args.output), indent=2))
