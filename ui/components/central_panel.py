"""
ui/components/central_panel.py
==============================
Main workspace: Welcome/command panel, Execution Details panel and the
collapsible Result row.

Each panel is a content frame placed directly on the window (above the baked
gradient/shape canvas).  ``CentralPanel`` is a controller that owns the three
panels, subscribes to ``AppState`` and tells the window when the layout needs
to change (result row appears / expands).

Honesty rules implemented here
------------------------------
* Execution metadata comes from the real ``RoutingDecision``/``ExecutionResult``.
* The result row only exists after a command has *finished*; its wording,
  colour and expandability follow the real ``Outcome`` (success, empty,
  error, refused, pending, LLM not configured, no supported action).
* Starting a command immediately drops the previous execution and collapses
  the result row, so nothing leaks between runs.
* The microphone is live only when the speech stack is importable; otherwise
  it is shown disabled.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from ui import icons, render, voice
from ui.components.base import Panel, UIContext
from ui.layout import EXEC_H_COMPACT
from ui.state import AppState, Execution, Outcome
from ui.styles import PALETTE as C

DASH = "\u2013"


# ---------------------------------------------------------------------------
# Static content
# ---------------------------------------------------------------------------

# (glyph, glyph colour, chip label, command placed in the input, ref x, ref w)
_CHIPS = [
    ("calculator", C["blue"],   "Open Calculator",        "open calculator",    46, 176),
    ("sigma",      C["green"],  "Calculate 125 \u00d7 48", "calculate 125 * 48", 236, 190),
    ("search",     C["orange"], "Find my resume",         "find my resume",     440, 171),
    ("doc",        C["pink"],   "Summarize this PDF",     "summarize this PDF", 626, 200),
]

# (glyph, glyph colour, circle bg, title, subtitle)
_STEPS = [
    ("chat",  "#3B7BFF", "#DCE9FF", "1. Intent",  "Detect request"),
    ("route", "#7C4DFF", "#E9E1FF", "2. Route",   "Local or LLM"),
    ("gear",  "#15A36B", "#D8F4E7", "3. Execute", "Run action"),
    ("doc",   "#F58A1F", "#FFE8D1", "4. Result",  "Show output"),
]
_STEP_CX = [155, 398, 641, 886]          # reference px, relative to the panel
_ARROW_CX = [275, 519, 763]

_META = ["Intent", "Route", "Confidence", "Action", "LLM Used"]
_META_X = [42, 237, 431, 626, 836]
_META_W = [175, 175, 175, 190, 174]

_SUBTITLE_IDLE = "How OmniOS understood and executed your request"


# ---------------------------------------------------------------------------
# Welcome / command panel
# ---------------------------------------------------------------------------

class WelcomePanel(Panel):
    REF_W, REF_H = 1038.0, 374.0

    def __init__(self, root, ui: UIContext, *, on_submit: Callable[[str], None],
                 on_mic: Callable[[], None], mic_available: bool) -> None:
        super().__init__(root, ui, "welcome")
        self._on_submit = on_submit
        self._on_mic = on_mic
        self._mic_available = mic_available
        F = ui.fonts

        # Wordmark (tracked) + short gradient rule, and the slogan.
        track = render.fit_tracking("OMNIOS", 15, 117.0, bold=True)
        wm, (wmw, wmh) = render.text_image(
            [("OMNIOS", "#55618A")], 15, bold=True, tracking=track,
            trailing=["#E8479F", "#7C4DFF"],
        )
        self._wordmark = ctk.CTkLabel(self, text="", image=ui.image(wm, wmw, wmh), fg_color="transparent")
        sg_track = render.fit_tracking("YOUR DESKTOP. UNDER COMMAND.", 11, 222.0, bold=False)
        sg, (sgw, sgh) = render.text_image(
            [("YOUR DESKTOP. UNDER COMMAND.", "#8591B3")], 11, bold=False, tracking=sg_track)
        self._slogan = ctk.CTkLabel(self, text="", image=ui.image(sg, sgw, sgh), fg_color="transparent")

        # Headline with the gradient "you today?"
        h1, (h1w, h1h) = render.text_image(
            [("How can I help ", C["ink"]),
             ("you today?", ["#2563EB", "#4A6CF5", "#8B46E6", "#D2429F"])],
            55, bold=True,
        )
        self._h1 = ctk.CTkLabel(self, text="", image=ui.image(h1, h1w, h1h), fg_color="transparent")

        self._sub = ctk.CTkLabel(
            self, text="Open apps, search files, calculate, summarize PDFs, or just ask.",
            font=F["sub"], text_color=C["muted"], anchor="w", fg_color="transparent")

        # Command pill
        self._pill = ctk.CTkFrame(self, fg_color=C["field"], border_width=1,
                                  border_color="#E1E8F8", corner_radius=36)
        spark = icons.glyph_image("spark", 24 * 4, C["blue_2"], 1.5)
        self._spark = ctk.CTkLabel(self._pill, text="", fg_color="transparent",
                                   image=ui.image(spark, 26))
        self._divider = ctk.CTkFrame(self._pill, fg_color="#E3E9F7", width=1, corner_radius=0)
        self.entry = ctk.CTkEntry(
            self._pill, placeholder_text="Type a command or ask anything...",
            placeholder_text_color=C["muted_2"], fg_color="transparent", border_width=0,
            text_color=C["ink"], font=F["input"])
        self.entry.bind("<Return>", lambda _e: self._send())

        mic_color = C["muted"] if mic_available else "#B9C2DA"
        self._mic_img = ui.image(icons.glyph_image("mic", 26 * 4, mic_color, 1.6), 26)
        self._mic_on_img = ui.image(icons.glyph_image("mic", 26 * 4, C["blue"], 1.8), 26)
        # NB: CTkButton enforces a minimum width around its image, so the
        # icon buttons are plain image labels with click bindings.
        self._mic = ctk.CTkLabel(
            self._pill, text="", image=self._mic_img, width=44, height=44, corner_radius=22,
            fg_color="transparent", cursor="hand2" if mic_available else "arrow")
        if mic_available:
            self._mic.bind("<Button-1>", lambda _e: self._mic_clicked())
            self._mic.bind("<Enter>", lambda _e: self._mic.configure(fg_color="#E8EEFF"))
            self._mic.bind("<Leave>", lambda _e: self._mic.configure(
                fg_color="#E3ECFF" if self._listening else "transparent"))
        self._listening = False

        # Send button (pre-rendered gradient images)
        self._send_imgs = {}
        for key, (top, bot, glyph) in {
            "normal": (C["send_top"], C["send_bottom"], "send"),
            "hover":  ("#6DB3FF", "#3C69FF", "send"),
            "busy":   ("#9DBDF5", "#8FA5E8", "clock"),
        }.items():
            btn = render.rounded_gradient_button(74, 68, 20, top, bot)
            g = icons.glyph_image(glyph, 34 * 3, "#FFFFFF", 1.5)
            btn.alpha_composite(g, ((btn.width - g.width) // 2, (btn.height - g.height) // 2))
            self._send_imgs[key] = ui.image(btn, 74, 68)
        self._send_btn = ctk.CTkLabel(
            self._pill, text="", image=self._send_imgs["normal"], width=74, height=68,
            fg_color="transparent", cursor="hand2")
        self._send_btn.bind("<Button-1>", lambda _e: self._send())
        self._send_btn.bind("<Enter>", lambda _e: self._send_hover(True))
        self._send_btn.bind("<Leave>", lambda _e: self._send_hover(False))
        self._busy = False

        # Quick-action chips
        self._chips: list[tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel, tuple]] = []
        for glyph, color, label, cmd, rx, rw in _CHIPS:
            chip = ctk.CTkFrame(self, fg_color=C["chip_pill"], border_width=1,
                                border_color="#E5EBFA", corner_radius=27, cursor="hand2")
            ic = ctk.CTkLabel(chip, text="", fg_color="transparent",
                              image=ui.image(icons.glyph_image(glyph, 26 * 4, color, 1.9), 26))
            tx = ctk.CTkLabel(chip, text=label, font=F["chip"], text_color=C["ink_2"],
                              fg_color="transparent", anchor="w")
            for w in (chip, ic, tx):
                w.bind("<Button-1>", lambda _e, c=cmd: self.fill(c))
                w.bind("<Enter>", lambda _e, ch=chip: ch.configure(fg_color="#FFFFFF"))
                w.bind("<Leave>", lambda _e, ch=chip: ch.configure(fg_color=C["chip_pill"]))
            self._chips.append((chip, ic, tx, (rx, rw)))

    # -- layout -----------------------------------------------------------
    def relayout(self) -> None:
        f = self.f
        self.put(self._wordmark, 42, 40, anchor="w")
        self.put_right(self._slogan, 37, 40, anchor="e")
        self.put(self._h1, 38, 115, anchor="w")
        self.put(self._sub, 42, 167, anchor="w")

        pill_w, pill_h = self.W(955), self.H(73)
        self._pill.configure(width=pill_w, height=pill_h, corner_radius=int(pill_h / 2))
        self.put(self._pill, 42, 205)
        pf = self.ui.px
        self._spark.place(x=int(35 * self.sx) - pf(13), rely=0.5, anchor="w")
        self._divider.configure(height=pf(34))
        self._divider.place(x=int(66 * self.sx), rely=0.5, anchor="w")
        send_w = pf(74)
        self._send_btn.configure(width=send_w, height=pf(68))
        self._mic.configure(width=pf(44), height=pf(44), corner_radius=pf(22))
        self._send_btn.place(x=pill_w - send_w - pf(5), rely=0.5, anchor="w")
        self._mic.place(x=int(832 * self.sx), rely=0.5, anchor="center")
        entry_x = int(70 * self.sx)
        self.entry.configure(height=pf(44),
                             width=max(80, pill_w - entry_x - send_w - pf(80)))
        self.entry.place(x=entry_x, rely=0.5, anchor="w")

        chip_h = self.H(54)
        for chip, ic, tx, (rx, rw) in self._chips:
            chip.configure(width=self.W(rw), height=chip_h, corner_radius=int(chip_h / 2))
            self.put(chip, rx, 299)
            ic.place(x=self.ui.px(22), rely=0.5, anchor="w")
            tx.place(x=self.ui.px(56), rely=0.5, anchor="w")

    # -- behaviour --------------------------------------------------------
    def _send_hover(self, on: bool) -> None:
        if not self._busy:
            self._send_btn.configure(image=self._send_imgs["hover" if on else "normal"])

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._send_btn.configure(
            image=self._send_imgs["busy" if busy else "normal"],
            cursor="arrow" if busy else "hand2")

    def set_listening(self, on: bool) -> None:
        self._listening = on
        self._mic.configure(image=self._mic_on_img if on else self._mic_img,
                            fg_color="#E3ECFF" if on else "transparent")
        self.entry.configure(
            placeholder_text="Listening\u2026" if on else "Type a command or ask anything...")

    def flash_placeholder(self, text: str) -> None:
        self.entry.configure(placeholder_text=text)
        self.after(2600, lambda: self.entry.configure(
            placeholder_text="Type a command or ask anything..."))

    def fill(self, text: str) -> None:
        """Quick-action chips pre-fill the input (existing behaviour)."""
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.entry.focus_set()

    def _send(self) -> None:
        text = self.entry.get().strip()
        if text and not self._busy:
            self.entry.delete(0, "end")
            self._on_submit(text)

    def _mic_clicked(self) -> None:
        if self._mic_available:
            self._on_mic()


# ---------------------------------------------------------------------------
# Execution Details panel
# ---------------------------------------------------------------------------

class ExecPanel(Panel):
    REF_W, REF_H = 1038.0, 362.0

    def __init__(self, root, ui: UIContext) -> None:
        super().__init__(root, ui, "exec")
        F = ui.fonts
        self.compact = False

        self._icon = ctk.CTkLabel(
            self, text="", fg_color="transparent",
            image=ui.image(icons.badge_image("pulse", 44 * 3, "#2F6BFF", "#E3ECFF", "circle", 0.52, 1.7), 44))
        self._title = ctk.CTkLabel(self, text="Execution Details", font=F["panel_h"],
                                   text_color=C["ink"], anchor="w", fg_color="transparent")
        self._subtitle = ctk.CTkLabel(self, text=_SUBTITLE_IDLE, font=F["panel_sub"],
                                      text_color=C["muted"], anchor="w", fg_color="transparent")

        self._steps = []     # (circle label, name label, sub label)
        for glyph, gcol, bg, name, sub in _STEPS:
            circ = ctk.CTkLabel(
                self, text="", fg_color="transparent",
                image=ui.image(icons.badge_image(glyph, 80 * 3, gcol, bg, "circle", 0.46, 1.6), 80))
            nm = ctk.CTkLabel(self, text=name, font=F["step"], text_color=C["ink"], fg_color="transparent")
            sb = ctk.CTkLabel(self, text=sub, font=F["step_sub"], text_color=C["muted"], fg_color="transparent")
            self._steps.append((circ, nm, sb))
        arrow = icons.glyph_image("arrow_right", 24 * 4, "#7E96CF", 1.3)
        self._arrows = [
            ctk.CTkLabel(self, text="", fg_color="transparent", image=ui.image(arrow, 24))
            for _ in range(3)
        ]

        self._meta_lbl: list[ctk.CTkLabel] = []
        self._meta_box: list[ctk.CTkFrame] = []
        self._meta_val: list[ctk.CTkLabel] = []
        for name in _META:
            self._meta_lbl.append(ctk.CTkLabel(
                self, text=name, font=F["meta_lbl"], text_color=C["muted"],
                anchor="w", fg_color="transparent"))
            box = ctk.CTkFrame(self, fg_color=C["field"], border_width=1,
                               border_color=C["field_edge"], corner_radius=8)
            val = ctk.CTkLabel(box, text=DASH, font=F["meta_val"], text_color=C["muted_2"],
                               anchor="w", fg_color="transparent")
            self._meta_box.append(box)
            self._meta_val.append(val)

    def relayout(self) -> None:
        compact = self.compact
        self.put(self._icon, 54, 41, anchor="center")
        self.put(self._title, 90, 36, anchor="w")
        self.put(self._subtitle, 90, 61, anchor="w")

        for i, (circ, nm, sb) in enumerate(self._steps):
            if compact:
                circ.place_forget(); nm.place_forget(); sb.place_forget()
                continue
            cx = _STEP_CX[i]
            self.put(circ, cx, 138, anchor="center")
            self.put(nm, cx, 196, anchor="center")
            self.put(sb, cx, 220, anchor="center")
        for i, a in enumerate(self._arrows):
            if compact:
                a.place_forget()
            else:
                self.put(a, _ARROW_CX[i], 140, anchor="center")

        lbl_y, box_y, box_h = (279, 294, 47) if not compact else (116, 131, 47)
        for i in range(5):
            self.put(self._meta_lbl[i], _META_X[i] + 2, lbl_y, anchor="w")
            box = self._meta_box[i]
            box.configure(width=self.W(_META_W[i]), height=self.H(box_h),
                          corner_radius=max(4, self.ui.px(9)))
            self.put(box, _META_X[i], box_y)
            self._meta_val[i].place(x=self.ui.px(16), rely=0.5, anchor="w")

    # -- state ------------------------------------------------------------
    def set_compact(self, compact: bool) -> None:
        """Compact = stage flow hidden (used while the result body is open)."""
        self.compact = compact
        self.REF_H = float(EXEC_H_COMPACT if compact else 362)

    def show_idle(self) -> None:
        self._subtitle.configure(text=_SUBTITLE_IDLE)
        self._set_values([DASH] * 5, muted=True)

    def show_running(self, command: str) -> None:
        shown = command if len(command) <= 46 else command[:45] + "\u2026"
        self._subtitle.configure(text=f"Running \u201c{shown}\u201d\u2026")
        self._set_values(["\u2026"] * 5, muted=True)

    def show_execution(self, ex: Execution) -> None:
        d = ex.decision
        self._subtitle.configure(text=_SUBTITLE_IDLE)
        vals = [
            d.intent.value,
            d.route.value,
            f"{d.confidence:.0%}",
            d.action_name or DASH,
            "Yes" if ex.used_llm else "No",
        ]
        self._set_values(vals, muted=False)

    def _set_values(self, values: list[str], *, muted: bool) -> None:
        for lbl, v in zip(self._meta_val, values):
            lbl.configure(text=v, text_color=C["muted_2"] if muted else "#26324F")


# ---------------------------------------------------------------------------
# Result row
# ---------------------------------------------------------------------------

# outcome -> (glyph, glyph colour, circle bg, title, link text, link colour, subtitle)
_RESULT_STYLE = {
    Outcome.SUCCESS: ("doc", "#7C4DFF", "#EEE6FF", "Result available", "Click to view", "#3F36F0",
                      "Last output hidden"),
    Outcome.ERROR: ("alert", "#E5484D", "#FFE3E3", "Action failed", "Click to view details", "#E5484D",
                    "Error details hidden"),
    Outcome.REFUSED: ("alert", "#D9822B", "#FFEBD1", "Action refused", "Click to view details", "#D9822B",
                      "Refusal details hidden"),
    Outcome.PENDING: ("clock", "#D9822B", "#FFEBD1", "Action pending", "Click to view", "#D9822B",
                      "The action has not finished"),
    Outcome.LLM_UNAVAILABLE: ("cloud", "#D9822B", "#FFEBD1", "LLM not configured", "Click to view",
                              "#D9822B", "No language-model call was made"),
    Outcome.NO_ACTION: ("alert", "#8591B3", "#E9EEFB", "No supported action", "Click to view",
                        "#6B7AA5", "OmniOS could not match this request"),
    Outcome.EMPTY: ("search", "#8591B3", "#E9EEFB", "No matches found", "", "#6B7AA5",
                    "The command completed without any output"),
}


def result_body_text(ex: Execution) -> str:
    """Text shown when the row is expanded — built only from real data."""
    res = ex.result
    if ex.outcome is Outcome.LLM_UNAVAILABLE:
        return ("This request was routed to the LLM, but GROQ_API_KEY is not set, "
                "so no model call was made.\n\n"
                "Add GROQ_API_KEY to your .env file, then press Refresh in System Status.")
    if ex.outcome is Outcome.NO_ACTION:
        why = getattr(ex.decision, "explanation", "") or "No supported action matched."
        return f"{why}\n\nTry: calculate, open <app>, open <url>, or find <filename>."
    if ex.outcome in (Outcome.ERROR, Outcome.REFUSED):
        label = "Action refused" if ex.outcome is Outcome.REFUSED else "Error"
        detail = getattr(res, "error", None) or (str(res.output) if res.output is not None else "No details available.")
        return f"{label}:\n{detail}"
    out = getattr(res, "output", None)
    if isinstance(out, (list, tuple)):
        return "\n".join(str(x) for x in out)
    return "" if out is None else str(out)


class ResultPanel(Panel):
    REF_W, REF_H = 1038.0, 91.0

    def __init__(self, root, ui: UIContext, *, on_toggle: Callable[[bool], None]) -> None:
        super().__init__(root, ui, "result")
        self._on_toggle = on_toggle
        self.expanded = False
        self._expandable = False
        self._ex: Optional[Execution] = None
        self._title_font = ui.fonts["res_title"]
        F = ui.fonts

        self._badge = ctk.CTkLabel(self, text="", fg_color="transparent")
        self._title = ctk.CTkLabel(self, text="", font=F["res_title"], text_color=C["ink"],
                                   anchor="w", fg_color="transparent")
        self._link = ctk.CTkLabel(self, text="", font=F["res_title"], anchor="w", fg_color="transparent")
        self._sub = ctk.CTkLabel(self, text="", font=F["res_sub"], text_color=C["muted"],
                                 anchor="w", fg_color="transparent")
        self._count = ctk.CTkLabel(self, text="", font=F["res_badge"], text_color=C["blue"],
                                   fg_color="#E4EBFF", corner_radius=17)
        self._chev_down = ui.image(icons.glyph_image("chev_down", 26 * 4, "#2F6BFF", 1.8), 26)
        self._chev_up = ui.image(icons.glyph_image("chev_up", 26 * 4, "#2F6BFF", 1.8), 26)
        self._chev = ctk.CTkLabel(self, text="", image=self._chev_down, fg_color="transparent")

        self._body = ctk.CTkFrame(self, fg_color="#F7F9FF", border_width=1,
                                  border_color="#DCE5FB", corner_radius=14)
        self._body.pack_propagate(False)
        self._text = ctk.CTkTextbox(self._body, fg_color="transparent", border_width=0,
                                    text_color=C["ink_2"], font=F["mono"], wrap="word",
                                    state="disabled")
        self._text.pack(fill="both", expand=True, padx=10, pady=10)

        self._clickable = (self, self._badge, self._title, self._link, self._sub,
                           self._count, self._chev)
        for w in self._clickable:
            w.bind("<Button-1>", self._clicked)

    # -- state ------------------------------------------------------------
    def show(self, ex: Execution) -> None:
        self._ex = ex
        self.expanded = False
        glyph, gcol, bg, title, link, lcol, sub = _RESULT_STYLE[ex.outcome]
        self._badge.configure(image=self.ui.image(
            icons.badge_image(glyph, 70 * 3, gcol, bg, "circle", 0.46, 1.6), 70))
        self._title.configure(text=title)
        self._link.configure(text=(" \u00b7 " + link) if link else "", text_color=lcol)
        self._sub.configure(text=sub)
        count = ex.item_count
        self._count.configure(text=f"{count} item{'s' if count != 1 else ''}" if count is not None else "")
        self._expandable = ex.outcome is not Outcome.EMPTY
        self._chev.configure(image=self._chev_down)
        self._set_body(result_body_text(ex) if self._expandable else "")
        self._sync_ref_height()
        self.relayout()

    def hide(self) -> None:
        self._ex = None
        self.expanded = False
        self._sync_ref_height()

    def toggle(self) -> None:
        if self._ex is None or not self._expandable:
            return
        self.expanded = not self.expanded
        self._chev.configure(image=self._chev_up if self.expanded else self._chev_down)
        self._sync_ref_height()
        self._sub.configure(text="Output shown \u00b7 Click to collapse" if self.expanded
                            else _RESULT_STYLE[self._ex.outcome][6])
        self._on_toggle(self.expanded)

    def _clicked(self, _e=None) -> None:
        self.toggle()

    def _set_body(self, text: str) -> None:
        err = self._ex is not None and self._ex.outcome in (Outcome.ERROR, Outcome.REFUSED)
        self._text.configure(state="normal", text_color="#C2343A" if err else C["ink_2"])
        self._text.delete("0.0", "end")
        self._text.insert("0.0", text)
        self._text.configure(state="disabled")

    # -- layout -----------------------------------------------------------
    def _sync_ref_height(self) -> None:
        extra = 362 - EXEC_H_COMPACT
        self.REF_H = 91.0 + (extra if self.expanded else 0)

    def relayout(self) -> None:
        if self._ex is None:
            return
        cy = self.Y(45.5)
        self._badge.place(x=self.X(75), y=cy, anchor="center")
        title_y = cy - self.ui.px(13)
        self._title.place(x=self.X(128), y=title_y, anchor="w")
        # " · Click to view" sits right after the (measured) title text
        tw = self._title_font.measure(self._title.cget("text"))
        self._link.place(x=self.X(128) + tw, y=title_y, anchor="w")
        self._sub.place(x=self.X(128), y=cy + self.ui.px(13), anchor="w")
        if self._count.cget("text"):
            self._count.configure(width=self.ui.px(76), height=self.ui.px(34))
            self._count.place(x=round(self.pw - self.ins - 197 * self.sx), y=cy, anchor="e")
        else:
            self._count.place_forget()
        if self._expandable:
            self._chev.place(x=round(self.pw - self.ins - 46 * self.sx), y=cy, anchor="center")
        else:
            self._chev.place_forget()
        if self.expanded:
            top = self.Y(91)
            self._body.configure(width=max(40, int(self.pw - 56 * self.sx)),
                                 height=max(40, int(self.ph - 91 * self.sy - 16 * self.sy)))
            self._body.place(x=self.X(28), y=top)
        else:
            self._body.place_forget()


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class CentralPanel:
    """Owns the three main panels and keeps them in sync with ``AppState``."""

    def __init__(self, root, *, ui: UIContext, state: AppState,
                 on_submit: Callable[[str], None],
                 on_layout_change: Callable[[], None]) -> None:
        self.root = root
        self.ui = ui
        self._state = state
        self._on_layout_change = on_layout_change
        mic_ok, self.mic_reason = voice.availability()
        self.welcome = WelcomePanel(root, ui, on_submit=on_submit,
                                    on_mic=self._start_voice, mic_available=mic_ok)
        self.exec = ExecPanel(root, ui)
        self.result = ResultPanel(root, ui, on_toggle=self._toggled)
        self.result_visible = False
        state.subscribe(self.refresh)

    # -- panels / layout state -------------------------------------------
    @property
    def panels(self) -> dict[str, Panel]:
        d = {"welcome": self.welcome, "exec": self.exec}
        if self.result_visible:
            d["result"] = self.result
        return d

    @property
    def expanded(self) -> bool:
        return self.result_visible and self.result.expanded

    def _toggled(self, expanded: bool) -> None:
        self.exec.set_compact(expanded)
        self._on_layout_change()

    # -- state refresh ----------------------------------------------------
    def refresh(self) -> None:
        st = self._state
        self.welcome.set_busy(st.is_processing)
        ex = st.current
        was_visible = self.result_visible
        if st.is_processing:
            self.exec.set_compact(False)
            self.exec.show_running(st.running_command or "")
            self.result_visible = False
            self.result.hide()
        elif ex is not None:
            self.exec.set_compact(False)
            self.exec.show_execution(ex)
            self.result.show(ex)
            self.result_visible = True
        else:
            self.exec.set_compact(False)
            self.exec.show_idle()
            self.result_visible = False
            self.result.hide()
        if not self.result_visible:
            self.result.place_forget()
        if was_visible != self.result_visible or self.result_visible:
            self._on_layout_change()

    # -- voice ------------------------------------------------------------
    def _start_voice(self) -> None:
        self.welcome.set_listening(True)

        def done(text, error):
            self.root.after(0, lambda: self._voice_done(text, error))

        voice.listen_async(done)

    def _voice_done(self, text: Optional[str], error: Optional[str]) -> None:
        self.welcome.set_listening(False)
        if text:
            self.welcome.fill(text)      # shown for review; the user presses Send
        elif error:
            self.welcome.flash_placeholder(error)
