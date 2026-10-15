"""
ui/render.py
============
Pillow-based rendering helpers.

* ``gradient_image`` — smooth pastel background built from colours sampled
  from the approved reference (Gaussian-weighted blend on a tiny grid, then
  bicubic upscaled and cached).  No tiling, no per-pixel Tk drawing.
* ``compose_background`` — gradient + soft panel shadows + anti-aliased
  rounded panel surfaces, baked into one image so panel corners are smooth
  against the *gradient* (CustomTkinter frames cannot be transparent).
* ``text_image`` — tracked / multi-colour / gradient text (used for the
  wordmark and the "How can I help you today?" headline).
"""
from __future__ import annotations

import math
import os
import sys
from functools import lru_cache
from typing import Iterable, Sequence, Union

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Gradient
# ---------------------------------------------------------------------------

# (x, y, colour) sampled from the reference; x,y normalised to the client area.
_ANCHORS: list[tuple[float, float, str]] = [
    (0.0315, 0.0084, "#d6e8fc"), (0.0315, 0.0823, "#d6e6fc"), (0.0315, 0.1561, "#e0ebfc"),
    (0.0315, 0.2300, "#95c3fc"), (0.0315, 0.3038, "#9db9fc"), (0.0315, 0.3776, "#bfb8fc"),
    (0.0315, 0.4515, "#eec7fb"), (0.0315, 0.5253, "#dbcefa"), (0.0315, 0.5992, "#bac6fc"),
    (0.0315, 0.6730, "#bfc8fc"), (0.0315, 0.7468, "#ded6fa"), (0.0315, 0.8207, "#edd8f6"),
    (0.0315, 0.8945, "#fdcee1"), (0.0315, 0.9684, "#fdb9cf"),
    (0.0662, 0.0084, "#dceafc"), (0.0662, 0.1561, "#cce1fd"), (0.0662, 0.3038, "#a6c4fc"),
    (0.0662, 0.4515, "#f7d5f7"), (0.0662, 0.5992, "#a5c5fc"), (0.0662, 0.7468, "#e8ddf5"),
    (0.0662, 0.8945, "#fddfe0"),
    (0.9943, 0.0084, "#b4d1fd"), (0.9943, 0.0823, "#a8d0fd"), (0.9943, 0.1561, "#9fd2fd"),
    (0.9943, 0.2300, "#a5d9fd"), (0.9943, 0.3038, "#aedafd"), (0.9943, 0.3776, "#b1ddfd"),
    (0.9943, 0.4515, "#bde0fd"), (0.9943, 0.5253, "#c7e0fd"), (0.9943, 0.5992, "#d4e2fd"),
    (0.9943, 0.6730, "#e3e3fd"), (0.9943, 0.7468, "#f0dafd"), (0.9943, 0.8207, "#ebcafc"),
    (0.9943, 0.8945, "#e0c8fc"), (0.9943, 0.9684, "#ebc9fc"),
    (0.0946, 0.0137, "#cce3fd"), (0.1828, 0.0137, "#b8d8fd"), (0.2711, 0.0137, "#bcd3fd"),
    (0.3594, 0.0137, "#c0d3fa"), (0.4477, 0.0137, "#d3d6f0"), (0.5359, 0.0137, "#f8dde0"),
    (0.6242, 0.0137, "#fdd7cb"), (0.7125, 0.0137, "#edc3d6"), (0.8008, 0.0137, "#b5b5ea"),
    (0.8890, 0.0137, "#a4bdfa"), (0.9773, 0.0137, "#aecffd"),
    (0.0378, 0.9895, "#febacd"), (0.1261, 0.9895, "#fec8c4"), (0.2144, 0.9895, "#fedbe7"),
    (0.3026, 0.9895, "#c8d6fb"), (0.3909, 0.9895, "#a4d0fc"), (0.4792, 0.9895, "#c2ddfc"),
    (0.5675, 0.9895, "#bbbcfc"), (0.6557, 0.9895, "#bcbbfc"), (0.7440, 0.9895, "#bcc5fc"),
    (0.8323, 0.9895, "#cdd4fd"), (0.9206, 0.9895, "#d2c3fc"),
    (0.0946, 0.9578, "#fec8c5"), (0.2018, 0.9578, "#fddbd6"), (0.3090, 0.9578, "#c0d5fc"),
    (0.4161, 0.9578, "#b0d7fc"), (0.5233, 0.9578, "#d2dffc"), (0.6305, 0.9578, "#c0c0fb"),
    (0.7377, 0.9578, "#c8cdfc"),
    (0.7402, 0.0084, "#d7bee0"), (0.7402, 0.1139, "#cdbbe4"), (0.7402, 0.2194, "#c4c4ed"),
    (0.7402, 0.3249, "#c8ccf6"), (0.7402, 0.4304, "#d0cdfc"), (0.7402, 0.5359, "#eae4fc"),
    (0.7402, 0.6414, "#e6e5fd"), (0.7402, 0.7468, "#eee8fc"), (0.7402, 0.8523, "#eee6fc"),
    (0.7402, 0.9578, "#c8cdfc"),
]

