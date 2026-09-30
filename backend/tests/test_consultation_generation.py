"""Consultation-02 uses the real central dispatch with fake generation at its boundary."""

import asyncio
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app import main
from app.consultation.store import GenerationConflict
from tests.central_remote_fixture import CentralRemoteScenario, png


client = TestClient(main.app)


def portrait() -> bytes:
    output = BytesIO()
    Image.new("RGB", (128, 96), "#829cba").save(output, format="PNG")
    return output.getvalue()


def prepared(feature: str, photo: bytes | None = None) -> tuple[str, list[dict], bytes]:
    photo = photo or portrait()
    identity = client.post("/consultations", json={"primary_service": feature}).json()["id"]
    assert client.put(f"/consultations/{identity}/photo",
                      files={"image": ("photo.png", photo, "image/png")}).status_code == 200
    response = client.post(f"/consultations/{identity}/recommendations")
    assert response.status_code == 200
    return identity, response.json()["recommendations"], photo


@pytest.fixture(autouse=True)
def empty_sessions():
    main.consultation_store._entries.clear()
    yield
    main.consultation_store._entries.clear()


@pytest.mark.parametrize("feature", ["hairstyle", "makeup", "nails"])
def test_recommendations_reuse_photo_and_actual_feature_route(monkeypatch, feature):
    identity, rows, photo = prepared(feature)
    calls = []

    async def fake(image, style_id):
        calls.append((image.content_type, await image.read(), style_id))
        return main.GenerateResponse(status="completed", generator=f"fake_{feature}",
                                     style=main.StyleResponse(id=style_id, name="Preview",
                                                              description="", status="available"),
                                     image=main.ImageResponse(data_url="data:image/png;base64,YQ==",
                                                              content_type="image/png", width=1, height=1))

    route = main.FEATURE_ROUTES[feature]
    monkeypatch.setitem(main.FEATURE_ROUTES, feature,
                        main.FeatureRoute(route.info, route.styles, fake))
    for row in rows:
        rid = row["id"]
        response = client.post(f"/consultations/{identity}/recommendations/{rid}/generation")
        assert response.status_code == 200
        assert response.json()["generation"]["status"] == "completed"
        assert response.json()["result"]["style"]["id"] == row["primary"]["style_id"]
    assert calls == [("image/png", photo, row["primary"]["style_id"]) for row in rows]
    state = client.get(f"/consultations/{identity}").json()
    assert [row["status"] for row in state["generations"]] == ["completed"] * 3
    assert "data:image" not in str(state)
    assert client.post(f"/consultations/{identity}/recommendations/{rows[0]['id']}/generation").status_code == 409
    assert client.post(f"/consultations/{identity}/recommendations/{rows[0]['id']}/select").json()[
        "selected_recommendation_id"] == rows[0]["id"]
    assert client.get(f"/consultations/{identity}/recommendations/{rows[0]['id']}/generation").json()[
        "result"]["image"]["data_url"].startswith("data:image/")


def test_failed_look_does_not_erase_siblings_and_manual_retry_only(monkeypatch):
    identity, rows, _ = prepared("makeup")
    calls = []
    failed_style = rows[1]["primary"]["style_id"]

    async def fake(_image, style_id):
        calls.append(style_id)
        if style_id == failed_style and calls.count(style_id) == 1:
            raise HTTPException(502, "Makeup generation is temporarily unavailable.")
        return main.GenerateResponse(status="completed", generator="fake_makeup",
                                     style=main.StyleResponse(id=style_id, name="Look", description="",
                                                              status="available"),
                                     image=main.ImageResponse(data_url="data:image/png;base64,YQ==",
                                                              content_type="image/png", width=1, height=1))

    route = main.FEATURE_ROUTES["makeup"]
    monkeypatch.setitem(main.FEATURE_ROUTES, "makeup",
                        main.FeatureRoute(route.info, route.styles, fake))
    statuses = [client.post(f"/consultations/{identity}/recommendations/{row['id']}/generation").status_code
                for row in rows]
    assert statuses == [200, 502, 200]
    assert calls == [row["primary"]["style_id"] for row in rows]
    state = client.get(f"/consultations/{identity}").json()
    assert [row["status"] for row in state["generations"]] == ["completed", "failed", "completed"]
    assert state["generations"][1]["attempts"] == 1
    assert client.post(f"/consultations/{identity}/recommendations/{rows[0]['id']}/select").json()[
        "selected_recommendation_id"] == rows[0]["id"]
    assert client.post(f"/consultations/{identity}/recommendations/{rows[1]['id']}/generation").status_code == 200
    assert calls.count(failed_style) == 2
    assert len(calls) == 4
    assert client.get(f"/consultations/{identity}/recommendations/{rows[0]['id']}/generation").json()[
        "generation"]["attempts"] == 1


