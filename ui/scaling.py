"""
ui/scaling.py
=============
Live UI scale factor.

The layout is authored in *reference pixels* (see ``ui.styles.REF_W/REF_H``).
``Scaler`` turns the current window size into a factor ``f`` and tells every
registered widget helper to re-apply itself.  Fonts and images are updated in
place (``CTkFont.configure`` / ``CTkImage.configure``), so nothing is rebuilt
and no window geometry is touched — unlike ``ctk.set_widget_scaling``, which
resizes the window and fights the user's own resizing.
"""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui.styles import MONO_FAMILY, REF_H, REF_W, TYPE, UI_FONT_FAMILY

F_MIN = 0.70
F_MAX = 1.35


def scale_for(width: float, height: float) -> float:
    """Scale factor for a client area of ``width`` x ``height`` logical px."""
    f = min(width / REF_W, height / REF_H)
    return max(F_MIN, min(F_MAX, f))


class Scaler:
    """Holds the current factor and the callbacks that apply it."""

    def __init__(self) -> None:
        self.f = 1.0
        self._callbacks: list[Callable[[float], None]] = []

    def register(self, fn: Callable[[float], None]) -> None:
        self._callbacks.append(fn)
        fn(self.f)

    def px(self, n: float) -> int:
        return max(1, int(round(n * self.f)))

    def set(self, f: float) -> bool:
        """Apply ``f``.  Returns False (and does nothing) for tiny changes."""
        f = max(F_MIN, min(F_MAX, f))
        if abs(f - self.f) < 0.02:
            return False
        self.f = f
        for fn in list(self._callbacks):
            try:
                fn(f)
            except Exception:  # a dead widget must not break the others
                pass
        return True


class Fonts:
    """One live-scaling ``CTkFont`` per token in ``ui.styles.TYPE``."""

    def __init__(self, scaler: Scaler) -> None:
        self._scaler = scaler
        self._fonts: dict[str, ctk.CTkFont] = {}
        for name, (size, weight) in TYPE.items():
            family = MONO_FAMILY if name == "mono" else UI_FONT_FAMILY
            self._fonts[name] = ctk.CTkFont(
                family=family, size=scaler.px(size), weight=weight
            )
        scaler.register(self._apply)

    def _apply(self, _f: float) -> None:
        for name, font in self._fonts.items():
            font.configure(size=self._scaler.px(TYPE[name][0]))

    def __getitem__(self, name: str) -> ctk.CTkFont:
        return self._fonts[name]
