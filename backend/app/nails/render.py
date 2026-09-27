"""Deterministic target renderer for reviewed DATA-N001 masks."""

import numpy as np
from PIL import Image, ImageFilter

from app.nails.geometry import HandGeometry, nail_components


COLORS = {
    "classic_red": np.array([177, 19, 39]),
    "nude_pink": np.array([207, 143, 151]),
    "glossy_black": np.array([18, 18, 25]),
}


def render_target(source: Image.Image, mask_image: Image.Image, style_id: str,
                  hand: HandGeometry, *, production_palette: bool = False) -> Image.Image:
    """Keep all pixels outside the mask bit identical to the source."""
    if style_id not in (*COLORS, "french_tip", "pink_ombre"):
        raise ValueError("Unknown nail style")
    source_array = np.asarray(source.convert("RGB")).copy()
    mask = np.asarray(mask_image.convert("L")) > 127
    if mask.shape != source_array.shape[:2]:
        raise ValueError("Mask and source dimensions differ")
    output = source_array.copy()
    luminance_image = Image.fromarray(np.clip(
        source_array[..., 0] * .2126 + source_array[..., 1] * .7152
        + source_array[..., 2] * .0722, 0, 255).astype(np.uint8))
    smooth_luminance = np.asarray(luminance_image.filter(ImageFilter.GaussianBlur(radius=2.2)))
    edge_alpha = np.asarray(mask_image.convert("L").filter(ImageFilter.GaussianBlur(radius=.8))) / 255.0
    tips = [(4, 3), (8, 7), (12, 11), (16, 15), (20, 19)]
    for component in nail_components(mask):
        yy, xx = component[:, 0], component[:, 1]
        center = np.array([xx.mean(), yy.mean()])
        finger = min(tips, key=lambda pair: np.linalg.norm(center - np.array([
            hand.points[pair[0]][0] * source.width, hand.points[pair[0]][1] * source.height])))
        tip = np.array([hand.points[finger[0]][0] * source.width, hand.points[finger[0]][1] * source.height])
        base = np.array([hand.points[finger[1]][0] * source.width, hand.points[finger[1]][1] * source.height])
        direction = tip - base
        length = np.linalg.norm(direction)
        if length < 1:
            raise ValueError("Fingertip direction is degenerate")
        projection = (np.stack((xx, yy), axis=1) @ (direction / length))
        relative = (projection - projection.min()) / max(1e-6, np.ptp(projection))
        pixels = source_array[yy, xx].astype(np.float32)
        local_luminance = np.asarray(luminance_image)[yy, xx].astype(np.float32)
        smooth = smooth_luminance[yy, xx].astype(np.float32)
        # Keep the source nail's photographed lighting and small highlights.
        shade = np.clip((smooth - np.median(smooth)) * .48
                        + (local_luminance - smooth) * .85, -28, 44)[:, None]
        if style_id in COLORS:
            color = np.broadcast_to(COLORS[style_id], pixels.shape).astype(float)
        elif style_id == "french_tip":
            transition = np.clip((relative - .69) / .08, 0, 1)[:, None]
            color = np.array([216, 165, 169]) * (1-transition) + np.array([242, 239, 231]) * transition
        else:
            t = np.clip((relative - .15) / .8, 0, 1)[:, None]
            tip_pink = [198, 101, 129] if production_palette else [190, 67, 119]
            color = np.array([228, 184, 190]) * (1-t) + np.array(tip_pink) * t
        perpendicular = np.array([-direction[1], direction[0]]) / length
        cross = (np.stack((xx, yy), axis=1) - center) @ perpendicular
        width = max(1.0, np.ptp(cross))
        glint = (24 * np.exp(-((cross / width + .15) / .22) ** 2)
                 * np.exp(-((relative - .55) / .38) ** 2))[:, None]
        rendered = np.clip(color + shade + glint, 0, 255)
        alpha = np.clip(edge_alpha[yy, xx] * .95, 0, 1)[:, None]
        output[yy, xx] = np.clip(pixels * (1-alpha) + rendered * alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(output, "RGB")
