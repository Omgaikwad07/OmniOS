"""
ui/components/right_sidebar.py
==============================
Right column: System Status and Recent Activity.

* System Status shows the *real* result of ``ui.services`` checks.  Refresh
  re-reads ``.env`` and re-runs every check in a worker thread.  (The chevrons
  in the mock-up are intentionally omitted: the rows have no detail view, and
  the UI must not imply actions that do not exist.)
* Recent Activity lists genuine records from ``AppState.activity``.  Clear
  empties that list.  Only the newest rows that fit are shown; scroll the
  mouse wheel over the list to reveal older ones.
"""
from __future__ import annotations

import threading
from typing import Optional

import customtkinter as ctk

from ui import icons, services
from ui.components.base import Panel, UIContext
from ui.state import AppState
from ui.styles import PALETTE as C

_STATE_DOT = {
    services.READY: C["green"],
    services.NOT_CONFIGURED: C["amber"],
    services.UNAVAILABLE: C["red"],
}

# service key -> (glyph, glyph colour, circle bg)
_SERVICE_ICON = {
    "local": ("chip",  "#15A36B", "#D8F4E7"),
    "groq":  ("cloud", "#F29A1F", "#FFEBD0"),
    "pdf":   ("doc",   "#2F6BFF", "#DCE9FF"),
}
_ROW_NAME_Y = [99, 226, 358]
_DIVIDER_Y = [70, 196, 328]

# intent -> (glyph, glyph colour, badge bg)
_ACTIVITY_ICON = {
    "CALCULATE":   ("sigma",  "#15A36B", "#D8F4E7"),
    "OPEN_APP":    ("window", "#2F6BFF", "#DCE9FF"),
    "OPEN_URL":    ("globe",  "#7C4DFF", "#E9E1FF"),
    "FILE_SEARCH": ("search", "#F2A014", "#FFF0C9"),
    "LLM_TASK":    ("doc",    "#E8479F", "#FFE1EE"),
    "LLM":         ("doc",    "#E8479F", "#FFE1EE"),
}
_ACTIVITY_DEFAULT = ("alert", "#8591B3", "#E9EEFB")
_TONE_COLOR = {"ok": ("#16B364", "#12A150"), "warn": ("#F5A524", "#B7791F"),
               "bad": ("#EF4444", "#D92D3A")}
_ROW_PITCH = 66.0


# ---------------------------------------------------------------------------
# System Status
# ---------------------------------------------------------------------------

class StatusPanel(Panel):
    REF_W, REF_H = 380.0, 471.0

    def __init__(self, root, ui: UIContext, *, on_refresh) -> None:
        super().__init__(root, ui, "status")
        F = ui.fonts
        self._on_refresh = on_refresh
        self._statuses: list[services.ServiceStatus] = []

        self._pulse = ctk.CTkLabel(
            self, text="", fg_color="transparent",
            image=ui.image(icons.glyph_image("pulse", 30 * 4, "#2F6BFF", 1.5), 30))
        self._title = ctk.CTkLabel(self, text="System Status", font=F["side_h"],
                                   text_color=C["ink_2"], fg_color="transparent")
        self._refresh_btn = ctk.CTkButton(
            self, text=" Refresh", font=F["side_link"], text_color=C["blue"],
            image=ui.image(icons.glyph_image("refresh", 22 * 4, C["blue"], 1.6), 22),
            compound="left", fg_color="transparent", hover_color="#E4EBFF",
            border_width=0, width=96, height=34, corner_radius=10,
            command=self._refresh_clicked)
        self._dividers = [ctk.CTkFrame(self, fg_color="#E1E7F6", height=1, corner_radius=0)
                          for _ in range(3)]
        self._rows: list[dict] = []
        for _ in range(3):
            row = {
                "badge": ctk.CTkLabel(self, text="", fg_color="transparent"),
                "name": ctk.CTkLabel(self, text="", font=F["svc_name"], text_color=C["ink"],
                                     fg_color="transparent"),
                "dot": ctk.CTkFrame(self, width=10, height=10, corner_radius=5, fg_color=C["green"]),
                "state": ctk.CTkLabel(self, text="", font=F["svc_state"], text_color="#26324F",
                                      fg_color="transparent"),
                "desc": ctk.CTkLabel(self, text="", font=F["svc_desc"], text_color=C["muted"],
                                     fg_color="transparent", anchor="nw", justify="left"),
            }
            self._rows.append(row)

    def set_statuses(self, statuses: list[services.ServiceStatus]) -> None:
        self._statuses = statuses
        for row, st in zip(self._rows, statuses):
            glyph, gcol, bg = _SERVICE_ICON[st.key]
            row["badge"].configure(image=self.ui.image(
                icons.badge_image(glyph, 72 * 3, gcol, bg, "circle", 0.46, 1.6), 72))
            row["name"].configure(text=st.name)
            row["dot"].configure(fg_color=_STATE_DOT[st.state])
            row["state"].configure(text=st.label)
            row["desc"].configure(text=st.description)
        self.relayout()

    def set_refreshing(self, busy: bool) -> None:
        self._refresh_btn.configure(text=" Refreshing\u2026" if busy else " Refresh",
                                    state="disabled" if busy else "normal")

    def _refresh_clicked(self) -> None:
        self._on_refresh()

    def relayout(self) -> None:
        self.put(self._pulse, 36, 37, anchor="center")
        self.put(self._title, 60, 37, anchor="w")
        self.put_right(self._refresh_btn, 22, 37, anchor="e")
        for i, d in enumerate(self._dividers):
            d.configure(width=self.W(340))
            self.put(d, 20, _DIVIDER_Y[i])
        wrap = max(60, int(222 * self.sx))
        for row, ny in zip(self._rows, _ROW_NAME_Y):
            self.put(row["badge"], 59, ny + 20, anchor="center")
            self.put(row["name"], 113, ny, anchor="w")
            row["dot"].configure(width=self.ui.px(10), height=self.ui.px(10),
                                 corner_radius=self.ui.px(5))
            self.put(row["dot"], 120, ny + 26, anchor="center")
            self.put(row["state"], 136, ny + 26, anchor="w")
            row["desc"].configure(wraplength=wrap)
            self.put(row["desc"], 113, ny + 42, anchor="nw")


