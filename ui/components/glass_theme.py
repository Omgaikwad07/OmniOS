"""ui/components/glass_theme.py - reusable glass-style building blocks."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw

PALETTE = {
    "text": "#17233F",
    "muted": "#6D7FA6",
    "blue": "#2D63F5",
    "blue_hover": "#1E4FD1",
    "border_soft": "#DCE6F8",
    "success": "#08B981",
    "warning": "#F5A400",
    "danger": "#F04468",
    "purple": "#8B45F6",
}

RADIUS = {"card": 28, "panel": 20, "button": 14, "input": 22, "chip": 22}

SURFACES = {
    "glass": "#F3F7FF",
    "glass_warm": "#FFF5F8",
    "glass_cool": "#EEF5FF",
    "solid": "#FFFFFF",
    "input": "#FAFCFF",
}

HAIRLINE = "#E3EAF8"
ICON_FONT = "Segoe MDL2 Assets"


def card(parent, *, variant="glass", radius=None, **kwargs):
    """Borderless rounded card (Tk has no alpha, so 'glass' = light tint)."""
    colors = {
        "glass": SURFACES["glass"], "warm": SURFACES["glass_warm"],
        "cool": SURFACES["glass_cool"], "solid": SURFACES["solid"],
        "transparent": "transparent",
    }
    return ctk.CTkFrame(
        parent,
        fg_color=colors.get(variant, SURFACES["glass"]),
        corner_radius=RADIUS["card"] if radius is None else radius,
        border_width=kwargs.pop("border_width", 0),
        border_color=kwargs.pop("border_color", PALETTE["border_soft"]),
        **kwargs,
    )


def divider(parent) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, height=1, fg_color=HAIRLINE, corner_radius=0)


def icon_badge(parent, glyph, *, size=48, bg, fg, font_size=20,
               family=ICON_FONT) -> ctk.CTkFrame:
    """Coloured circle with a centred glyph (the target's icon style)."""
    badge = ctk.CTkFrame(parent, width=size, height=size,
                         corner_radius=size // 2, fg_color=bg)
    badge.grid_propagate(False)
    badge.pack_propagate(False)
    ctk.CTkLabel(badge, text=glyph, font=(family, font_size),
                 text_color=fg, fg_color="transparent",
                 ).place(relx=0.5, rely=0.5, anchor="center")
    return badge


# ---------------------------------------------------------------------------
# Gradients
# ---------------------------------------------------------------------------

def lerp_color(t: float, stops):
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            f = 0 if p1 == p0 else max(0.0, (t - p0) / (p1 - p0))
            return tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return stops[-1][1]


def horizontal_gradient(width: int, height: int, stops) -> Image.Image:
    strip = Image.new("RGB", (max(1, width), 1))
    for x in range(strip.width):
        strip.putpixel((x, 0), lerp_color(x / max(1, strip.width - 1), stops))
    return strip.resize((max(1, width), max(1, height)))


def gradient_image(width: int, height: int, stops, radius: int = 0) -> ctk.CTkImage:
    """Rounded horizontal-gradient CTkImage (rendered 3x for smooth edges)."""
    s = 3
    img = horizontal_gradient(width * s, height * s, stops).convert("RGBA")
    if radius:
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, img.width - 1, img.height - 1), radius=radius * s, fill=255)
        img.putalpha(mask)
    return ctk.CTkImage(light_image=img, size=(width, height))


def install_wallpaper_underlay(frame):
    """Keep layout containers neutral; the root window owns the wallpaper."""
    try:
        frame.configure(fg_color="transparent", corner_radius=0, border_width=0)
    except (AttributeError, tk.TclError):
        pass
    return True