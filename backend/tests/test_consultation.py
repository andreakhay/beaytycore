"""CPU-only consultation contract, catalog, provider and API checks."""

from io import BytesIO
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app import main
from app.consultation.catalog import active_catalog
from app.consultation.api import build_router
from app.consultation.metadata import SERVICES
from app.consultation.models import ConsultationState, Preferences
from app.consultation.recommend import (InvalidRecommendation, candidate_styles,
                                        validate_recommendations)
from app.consultation.store import ConsultationStore, StoreFullError
from app.registry import load_registry
from app.styles import REAL_STYLE_PROMPTS


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clear_consultations():
    main.consultation_store._entries.clear()
    yield
    main.consultation_store._entries.clear()


def photo_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (128, 96), "#8aafbb").save(output, format="PNG")
    return output.getvalue()


def start(feature: str) -> tuple[str, bytes]:
    created = client.post("/consultations", json={"primary_service": feature})
    assert created.status_code == 201
    identity = created.json()["id"]
    photo = photo_bytes()
    uploaded = client.put(f"/consultations/{identity}/photo",
                          files={"image": ("photo.png", photo, "image/png")})
    assert uploaded.status_code == 200
    return identity, photo


@pytest.mark.parametrize("feature", ["hairstyle", "makeup", "nails"])
def test_service_state_photo_preferences_and_recommendations(feature):
    identity, photo = start(feature)
    initial = client.get(f"/consultations/{identity}").json()
    assert initial["primary_service"] == feature
    assert initial["stage"] == "collecting"
    assert initial["photo"]["width"] == 128
    assert initial["photo"]["height"] == 96
    assert "image" not in initial and "data_url" not in str(initial)
    assert main.consultation_store.photo_bytes(UUID(identity)) == photo

    changed = client.patch(f"/consultations/{identity}", json={
        "preferences": {"occasion": "everyday", "vibe": "soft", "likes": ["classic"]},
        "message": "I would like a simple look.",
    })
    assert changed.status_code == 200
    assert changed.json()["preferences"]["occasion"] == "everyday"
    assert changed.json()["messages"][0]["role"] == "user"
    result = client.post(f"/consultations/{identity}/recommendations")
    assert result.status_code == 200
    recommendations = result.json()["recommendations"]
    assert len(recommendations) == len({item["primary"]["style_id"] for item in recommendations}) == 3
    assert all(item["primary"]["feature"] == feature for item in recommendations)
    assert all(item["primary"]["service"]["estimate_kind"] == "demo_only" for item in recommendations)
    assert any(item["complements"] for item in recommendations)
    assert client.get(f"/consultations/{identity}").json()["stage"] == "recommended"
    changed_again = client.patch(f"/consultations/{identity}", json={"preferences": {"vibe": "bold"}})
    assert changed_again.json()["stage"] == "collecting"
    assert changed_again.json()["recommendations"] is None
    assert changed_again.json()["preferences"]["occasion"] == "everyday"


def test_invalid_state_and_photo_requests_are_rejected():
    assert client.post("/consultations", json={"primary_service": "skin"}).status_code == 422
    response = client.post("/consultations", json={"primary_service": "hairstyle"})
    identity = response.json()["id"]
    assert client.post(f"/consultations/{identity}/recommendations").status_code == 409
    assert client.put(f"/consultations/{identity}/photo",
                      files={"image": ("invalid.txt", b"bad", "text/plain")}).status_code == 415
    assert client.put(f"/consultations/{identity}/photo",
                      files={"image": ("invalid.png", b"bad", "image/png")}).status_code == 400
    assert client.patch(f"/consultations/{identity}", json={}).status_code == 422
    assert client.patch(f"/consultations/{identity}", json={"preferences": {"imagined_field": "x"}}).status_code == 422
    assert client.get("/consultations/00000000-0000-0000-0000-000000000000").status_code == 404


