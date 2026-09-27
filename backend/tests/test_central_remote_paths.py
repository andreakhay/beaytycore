"""Central HTTP dispatch through production clients, with synthetic boundaries."""

import base64
from io import BytesIO

from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import pytest

from app import main
from central_remote_fixture import CentralRemoteScenario, STYLES, png


@pytest.fixture
def scenario():
    with CentralRemoteScenario().installed() as scenario:
        yield scenario


@pytest.fixture
def client(scenario):
    return TestClient(main.app)


def generate(client, scenario, feature, style=None):
    return client.post(f"/features/{feature}/generate", data={"style_id": style or STYLES[feature]},
                       files={"image": ("synthetic.png", png(scenario.source), "image/png")})


@pytest.mark.parametrize("feature", STYLES)
def test_central_path_reaches_only_its_remote_client(client, scenario, feature):
    response = generate(client, scenario, feature)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed" and body["style"]["id"] == STYLES[feature]
    assert body["metadata"]["feature"] == feature
    assert scenario.calls == [(feature, STYLES[feature])] * (5 if feature == "nails" else 1)
    if feature == "nails":
        assert body["generator"] == "nails_hybrid"
        assert body["metadata"]["inference_path"] == "model"
        assert body["metadata"]["nails_edited"] == 5
        assert "mask_refinement" in body["metadata"]["timing_seconds"]
        assert_preservation(scenario, body)


def assert_preservation(scenario, body):
    content = base64.b64decode(body["image"]["data_url"].split(",", 1)[1])
    with Image.open(BytesIO(content)) as image:
        before, after = np.asarray(scenario.source), np.asarray(image)
        outside = np.asarray(scenario.refined) == 0
        assert np.array_equal(before[outside], after[outside])
        assert np.any(before[~outside] != after[~outside])


@pytest.mark.parametrize("style", ["nude_pink", "french_tip", "pink_ombre"])
def test_central_nails_renderer_needs_no_remote_service(client, scenario, style):
    scenario.failures["nails"] = "unavailable"
    response = generate(client, scenario, "nails", style)
    assert response.status_code == 200
    assert response.json()["metadata"]["inference_path"] == "renderer"
    assert scenario.calls == []
    assert_preservation(scenario, response.json())


@pytest.mark.parametrize("failed", STYLES)
def test_remote_outage_is_scoped_and_recovers(client, scenario, failed):
    scenario.failures[failed] = "unavailable"
    assert generate(client, scenario, failed).status_code == 502
    for other in STYLES:
        if other != failed:
            assert generate(client, scenario, other).status_code == 200
    del scenario.failures[failed]
    assert generate(client, scenario, failed).status_code == 200


@pytest.mark.parametrize("feature", STYLES)
@pytest.mark.parametrize("failure", ["timeout", "inference_error", "not_ready", "invalid_json",
                                     "invalid_image", "invalid_metadata"])
def test_remote_errors_are_controlled(client, scenario, feature, failure):
    scenario.failures[feature] = failure
    response = generate(client, scenario, feature)
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert isinstance(detail, str) and detail
    assert "traceback" not in detail and "synthetic" not in detail


@pytest.mark.parametrize("feature", ["makeup", "nails"])
def test_existing_provenance_checks_remain_active(client, scenario, feature):
    scenario.failures[feature] = "wrong_provenance"
    assert generate(client, scenario, feature).status_code == 502


def test_remote_discovery_and_validation_do_not_invoke_inference(client, scenario):
    assert {item["id"] for item in client.get("/features").json()} == set(STYLES)
    catalogs = {feature: {style["id"] for style in client.get(f"/features/{feature}/styles").json()}
                for feature in STYLES}
    for feature, ids in catalogs.items():
        assert STYLES[feature] in ids
        for other, other_ids in catalogs.items():
            if other != feature:
                assert not ids & other_ids
                assert generate(client, scenario, feature, STYLES[other]).status_code == 400
        route = f"/features/{feature}/generate"
        assert client.post(route, data={"style_id": STYLES[feature]}).status_code == 422
        assert client.post(route, json={"style_id": STYLES[feature], "image": "bad"}).status_code == 422
        for content in (b"", b"invalid image"):
            assert client.post(route, data={"style_id": STYLES[feature]},
                               files={"image": ("bad.png", content, "image/png")}).status_code == 400
    assert client.get("/features/unknown/styles").status_code == 404
    assert generate(client, scenario, "unknown", "crew_cut").status_code == 404
    assert scenario.calls == []