# ---------------------------------------------------------------------------
# Recent Activity
# ---------------------------------------------------------------------------

class ActivityPanel(Panel):
    REF_W, REF_H = 380.0, 408.0

    def __init__(self, root, ui: UIContext, *, state: AppState) -> None:
        super().__init__(root, ui, "activity")
        F = ui.fonts
        self._state = state
        self._offset = 0
        self._row_widgets: list[ctk.CTkBaseClass] = []

        self._clock = ctk.CTkLabel(
            self, text="", fg_color="transparent",
            image=ui.image(icons.glyph_image("clock", 30 * 4, "#2F6BFF", 1.5), 30))
        self._title = ctk.CTkLabel(self, text="Recent Activity", font=F["side_h"],
                                   text_color=C["ink_2"], fg_color="transparent")
        self._clear = ctk.CTkButton(
            self, text=" Clear", font=F["side_link"], text_color=C["blue"],
            image=ui.image(icons.glyph_image("clear", 22 * 4, C["blue"], 1.6), 22),
            compound="left", fg_color="transparent", hover_color="#E4EBFF",
            border_width=0, width=84, height=34, corner_radius=10, command=self._clear_clicked)
        self._list = ctk.CTkFrame(self, fg_color=C["card"], border_width=1,
                                  border_color="#FFFFFF", corner_radius=18)
        self._empty_icon = ctk.CTkLabel(
            self._list, text="", fg_color="transparent",
            image=ui.image(icons.glyph_image("clock", 40 * 4, "#B7C2E2", 1.4), 40))
        self._empty_title = ctk.CTkLabel(self._list, text="No activity yet", font=F["empty_h"],
                                         text_color=C["muted"], fg_color="transparent")
        self._empty_sub = ctk.CTkLabel(self._list, text="Your recent commands will appear here",
                                       font=F["empty_s"], text_color=C["muted_2"], fg_color="transparent")
        self._wheel_widgets = [self._list]
        self._bind_wheel(self._list)
        state.subscribe(self.refresh)

    # -- scrolling --------------------------------------------------------
    def _bind_wheel(self, w) -> None:
        w.bind("<MouseWheel>", self._on_wheel, add="+")
        w.bind("<Button-4>", lambda e: self._scroll(-1), add="+")
        w.bind("<Button-5>", lambda e: self._scroll(1), add="+")

    def _on_wheel(self, event) -> None:
        self._scroll(-1 if event.delta > 0 else 1)

    def _scroll(self, step: int) -> None:
        n = len(self._state.activity)
        max_off = max(0, n - self._visible_rows())
        new = min(max_off, max(0, self._offset + step))
        if new != self._offset:
            self._offset = new
            self.refresh()

    def _visible_rows(self) -> int:
        list_h = 330 * self.sy
        return max(1, int(list_h // (_ROW_PITCH * self.sy)))

    # -- layout -----------------------------------------------------------
    def relayout(self) -> None:
        self.put(self._clock, 36, 32, anchor="center")
        self.put(self._title, 61, 32, anchor="w")
        self.put_right(self._clear, 22, 32, anchor="e")
        self._list.configure(width=self.W(343), height=self.H(330),
                             corner_radius=max(8, self.ui.px(18)))
        self.put(self._list, 19, 65)
        self.refresh()

    # -- content ----------------------------------------------------------
    def refresh(self) -> None:
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()
        entries = self._state.activity
        if not entries:
            self._offset = 0
            self._empty_icon.place(relx=0.5, rely=0.40, anchor="center")
            self._empty_title.place(relx=0.5, rely=0.54, anchor="center")
            self._empty_sub.place(relx=0.5, rely=0.62, anchor="center")
            return
        for w in (self._empty_icon, self._empty_title, self._empty_sub):
            w.place_forget()
        rows = self._visible_rows()
        self._offset = min(self._offset, max(0, len(entries) - rows))
        for i, entry in enumerate(entries[self._offset:self._offset + rows]):
            self._build_row(i, entry)

    def _build_row(self, i: int, e: dict) -> None:
        F = self.ui.fonts
        glyph, gcol, bg = _ACTIVITY_ICON.get(e["intent"], _ACTIVITY_DEFAULT)
        cy = int((33 + i * _ROW_PITCH) * self.sy)
        sx = self.sx
        dot_c, text_c = _TONE_COLOR[e["tone"]]

        badge = ctk.CTkLabel(self._list, text="", fg_color="transparent", image=self.ui.image(
            icons.badge_image(glyph, 48 * 3, gcol, bg, "round", 0.5, 1.6), 48))
        badge.place(x=int(35 * sx), y=cy, anchor="center")
        cmd = ctk.CTkLabel(self._list, text=e["command"], font=F["act_cmd"], text_color=C["ink"],
                           fg_color="transparent", anchor="w")
        cmd.place(x=int(76 * sx), y=cy - self.ui.px(11), anchor="w")
        dot = ctk.CTkFrame(self._list, width=self.ui.px(8), height=self.ui.px(8),
                           corner_radius=self.ui.px(4), fg_color=dot_c)
        dot.place(x=int(80 * sx), y=cy + self.ui.px(12), anchor="center")
        meta = ctk.CTkLabel(self._list, text=f"{e['intent']} \u00b7 {e['status']}",
                            font=F["act_meta"], text_color=text_c, fg_color="transparent", anchor="w")
        meta.place(x=int(76 * sx) + self.ui.px(10), y=cy + self.ui.px(12), anchor="w")
        when = ctk.CTkLabel(self._list, text=e["time"], font=F["act_time"], text_color=C["muted"],
                            fg_color="transparent")
        when.place(x=int(329 * sx), y=cy - self.ui.px(9), anchor="e")
        for w in (badge, cmd, dot, meta, when):
            self._bind_wheel(w)
        self._row_widgets.extend([badge, cmd, dot, meta, when])

    def _clear_clicked(self) -> None:
        self._offset = 0
        self._state.clear_activity()


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class RightSidebar:
    """Owns the two sidebar panels."""

    def __init__(self, root, *, ui: UIContext, state: AppState) -> None:
        self.root = root
        self.status = StatusPanel(root, ui, on_refresh=self.refresh_status)
        self.activity = ActivityPanel(root, ui, state=state)
        self._busy = False
        self.status.set_statuses(services.refresh(reload_env=False))

    @property
    def panels(self) -> dict[str, Panel]:
        return {"status": self.status, "activity": self.activity}

    def refresh_status(self) -> None:
        """Re-read .env and re-run all service checks off the UI thread."""
        if self._busy:
            return
        self._busy = True
        self.status.set_refreshing(True)

        def work() -> None:
            statuses: Optional[list] = None
            try:
                statuses = services.refresh(reload_env=True)
            finally:
                try:
                    self.root.after(0, lambda: self._done(statuses))
                except Exception:
                    pass

        threading.Thread(target=work, name="OmniOSStatusRefresh", daemon=True).start()

    def _done(self, statuses) -> None:
        self._busy = False
        self.status.set_refreshing(False)
        if statuses:
            self.status.set_statuses(statuses)
