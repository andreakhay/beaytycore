"""CPU-only inventory and visual sampling of an FFHQ-Makeup ZIP.

No dataset files are extracted, no model is loaded, and numeric makeup suffixes
are never interpreted as style labels. Run this before DATA-M001 selection.
"""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
import json
import platform
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import time
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageOps


NAME = re.compile(r"^(?P<identity>\d+)_(?P<variant>bare|makeup_0[1-5])\.jpe?g$", re.I)
NESTED_NAME = re.compile(r"^(?P<variant>bare|makeup_0[1-5])\.jpe?g$", re.I)
VARIANTS = ("bare", "makeup_01", "makeup_02", "makeup_03", "makeup_04", "makeup_05")
REPOSITORY = "cyberagent/FFHQ-Makeup"
REVISION = "25955d8cb70e97b00f3ee9eacffabc9d3fda81a7"
ARCHIVE_NAME = "FFHQ-Makeup.zip"


def audit(archive_path: Path, output: Path, sample_count: int) -> dict:
    started = time.monotonic()
    if sample_count < 1 or sample_count > 40:
        raise ValueError("sample_count must be between 1 and 40")
    output.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(dict)
    unrecognized = []
    duplicate_members = []
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            path = PurePosixPath(member.filename)
            match = NAME.fullmatch(path.name)
            if match:
                identity, variant = match.group("identity"), match.group("variant").lower()
            else:
                nested = NESTED_NAME.fullmatch(path.name)
                if nested and path.parent.name.isdigit():
                    identity, variant = path.parent.name, nested.group("variant").lower()
                else:
                    identity = variant = None
            if identity is None:
                unrecognized.append(member.filename)
                continue
            if variant in groups[identity]:
                duplicate_members.append([identity, variant, groups[identity][variant], member.filename])
            else:
                groups[identity][variant] = member.filename

        complete = sorted(identity for identity, members in groups.items()
                          if all(variant in members for variant in VARIANTS))
        incomplete = {identity: sorted(set(VARIANTS) - set(members))
                      for identity, members in groups.items() if identity not in complete}
        formats, dimensions, errors = Counter(), Counter(), []
        first_by_hash, duplicate_hashes = {}, []
        checked = 0
        for identity in sorted(groups):
            for variant, name in groups[identity].items():
                try:
                    raw = archive.read(name)
                    digest = sha256(raw).hexdigest()
                    if digest in first_by_hash:
                        duplicate_hashes.append([first_by_hash[digest], name, digest])
                    else:
                        first_by_hash[digest] = name
                    with Image.open(BytesIO(raw)) as im:
                        im.load()
                        formats[im.format] += 1
                        dimensions[im.size] += 1
                except Exception as exc:
                    errors.append({"identity_id": identity, "variant": variant,
                                   "member": name, "error": str(exc)})
                checked += 1
                if checked % 10000 == 0:
                    print(f"Decoded {checked} recognized images", flush=True)
        error_ids = {item["identity_id"] for item in errors}
        valid = [identity for identity in complete if identity not in error_ids]
        # Evenly cover the archive's sorted identity range. This is a visual
        # sample, not a statistical estimate of style frequency or quality.
        chosen = ([valid[(i * (len(valid) - 1)) // max(1, min(sample_count, len(valid)) - 1)]
                   for i in range(min(sample_count, len(valid)))] if valid else [])
        cells = (220, 252)
        sheet = Image.new("RGB", (cells[0] * len(VARIANTS), cells[1] * len(chosen)), "white") if chosen else None
        draw = ImageDraw.Draw(sheet) if sheet else None
        sampled = []
        for row, identity in enumerate(chosen):
            members = groups[identity]
            record = {"identity_id": identity, "variants": {}}
            for column, variant in enumerate(VARIANTS):
                name = members[variant]
                raw = archive.read(name)
                try:
                    with Image.open(BytesIO(raw)) as im:
                        im.load()
                        fmt, size = im.format, list(im.size)
                        image = ImageOps.contain(im.convert("RGB"), (210, 212))
                except Exception as exc:
                    record["variants"][variant] = {"member": name, "error": str(exc)}
                    continue
                record["variants"][variant] = {
                    "member": name, "sha256": sha256(raw).hexdigest(),
                    "format": fmt, "size": size, "bytes": len(raw),
                }
                sample_path = output / "samples" / identity / f"{variant}.jpg"
                sample_path.parent.mkdir(parents=True, exist_ok=True)
                sample_path.write_bytes(raw)
                x, y = column * cells[0], row * cells[1]
                draw.text((x + 6, y + 6), f"{identity} | {variant}", fill="black")
                sheet.paste(image, (x + (cells[0] - image.width) // 2, y + 28))
            sampled.append(record)

    sheet_path = output / "ffhq_makeup_sample_sheet.jpg" if sheet else None
    sheet_pages = []
    if sheet:
        sheet.save(sheet_path, quality=92)
        for start_row in range(0, len(chosen), 4):
            page = sheet.crop((0, start_row * cells[1], sheet.width,
                               min(start_row + 4, len(chosen)) * cells[1]))
            page_path = output / f"ffhq_makeup_sample_sheet_{start_row // 4 + 1:02d}.jpg"
            page.save(page_path, quality=94)
            sheet_pages.append(str(page_path))
    report = {
        "audit_runtime": {"python": sys.version.split()[0], "platform": platform.platform(),
                          "accelerator_used": "none", "model_loaded": False,
                          "output_free_bytes_before_report": shutil.disk_usage(output).free,
                          "duration_seconds": round(time.monotonic() - started, 2)},
        "expected_repository": REPOSITORY,
        "expected_revision": REVISION,
        "expected_archive_name": ARCHIVE_NAME,
        "source_archive": str(archive_path),
        "source_archive_sha256": file_hash(archive_path),
        "source_archive_bytes": archive_path.stat().st_size,
        "identity_groups": len(groups),
        "complete_groups": len(complete),
        "valid_groups": len(valid),
        "incomplete_groups": incomplete,
        "decode_failures": errors,
        "duplicate_members": duplicate_members,
        "duplicate_hashes": duplicate_hashes,
        "unrecognized_member_count": len(unrecognized),
        "unrecognized_member_examples": unrecognized[:30],
        "variant_counts": dict(Counter(variant for members in groups.values() for variant in members)),
        "sample_rule": "evenly spaced sorted complete identity IDs; visual sample only",
        "sampled_identities": sampled,
        "all_formats": dict(formats),
        "all_dimensions": {f"{w}x{h}": count for (w, h), count in dimensions.items()},
        "sample_file_list": [value["member"] for item in sampled for value in item["variants"].values()],
        "contact_sheet": str(sheet_path) if sheet_path else None,
        "contact_sheet_pages": sheet_pages,
        "style_warning": "makeup_01..05 are positions, not project style labels",
    }
    (output / "ffhq_makeup_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, nargs="?", help="Previously downloaded FFHQ-Makeup.zip")
    parser.add_argument("--download", action="store_true", help="Download the pinned ZIP from Hugging Face; CPU and Internet only")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=12)
    args = parser.parse_args()
    if args.download == (args.archive is not None):
        parser.error("Provide exactly one of an archive path or --download")
    archive_path = args.archive
    if args.download:
        from huggingface_hub import hf_hub_download
        archive_path = Path(hf_hub_download(REPOSITORY, ARCHIVE_NAME, repo_type="dataset", revision=REVISION))
    report = audit(archive_path, args.output, args.sample_count)
    print(json.dumps({key: report[key] for key in ("identity_groups", "complete_groups",
          "valid_groups", "variant_counts", "all_dimensions", "all_formats",
          "contact_sheet")}, indent=2))


if __name__ == "__main__":
    main()