def test_photo_state_is_bounded_and_expires_without_persistence(monkeypatch):
    from app.consultation import store as store_module

    fixed = datetime(2026, 9, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(store_module, "now", lambda: fixed)
    sessions = ConsultationStore(max_sessions=1)
    first = sessions.create("nails")
    with pytest.raises(StoreFullError):
        sessions.create("makeup")
    monkeypatch.setattr(store_module, "now", lambda: fixed + timedelta(hours=1, seconds=1))
    with pytest.raises(KeyError):
        sessions.get(first.id)
    assert sessions.create("makeup").primary_service == "makeup"


def test_consultation_update_methods_are_allowed_from_frontend_origin():
    for method in ("PUT", "PATCH"):
        response = client.options("/consultations/00000000-0000-0000-0000-000000000000",
                                  headers={"Origin": "http://localhost:3000",
                                           "Access-Control-Request-Method": method})
        assert response.status_code == 200
        assert method in response.headers["access-control-allow-methods"]


def test_catalog_uses_current_feature_styles_and_keeps_nail_execution_paths():
    before_registry = load_registry()
    before_prompts = dict(REAL_STYLE_PROMPTS)
    response = client.get("/consultations/catalog")
    assert response.status_code == 200
    catalog = response.json()
    for feature in ("hairstyle", "makeup", "nails"):
        active = client.get(f"/features/{feature}/styles").json()
        assert {item["style_id"] for item in catalog["styles"][feature]} == {item["id"] for item in active}
        assert all(item["tags"] for item in catalog["styles"][feature])
    nails = {item["style_id"]: item["nail_path"] for item in catalog["styles"]["nails"]}
    assert nails == {"classic_red": "model", "glossy_black": "model", "nude_pink": "renderer",
                     "french_tip": "renderer", "pink_ombre": "renderer"}
    assert load_registry() == before_registry
    assert REAL_STYLE_PROMPTS == before_prompts
    assert {item["estimate_kind"] for item in catalog["services"]} == {"demo_only"}


def test_disabled_styles_are_removed_from_catalog_and_cannot_be_recommended(monkeypatch):
    original = main.FEATURE_ROUTES["hairstyle"]

    async def with_disabled():
        return [*await original.styles(), main.StyleResponse(id="disabled_test", name="Disabled",
                                                               description="Unavailable", status="disabled")]

    monkeypatch.setitem(main.FEATURE_ROUTES, "hairstyle",
                        main.FeatureRoute(original.info, with_disabled, original.generate))
    assert "disabled_test" not in {item["style_id"] for item in client.get("/consultations/catalog").json()["styles"]["hairstyle"]}
    identity, _ = start("hairstyle")
    assert client.post(f"/consultations/{identity}/recommendations").status_code == 200
    assert "disabled_test" not in str(client.get(f"/consultations/{identity}").json()["recommendations"])


def test_expanded_hair_registry_is_tagged_without_changing_generator_registry():
    import asyncio
    from app.registry import enabled_styles

    expanded = load_registry(Path(__file__).resolve().parents[1] /
                             "app/style_registry_train002_smoke.json")
    assert len(enabled_styles(expanded)) == 13
    original = {feature: route.styles for feature, route in main.FEATURE_ROUTES.items()}

    async def expanded_hair():
        return [main.StyleResponse(id=row["style_id"], name=row["display_name"],
                                   description=row["description"], status=row["support_status"])
                for row in enabled_styles(expanded)]

    catalog = asyncio.run(active_catalog({**original, "hairstyle": expanded_hair}))
    assert len(catalog.styles["hairstyle"]) == 13
    assert {row.style_id for row in catalog.styles["hairstyle"]} == {
        row["style_id"] for row in enabled_styles(expanded)}
    assert len(load_registry()["styles"]) == 3


def test_mock_provider_is_deterministic_and_does_not_call_any_generator(monkeypatch):
    async def no_generation(*_args, **_kwargs):
        raise AssertionError("Consultation invoked generation")

    for feature, route in list(main.FEATURE_ROUTES.items()):
        monkeypatch.setitem(main.FEATURE_ROUTES, feature,
                            main.FeatureRoute(route.info, route.styles, no_generation))
    identity, _ = start("hairstyle")
    first = client.post(f"/consultations/{identity}/recommendations")
    second = client.post(f"/consultations/{identity}/recommendations")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert all(row["primary"]["feature"] == "hairstyle" for row in first.json()["recommendations"])
    assert all(row["complements"][0]["feature"] in {"makeup", "nails"}
               for row in first.json()["recommendations"])


def test_candidate_filter_and_insufficient_styles(monkeypatch):
    original = main.FEATURE_ROUTES["nails"]

    async def two_styles():
        return (await original.styles())[:2]

    monkeypatch.setitem(main.FEATURE_ROUTES, "nails",
                        main.FeatureRoute(original.info, two_styles, original.generate))
    identity, _ = start("nails")
    response = client.post(f"/consultations/{identity}/recommendations")
    assert response.status_code == 422
    assert "Fewer than three" in response.json()["detail"]
    assert client.get(f"/consultations/{identity}").json()["stage"] == "collecting"


def test_avoid_phrases_target_style_traits_without_excluding_service_names():
    import asyncio

    catalog = asyncio.run(active_catalog({feature: route.styles for feature, route in main.FEATURE_ROUTES.items()}))
    makeup = {row.style_id for row in candidate_styles(
        catalog.styles["makeup"],
        Preferences(avoids=["heavy makeup", "dramatic eye makeup"]))}
    assert {"no_makeup_makeup", "natural_makeup", "matte_nude"} <= makeup
    assert {"bold_evening_glam", "smoky_glam"}.isdisjoint(makeup)

    nails = {row.style_id for row in candidate_styles(
        catalog.styles["nails"], Preferences(avoids=["black nails"]))}
    assert "glossy_black" not in nails
    assert "nude_pink" in nails


def test_validator_fails_closed_on_provider_hallucinations():
    import asyncio

    loaders = {feature: route.styles for feature, route in main.FEATURE_ROUTES.items()}
    catalog = asyncio.run(active_catalog(loaders))
    current = datetime.now(timezone.utc)
    state = ConsultationState(id=UUID("00000000-0000-0000-0000-000000000001"),
                              primary_service="hairstyle", created_at=current,
                              updated_at=current, expires_at=current)
    candidates = {feature: candidate_styles(styles, Preferences()) for feature, styles in catalog.styles.items()}
    ids = [style.style_id for style in candidates["hairstyle"][:3]]
    valid = {"recommendations": [
        {"primary": {"feature": "hairstyle", "style_id": style_id}, "reason": "Supported look", "complements": []}
        for style_id in ids]}
    assert len(validate_recommendations(valid, state, catalog, candidates).recommendations) == 3

    def rejected(changed):
        with pytest.raises(InvalidRecommendation):
            validate_recommendations(changed, state, catalog, candidates)

    rejected({"recommendations": valid["recommendations"][:2]})
    rejected({"recommendations": [{**row, "price": 1} for row in valid["recommendations"]]})
    with_price = {"recommendations": [*valid["recommendations"]]}
    with_price["recommendations"][0] = {**with_price["recommendations"][0],
                                         "primary": {"feature": "hairstyle", "style_id": ids[0],
                                                     "estimated_price": 1}}
    rejected(with_price)
    invented = {"recommendations": [*valid["recommendations"]]}
    invented["recommendations"][0] = {**invented["recommendations"][0],
                                       "primary": {"feature": "hairstyle", "style_id": "invented"}}
    rejected(invented)
    wrong_pair = {"recommendations": [*valid["recommendations"]]}
    wrong_pair["recommendations"][0] = {**wrong_pair["recommendations"][0],
                                         "primary": {"feature": "makeup", "style_id": ids[0]}}
    rejected(wrong_pair)
    duplicate = {"recommendations": [*valid["recommendations"]]}
    duplicate["recommendations"][1] = duplicate["recommendations"][0]
    rejected(duplicate)
    for complement in ({"feature": "nails", "style_id": "unknown"},
                       {"feature": "makeup", "style_id": "classic_red"},
                       {"feature": "hairstyle", "style_id": ids[1]}):
        broken = {"recommendations": [*valid["recommendations"]]}
        broken["recommendations"][0] = {**broken["recommendations"][0], "complements": [complement]}
        rejected(broken)
    disabled_catalog = catalog.model_copy(deep=True)
    disabled_style = disabled_catalog.styles["hairstyle"][0]
    disabled_catalog.styles["hairstyle"][0] = disabled_style.model_copy(update={"status": "disabled"})
    rejected_with_disabled = {"recommendations": [*valid["recommendations"]]}
    rejected_with_disabled["recommendations"][0] = {
        **rejected_with_disabled["recommendations"][0],
        "primary": {"feature": "hairstyle", "style_id": disabled_style.style_id},
    }
    with pytest.raises(InvalidRecommendation):
        validate_recommendations(rejected_with_disabled, state, disabled_catalog, candidates)


def test_service_estimates_are_backend_owned_and_not_provider_values():
    identity, _ = start("makeup")
    result = client.post(f"/consultations/{identity}/recommendations").json()
    assert all(row["primary"]["service"] == SERVICES["makeup"].model_dump()
               for row in result["recommendations"])
    assert all(row["complements"][0]["service"]["estimated_price"] ==
               SERVICES[row["complements"][0]["feature"]].estimated_price
               for row in result["recommendations"])


def test_bad_provider_is_rejected_at_http_boundary_without_generation():
    class BadProvider:
        def recommend(self, _state, _candidates):
            return {"recommendations": [{"primary": {"feature": "hairstyle", "style_id": "invented"},
                                          "reason": "Unsupported", "complements": []}] * 3}

    routes = {feature: route.styles for feature, route in main.FEATURE_ROUTES.items()}
    isolated = FastAPI()
    isolated.include_router(build_router(lambda: routes, main.validated_image,
                                         ConsultationStore(), BadProvider()))
    local = TestClient(isolated)
    created = local.post("/consultations", json={"primary_service": "hairstyle"}).json()
    identity = created["id"]
    assert local.put(f"/consultations/{identity}/photo",
                     files={"image": ("portrait.png", photo_bytes(), "image/png")}).status_code == 200
    response = local.post(f"/consultations/{identity}/recommendations")
    assert response.status_code == 502
    assert response.json()["detail"] == "Recommendation output failed validation."
