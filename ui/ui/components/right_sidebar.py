"""
ui/components/right_sidebar.py
================================
Right status and activity panel.

Sections:
  • System Status card   — Local Engine / Groq LLM / PDF Processing
  • Recent Activity card — empty state or list of past commands
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from ui.styles import COLORS, DIMS, FONTS, ICO
from ui.state import AppState


class RightSidebar(ctk.CTkFrame):
    """Right sidebar: system status + recent activity."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        *,
        state: AppState,
        **kw,
    ) -> None:
        super().__init__(
            parent,
            fg_color=COLORS["window_bg"],
            corner_radius=0,
            border_width=0,
            **kw,
        )
        self._state = state
        self._activity_widgets: list[ctk.CTkFrame] = []

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_status_card()
        self._build_activity_card()

        state.subscribe(self._refresh)

    # ── System Status ─────────────────────────────────────────────────────────

    def _build_status_card(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            corner_radius=DIMS["card_radius"],
            border_width=DIMS["border_w"],
            border_color=COLORS["border"],
        )
        card.grid(row=0, column=0, sticky="ew", padx=12, pady=(16, 8))
        card.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=DIMS["pad_card"], pady=(12, 8))
        ctk.CTkLabel(
            header,
            text=ICO["wave"],
            font=FONTS["icon_sm"],
            text_color=COLORS["blue"],
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            header,
            text="System Status",
            font=FONTS["heading_md"],
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # Separator
        ctk.CTkFrame(
            card, height=1, fg_color=COLORS["border"], corner_radius=0
        ).grid(row=1, column=0, sticky="ew", padx=DIMS["pad_card"])

        # Check PDF availability
        try:
            import fitz  # noqa: F401
            pdf_ready = True
        except ImportError:
            pdf_ready = False

        # Check Groq
        import core.config as _cfg
        groq_ok = bool(getattr(_cfg, "GROQ_API_KEY", ""))

        statuses = [
            (ICO["engine"], "Local Engine",    "Ready",          "green", False),
            (ICO["cloud"],  "Groq LLM",
                "Ready" if groq_ok else "Not Configured",
                "green" if groq_ok else "amber",
                not groq_ok,
            ),
            (ICO["file_proc"], "PDF Processing",
                "Ready" if pdf_ready else "Not Available",
                "green" if pdf_ready else "amber",
                False,
            ),
        ]

        for i, (icon, name, status, dot_color, arrow) in enumerate(statuses):
            base_row = i * 2 + 2
            self._status_row(card, base_row, icon, name, status, dot_color, arrow)
            if i < len(statuses) - 1:
                ctk.CTkFrame(
                    card, height=1, fg_color=COLORS["border"], corner_radius=0
                ).grid(row=base_row + 1, column=0, sticky="ew", padx=DIMS["pad_card"])

        # Bottom padding
        ctk.CTkFrame(card, height=4, fg_color="transparent").grid(
            row=100, column=0
        )

    def _status_row(
        self,
        parent: ctk.CTkFrame,
        row: int,
        icon: str,
        name: str,
        status: str,
        dot_color: str,
        arrow: bool,
    ) -> None:
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.grid(row=row, column=0, sticky="ew", padx=DIMS["pad_card"], pady=10)
        row_frame.grid_columnconfigure(1, weight=1)

        # Left outline icon
        ctk.CTkLabel(
            row_frame,
            text=icon,
            font=FONTS["icon_sm"],
            text_color=COLORS["text_secondary"],
            width=24,
        ).grid(row=0, column=0, rowspan=2, sticky="w")

        # Name
        ctk.CTkLabel(
            row_frame,
            text=name,
            font=FONTS["heading_sm"],
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        # Status dot + text (packed horizontally)
        status_row = ctk.CTkFrame(row_frame, fg_color="transparent")
        status_row.grid(row=1, column=1, sticky="w", padx=(8, 0))

        dot = ctk.CTkFrame(
            status_row,
            width=DIMS["status_dot"],
            height=DIMS["status_dot"],
            corner_radius=DIMS["status_dot"] // 2,
            fg_color=COLORS[dot_color],
        )
        dot.pack(side="left", padx=(0, 5))
        dot.pack_propagate(False)

        ctk.CTkLabel(
            status_row,
            text=status,
            font=FONTS["caption"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        if arrow:
            ctk.CTkLabel(
                row_frame,
                text="›",
                font=("Segoe UI", 18),
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=2, rowspan=2, padx=(4, 0))

    # ── Recent Activity ───────────────────────────────────────────────────────

    def _build_activity_card(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            corner_radius=DIMS["card_radius"],
            border_width=DIMS["border_w"],
            border_color=COLORS["border"],
        )
        card.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 16))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)
        self._activity_card = card

        # Header row
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=DIMS["pad_card"], pady=(12, 8))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr,
            text=ICO["clock"],
            font=FONTS["icon_sm"],
            text_color=COLORS["blue"],
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkLabel(
            hdr,
            text="Recent Activity",
            font=FONTS["heading_md"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=1, sticky="w")

        self._clear_btn = ctk.CTkButton(
            hdr,
            text="Clear",
            font=FONTS["body_sm"],
            text_color=COLORS["blue"],
            fg_color="transparent",
            hover_color=COLORS["nav_selected"],
            border_width=0,
            width=40,
            height=24,
            command=self._on_clear,
        )
        self._clear_btn.grid(row=0, column=2)

        # Separator
        ctk.CTkFrame(
            card, height=1, fg_color=COLORS["border"], corner_radius=0
        ).grid(row=1, column=0, sticky="ew", padx=DIMS["pad_card"])

        # Content area (empty state or list)
        self._activity_area = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["border_input"],
        )
        self._activity_area.grid(row=2, column=0, sticky="nsew", padx=4, pady=(4, 4))
        self._activity_area.grid_columnconfigure(0, weight=1)

        # Empty state (shown initially)
        self._empty_frame = ctk.CTkFrame(self._activity_area, fg_color="transparent")
        self._empty_frame.grid(row=0, column=0, sticky="nsew", pady=20)
        self._empty_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._empty_frame,
            text=ICO["document"],
            font=FONTS["icon_lg"],
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=0, pady=(20, 8))

        ctk.CTkLabel(
            self._empty_frame,
            text="No activity yet",
            font=FONTS["heading_sm"],
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0)

        ctk.CTkLabel(
            self._empty_frame,
            text="Your recent commands\nwill appear here",
            font=FONTS["caption"],
            text_color=COLORS["text_muted"],
            justify="center",
        ).grid(row=2, column=0, pady=(4, 20))

    # ── Refresh ───────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        """Called by AppState.notify() on every state change."""
        activity = self._state.activity

        # Remove old activity widgets
        for w in self._activity_widgets:
            w.destroy()
        self._activity_widgets.clear()

        if not activity:
            self._empty_frame.grid()
            return

        self._empty_frame.grid_remove()

        for i, entry in enumerate(activity):
            row_frame = ctk.CTkFrame(
                self._activity_area,
                fg_color=COLORS["surface_alt"],
                corner_radius=6,
                border_width=DIMS["border_w"],
                border_color=COLORS["border"],
            )
            row_frame.grid(row=i, column=0, sticky="ew", padx=4, pady=2)
            row_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row_frame,
                text=entry["command"],
                font=FONTS["body_sm"],
                text_color=COLORS["text_primary"],
                anchor="w",
                wraplength=160,
            ).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))

            status_color = (
                COLORS["green"] if entry["status"] == "SUCCESS"
                else COLORS["red"] if entry["status"] == "ERROR"
                else COLORS["amber"]
            )
            ctk.CTkLabel(
                row_frame,
                text=f"{entry['intent']}  •  {entry['status']}",
                font=FONTS["caption"],
                text_color=status_color,
                anchor="w",
            ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))

            self._activity_widgets.append(row_frame)

    def _on_clear(self) -> None:
        self._state.clear_activity()