def test_stale_or_disabled_style_is_rejected_before_dispatch(monkeypatch):
    identity, rows, _ = prepared("hairstyle")
    called = []
    route = main.FEATURE_ROUTES["hairstyle"]

    async def disabled_styles():
        return [style for style in await route.styles() if style.id != rows[0]["primary"]["style_id"]]

    async def fake(*_args):
        called.append(True)
        raise AssertionError("Should not dispatch")

    monkeypatch.setitem(main.FEATURE_ROUTES, "hairstyle",
                        main.FeatureRoute(route.info, disabled_styles, fake))
    response = client.post(f"/consultations/{identity}/recommendations/{rows[0]['id']}/generation")
    assert response.status_code == 409
    assert called == []
    assert client.get(f"/consultations/{identity}").json()["generations"][0]["status"] == "pending"


def test_one_active_generation_blocks_competing_request_and_mutations():
    identity, rows, _ = prepared("nails")
    state = main.consultation_store.get(UUID(identity))
    main.consultation_store.begin_generation(UUID(identity), rows[0]["id"], state.updated_at)
    assert client.post(f"/consultations/{identity}/recommendations/{rows[1]['id']}/generation").status_code == 409
    assert client.patch(f"/consultations/{identity}", json={"preferences": {"vibe": "soft"}}).status_code == 409
    assert client.put(f"/consultations/{identity}/photo",
                      files={"image": ("new.png", portrait(), "image/png")}).status_code == 409
    assert client.post(f"/consultations/{identity}/recommendations").status_code == 409
    with pytest.raises(GenerationConflict):
        main.consultation_store.select(UUID(identity), rows[0]["id"])
    main.consultation_store.finish_generation(UUID(identity), rows[0]["id"], None, "Controlled failure")
    assert client.get(f"/consultations/{identity}").json()["generations"][0]["status"] == "failed"


def test_nails_path_metadata_does_not_change_routing(monkeypatch):
    identity, rows, _ = prepared("nails")
    # The existing Nails handler owns model/renderer routing. Consultation only passes the style.
    received = []
    route = main.FEATURE_ROUTES["nails"]

    async def fake(image, style_id):
        received.append((style_id, await image.read()))
        return main.GenerateResponse(status="completed", generator="fake_nails",
                                     style=main.StyleResponse(id=style_id, name="Nail look", description="",
                                                              status="available"),
                                     image=main.ImageResponse(data_url="data:image/png;base64,YQ==",
                                                              content_type="image/png", width=1, height=1))

    monkeypatch.setitem(main.FEATURE_ROUTES, "nails", main.FeatureRoute(route.info, route.styles, fake))
    for row in rows:
        assert client.post(f"/consultations/{identity}/recommendations/{row['id']}/generation").status_code == 200
    assert {row["primary"]["nail_path"] for row in rows} <= {"model", "renderer"}
    assert len(received) == 3