_GRID_W, _GRID_H = 96, 64
_ASPECT = 1586 / 948  # x distances are stretched by this so blobs stay round


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


@lru_cache(maxsize=1)
def _gradient_small() -> Image.Image:
    anchors = [(x * _ASPECT, y, _hex(c)) for x, y, c in _ANCHORS]
    sigma2 = 2 * (0.085 ** 2)
    img = Image.new("RGB", (_GRID_W, _GRID_H))
    px = img.load()
    for j in range(_GRID_H):
        ny = j / (_GRID_H - 1)
        for i in range(_GRID_W):
            nx = (i / (_GRID_W - 1)) * _ASPECT
            tw = 0.0
            r = g = b = 0.0
            for ax, ay, (cr, cg, cb) in anchors:
                d2 = (nx - ax) ** 2 + (ny - ay) ** 2
                w = math.exp(-d2 / sigma2)
                tw += w
                r += w * cr
                g += w * cg
                b += w * cb
            tw += 1e-9
            px[i, j] = (int(r / tw), int(g / tw), int(b / tw))
    return img


@lru_cache(maxsize=8)
def gradient_image(width: int, height: int) -> Image.Image:
    """Smooth pastel gradient of the requested size (cached)."""
    return _gradient_small().resize(
        (max(2, width), max(2, height)), Image.Resampling.BICUBIC
    )


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

PanelSpec = tuple  # (x0, y0, x1, y1, radius, fill_hex)


def _rounded_mask(w: int, h: int, radius: float, inset: float = 0.0, ss: int = 3) -> Image.Image:
    big = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(big)
    i = inset * ss
    d.rounded_rectangle(
        (i, i, w * ss - 1 - i, h * ss - 1 - i),
        radius=max(1.0, (radius - inset) * ss),
        fill=255,
    )
    return big.resize((w, h), Image.Resampling.LANCZOS)


def compose_background(width: int, height: int, panels: Iterable[PanelSpec]) -> Image.Image:
    """Gradient + shadows + panel surfaces for a ``width`` x ``height`` client."""
    base = gradient_image(width, height).copy().convert("RGBA")
    panels = list(panels)

    if panels:
        # Soft shadows: blur a coarse mask, tint, composite.
        q = 4
        sw, sh = max(1, width // q), max(1, height // q)
        shadow = Image.new("L", (sw, sh), 0)
        sd = ImageDraw.Draw(shadow)
        for x0, y0, x1, y1, r, _ in panels:
            sd.rounded_rectangle(
                ((x0 + 2) / q, (y0 + 10) / q, (x1 - 2) / q, (y1 + 8) / q),
                radius=r / q, fill=120,
            )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10 / q * 1.6))
        shadow = shadow.resize((width, height), Image.Resampling.BICUBIC)
        tint = Image.new("RGBA", (width, height), (96, 104, 190, 255))
        base = Image.composite(tint, base, shadow.point(lambda v: int(v * 0.34)))

    for x0, y0, x1, y1, r, fill in panels:
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        w, h = x1 - x0, y1 - y0
        if w < 4 or h < 4:
            continue
        outer = _rounded_mask(w, h, r)
        inner = _rounded_mask(w, h, r, inset=1.4)
        base.paste(Image.new("RGBA", (w, h), (255, 255, 255, 255)), (x0, y0), outer)
        base.paste(Image.new("RGBA", (w, h), fill), (x0, y0), inner)
    return base.convert("RGB")


# ---------------------------------------------------------------------------
# Text images
# ---------------------------------------------------------------------------

_WIN_FONTS = {
    False: ("segoeui.ttf", "seguisb.ttf"),
    True: ("segoeuib.ttf", "seguisb.ttf"),
}
_FALLBACKS = {
    False: ("Selawik", "selawk.ttf", "DejaVuSans.ttf", "arial.ttf"),
    True: ("selawkb.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"),
}


@lru_cache(maxsize=64)
def _font(size: int, bold: bool, semibold: bool = False) -> ImageFont.FreeTypeFont:
    names: list[str] = []
    if sys.platform.startswith("win"):
        win = os.environ.get("WINDIR", r"C:\Windows")
        pick = ("seguisb.ttf",) if semibold else _WIN_FONTS[bold][:1]
        names += [os.path.join(win, "Fonts", n) for n in pick + _WIN_FONTS[bold]]
    names += list(_FALLBACKS[bold])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


