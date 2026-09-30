"""Additive consultation API. No image generation or remote inference calls."""

from collections.abc import Awaitable, Callable, Mapping
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image

from app.consultation.catalog import CatalogConfigurationError, active_catalog
from app.consultation.models import (CatalogResponse, ConsultationState, CreateConsultation,
                                     RecommendationSet, UpdateConsultation)
from app.consultation.recommend import (DeterministicProvider, InsufficientCandidates,
                                        InvalidRecommendation, RecommendationProvider, candidate_styles,
                                        validate_recommendations)
from app.consultation.store import (ConsultationStore, StaleConsultationError,
                                    StoreFullError)


def build_router(style_loaders: Callable[[], Mapping[str, Callable[[], Awaitable[list]]]],
                 validate_image: Callable[[UploadFile], Awaitable[Image.Image]],
                 store: ConsultationStore | None = None,
                 provider: RecommendationProvider | None = None) -> APIRouter:
    sessions = store or ConsultationStore()
    recommender = provider or DeterministicProvider()
    router = APIRouter(prefix="/consultations", tags=["consultations"])

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

    @router.patch("/{consultation_id}", response_model=ConsultationState)
    async def update(consultation_id: UUID, body: UpdateConsultation) -> ConsultationState:
        state_or_404(consultation_id)
        try:
            return sessions.update(consultation_id, body)
        except KeyError:
            raise HTTPException(404, "Consultation not found or expired.") from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @router.post("/{consultation_id}/recommendations", response_model=RecommendationSet)
    async def recommend(consultation_id: UUID) -> RecommendationSet:
        state = state_or_404(consultation_id)
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
        except KeyError:
            raise HTTPException(404, "Consultation not found or expired.") from None

    return router
