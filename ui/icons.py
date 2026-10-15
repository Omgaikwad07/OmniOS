"""
ui/icons.py
===========
Vector-style line icons drawn with Pillow.

Why not an icon font?  Segoe MDL2 only exists on Windows and its glyphs do not
match the thin rounded line style of the approved design.  Pillow ships with
the app's dependencies, so icons are rasterised once (8x supersampled), cached
and handed to CustomTkinter as ``CTkImage`` objects.

All icons are authored on a 24 x 24 grid (Feather-like).  ``badge()`` bakes an
anti-aliased circle / rounded-square background behind a glyph so that the
shape's edge is smooth against whatever surface it sits on.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Callable

from PIL import Image, ImageChops, ImageDraw

import customtkinter as ctk

SS = 8  # supersampling factor


# ---------------------------------------------------------------------------
# Drawing context
# ---------------------------------------------------------------------------

class _Ctx:
    """Tiny drawing helper working in 24-unit icon space."""

    def __init__(self, size: int, color: str, stroke: float) -> None:
        self.px = size * SS
        self.k = self.px / 24.0
        self.color = color
        self.w = max(1, int(round(stroke * self.k)))
        self.img = Image.new("RGBA", (self.px, self.px), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _p(self, pt):
        return (pt[0] * self.k, pt[1] * self.k)

    def line(self, pts, close=False):
        pts = [self._p(p) for p in pts]
        if close:
            pts = pts + [pts[0]]
        self.d.line(pts, fill=self.color, width=self.w, joint="curve")
        r = self.w / 2.0
        for x, y in pts:  # round caps / joins
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=self.color)

    def circle(self, c, r, fill=False):
        x, y = self._p(c)
        rr = r * self.k
        if fill:
            self.d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=self.color)
        else:
            self.d.ellipse(
                (x - rr, y - rr, x + rr, y + rr), outline=self.color, width=self.w
            )

    def rrect(self, box, r):
        x0, y0, x1, y1 = (v * self.k for v in box)
        self.d.rounded_rectangle(
            (x0, y0, x1, y1), radius=r * self.k, outline=self.color, width=self.w
        )

    def arc(self, box, start, end):
        x0, y0, x1, y1 = (v * self.k for v in box)
        self.d.arc((x0, y0, x1, y1), start, end, fill=self.color, width=self.w)
        # round the ends
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
        r = self.w / 2.0
        for a in (start, end):
            x = cx + rx * math.cos(math.radians(a))
            y = cy + ry * math.sin(math.radians(a))
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=self.color)

    def poly_fill(self, pts):
        self.d.polygon([self._p(p) for p in pts], fill=self.color)

    def result(self, size: int) -> Image.Image:
        return self.img.resize((size, size), Image.Resampling.LANCZOS)


# ---------------------------------------------------------------------------
# Glyph definitions
# ---------------------------------------------------------------------------

def _spark(c: _Ctx):
    c.line([(12, 2.5), (14.2, 9.8), (21.5, 12), (14.2, 14.2), (12, 21.5),
            (9.8, 14.2), (2.5, 12), (9.8, 9.8)], close=True)


def _mic(c: _Ctx):
    c.rrect((8.5, 2.5, 15.5, 14.5), 3.5)
    c.arc((5, 7, 19, 19), 0, 180)
    c.line([(12, 19), (12, 22)])
    c.line([(8.5, 22), (15.5, 22)])


def _send(c: _Ctx):
    c.line([(21.5, 2.5), (10.5, 13.5)])
    c.line([(21.5, 2.5), (14.5, 21.5), (10.5, 13.5), (2.5, 9.5)], close=True)


def _calculator(c: _Ctx):
    c.rrect((4.5, 2.5, 19.5, 21.5), 2.8)
    c.line([(8, 7), (16, 7)])
    for x in (8.5, 12, 15.5):
        for y in (12, 16, 19.2):
            c.circle((x, y), 0.85, fill=True)


def _sigma(c: _Ctx):
    c.line([(18, 4.5), (6.5, 4.5), (13, 12), (6.5, 19.5), (18, 19.5)])


def _search(c: _Ctx):
    c.circle((10.5, 10.5), 6.8)
    c.line([(15.6, 15.6), (21, 21)])


def _doc(c: _Ctx):
    c.line([(6, 2.5), (14, 2.5), (19.5, 8), (19.5, 21.5), (6, 21.5)], close=True)
    c.line([(14, 2.5), (14, 8), (19.5, 8)])
    c.line([(9, 13), (16.5, 13)])
    c.line([(9, 17), (16.5, 17)])


def _pulse(c: _Ctx):
    c.line([(2.5, 12), (6.5, 12), (9.5, 3.5), (14.5, 20.5), (17.5, 12), (21.5, 12)])


def _chat(c: _Ctx):
    c.line([(5, 3.5), (19, 3.5), (21, 5.5), (21, 15.5), (19, 17.5),
            (11, 17.5), (6.5, 21.5), (6.5, 17.5), (5, 17.5), (3, 15.5),
            (3, 5.5)], close=True)
    c.line([(8, 8), (16, 8)])
    c.line([(8, 12), (13, 12)])


def _route(c: _Ctx):
    c.circle((5.5, 12), 2.6)
    c.circle((18.5, 5), 2.6)
    c.circle((18.5, 19), 2.6)
    c.line([(8, 11), (16, 6)])
    c.line([(8, 13), (16, 18)])


def _gear(c: _Ctx):
    pts = []
    teeth = 8
    for i in range(teeth * 4):
        ang = (i / (teeth * 4)) * 2 * math.pi - math.pi / 2
        # trapezoid teeth: out, out, in, in
        r = 9.3 if (i % 4) in (0, 1) else 7.0
        pts.append((12 + r * math.cos(ang), 12 + r * math.sin(ang)))
    c.line(pts, close=True)
    c.circle((12, 12), 3.2)


def _chip(c: _Ctx):
    c.rrect((6, 6, 18, 18), 2.2)
    c.rrect((9.3, 9.3, 14.7, 14.7), 0.8)
    for t in (9.5, 12, 14.5):
        c.line([(t, 2.5), (t, 6)])
        c.line([(t, 18), (t, 21.5)])
        c.line([(2.5, t), (6, t)])
        c.line([(18, t), (21.5, t)])


def _cloud(c: _Ctx):
    # Outline of a union of circles + a base, built from masks.
    k, px = c.k, c.px
    outer = Image.new("L", (px, px), 0)
    inner = Image.new("L", (px, px), 0)
    shapes = [  # (cx, cy, r) in icon units
        (7.2, 15.2, 4.2), (12.4, 10.6, 5.6), (17.6, 14.6, 4.0),
    ]
    sw = c.w / k  # stroke in units

    def paint(mask, grow):
        md = ImageDraw.Draw(mask)
        for cx, cy, r in shapes:
            rr = (r + grow) * k
            md.ellipse((cx * k - rr, cy * k - rr, cx * k + rr, cy * k + rr), fill=255)
        md.rectangle(((7.2) * k, (15.2 - 4.2 - grow) * k + 4.2 * k,
                      (17.6) * k, (19.4 + grow) * k), fill=255)

    paint(outer, sw / 2)
    paint(inner, -sw / 2)
    ring = ImageChops.subtract(outer, inner)
    solid = Image.new("RGBA", (px, px), c.color)
    c.img.paste(solid, (0, 0), ring)


def _clock(c: _Ctx):
    c.circle((12, 12), 9.2)
    c.line([(12, 6.5), (12, 12), (16, 14.2)])


def _refresh(c: _Ctx):
    c.arc((4.5, 4.5, 19.5, 19.5), 25, 315)
    # arrow head at the arc start (pointing along the circle)
    c.line([(19.5, 3.5), (19.6, 8.3), (14.8, 8.3)])


def _clear(c: _Ctx):
    c.line([(4, 6.5), (20, 6.5)])
    c.line([(9, 6.5), (9, 3.5), (15, 3.5), (15, 6.5)])
    c.line([(6, 6.5), (7, 20.5), (17, 20.5), (18, 6.5)])
    c.line([(10.2, 10.5), (10.2, 16.5)])
    c.line([(13.8, 10.5), (13.8, 16.5)])


def _chev_down(c: _Ctx):
    c.line([(5.5, 9), (12, 15.5), (18.5, 9)])


def _chev_up(c: _Ctx):
    c.line([(5.5, 15), (12, 8.5), (18.5, 15)])


def _arrow_right(c: _Ctx):
    c.line([(3.5, 12), (20, 12)])
    c.line([(14.5, 6.5), (20, 12), (14.5, 17.5)])


def _window(c: _Ctx):
    c.rrect((3, 4.5, 21, 19.5), 2.6)
    c.line([(3, 9.2), (21, 9.2)])


def _globe(c: _Ctx):
    c.circle((12, 12), 9.2)
    c.line([(2.8, 12), (21.2, 12)])
    c.arc((7.5, 2.8, 16.5, 21.2), 90, 270)
    c.arc((7.5, 2.8, 16.5, 21.2), 270, 90)


def _alert(c: _Ctx):
    c.circle((12, 12), 9.2)
    c.line([(12, 7), (12, 13)])
    c.circle((12, 16.8), 0.6, fill=True)


GLYPHS: dict[str, Callable[[_Ctx], None]] = {
    "spark": _spark, "mic": _mic, "send": _send, "calculator": _calculator,
    "sigma": _sigma, "search": _search, "doc": _doc, "pulse": _pulse,
    "chat": _chat, "route": _route, "gear": _gear, "chip": _chip,
    "cloud": _cloud, "clock": _clock, "refresh": _refresh, "clear": _clear,
    "chev_down": _chev_down, "chev_up": _chev_up, "arrow_right": _arrow_right,
    "window": _window, "globe": _globe, "alert": _alert,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@lru_cache(maxsize=512)
def glyph_image(name: str, px: int, color: str, stroke: float = 1.7) -> Image.Image:
    """Return an RGBA glyph of ``px`` x ``px`` pixels."""
    ctx = _Ctx(px, color, stroke)
    GLYPHS[name](ctx)
    return ctx.result(px)


@lru_cache(maxsize=512)
def badge_image(
    name: str,
    px: int,
    glyph_color: str,
    bg: str,
    shape: str = "circle",
    glyph_ratio: float = 0.5,
    stroke: float = 1.7,
) -> Image.Image:
    """Glyph centred on a smooth circle / rounded-square background."""
    big = px * SS
    base = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    if shape == "circle":
        d.ellipse((0, 0, big - 1, big - 1), fill=bg)
    else:
        d.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.28), fill=bg)
    base = base.resize((px, px), Image.Resampling.LANCZOS)
    g_px = max(8, int(round(px * glyph_ratio)))
    glyph = glyph_image(name, g_px * 3, glyph_color, stroke).resize(
        (g_px, g_px), Image.Resampling.LANCZOS
    )
    off = (px - g_px) // 2
    base.alpha_composite(glyph, (off, off))
    return base


def ctk_image(pil: Image.Image, logical: int) -> ctk.CTkImage:
    """Wrap a (high-resolution) PIL image as a square ``CTkImage``."""
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=(logical, logical))
