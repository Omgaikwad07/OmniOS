"""
ui/components/base.py
=====================
Shared building blocks for the panel components.

``UIContext`` bundles the live scaler, the live-scaling fonts and image
factories.  ``Panel`` is a content frame that lives directly on the window
(above the baked background canvas); ``Panel.relayout`` re-places every child
from *reference-pixel* coordinates whenever the panel size or scale changes.
"""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image

from ui.layout import panel_inset
from ui.scaling import Fonts, Scaler
from ui.styles import PALETTE


class UIContext:
    """Scaler + fonts + image helpers shared by all panels."""

    def __init__(self) -> None:
        self.scaler = Scaler()
        self.fonts = Fonts(self.scaler)

    @property
    def f(self) -> float:
        return self.scaler.f

    def px(self, n: float) -> int:
        return self.scaler.px(n)

    def image(self, pil: Image.Image, logical_w: float, logical_h: Optional[float] = None) -> ctk.CTkImage:
        """``CTkImage`` whose displayed size follows the live scale."""
        lh = logical_w if logical_h is None else logical_h
        img = ctk.CTkImage(light_image=pil, dark_image=pil,
                           size=(self.px(logical_w), self.px(lh)))
        self.scaler.register(
            lambda _f, i=img, w=logical_w, h=lh: i.configure(size=(self.px(w), self.px(h)))
        )
        return img


class Panel(ctk.CTkFrame):
    """A panel's content frame (solid near-white, square, inset in its shape)."""

    #: reference size of the panel (used to scale child coordinates)
    REF_W = 1038.0
    REF_H = 374.0

    def __init__(self, root, ui: UIContext, name: str) -> None:
        super().__init__(root, fg_color=PALETTE["panel"], corner_radius=0, border_width=0)
        self.ui = ui
        self.name = name
        self.pw = self.REF_W      # full panel (shape) size, logical px
        self.ph = self.REF_H
        self.ins = 0
        self.f = 1.0
        self.sx = 1.0
        self.sy = 1.0

    # -- geometry ---------------------------------------------------------
    def set_rect(self, rect: tuple[float, float, float, float], f: float) -> None:
        """Place the content frame inside the panel shape and re-layout."""
        x, y, w, h = rect
        ins = panel_inset(f)
        self.pw, self.ph, self.ins, self.f = w, h, ins, f
        self.sx = w / self.REF_W
        self.sy = h / self.REF_H
        self.configure(width=max(10, round(w - 2 * ins)), height=max(10, round(h - 2 * ins)))
        self.place(x=round(x + ins), y=round(y + ins))
        self.relayout()

    # coordinate helpers (reference px -> content-frame px)
    def X(self, x: float) -> int:
        return int(round(x * self.sx - self.ins))

    def Y(self, y: float) -> int:
        return int(round(y * self.sy - self.ins))

    def W(self, w: float) -> int:
        return max(1, int(round(w * self.sx)))

    def H(self, h: float) -> int:
        return max(1, int(round(h * self.sy)))

    def put(self, widget, x: float, y: float, *, anchor: str = "nw") -> None:
        widget.place(x=self.X(x), y=self.Y(y), anchor=anchor)

    def put_right(self, widget, x_from_right: float, y: float, *, anchor: str = "e") -> None:
        """Right-aligned: ``x_from_right`` is measured from the panel's right edge."""
        widget.place(x=round(self.pw - self.ins - x_from_right * self.sx),
                     y=self.Y(y), anchor=anchor)

    def relayout(self) -> None:  # overridden
        pass
