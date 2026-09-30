"""Text-only Gemini boundary and authoritative consultation state tests."""

import asyncio
from io import BytesIO
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app import main
from app.consultation.api import build_router
from app.consultation.gemini import GeminiProvider, ProviderFailure
from app.consultation.models import ConversationProposal, Preferences
from app.consultation.store import ConsultationStore


def portrait():
    output = BytesIO()
    Image.new("RGB", (128, 96), "#617da0").save(output, format="PNG")
    return output.getvalue()


def app_with(provider):
    app = FastAPI()
    store = ConsultationStore()
    app.include_router(build_router(
        lambda: {key: route.styles for key, route in main.FEATURE_ROUTES.items()},
        main.validated_image, store, conversation=provider))
    return TestClient(app), store


def start(client, feature="hairstyle"):
    created = client.post("/consultations", json={"primary_service": feature})
    assert created.status_code == 201
    identity = created.json()["id"]
    photo = portrait()
    uploaded = client.put(f"/consultations/{identity}/photo",
                          files={"image": ("portrait.png", photo, "image/png")})
    assert uploaded.status_code == 200
    return identity, photo


def proposals(feature, candidates):
    return [{"primary": {"feature": feature, "style_id": row.style_id},
             "reason": f"{row.name} suits the stated direction.", "complements": []}
            for row in candidates[feature][:3]]


class FakeConversation:
    def __init__(self):
        self.contexts = []

    async def turn(self, state, message, candidates):
        self.contexts.append((state, message, candidates))
        if message is None:
            return ConversationProposal(status="more_information",
                assistant_message="What are you getting ready for?")
        if len([row for row in state.messages if row.role == "user"]) == 0 and "graduation" in message:
            return ConversationProposal(status="more_information",
                assistant_message="Would you prefer an easy to maintain look?",
                preferences=Preferences(occasion="graduation", vibe="clean"))
        return ConversationProposal(status="ready_for_recommendation",
            assistant_message="Here are three supported looks for your plans.",
            preferences=Preferences(hair_maintenance="low") if state.primary_service == "hairstyle"
            else Preferences(vibe="natural"),
            recommendations={"recommendations": proposals(state.primary_service, candidates)})


@pytest.mark.parametrize("feature", ["hairstyle", "makeup", "nails"])
def test_conversation_commits_preferences_and_three_real_styles(feature):
    provider = FakeConversation()
    client, store = app_with(provider)
    identity, photo = start(client, feature)
    assert client.get("/consultations/mode").json()["provider"] == "gemini"
    assert client.post(f"/consultations/{identity}/recommendations").status_code == 409
    first = client.post(f"/consultations/{identity}/turn", json={})
    assert first.status_code == 200
    assert first.json()["status"] == "more_information"
    assert first.json()["state"]["messages"][0]["role"] == "assistant"
    second = client.post(f"/consultations/{identity}/turn",
                         json={"message": "For graduation, clean and classy."})
    assert second.status_code == 200
    assert second.json()["state"]["preferences"]["occasion"] == "graduation"
    third = client.post(f"/consultations/{identity}/turn", json={"message": "Easy to maintain."})
    assert third.status_code == 200
    data = third.json()
    assert data["status"] == "ready_for_recommendation"
    rows = data["recommendations"]["recommendations"]
    assert len(rows) == len({row["primary"]["style_id"] for row in rows}) == 3
    assert all(row["primary"]["feature"] == feature for row in rows)
    assert all(row["primary"]["service"]["estimate_kind"] == "demo_only" for row in rows)
    assert all("stated direction" in row["reason"] for row in rows)
    assert store.photo_bytes(UUID(identity)) == photo
    assert data["state"]["photo"] is not None
    assert client.post(f"/consultations/{identity}/recommendations").json() == data["recommendations"]
    # Provider receives only structured state and catalog; photo bytes are not part of it.
    assert all(photo not in str(context).encode() for context in provider.contexts)


def test_one_answer_and_no_optional_preference_can_be_ready():
    class Short(FakeConversation):
        async def turn(self, state, message, candidates):
            if message is None:
                return ConversationProposal(status="more_information", assistant_message="What is the occasion?")
            return ConversationProposal(status="ready_for_recommendation",
                assistant_message="Here are three simple options.",
                preferences=Preferences(occasion="graduation"),
                recommendations={"recommendations": proposals(state.primary_service, candidates)})
    client, _ = app_with(Short())
    identity, _ = start(client)
    client.post(f"/consultations/{identity}/turn", json={})
    result = client.post(f"/consultations/{identity}/turn",
                         json={"message": "Graduation. I don't care about length, just something simple."})
    assert result.status_code == 200
    assert result.json()["status"] == "ready_for_recommendation"