def test_new_photo_invalidates_old_results_and_selection(monkeypatch):
    identity, rows, _ = prepared("hairstyle")
    route = main.FEATURE_ROUTES["hairstyle"]

    async def fake(_image, style_id):
        return main.GenerateResponse(status="completed", generator="fake",
                                     style=main.StyleResponse(id=style_id, name="Look", description="",
                                                              status="available"),
                                     image=main.ImageResponse(data_url="data:image/png;base64,YQ==",
                                                              content_type="image/png", width=1, height=1))

    monkeypatch.setitem(main.FEATURE_ROUTES, "hairstyle", main.FeatureRoute(route.info, route.styles, fake))
    rid = rows[0]["id"]
    assert client.post(f"/consultations/{identity}/recommendations/{rid}/generation").status_code == 200
    assert client.post(f"/consultations/{identity}/recommendations/{rid}/select").status_code == 200
    replaced = client.put(f"/consultations/{identity}/photo",
                          files={"image": ("new.png", portrait(), "image/png")}).json()
    assert replaced["stage"] == "collecting" and replaced["recommendations"] is None
    assert replaced["generations"] == [] and replaced["selected_recommendation_id"] is None
    assert client.get(f"/consultations/{identity}/recommendations/{rid}/generation").status_code == 404


def test_consultation_uses_real_handlers_and_hybrid_nails_with_synthetic_remote():
    scenario = CentralRemoteScenario()
    with scenario.installed():
        for feature in ("hairstyle", "makeup", "nails"):
            identity, rows, _ = prepared(feature, png(scenario.source))
            chosen = rows[0]
            response = client.post(f"/consultations/{identity}/recommendations/{chosen['id']}/generation")
            assert response.status_code == 200, response.text
            assert response.json()["result"]["style"]["id"] == chosen["primary"]["style_id"]
            assert response.json()["generation"]["status"] == "completed"
            if feature == "nails":
                assert chosen["primary"]["nail_path"] == "model"
                model_calls = len([call for call in scenario.calls if call[0] == "nails"])
                assert model_calls == 5
                renderer = next(row for row in rows if row["primary"]["nail_path"] == "renderer")
                rendered = client.post(f"/consultations/{identity}/recommendations/{renderer['id']}/generation")
                assert rendered.status_code == 200, rendered.text
                assert rendered.json()["result"]["metadata"]["inference_path"] == "renderer"
                assert len([call for call in scenario.calls if call[0] == "nails"]) == model_calls
    assert {call[0] for call in scenario.calls} == {"hairstyle", "makeup", "nails"}


def test_cancelled_consultation_caller_does_not_release_active_generation(monkeypatch):
    identity, rows, _ = prepared("hairstyle")
    route = main.FEATURE_ROUTES["hairstyle"]
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow(_image, style_id):
        started.set()
        await release.wait()
        return main.GenerateResponse(status="completed", generator="fake",
                                     style=main.StyleResponse(id=style_id, name="Look", description="",
                                                              status="available"),
                                     image=main.ImageResponse(data_url="data:image/png;base64,YQ==",
                                                              content_type="image/png", width=1, height=1))

    monkeypatch.setitem(main.FEATURE_ROUTES, "hairstyle", main.FeatureRoute(route.info, route.styles, slow))
    endpoint = next(route.endpoint for route in main.app.routes
                    if route.path == "/consultations/{consultation_id}/recommendations/{recommendation_id}/generation"
                    and "POST" in route.methods)

    async def exercise():
        task = asyncio.create_task(endpoint(UUID(identity), rows[0]["id"]))
        await started.wait()
        task.cancel()
        await asyncio.sleep(0)
        state = main.consultation_store.get(UUID(identity))
        assert state.generations[0].status == "generating"
        with pytest.raises(GenerationConflict):
            main.consultation_store.begin_generation(UUID(identity), rows[1]["id"], state.updated_at)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert main.consultation_store.get(UUID(identity)).generations[0].status == "completed"

    asyncio.run(exercise())
