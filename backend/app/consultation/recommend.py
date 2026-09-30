"""Small deterministic provider and strict backend validation boundary."""

from hashlib import sha256
from typing import Protocol

from pydantic import ValidationError

from app.consultation.catalog import AVAILABLE_STATUSES
from app.consultation.metadata import SERVICES
from app.consultation.models import (CatalogResponse, CatalogStyle, ConsultationState,
                                     FeatureId, Preferences, ProposedRecommendation,
                                     ProposedSet, Recommendation, RecommendationSet,
                                     ResolvedChoice, StyleChoice)


class InsufficientCandidates(ValueError):
    pass


class InvalidRecommendation(ValueError):
    pass


def _words(value: str) -> set[str]:
    return {part.lower() for part in value.replace("-", " ").replace("_", " ").split() if part}


def preference_terms(preferences: Preferences) -> set[str]:
    values = [preferences.occasion, preferences.vibe, preferences.hair_length,
              preferences.hair_maintenance, preferences.makeup_intensity,
              preferences.makeup_finish, preferences.nail_color, preferences.nail_finish,
              *preferences.likes]
    return set().union(*(_words(value) for value in values if value))


def candidate_styles(styles: list[CatalogStyle], preferences: Preferences) -> list[CatalogStyle]:
    """Explicit things to avoid remove candidates; all other answers rank them."""
    avoids = set().union(*(_words(value) for value in preferences.avoids))
    terms = preference_terms(preferences)
    eligible = [style for style in styles if style.status in AVAILABLE_STATUSES
                and not (_words(" ".join(style.tags)) | _words(style.name)) & avoids]
    return sorted(eligible, key=lambda style: (-len(set(style.tags) & terms), style.style_id))


class RecommendationProvider(Protocol):
    def recommend(self, state: ConsultationState,
                  candidates: dict[FeatureId, list[CatalogStyle]]) -> ProposedSet: ...


class DeterministicProvider:
    def recommend(self, state: ConsultationState,
                  candidates: dict[FeatureId, list[CatalogStyle]]) -> ProposedSet:
        primary = candidates[state.primary_service]
        if len(primary) < 3:
            raise InsufficientCandidates("Fewer than three supported styles match these preferences.")
        terms = preference_terms(state.preferences)
        other_features = [feature for feature in SERVICES if feature != state.primary_service
                          and candidates.get(feature)]
        rows = []
        for index, style in enumerate(primary[:3]):
            matched = sorted(set(style.tags) & terms)
            reason = (f"{style.name} matches your {', '.join(matched[:2])} preference."
                      if matched else f"{style.name} is a supported look to explore.")
            complements = []
            if other_features:
                other = other_features[index % len(other_features)]
                complement = candidates[other][0]
                complements.append(StyleChoice(feature=other, style_id=complement.style_id))
            rows.append(ProposedRecommendation(
                primary=StyleChoice(feature=state.primary_service, style_id=style.style_id),
                reason=reason, complements=complements))
        return ProposedSet(recommendations=rows)


def validate_recommendations(raw: object, state: ConsultationState, catalog: CatalogResponse,
                             candidates: dict[FeatureId, list[CatalogStyle]]) -> RecommendationSet:
    """Recheck every provider-selected ID against the current active feature catalog.

    The provider cannot supply service price, duration, style names, or Nail
    execution paths; the backend resolves those from its own catalogs.
    """
    try:
        proposed = ProposedSet.model_validate(raw)
    except ValidationError as exc:
        raise InvalidRecommendation("Malformed recommendation set.") from exc
    active = {feature: {style.style_id: style for style in styles}
              for feature, styles in catalog.styles.items()}
    candidate_ids = {feature: {style.style_id for style in styles}
                     for feature, styles in candidates.items()}
    selected = set()
    resolved = []
    for row in proposed.recommendations:
        choice = row.primary
        if choice.feature != state.primary_service:
            raise InvalidRecommendation("Primary feature differs from the consultation service.")
        if choice.style_id in selected:
            raise InvalidRecommendation("Duplicate primary recommendation.")
        selected.add(choice.style_id)
        if (choice.style_id not in candidate_ids.get(choice.feature, set())
                or choice.style_id not in active.get(choice.feature, {})):
            raise InvalidRecommendation("Primary style is unavailable or excluded.")
        primary_style = active[choice.feature][choice.style_id]
        if primary_style.status not in AVAILABLE_STATUSES:
            raise InvalidRecommendation("Primary style is disabled.")
        extras = []
        seen_extras = set()
        for extra in row.complements:
            if extra.feature == state.primary_service:
                raise InvalidRecommendation("Complement must be another service.")
            pair = (extra.feature, extra.style_id)
            if pair in seen_extras:
                raise InvalidRecommendation("Duplicate complementary style.")
            seen_extras.add(pair)
            if (extra.style_id not in candidate_ids.get(extra.feature, set())
                    or extra.style_id not in active.get(extra.feature, {})):
                raise InvalidRecommendation("Complementary style is unavailable or excluded.")
            extra_style = active[extra.feature][extra.style_id]
            if extra_style.status not in AVAILABLE_STATUSES:
                raise InvalidRecommendation("Complementary style is disabled.")
            extras.append(ResolvedChoice(feature=extra.feature, style_id=extra.style_id,
                                         style_name=extra_style.name, service=SERVICES[extra.feature],
                                         nail_path=extra_style.nail_path))
        digest = sha256(f"{state.primary_service}:{choice.style_id}".encode()).hexdigest()[:12]
        resolved.append(Recommendation(
            id=f"rec-{digest}",
            primary=ResolvedChoice(feature=choice.feature, style_id=choice.style_id,
                                   style_name=primary_style.name, service=SERVICES[choice.feature],
                                   nail_path=primary_style.nail_path),
            reason=row.reason, complements=extras))
    return RecommendationSet(recommendations=resolved)
