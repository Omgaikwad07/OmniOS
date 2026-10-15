r"""OmniOS desktop application launcher (reference-aligned pastel UI).

Run with the project's own interpreter:

    .venv\Scripts\python.exe -m ui.main

Architecture
------------
* A single ``tk.Canvas`` fills the window.  Its image is the smooth pastel
  gradient **plus** soft shadows and anti-aliased rounded panel surfaces, baked
  by ``ui.render.compose_background`` from the current panel rectangles.  The
  canvas is created first, so it is the lowest widget in the stacking order —
  no ``lower()`` calls are needed (``Canvas.lower`` only reorders canvas
  *items*, which was the cause of an earlier startup crash).
* Panels are content frames placed directly on the window at the rectangles
  returned by ``ui.layout.compute_layout`` (pure math, unit-tested).
* Commands run in a worker thread; results are marshalled back to the Tk
  thread with ``after(0, ...)`` before touching ``AppState``.
"""
from __future__ import annotations

import threading
import tkinter as tk
import traceback
from typing import Optional

import customtkinter as ctk
from PIL import ImageTk

from app import process_command
from core.schemas import ExecutionResult, Intent, ResultStatus, Route, RoutingDecision
from ui import render
from ui.components.base import UIContext
from ui.components.central_panel import CentralPanel
from ui.components.right_sidebar import RightSidebar
from ui.layout import compute_layout, panel_radius
from ui.scaling import scale_for
from ui.state import AppState
from ui.styles import PALETTE

DEFAULT_W, DEFAULT_H = 1536, 1024       # logical px (title bar included)
MIN_W, MIN_H = 1100, 740
PAINT_DELAY_MS = 70


class OmniOSApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title("OmniOS")
        self.configure(fg_color="#DDE9FF")
        self._closing = False
        self._workers: set[threading.Thread] = set()
        self._paint_job: Optional[str] = None
        self._layout_job: Optional[str] = None
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._rects: dict = {}

        self._set_initial_geometry()
        self.minsize(MIN_W, MIN_H)

        self.state_store = AppState()
        self.ui = UIContext()

        # Created first => lowest in the stacking order (see module docstring).
        self._canvas = tk.Canvas(self, bd=0, highlightthickness=0, relief="flat", bg="#DDE9FF")
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.central = CentralPanel(
            self, ui=self.ui, state=self.state_store,
            on_submit=self.submit_command, on_layout_change=self.request_layout,
        )
        self.sidebar = RightSidebar(self, ui=self.ui, state=self.state_store)

        self.bind("<Configure>", self._on_configure)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(30, self._relayout)

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    def _dpi(self) -> float:
        try:
            return float(self._get_window_scaling())
        except Exception:
            return 1.0

    def _set_initial_geometry(self) -> None:
        dpi = self._dpi()
        sw, sh = self.winfo_screenwidth() / dpi, self.winfo_screenheight() / dpi
        w = int(min(DEFAULT_W, sw * 0.96))
        h = int(min(DEFAULT_H, sh * 0.92))
        x = int(max(0, (self.winfo_screenwidth() - w * dpi) // 2))
        y = int(max(0, (self.winfo_screenheight() - h * dpi) // 2 - 24))
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _client_logical(self) -> tuple[float, float]:
        dpi = self._dpi()
        return max(2.0, self.winfo_width() / dpi), max(2.0, self.winfo_height() / dpi)

    def _on_configure(self, event=None) -> None:
        if event is not None and event.widget is not self:
            return
        self.request_layout()

    def request_layout(self) -> None:
        """Coalesce layout requests (resize storms, state changes)."""
        if self._layout_job is None and not self._closing:
            self._layout_job = self.after_idle(self._relayout)

    def _relayout(self) -> None:
        self._layout_job = None
        if self._closing:
            return
        w, h = self._client_logical()
        if w < 50 or h < 50:      # not mapped yet
            return
        self.ui.scaler.set(scale_for(w, h))
        f = self.ui.f
        self._rects = compute_layout(
            w, h,
            result_visible=self.central.result_visible,
            expanded=self.central.expanded,
        )
        panels = {**self.central.panels, **self.sidebar.panels}
        for name, panel in panels.items():
            panel.set_rect(self._rects[name], f)
        self._schedule_paint()

    # ------------------------------------------------------------------
    # Background painting
    # ------------------------------------------------------------------
    def _schedule_paint(self) -> None:
        if self._paint_job is not None:
            try:
                self.after_cancel(self._paint_job)
            except tk.TclError:
                pass
        self._paint_job = self.after(PAINT_DELAY_MS, self._paint)

    def _paint(self) -> None:
        self._paint_job = None
        if self._closing:
            return
        try:
            dpi = self._dpi()
            wp, hp = max(2, self.winfo_width()), max(2, self.winfo_height())
            radius = panel_radius(self.ui.f) * dpi
            specs = []
            for x, y, w, h in self._rects.values():
                specs.append((x * dpi, y * dpi, (x + w) * dpi, (y + h) * dpi,
                              radius, PALETTE["panel"]))
            image = render.compose_background(wp, hp, specs)
            self._photo = ImageTk.PhotoImage(image)
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, image=self._photo, anchor="nw")
        except (tk.TclError, RuntimeError):
            pass

    # ------------------------------------------------------------------
    # Command execution (worker thread -> Tk thread)
    # ------------------------------------------------------------------
    def submit_command(self, command: str) -> None:
        command = command.strip()
        if not command or self._closing or self.state_store.is_processing:
            return
        self.state_store.begin(command)
        worker = threading.Thread(
            target=self._execute_command, args=(command,),
            name="OmniOSCommandWorker", daemon=True,
        )
        self._workers.add(worker)
        worker.start()

    def _execute_command(self, command: str) -> None:
        try:
            decision, result = process_command(command)
        except Exception as exc:
            traceback.print_exc()
            decision = RoutingDecision(
                intent=Intent.UNKNOWN, route=Route.NONE, confidence=0.0,
                explanation="Command execution raised an exception.",
            )
            result = ExecutionResult(
                status=ResultStatus.ERROR, output=None,
                error=f"{type(exc).__name__}: {exc}", used_llm=False,
            )
        try:
            self.after(0, lambda d=decision, r=result, c=command: self._finish_command(d, r, c))
        except (tk.TclError, RuntimeError):
            pass

    def _finish_command(self, decision, result, command: str) -> None:
        self._workers = {w for w in self._workers if w.is_alive()}
        if self._closing:
            return
        self.state_store.update_result(decision, result, command)

    def _on_close(self) -> None:
        self._closing = True
        self.destroy()


def main() -> None:
    app = OmniOSApp()
    app.mainloop()


if __name__ == "__main__":
    main()