Fill = Union[str, Sequence[str]]  # a colour, or gradient stops


def _lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient_strip(w: int, h: int, stops: Sequence[str]) -> Image.Image:
    cols = [_hex(s) for s in stops]
    strip = Image.new("RGB", (max(1, w), 1))
    px = strip.load()
    for x in range(max(1, w)):
        t = x / max(1, w - 1) * (len(cols) - 1)
        i = min(int(t), len(cols) - 2)
        px[x, 0] = _lerp(cols[i], cols[i + 1], t - i)
    return strip.resize((max(1, w), max(1, h)), Image.Resampling.NEAREST)


def text_image(
    runs: Sequence[tuple[str, Fill]],
    size: int,
    *,
    bold: bool = True,
    semibold: bool = False,
    tracking: float = 0.0,
    ss: int = 3,
    trailing: Sequence[str] | None = None,
) -> tuple[Image.Image, tuple[int, int]]:
    """Render coloured/gradient text.

    Returns ``(image, (logical_w, logical_h))``.  ``image`` is ``ss`` times
    larger than the logical size so CustomTkinter can downsample it crisply.
    ``trailing`` optionally appends a short gradient rule (the wordmark dash).
    """
    font = _font(size * ss, bold, semibold)
    ascent, descent = font.getmetrics()
    track = tracking * ss
    gap = 0
    segs: list[tuple[str, Fill, float]] = []
    total = 0.0
    for text, fill in runs:
        width = sum(font.getlength(ch) + track for ch in text) if track else font.getlength(text)
        segs.append((text, fill, width))
        total += width
    rule_w = rule_h = 0
    if trailing:
        gap = int(size * 1.6 * ss)
        rule_w, rule_h = int(size * 3.4 * ss), max(2, int(size * 0.16 * ss))
        total += gap + rule_w
    W, H = int(math.ceil(total)) + ss * 2, ascent + descent + ss * 2
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = float(ss)
    for text, fill, width in segs:
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        if track:
            cx = x
            for ch in text:
                md.text((cx, ss), ch, font=font, fill=255)
                cx += font.getlength(ch) + track
        else:
            md.text((x, ss), text, font=font, fill=255)
        if isinstance(fill, str):
            layer = Image.new("RGBA", (W, H), fill)
        else:
            strip = _gradient_strip(int(width), H, fill)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            layer.paste(strip.convert("RGBA"), (int(x), 0))
        out.paste(layer, (0, 0), mask)
        x += width
    if trailing:
        rx = int(x - track + gap)
        ry = ss + int(ascent * 0.62)
        strip = _gradient_strip(rule_w, rule_h, trailing).convert("RGBA")
        rmask = Image.new("L", (rule_w, rule_h), 0)
        ImageDraw.Draw(rmask).rounded_rectangle(
            (0, 0, rule_w - 1, rule_h - 1), radius=rule_h // 2, fill=255
        )
        out.paste(strip, (rx, ry), rmask)
    return out, (int(math.ceil(W / ss)), int(math.ceil(H / ss)))


def fit_tracking(text: str, size: int, target_width: float, *, bold: bool = True) -> float:
    """Letter-spacing (logical px) that makes ``text`` ``target_width`` wide."""
    font = _font(size * 3, bold)
    natural = sum(font.getlength(ch) for ch in text) / 3.0
    n = max(1, len(text) - 1)
    return max(0.0, (target_width - natural) / n)


def vertical_gradient(w: int, h: int, top: str, bottom: str) -> Image.Image:
    """Simple top->bottom gradient (used for the send button)."""
    t, b = _hex(top), _hex(bottom)
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=_lerp(t, b, y / max(1, h - 1)))
    return img


def rounded_gradient_button(
    w: int, h: int, radius: int, top: str, bottom: str, ss: int = 3
) -> Image.Image:
    """Anti-aliased rounded diagonal-ish gradient button background (RGBA)."""
    grad = vertical_gradient(w * ss, h * ss, top, bottom).convert("RGBA")
    mask = _rounded_mask(w * ss, h * ss, radius * ss, ss=1)
    grad.putalpha(mask)
    # subtle white inner hairline for the glossy edge in the reference
    edge = Image.new("RGBA", grad.size, (0, 0, 0, 0))
    ed = ImageDraw.Draw(edge)
    ed.rounded_rectangle(
        (ss, ss, w * ss - 1 - ss, h * ss - 1 - ss),
        radius=(radius - 1) * ss, outline=(255, 255, 255, 90), width=ss,
    )
    grad.alpha_composite(edge)
    return grad
