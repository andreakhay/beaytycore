"""Editorial recommendation tags and demo-only service estimates.

Style names, availability, and generator configuration stay in the existing
feature catalogs. Missing tags fail closed for consultation only.
"""

from app.consultation.models import FeatureId, ServiceEstimate


SERVICES: dict[FeatureId, ServiceEstimate] = {
    "hairstyle": ServiceEstimate(feature="hairstyle", name="Hairstyle", estimated_price=600,
                                  estimated_duration_minutes=60),
    "makeup": ServiceEstimate(feature="makeup", name="Makeup", estimated_price=500,
                               estimated_duration_minutes=45),
    "nails": ServiceEstimate(feature="nails", name="Nails", estimated_price=350,
                              estimated_duration_minutes=45),
}

# Tags describe visible style direction. They are demo guidance, not claims
# about suitability, real appointment length, or model output quality.
STYLE_TAGS: dict[FeatureId, dict[str, tuple[str, ...]]] = {
    "hairstyle": {
        "crew_cut": ("short", "clean", "classic", "low", "everyday"),
        "bob_hair": ("short", "classic", "polished", "medium", "everyday"),
        "layered_hair": ("long", "soft", "layered", "medium", "everyday"),
        "bun": ("long", "polished", "formal", "medium"),
        "curtain_hair": ("medium", "soft", "relaxed", "everyday"),
        "perm_curls": ("medium", "curly", "bold", "high"),
        "pixie_cut": ("short", "textured", "bold", "low"),
        "pompadour_undercut": ("short", "bold", "formal", "high"),
        "ponytail": ("long", "classic", "everyday", "low"),
        "shag_hair": ("medium", "textured", "relaxed", "medium"),
        "shoulder_length_hair": ("medium", "classic", "soft", "medium"),
        "side_part_undercut": ("short", "clean", "formal", "medium"),
        "wavy_hair": ("long", "wavy", "soft", "medium"),
        # The six mock-only Hair styles remain previewable in mock mode.
        "crew-cut": ("short", "clean", "classic", "low"),
        "textured-crop": ("short", "textured", "relaxed", "low"),
        "curtain": ("medium", "soft", "relaxed", "medium"),
        "bob": ("short", "classic", "polished", "medium"),
        "pixie": ("short", "textured", "bold", "low"),
        "layered": ("long", "soft", "layered", "medium"),
    },
    "makeup": {
        "natural_makeup": ("natural", "soft", "everyday", "dewy"),
        "no_makeup_makeup": ("natural", "minimal", "everyday"),
        "soft_glam": ("soft", "glam", "formal"),
        "smoky_glam": ("bold", "smoky", "evening"),
        "dewy_peach": ("soft", "peach", "dewy", "everyday"),
        "rosy_pink": ("soft", "pink", "everyday"),
        "bronze_golden_glam": ("bold", "bronze", "gold", "evening"),
        "matte_nude": ("natural", "nude", "matte", "everyday"),
        "classic_red_lip": ("bold", "red", "classic", "formal"),
        "bold_evening_glam": ("bold", "glam", "evening"),
    },
    "nails": {
        "classic_red": ("red", "classic", "glossy", "bold"),
        "nude_pink": ("pink", "nude", "glossy", "natural"),
        "glossy_black": ("black", "bold", "glossy"),
        "french_tip": ("pink", "white", "french", "classic"),
        "pink_ombre": ("pink", "ombre", "soft"),
    },
}
