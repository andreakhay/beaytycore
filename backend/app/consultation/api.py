"""Consultation orchestration over the existing central feature handlers."""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable, Mapping
from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.consultation.catalog import CatalogConfigurationError, active_catalog
from app.consultation.models import (CatalogResponse, ConsultationState, CreateConsultation,
                                     ConsultationMode, ConversationTurnInput,
                                     ConversationTurnResult, GenerationDetail, Preferences,
                                     RecommendationSet, UpdateConsultation)
from app.consultation.gemini import ConversationProvider, GeminiProvider, ProviderFailure
from app.consultation.recommend import (DeterministicProvider, InsufficientCandidates,
                                        InvalidRecommendation, RecommendationProvider, candidate_styles,
                                        validate_recommendations)
from app.consultation.store import (ConsultationStore, GenerationConflict,
                                    StaleConsultationError, StoreFullError)


def build_router(style_loaders: Callable[[], Mapping[str, Callable[[], Awaitable[list]]]],
                 validate_image: Callable[[UploadFile], Awaitable[Image.Image]],
                 store: ConsultationStore | None = None,
                 provider: RecommendationProvider | None = None,
                 dispatch: Callable[[str, UploadFile, str], Awaitable[object]] | None = None,
                 conversation: ConversationProvider | None = None) -> APIRouter:
    sessions = store or ConsultationStore()
    recommender = provider or DeterministicProvider()
    mode = "gemini" if conversation is not None else os.getenv("CONSULTATION_PROVIDER", "deterministic").strip().lower()
    if mode not in ("deterministic", "gemini"):
        raise ValueError("CONSULTATION_PROVIDER must be deterministic or gemini")
    conversational = conversation or (GeminiProvider() if mode == "gemini" else None)
    router = APIRouter(prefix="/consultations", tags=["consultations"])

    @router.get("/mode", response_model=ConsultationMode)
    async def consultation_mode() -> ConsultationMode:
        return ConsultationMode(provider=mode, model=conversational.model if isinstance(conversational, GeminiProvider) else None)

    def state_or_404(consultation_id: UUID) -> ConsultationState:
        try:
            return sessions.get(consultation_id)
        except KeyError:
            raise HTTPException(404, "Consultation not found or expired.") from None

    @router.get("/catalog", response_model=CatalogResponse)
    async def catalog() -> CatalogResponse:
        try:
            return await active_catalog(style_loaders())
        except CatalogConfigurationError:
            raise HTTPException(503, "Consultation catalog is not configured for the active styles.") from None

    @router.post("", response_model=ConsultationState, status_code=201)
    async def create(body: CreateConsultation) -> ConsultationState:
        try:
            return sessions.create(body.primary_service)
        except StoreFullError:
            raise HTTPException(503, "Consultation capacity reached. Try again later.") from None

    @router.get("/{consultation_id}", response_model=ConsultationState)
    async def get(consultation_id: UUID) -> ConsultationState:
        return state_or_404(consultation_id)

    @router.put("/{consultation_id}/photo", response_model=ConsultationState)
    async def photo(consultation_id: UUID, image: Annotated[UploadFile, File()]) -> ConsultationState:
        state_or_404(consultation_id)
        # The same validation contract used by /features/{feature}/generate.
        validated = await validate_image(image)
        await image.seek(0)
        content = await image.read()
        try:
            return sessions.attach_photo(consultation_id, content, image.content_type,
                                         validated.width, validated.height)
        except KeyError:
            raise HTTPException(404, "Consultation not found or expired.") from None
        except GenerationConflict as exc:
            raise HTTPException(409, str(exc)) from None

    @router.patch("/{consultation_id}", response_model=ConsultationState)
    async def update(consultation_id: UUID, body: UpdateConsultation) -> ConsultationState:
        state_or_404(consultation_id)
        try:
            return sessions.update(consultation_id, body)
        except KeyError:
            raise HTTPException(404, "Consultation not found or expired.") from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        except GenerationConflict as exc:
            raise HTTPException(409, str(exc)) from None

    @router.post("/{consultation_id}/recommendations", response_model=RecommendationSet)
    async def recommend(consultation_id: UUID) -> RecommendationSet:
        state = state_or_404(consultation_id)
        if conversational is not None:
            if state.recommendations is None:
                raise HTTPException(409, "Complete the conversation before requesting recommendations.")
            return state.recommendations
        if state.photo is None:
            raise HTTPException(409, "Upload a photo before requesting recommendations.")
        try:
            current = await active_catalog(style_loaders())
            candidates = {feature: candidate_styles(styles, state.preferences)
                          for feature, styles in current.styles.items()}
            proposed = recommender.recommend(state, candidates)
            resolved = validate_recommendations(proposed, state, current, candidates)
            sessions.save_recommendations(consultation_id, state.updated_at, resolved)
            return resolved
        except CatalogConfigurationError:
            raise HTTPException(503, "Consultation catalog is not configured for the active styles.") from None
        except InsufficientCandidates as exc:
            raise HTTPException(422, str(exc)) from None
        except InvalidRecommendation:
            raise HTTPException(502, "Recommendation output failed validation.") from None
        except StaleConsultationError:
            raise HTTPException(409, "Consultation changed; request recommendations again.") from None
        except GenerationConflict as exc:
            raise HTTPException(409, str(exc)) from None
        except KeyError:
            raise HTTPException(404, "Consultation not found or expired.") from None

    @router.post("/{consultation_id}/turn", response_model=ConversationTurnResult)
    async def turn(consultation_id: UUID, body: ConversationTurnInput) -> ConversationTurnResult:
        if conversational is None:
            raise HTTPException(409, "Conversational consultation is not enabled.")
        state_or_404(consultation_id)
        try:
            state = sessions.begin_turn(consultation_id, body.message)
        except GenerationConflict as exc:
            raise HTTPException(409, str(exc)) from None
        committed = False
        try:
            catalog = await active_catalog(style_loaders())
            candidates = {feature: candidate_styles(styles, state.preferences)
                          for feature, styles in catalog.styles.items()}
            proposal = await conversational.turn(state, body.message, candidates)
            fields = proposal.preferences.model_dump(exclude_unset=True, exclude_none=True)
            preferences = Preferences.model_validate({**state.preferences.model_dump(), **fields})
            # New exclusions from this turn must also apply before validation.
            eligible = {feature: candidate_styles(styles, preferences)
                        for feature, styles in catalog.styles.items()}
            resolved = None
            if proposal.status == "ready_for_recommendation":
                if not body.message and not any(row.role == "user" for row in state.messages):
                    raise InvalidRecommendation("At least one user answer is required.")
                updated = state.model_copy(update={"preferences": preferences})
                resolved = validate_recommendations(proposal.recommendations, updated, catalog, eligible)
            saved = sessions.finish_turn(consultation_id, state.updated_at, body.message,
                                         proposal.assistant_message, proposal.status,
                                         preferences, resolved)
            committed = True
            return ConversationTurnResult(state=saved, assistant_message=proposal.assistant_message,
                                          status=proposal.status, recommendations=resolved)
        except ProviderFailure as exc:
            logging.getLogger(__name__).warning("Consultation provider failed category=%s", exc.category)
            status = {"missing_key": 503, "timeout": 504, "rate_limit": 429,
                      "model_unavailable": 503}.get(exc.category, 502)
            raise HTTPException(status, "The AI consultant is unavailable. Please try again shortly.") from None
        except CatalogConfigurationError:
            raise HTTPException(503, "Consultation catalog is not configured for the active styles.") from None
        except InvalidRecommendation:
            raise HTTPException(502, "AI consultation output failed validation. No recommendation was saved.") from None
        except (StaleConsultationError, GenerationConflict):
            raise HTTPException(409, "Consultation changed. Please try again.") from None
        finally:
            if not committed:
                sessions.abort_turn(consultation_id)

    @router.get("/{consultation_id}/recommendations/{recommendation_id}/generation",
                response_model=GenerationDetail)
    async def generation_detail(consultation_id: UUID, recommendation_id: str) -> GenerationDetail:
        state_or_404(consultation_id)
        try:
            return sessions.detail(consultation_id, recommendation_id)
        except KeyError:
            raise HTTPException(404, "Recommendation not found.") from None

    @router.post("/{consultation_id}/recommendations/{recommendation_id}/generation",
                 response_model=GenerationDetail)
    async def generate_recommendation(consultation_id: UUID, recommendation_id: str) -> GenerationDetail:
        state = state_or_404(consultation_id)
        if dispatch is None:
            raise HTTPException(503, "Consultation generation is unavailable.")
        selected = next((row for row in (state.recommendations.recommendations
                         if state.recommendations else []) if row.id == recommendation_id), None)
        if selected is None:
            raise HTTPException(404, "Recommendation not found.")
        try:
            current = await active_catalog(style_loaders())
        except CatalogConfigurationError:
            raise HTTPException(503, "Consultation catalog is not configured for the active styles.") from None
        eligible = candidate_styles(current.styles[state.primary_service], state.preferences)
        if (selected.primary.feature != state.primary_service
                or selected.primary.style_id not in {style.style_id for style in eligible}):
            raise HTTPException(409, "This recommendation is no longer available. Request new recommendations.")
        try:
            content, content_type = sessions.begin_generation(consultation_id, recommendation_id,
                                                               state.updated_at)
        except (GenerationConflict, StaleConsultationError) as exc:
            raise HTTPException(409, str(exc)) from None
        except KeyError:
            raise HTTPException(404, "Consultation or recommendation not found.") from None

        async def run_and_record() -> GenerationDetail:
            upload = UploadFile(file=BytesIO(content), filename="consultation-photo",
                                headers=Headers({"content-type": content_type}))
            try:
                generated = await dispatch(selected.primary.feature, upload,
                                           selected.primary.style_id)
                if getattr(getattr(generated, "style", None), "id", None) != selected.primary.style_id:
                    raise RuntimeError("Generator returned a different style.")
                return sessions.finish_generation(consultation_id, recommendation_id,
                                                  generated.model_dump())
            except HTTPException as exc:
                sessions.finish_generation(consultation_id, recommendation_id, None,
                                           str(exc.detail)[:240])
                raise
            except Exception:
                sessions.finish_generation(consultation_id, recommendation_id, None,
                                           "Generation failed. Please try again.")
                raise HTTPException(500, "Generation failed. Please try again.") from None
            finally:
                await upload.close()

        # A disconnected caller cannot free the consultation's generation slot while
        # the original feature handler may still be using the serialized GPU owner.
        task = asyncio.create_task(run_and_record())
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if task.done() and not task.cancelled():
                task.exception()
            raise

    @router.post("/{consultation_id}/recommendations/{recommendation_id}/select",
                 response_model=ConsultationState)
    async def select_recommendation(consultation_id: UUID, recommendation_id: str) -> ConsultationState:
        state_or_404(consultation_id)
        try:
            return sessions.select(consultation_id, recommendation_id)
        except KeyError:
            raise HTTPException(404, "Recommendation not found.") from None
        except GenerationConflict as exc:
            raise HTTPException(409, str(exc)) from None

    return router
