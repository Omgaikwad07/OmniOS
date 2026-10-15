"""
ui/components/left_sidebar.py
==============================
Left navigation panel.

Contains:
  • OmniOS logo (blue circle + name + subtitle)
  • Chat / History / Settings navigation items
  • Local Engine and Groq LLM status cards (bottom)
  • A 1 px right-edge border that separates the sidebar from the main area
"""

from __future__ import annotations

import customtkinter as ctk

from ui.styles import COLORS, DIMS, FONTS, ICO
from ui.state import AppState


# ---------------------------------------------------------------------------
# Navigation item definitions: (key, icon_char, display_label)
# ---------------------------------------------------------------------------

_NAV_ITEMS = [
    ("Chat",     ICO["chat"],     "Chat"),
    ("History",  ICO["history"],  "History"),
    ("Settings", ICO["settings"], "Settings"),
]


# ---------------------------------------------------------------------------
# _NavItem — a single clickable row in the nav list
# ---------------------------------------------------------------------------

class _NavItem(ctk.CTkFrame):
    """A single navigation row: icon + text label with hover / selected state."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        *,
        icon: str,
        label: str,
        selected: bool = False,
        on_click: "Callable[[str], None] | None" = None,
        **kw,
    ) -> None:
        super().__init__(
            parent,
            fg_color=COLORS["nav_selected"] if selected else "transparent",
            corner_radius=8,
            cursor="hand2",
            **kw,
        )
        self._on_click = on_click
        self._label_str = label
        self._selected = selected

        # Icon label
        self._icon_lbl = ctk.CTkLabel(
            self,
            text=icon,
            font=FONTS["icon_sm"],
            text_color=COLORS["blue"] if selected else COLORS["text_secondary"],
            width=22,
            anchor="center",
        )
        self._icon_lbl.pack(side="left", padx=(10, 0), pady=0)

        # Text label
        self._text_lbl = ctk.CTkLabel(
            self,
            text=label,
            font=FONTS["body"],
            text_color=COLORS["blue"] if selected else COLORS["text_secondary"],
            anchor="w",
        )
        self._text_lbl.pack(side="left", padx=(6, 10), pady=8, fill="x", expand=True)

        # Bind hover + click on all child widgets
        for widget in (self, self._icon_lbl, self._text_lbl):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._hover_on)
            widget.bind("<Leave>", self._hover_off)

    # ── Interaction ──────────────────────────────────────────────────────────

    def _click(self, _event=None) -> None:
        if self._on_click:
            self._on_click(self._label_str)

    def _hover_on(self, _event=None) -> None:
        if not self._selected:
            self.configure(fg_color=COLORS["nav_selected"])

    def _hover_off(self, _event=None) -> None:
        if not self._selected:
            self.configure(fg_color="transparent")

    # ── State ────────────────────────────────────────────────────────────────

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        color = COLORS["blue"] if selected else COLORS["text_secondary"]
        bg    = COLORS["nav_selected"] if selected else "transparent"
        self.configure(fg_color=bg)
        self._icon_lbl.configure(text_color=color)
        self._text_lbl.configure(text_color=color)


# ---------------------------------------------------------------------------
# LeftSidebar — the full left panel
# ---------------------------------------------------------------------------

class LeftSidebar(ctk.CTkFrame):
    """Left navigation sidebar."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        *,
        state: AppState,
        **kw,
    ) -> None:
        super().__init__(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=0,
            border_width=0,
            **kw,
        )
        self._state = state
        self._active = "Chat"
        self._nav_items: dict[str, _NavItem] = {}

        # Row 1 (nav area) expands vertically; logo and status cards are fixed
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_logo()
        self._build_nav()
        self._build_status_cards()

    # ── Build helpers ────────────────────────────────────────────────────────

    def _build_logo(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(20, 14))
        frame.grid_columnconfigure(1, weight=1)

        # Blue circle with white "O"
        circle = ctk.CTkFrame(
            frame,
            width=DIMS["logo_circle"],
            height=DIMS["logo_circle"],
            corner_radius=DIMS["logo_circle"] // 2,
            fg_color=COLORS["blue"],
        )
        circle.grid(row=0, column=0, rowspan=2)
        circle.grid_propagate(False)
        ctk.CTkLabel(
            circle,
            text="O",
            font=("Segoe UI", 16, "bold"),
            text_color="#FFFFFF",
        ).place(relx=0.5, rely=0.5, anchor="center")

        # App name
        ctk.CTkLabel(
            frame,
            text="OmniOS",
            font=FONTS["logo"],
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", padx=(10, 0))

        # Subtitle
        ctk.CTkLabel(
            frame,
            text="Your Desktop Assistant",
            font=FONTS["caption"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", padx=(10, 0))

    def _build_nav(self) -> None:
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        nav.grid_columnconfigure(0, weight=1)

        for i, (key, icon, label) in enumerate(_NAV_ITEMS):
            item = _NavItem(
                nav,
                icon=icon,
                label=label,
                selected=(key == "Chat"),
                on_click=self._on_nav,
            )
            item.grid(row=i, column=0, sticky="ew", pady=2)
            self._nav_items[key] = item

    def _build_status_cards(self) -> None:
        """Local Engine + Groq LLM status cards at the bottom of the sidebar."""
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["window_bg"],
            corner_radius=DIMS["card_radius"],
            border_width=DIMS["border_w"],
            border_color=COLORS["border"],
        )
        card.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        # Local Engine — always ready
        self._sidebar_status_row(
            card, row=0,
            name="Local Engine", status="Ready",
            dot_color="green", has_arrow=False,
        )

        # Separator
        ctk.CTkFrame(
            card, height=1, fg_color=COLORS["border"], corner_radius=0
        ).grid(row=1, column=0, sticky="ew", padx=8)

        # Groq LLM — depends on API key
        import core.config as _cfg
        groq_configured = bool(getattr(_cfg, "GROQ_API_KEY", ""))
        self._sidebar_status_row(
            card, row=2,
            name="Groq LLM",
            status="Ready" if groq_configured else "Not Configured",
            dot_color="green" if groq_configured else "amber",
            has_arrow=not groq_configured,
        )

    def _sidebar_status_row(
        self,
        parent: ctk.CTkFrame,
        *,
        row: int,
        name: str,
        status: str,
        dot_color: str,
        has_arrow: bool,
    ) -> None:
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=8)
        row_frame.grid_columnconfigure(1, weight=1)

        # Coloured dot
        dot = ctk.CTkFrame(
            row_frame,
            width=DIMS["status_dot"],
            height=DIMS["status_dot"],
            corner_radius=DIMS["status_dot"] // 2,
            fg_color=COLORS[dot_color],
        )
        dot.grid(row=0, column=0, rowspan=2, pady=2)
        dot.grid_propagate(False)

        ctk.CTkLabel(
            row_frame,
            text=name,
            font=FONTS["heading_sm"],
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        ctk.CTkLabel(
            row_frame,
            text=status,
            font=FONTS["caption"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=(8, 0))

        if has_arrow:
            ctk.CTkLabel(
                row_frame,
                text="›",
                font=("Segoe UI", 18, "normal"),
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=2, rowspan=2, padx=(4, 0))

    # ── Interaction ──────────────────────────────────────────────────────────

    def _on_nav(self, label: str) -> None:
        self._active = label
        for key, item in self._nav_items.items():
            item.set_selected(key == label)
