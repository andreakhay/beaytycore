"""DATA-M001 audit must not turn archive positions into style labels."""

from io import BytesIO
from pathlib import Path
import sys
from zipfile import ZipFile

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from data_m001_audit import audit  # noqa: E402


def _jpg(color):
    image = Image.new("RGB", (64, 64), color)
    data = BytesIO()
    image.save(data, format="JPEG")
    return data.getvalue()


def test_audit_counts_pairs_and_creates_sheet(tmp_path):
    source = tmp_path / "source.zip"
    with ZipFile(source, "w") as archive:
        for identity in ("000001", "000002"):
            for index, variant in enumerate(("bare", "makeup_01", "makeup_02", "makeup_03", "makeup_04", "makeup_05")):
                archive.writestr(f"FFHQ-Makeup/images/{identity}_{variant}.jpg", _jpg((index * 30, 30, 30)))
        archive.writestr("README.txt", "unrelated")
    report = audit(source, tmp_path / "audit", 2)
    assert report["identity_groups"] == 2
    assert report["complete_groups"] == 2
    assert report["unrecognized_member_count"] == 1
    assert report["all_formats"] == {"JPEG": 12}
    assert report["valid_groups"] == 2
    assert len(report["sample_file_list"]) == 12
    assert Path(report["contact_sheet"]).is_file()
    assert "not project style labels" in report["style_warning"]


def test_audit_records_incomplete_group(tmp_path):
    source = tmp_path / "source.zip"
    with ZipFile(source, "w") as archive:
        archive.writestr("000001_bare.jpg", _jpg((10, 20, 30)))
    report = audit(source, tmp_path / "audit", 1)
    assert report["complete_groups"] == 0
    assert report["valid_groups"] == 0
    assert "makeup_05" in report["incomplete_groups"]["000001"]
    assert report["contact_sheet"] is None


def test_audit_records_decode_failure_and_duplicate_pixels(tmp_path):
    source = tmp_path / "source.zip"
    with ZipFile(source, "w") as archive:
        for variant in ("bare", "makeup_01", "makeup_02", "makeup_03", "makeup_04", "makeup_05"):
            raw = b"not a jpeg" if variant == "makeup_05" else _jpg((10, 20, 30))
            archive.writestr(f"000001_{variant}.jpg", raw)
    report = audit(source, tmp_path / "audit", 1)
    assert report["complete_groups"] == 1
    assert report["valid_groups"] == 0
    assert report["decode_failures"][0]["variant"] == "makeup_05"
    assert len(report["duplicate_hashes"]) == 4


def test_audit_accepts_real_nested_identity_layout(tmp_path):
    source = tmp_path / "source.zip"
    with ZipFile(source, "w") as archive:
        for variant in ("bare", "makeup_01", "makeup_02", "makeup_03", "makeup_04", "makeup_05"):
            archive.writestr(f"000001/{variant}.jpg", _jpg((10, 20, 30)))
    report = audit(source, tmp_path / "audit", 1)
    assert report["identity_groups"] == 1
    assert report["valid_groups"] == 1
    assert report["unrecognized_member_count"] == 0
