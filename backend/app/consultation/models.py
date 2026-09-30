"""Public consultation contracts. These models never contain image bytes."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


FeatureId = Literal["hairstyle", "makeup", "nails"]
NailPath = Literal["model", "renderer"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Preferences(StrictModel):
    occasion: str | None = Field(default=None, max_length=80)
    vibe: str | None = Field(default=None, max_length=80)
    likes: list[str] = Field(default_factory=list, max_length=5)
    avoids: list[str] = Field(default_factory=list, max_length=5)
    notes: str | None = Field(default=None, max_length=500)
    hair_length: Literal["short", "medium", "long"] | None = None
    hair_maintenance: Literal["low", "medium", "high"] | None = None
    makeup_intensity: Literal["natural", "soft", "bold"] | None = None
    makeup_finish: Literal["dewy", "matte", "glossy"] | None = None
    nail_color: str | None = Field(default=None, max_length=40)
    nail_finish: Literal["glossy", "matte", "ombre", "french"] | None = None


class CreateConsultation(StrictModel):
    primary_service: FeatureId


class UpdateConsultation(StrictModel):
    preferences: Preferences | None = None
    message: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def has_update(self):
        if self.preferences is None and self.message is None:
            raise ValueError("Provide preferences or a message.")
        return self


class PhotoReference(StrictModel):
    id: UUID
    content_type: str
    width: int
    height: int


class ConsultationMessage(StrictModel):
    role: Literal["user"] = "user"
    content: str
    created_at: datetime


class ServiceEstimate(StrictModel):
    feature: FeatureId
    name: str
    estimated_price: int = Field(ge=0)
    currency: Literal["PHP"] = "PHP"
    estimated_duration_minutes: int = Field(gt=0)
    estimate_kind: Literal["demo_only"] = "demo_only"


class StyleChoice(StrictModel):
    feature: FeatureId
    style_id: str = Field(min_length=1)


class ProposedRecommendation(StrictModel):
    primary: StyleChoice
    reason: str = Field(min_length=1, max_length=240)
    complements: list[StyleChoice] = Field(default_factory=list, max_length=2)


class ProposedSet(StrictModel):
    recommendations: list[ProposedRecommendation] = Field(min_length=3, max_length=3)


class ResolvedChoice(StyleChoice):
    style_name: str
    service: ServiceEstimate
    nail_path: NailPath | None = None


class Recommendation(StrictModel):
    id: str
    primary: ResolvedChoice
    reason: str
    complements: list[ResolvedChoice]


class RecommendationSet(StrictModel):
    recommendations: list[Recommendation] = Field(min_length=3, max_length=3)


class ConsultationState(StrictModel):
    id: UUID
    primary_service: FeatureId
    stage: Literal["collecting", "recommended"] = "collecting"
    photo: PhotoReference | None = None
    preferences: Preferences = Field(default_factory=Preferences)
    messages: list[ConsultationMessage] = Field(default_factory=list)
    recommendations: RecommendationSet | None = None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class CatalogStyle(StrictModel):
    feature: FeatureId
    style_id: str
    name: str
    description: str
    status: str
    tags: tuple[str, ...]
    nail_path: NailPath | None = None


class CatalogResponse(StrictModel):
    services: list[ServiceEstimate]
    styles: dict[FeatureId, list[CatalogStyle]]
