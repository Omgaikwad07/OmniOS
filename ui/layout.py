"""
ui/layout.py
============
Pure layout math — no Tk imports, so it is unit-testable.

All outputs are rectangles ``(x, y, w, h)`` in *logical* client pixels.  At the
reference client size (1586 x 948) they reproduce the approved design exactly;
at other sizes columns/rows scale proportionally.
"""
from __future__ import annotations

from ui.styles import LAYOUT, REF_H, REF_W

Rect = tuple[float, float, float, float]

PANEL_RADIUS_REF = 26.0

# While the result body is expanded the Execution Details panel drops its
# stage-flow row (the metadata row stays) so the output gets real room.
EXEC_H_COMPACT = 190


def panel_radius(f: float) -> float:
    return PANEL_RADIUS_REF * f


def panel_inset(f: float) -> int:
    """Content is inset so its square corners hide inside the rounded shape."""
    return int(round(0.30 * panel_radius(f))) + 1


def compute_layout(
    width: float,
    height: float,
    *,
    result_visible: bool = False,
    expanded: bool = False,
) -> dict[str, Rect]:
    """Panel rectangles for a client area of ``width`` x ``height``."""
    sx = width / REF_W
    sy = height / REF_H
    L = LAYOUT

    x_main = L["margin_left"] * sx
    w_main = L["main_w"] * sx
    x_side = (L["margin_left"] + L["main_w"] + L["gap_x"]) * sx
    w_side = L["side_w"] * sx

    y = L["margin_top"] * sy
    welcome_h = L["welcome_h"] * sy
    gap_a = L["gap_a"] * sy
    gap_b = L["gap_b"] * sy

    exec_ref = EXEC_H_COMPACT if (result_visible and expanded) else L["exec_h"]
    exec_h = exec_ref * sy
    result_h = L["result_h"] * sy
    if result_visible and expanded:
        # hand the freed height to the result card
        result_h += (L["exec_h"] - EXEC_H_COMPACT) * sy

    rects: dict[str, Rect] = {
        "welcome": (x_main, y, w_main, welcome_h),
    }
    y_exec = y + welcome_h + gap_a
    rects["exec"] = (x_main, y_exec, w_main, exec_h)
    if result_visible:
        rects["result"] = (x_main, y_exec + exec_h + gap_b, w_main, result_h)

    status_h = L["status_h"] * sy
    rects["status"] = (x_side, y, w_side, status_h)
    rects["activity"] = (
        x_side, y + status_h + L["gap_s"] * sy, w_side, L["activity_h"] * sy,
    )
    return rects
