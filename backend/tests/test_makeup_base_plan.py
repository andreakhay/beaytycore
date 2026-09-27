from pathlib import Path
import sys

from PIL import Image
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from notebooks.makeup_base_001_kaggle import (  # noqa: E402
    PILOT_STYLE_IDS, expected_metadata, jobs, portrait_paths, review_sheets, run,
)
from argparse import Namespace


def test_pilot_uses_only_the_three_requested_styles_without_a_lora(tmp_path):
    image = Image.new("RGB", (128, 96), "#8aafbb")
    image.save(tmp_path / "portrait.png")
    paths = portrait_paths(tmp_path)

    pilot = jobs(paths, "pilot")
    assert [style.id for _, style in pilot] == [
        "natural_makeup", "soft_glam", "smoky_glam"
    ]
    assert all(expected_metadata(paths[0], style, "source-hash")["adapter_id"] is None
               for _, style in pilot)
    assert all(expected_metadata(paths[0], style, "source-hash")["lora_active"] is False
               for _, style in pilot)
    assert all("preserve" in expected_metadata(paths[0], style, "source-hash")["prompt"].lower()
               for _, style in pilot)


def test_plan_has_nine_jobs_for_three_identities(tmp_path, capsys):
    for portrait_id in ("identity_01", "identity_02", "identity_03"):
        Image.new("RGB", (128, 96), "#8aafbb").save(tmp_path / f"{portrait_id}.png")

    run(Namespace(phase="plan", inputs=tmp_path, output=tmp_path / "output"))

    import json
    plan = json.loads(capsys.readouterr().out)
    assert plan["job_count"] == 9
    assert plan["styles"] == list(PILOT_STYLE_IDS)
    assert plan["lora_active"] is False


def test_plan_rejects_portrait_count_other_than_three(tmp_path):
    Image.new("RGB", (128, 96), "#8aafbb").save(tmp_path / "only_one.png")
    with pytest.raises(ValueError, match="exactly 3 portraits"):
        run(Namespace(phase="plan", inputs=tmp_path, output=tmp_path / "output"))


def test_contact_sheet_compares_original_and_all_three_styles(tmp_path):
    paths = []
    for portrait_id in ("identity_01", "identity_02", "identity_03"):
        path = tmp_path / f"{portrait_id}.png"
        Image.new("RGB", (128, 96), "#8aafbb").save(path)
        paths.append(path)
        folder = tmp_path / "results" / portrait_id
        folder.mkdir(parents=True)
        Image.new("RGB", (512, 512), "#8aafbb").save(folder / "source.png")
        for style_id in PILOT_STYLE_IDS:
            style_folder = folder / style_id
            style_folder.mkdir()
            Image.new("RGB", (512, 512), "#bb8aaf").save(style_folder / "generated.png")

    sheets = review_sheets(tmp_path / "results", paths)

    assert len(sheets) == 1
    with Image.open(sheets[0]) as sheet:
        assert sheet.size == (1280, 1020)


def test_plan_rejects_ambiguous_portrait_ids(tmp_path):
    image = Image.new("RGB", (128, 96), "#8aafbb")
    image.save(tmp_path / "person.png")
    image.save(tmp_path / "person.jpg")
    with pytest.raises(ValueError, match="distinct stems"):
        portrait_paths(tmp_path)


def test_plan_rejects_unreadable_portrait_before_gpu_work(tmp_path):
    (tmp_path / "bad.png").write_bytes(b"not a PNG")
    with pytest.raises(ValueError, match="Unreadable portrait"):
        portrait_paths(tmp_path)
