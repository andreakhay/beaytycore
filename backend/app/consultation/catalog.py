"""Read the *active* generation catalogs without changing their routing."""

from collections.abc import Awaitable, Callable, Mapping

from app.consultation.metadata import SERVICES, STYLE_TAGS
from app.consultation.models import CatalogResponse, CatalogStyle, FeatureId
from app.nails.contract import MODEL_STYLES, RENDERER_STYLES


AVAILABLE_STATUSES = frozenset({"prototype", "experimental", "verified", "available", "trained_preset"})


class CatalogConfigurationError(RuntimeError):
    pass


async def active_catalog(style_loaders: Mapping[str, Callable[[], Awaitable[list]]]) -> CatalogResponse:
    """Only styles exposed by the current feature routes may be recommended."""
    styles: dict[FeatureId, list[CatalogStyle]] = {}
    for feature in SERVICES:
        loader = style_loaders.get(feature)
        if loader is None:
            raise CatalogConfigurationError(f"Missing {feature} style loader")
        found = []
        seen = set()
        for style in await loader():
            if style.status not in AVAILABLE_STATUSES:
                continue
            if style.id in seen:
                raise CatalogConfigurationError(f"Duplicate {feature} style ID")
            seen.add(style.id)
            tags = STYLE_TAGS[feature].get(style.id)
            if not tags:
                raise CatalogConfigurationError(f"Missing consultation tags for {feature}/{style.id}")
            nail_path = None
            if feature == "nails":
                if style.id in MODEL_STYLES:
                    nail_path = "model"
                elif style.id in RENDERER_STYLES:
                    nail_path = "renderer"
                else:
                    raise CatalogConfigurationError(f"Unknown Nails path for {style.id}")
            found.append(CatalogStyle(feature=feature, style_id=style.id, name=style.name,
                                      description=style.description, status=style.status,
                                      tags=tags, nail_path=nail_path))
        styles[feature] = found
    return CatalogResponse(services=list(SERVICES.values()), styles=styles)
