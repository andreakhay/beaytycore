"""Makeup catalog kept outside the Hairstyle adapter registry.

Legacy Base experiment instructions remain intact. Live MAKEUP-001 uses the
frozen reviewed inference presets in makeup_contract, not these older prompts.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MakeupStyle:
    id: str
    name: str
    description: str
    prompt: str
    status: str = "prototype"


MAKEUP_STYLES = (
    MakeupStyle("natural_makeup", "Natural Makeup", "Subtle, balanced everyday color.", "Apply natural everyday makeup with light complexion coverage, softly defined eyes, and a muted natural lip."),
    MakeupStyle("no_makeup_makeup", "No-Makeup Makeup", "Barely visible polish and even tone.", "Apply a no-makeup makeup look: very sheer complexion correction, subtle brows, nearly invisible eye definition, and a natural lip tint."),
    MakeupStyle("soft_glam", "Soft Glam", "Blended eyes and a polished finish.", "Apply soft glam makeup with blended neutral eyeshadow, defined lashes, softly sculpted cheeks, and a polished nude lip."),
    MakeupStyle("smoky_glam", "Smoky Glam", "Smoky eyes with a refined base.", "Apply smoky glam makeup with deep blended smoky eyeshadow, defined eyeliner and lashes, balanced complexion, and a restrained nude lip."),
    MakeupStyle("dewy_peach", "Dewy Peach", "Fresh peach color and luminous skin.", "Apply dewy peach makeup with luminous skin, peach blush, warm subtle eye color, and a peach tinted lip."),
    MakeupStyle("rosy_pink", "Rosy Pink", "Soft pink eyes, cheeks, and lips.", "Apply rosy pink makeup with soft pink blush, delicate rosy eyeshadow, natural lashes, and a coordinated pink lip."),
    MakeupStyle("bronze_golden_glam", "Bronze / Golden Glam", "Warm bronze eyes and golden glow.", "Apply bronze golden glam makeup with warm bronze and gold eyeshadow, softly bronzed cheeks, defined lashes, and a warm nude lip."),
    MakeupStyle("matte_nude", "Matte Nude", "Muted neutral color with a matte finish.", "Apply matte nude makeup with a natural matte complexion, neutral brown eye definition, subtle contour, and a matte nude lip."),
    MakeupStyle("classic_red_lip", "Classic Red Lip", "A crisp red lip with simple eyes.", "Apply classic red lip makeup with a precisely defined rich red lipstick, clean complexion, and understated eye makeup."),
    MakeupStyle("bold_evening_glam", "Bold Evening Glam", "Statement eyes and evening color.", "Apply bold evening glam makeup with dramatic defined eyes, full lashes, sculpted cheeks, and a rich statement lip."),
)

MAKEUP_STYLE_BY_ID = {style.id: style for style in MAKEUP_STYLES}


def base_prompt(style: MakeupStyle) -> str:
    return (
        f"{style.prompt} Preserve the person's identity, facial proportions, face shape, eye shape, nose structure, mouth and lip geometry, "
        "expression, hairstyle, hair color, clothing, pose, lighting, framing, and background. "
        "Change only the visible makeup."
    )