@pytest.mark.parametrize("bad", [
    lambda rows: rows.__setitem__(0, {**rows[0], "primary": {"feature": "hairstyle", "style_id": "invented"}}),
    lambda rows: rows.__setitem__(1, rows[0]),
    lambda rows: rows.__setitem__(0, {**rows[0], "primary": {"feature": "makeup", "style_id": "natural_makeup"}}),
    lambda rows: rows.__setitem__(0, {**rows[0], "complements": [{"feature": "makeup", "style_id": "invented"}]}),
])
def test_bad_proposal_cannot_mutate_state(bad):
    class Bad:
        async def turn(self, state, message, candidates):
            rows = proposals("hairstyle", candidates)
            bad(rows)
            return ConversationProposal(status="ready_for_recommendation",
                assistant_message="Three choices.", recommendations={"recommendations": rows})
    client, _ = app_with(Bad())
    identity, _ = start(client)
    response = client.post(f"/consultations/{identity}/turn", json={"message": "Formal look"})
    assert response.status_code == 502
    state = client.get(f"/consultations/{identity}").json()
    assert state["messages"] == [] and state["recommendations"] is None


def test_provider_extra_fields_and_malformed_json_fail_closed():
    async def unauthorized(_):
        return {"status": "more_information", "assistant_message": "Question?",
                "price": 1}
    async def malformed(_):
        return "not-json"
    state = ConsultationStore().create("nails")
    for transport in (unauthorized, malformed):
        with pytest.raises(ProviderFailure) as error:
            asyncio.run(GeminiProvider(api_key="test", transport=transport).turn(state, "Hello", {}))
        assert error.value.category == "malformed_response"


@pytest.mark.parametrize("category,status", [("missing_key",503), ("timeout",504),
                                            ("rate_limit",429), ("provider_error",502),
                                            ("model_unavailable",503)])
def test_provider_errors_are_safe_and_state_remains_unchanged(category, status):
    class Fail:
        async def turn(self, *_):
            raise ProviderFailure(category)
    client, _ = app_with(Fail())
    identity, _ = start(client)
    response = client.post(f"/consultations/{identity}/turn", json={"message": "Hi"})
    assert response.status_code == status
    assert "AI consultant is unavailable" in response.text
    assert client.get(f"/consultations/{identity}").json()["messages"] == []


def test_missing_api_key_and_prompt_privacy():
    state = ConsultationStore().create("hairstyle")
    with pytest.raises(ProviderFailure) as error:
        asyncio.run(GeminiProvider(api_key="").turn(state, "Hello", {}))
    assert error.value.category == "missing_key"
    captured = []
    async def transport(context):
        captured.append(context)
        return {"status": "more_information", "assistant_message": "What is the occasion?"}
    asyncio.run(GeminiProvider(api_key="test", transport=transport).turn(state, "Graduation", {}))
    assert set(captured[0]) == {"primary_service", "preferences", "conversation",
                                "latest_user_message", "eligible_styles"}
    assert "photo" not in str(captured[0]).lower()


@pytest.mark.parametrize("failure,category", [
    (asyncio.TimeoutError(), "timeout"),
    ("rate_limit", "rate_limit"),
    ("model_unavailable", "model_unavailable"),
    ("bad_schema", "provider_error"),
])
def test_sdk_boundary_has_one_attempt_and_classifies_failures(monkeypatch, failure, category):
    from google import genai
    from google.genai import errors

    observed = {}

    class FakeModels:
        async def generate_content(self, **kwargs):
            observed["request"] = kwargs
            if failure == "rate_limit":
                raise errors.ClientError(429, {"message": "limited"})
            if failure == "model_unavailable":
                raise errors.ClientError(404, {"message": "missing"})
            if failure == "bad_schema":
                raise errors.ClientError(400, {"message": "bad schema"})
            raise failure

    class FakeAio:
        models = FakeModels()

        async def aclose(self):
            observed["closed"] = True

    class FakeClient:
        aio = FakeAio()

        def __init__(self, *, api_key, http_options):
            observed["options"] = http_options
            assert api_key == "test"

    monkeypatch.setattr(genai, "Client", FakeClient)
    state = ConsultationStore().create("hairstyle")
    with pytest.raises(ProviderFailure) as error:
        asyncio.run(GeminiProvider(api_key="test").turn(state, "Hello", {}))
    assert error.value.category == category
    assert observed["options"].retry_options.attempts == 1
    assert observed["options"].timeout == 30000
    assert (observed["request"]["config"].response_json_schema
            == ConversationProposal.model_json_schema())
    assert observed["closed"] is True
