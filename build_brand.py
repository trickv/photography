#!/usr/bin/env python3
"""
Build brand1.png — the Trick van Staveren Photography watermark.

Layout (600 x 400):
  * Three lines of right-aligned peach text in the bottom-right.
  * A 90 degree arc centered on the text that wraps the upper-left,
    with a peach-fading exhaust trail.
  * A small narrow rocket at the head of the arc, pointing along the
    tangent (rightward at the top of the orbit) as if blasting off.
  * Everything sits over a soft dark drop shadow so the mark stays
    legible on light backgrounds (sky, sand, seafoam, snow).

PIL is used because ImageMagick 6 and cairosvg on this box don't
implement SVG filters, so the shadow has to be composed by hand.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Canvas + palette

W, H = 600, 400
PEACH = (255, 206, 192, 255)   # matches the original brand1.png text color
SHADOW_RGB = (0, 0, 0)

OUT_PATH = "/sessions/tender-eager-clarke/mnt/photography/brand1.png"
FONT_PATH = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
FONT_SIZE = 46

# Arc geometry — 90 degree quarter circle centered on the text block.
ARC_CX, ARC_CY = 380, 250
ARC_R = 220
ARC_THETA_START = math.radians(180)   # left of center
ARC_THETA_END = math.radians(270)     # above center (12 o'clock)
ARC_WIDTH = 5                          # px

# Rocket sits at the leading end (angle 270, i.e. top of the orbit) and
# points along the tangent of CCW motion at that point, which is +X.
ROCKET_X = ARC_CX + ARC_R * math.cos(ARC_THETA_END)
ROCKET_Y = ARC_CY + ARC_R * math.sin(ARC_THETA_END)
ROCKET_ANGLE = ARC_THETA_END + math.pi / 2  # tangent direction for CCW orbit


# ---------------------------------------------------------------------------
# Drawing helpers

def draw_trail(layer: Image.Image) -> None:
    """Draw the 90-degree arc as a peach exhaust trail that fades from
    transparent at the launch end to fully opaque at the rocket end."""
    draw = ImageDraw.Draw(layer)
    steps = 240
    for i in range(steps):
        t0 = i / steps
        t1 = (i + 1) / steps
        theta0 = ARC_THETA_START + (ARC_THETA_END - ARC_THETA_START) * t0
        theta1 = ARC_THETA_START + (ARC_THETA_END - ARC_THETA_START) * t1
        x0 = ARC_CX + ARC_R * math.cos(theta0)
        y0 = ARC_CY + ARC_R * math.sin(theta0)
        x1 = ARC_CX + ARC_R * math.cos(theta1)
        y1 = ARC_CY + ARC_R * math.sin(theta1)
        # Opacity ramp: 0 at launch end, ~1 at rocket end. Bias with a
        # gentle curve so the head is solid and the tail tapers nicely.
        alpha = int(255 * (t0 ** 0.85))
        color = (PEACH[0], PEACH[1], PEACH[2], alpha)
        draw.line([(x0, y0), (x1, y1)], fill=color, width=ARC_WIDTH)


def draw_rocket(layer: Image.Image) -> None:
    """Draw a small narrow rocket pointing along +X, then rotate the
    sprite to the arc's tangent direction and paste it at the rocket
    position."""
    # Render in a generous local sprite then rotate.
    sprite_size = 120
    sprite = Image.new("RGBA", (sprite_size, sprite_size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sprite)
    cx, cy = sprite_size // 2, sprite_size // 2

    def P(dx, dy):
        return (cx + dx, cy + dy)

    # Exhaust flame (slightly translucent peach).
    flame = (PEACH[0], PEACH[1], PEACH[2], 230)
    sd.polygon([P(-22, -4), P(-40, 0), P(-22, 4)], fill=flame)
    # Body
    sd.rectangle([P(-22, -5), P(-2, 5)], fill=PEACH)
    # Nose cone
    sd.polygon([P(-2, -5), P(12, 0), P(-2, 5)], fill=PEACH)
    # Fins
    sd.polygon([P(-20, -5), P(-28, -10), P(-14, -5)], fill=PEACH)
    sd.polygon([P(-20, 5), P(-28, 10), P(-14, 5)], fill=PEACH)
    # Porthole detail
    sd.ellipse([P(-12, -2), P(-8, 2)], fill=(122, 68, 56, 255))

    # PIL rotates counter-clockwise for positive angles. Our coord
    # system has Y down, so a +Y direction means rotating the sprite
    # so its +X axis ends up matching the tangent. The sprite's +X
    # currently points right; we want it to point in direction
    # (cos a, sin a) where a is ROCKET_ANGLE in image coords.
    deg = -math.degrees(ROCKET_ANGLE)  # PIL rotate is CCW
    rotated = sprite.rotate(deg, resample=Image.BICUBIC)

    # Paste centered on the rocket position.
    px = int(round(ROCKET_X - sprite_size / 2))
    py = int(round(ROCKET_Y - sprite_size / 2))
    layer.alpha_composite(rotated, (px, py))


def draw_text(layer: Image.Image) -> None:
    """Right-aligned three-line brand text."""
    draw = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    right_x = 560
    lines = [("Trick", 195), ("van Staveren", 250), ("Photography", 305)]
    for text, y in lines:
        # Anchor "rs" = right-baseline-ish; PIL Pillow >= 8 supports it.
        try:
            draw.text((right_x, y), text, font=font, fill=PEACH, anchor="rs")
        except (TypeError, ValueError):
            # Fallback: measure and place manually.
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            draw.text((right_x - w, y - (bbox[3] - bbox[1])),
                      text, font=font, fill=PEACH)


# ---------------------------------------------------------------------------
# Drop shadow

def build_shadow(foreground: Image.Image,
                 offset: tuple[int, int] = (3, 4),
                 blur_radius: float = 3.5,
                 strength: float = 1.6) -> Image.Image:
    """Return a same-size RGBA image holding only the drop shadow.

    `strength` > 1 pushes the blurred alpha up so the shadow stays
    opaque under the lighter parts of the foreground — important for
    legibility on bright backgrounds.
    """
    # Alpha-only mask of the foreground, scaled by the foreground's
    # own alpha so semi-transparent bits cast lighter shadows.
    alpha = foreground.split()[-1]
    # Blur the alpha.
    blurred = alpha.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    # Strengthen.
    blurred = blurred.point(lambda v: min(255, int(v * strength)))

    # Build a solid-color RGBA image using the blurred alpha.
    shadow = Image.new("RGBA", foreground.size, SHADOW_RGB + (0,))
    shadow.putalpha(blurred)

    # Offset.
    offset_img = Image.new("RGBA", foreground.size, (0, 0, 0, 0))
    offset_img.alpha_composite(shadow, offset)
    return offset_img


# ---------------------------------------------------------------------------
# Build

def main() -> None:
    # Foreground layer: arc + rocket + text, all peach.
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_trail(fg)
    draw_rocket(fg)
    draw_text(fg)

    # Shadow underneath the foreground.
    shadow = build_shadow(fg)

    composite = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    composite.alpha_composite(shadow)
    composite.alpha_composite(fg)
    composite.save(OUT_PATH, "PNG")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
