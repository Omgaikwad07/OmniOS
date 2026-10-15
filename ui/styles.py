"""
ui/styles.py
============
Central design tokens for the OmniOS desktop UI.

All colours, fonts, spacing values, and icon characters are defined
here.  No widget may hard-code a colour, font, or pixel dimension
directly — always import from this module.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    # Surfaces
    "window_bg":    "#DDE9FF",   # Main window / app background
    "surface":      "#F7F9FF",   # Card / panel fill
    "surface_alt":  "#F8FAFC",   # Input field / subtle alternate bg
    "nav_selected": "#EFF6FF",   # Highlighted nav item background

    # Borders
    "border":       "#DDE3EE",   # Primary border / separator
    "border_input": "#CBD5E1",   # Input-field border (slightly stronger)

    # Text
    "text_primary":   "#1E293B",  # Dark navy — headings and important labels
    "text_secondary": "#64748B",  # Medium grey — body and metadata
    "text_muted":     "#94A3B8",  # Light grey — placeholders and disabled
    "text_link":      "#2563EB",  # Blue — links and active labels

    # Actions
    "blue":       "#2563EB",   # Primary action (Send button, active nav)
    "blue_hover": "#1D4ED8",   # Primary button hover
    "blue_light": "#DBEAFE",   # Light blue tint

    # Status accents
    "green":   "#22C55E",  # Ready / Success
    "amber":   "#F59E0B",  # Warning / Not Configured
    "red":     "#EF4444",  # Error
    "purple":  "#8B5CF6",  # Step 2 / LLM

    # Step icon backgrounds and foregrounds
    "step1_bg": "#EFF6FF",  "step1_fg": "#3B82F6",   # blue-50 / blue
    "step2_bg": "#F5F3FF",  "step2_fg": "#8B5CF6",   # violet-50 / violet
    "step3_bg": "#ECFDF5",  "step3_fg": "#16A34A",   # green-50 / green
    "step4_bg": "#FFF7ED",  "step4_fg": "#EA580C",   # orange-50 / orange
}

# ---------------------------------------------------------------------------
# Typography  — (family, size, weight)
# ---------------------------------------------------------------------------

FONTS: dict[str, tuple] = {
    "heading_xl": ("Segoe UI", 48, "bold"),    # Main greeting heading
    "heading_lg": ("Segoe UI", 22, "bold"),    # Panel headings
    "heading_md": ("Segoe UI", 16, "bold"),    # Sub-headings / nav items
    "heading_sm": ("Segoe UI", 13, "bold"),    # Small headings / field labels
    "body":       ("Segoe UI", 18, "normal"),  # Standard body text
    "body_sm":    ("Segoe UI", 13, "normal"),  # Small body
    "caption":    ("Segoe UI", 12, "normal"),  # Captions / metadata values
    "logo":       ("Segoe UI", 14, "bold"),    # "OmniOS" in sidebar
    "greeting":   ("Segoe UI", 13, "normal"),  # "Hello," line
    "mono":       ("Consolas",  11, "normal"),  # Result output (monospace)
    # Icon fonts — Segoe MDL2 Assets is a Windows 10/11 system icon font.
    "icon_sm":    ("Segoe MDL2 Assets", 13, "normal"),
    "icon_md":    ("Segoe MDL2 Assets", 15, "normal"),
    "icon_lg":    ("Segoe MDL2 Assets", 20, "normal"),
}

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

DIMS: dict[str, int] = {
    "sidebar_left_w":  170,   # Left navigation sidebar width
    "sidebar_right_w": 235,   # Right status sidebar width
    "window_w":        1024,  # Default window width
    "window_h":        680,   # Default window height
    "window_min_w":    900,   # Minimum resize width
    "window_min_h":    560,   # Minimum resize height
    "card_radius":     10,    # Rounded corner radius for cards
    "btn_radius":      8,     # Button corner radius
    "chip_radius":     6,     # Quick-action chip corner radius
    "border_w":        1,     # Standard border thickness
    "pad_card":        16,    # Standard card internal padding
    "pad_sm":          8,     # Small padding
    "nav_item_h":      36,    # Navigation item height
    "status_dot":      9,     # Status indicator dot diameter
    "step_circle":     40,    # Execution-step icon circle diameter
    "logo_circle":     36,    # Logo circle diameter
    "input_h":         44,    # Command input bar height
    "send_btn_w":      90,    # Send button width
    "chip_h":          34,    # Quick-action chip height
}

# ---------------------------------------------------------------------------
# Icon characters  (Segoe MDL2 Assets codepoints)
# These render as proper vector icons on Windows 10/11.
# ---------------------------------------------------------------------------

ICO: dict[str, str] = {
    # Navigation
    "chat":       "\uE8BD",   # Comment / chat bubble
    "history":    "\uE823",   # Clock
    "settings":   "\uE713",   # Settings gear

    # Input bar
    "flash":      "\uE945",   # Lightning bolt (command input accent)
    "mic":        "\uE720",   # Microphone
    "send":       "\uE724",   # Send / paper plane

    # Quick-action chips
    "calculator": "\uE8EF",   # Calculator
    "search":     "\uE721",   # Search / find
    "document":   "\uE7C3",   # Document / file
    "pdf":        "\uECB4",   # PDF document

    # Execution details
    "wave":       "\uE9D9",   # Waveform / equalizer bars
    "route":      "\uEA8F",   # Route / branch
    "execute":    "\uE90F",   # Processing / run
    "result":     "\uE8A5",   # Result document

    # Right sidebar
    "engine":     "\uE7F7",   # Local engine / monitor
    "cloud":      "\uE753",   # Cloud (Groq)
    "file_proc":  "\uE8A5",   # File processing
    "clock":      "\uE823",   # Recent activity clock
}


# ===========================================================================
# V4 design tokens — reference-faithful pastel UI
# ===========================================================================
# The approved reference is 1586 x 992 including a 44 px title bar, so the
# client area the app draws into is 1586 x 948.  Every geometry value below
# is expressed in those reference pixels and scaled at runtime (ui/scaling.py).

REF_W = 1586
REF_H = 948

# Column / row proportions measured from the reference (client coordinates).
LAYOUT = {
    "margin_left":  124,
    "main_w":       1038,
    "gap_x":        24,
    "side_w":       380,
    "margin_right": 20,
    "margin_top":   29,
    "margin_bottom": 24,
    # Main column rows
    "welcome_h":    374,
    "gap_a":        20,
    "exec_h":       362,
    "gap_b":        16,
    "result_h":     91,
    # Sidebar rows
    "status_h":     471,
    "gap_s":        16,
    "activity_h":   408,
}

PALETTE: dict[str, str] = {
    "panel":        "#F0F3FE",   # panel surface (solid: Tk cannot do alpha)
    "panel_edge":   "#FFFFFF",
    "field":        "#F8FAFF",   # input pill / metadata boxes / chips
    "field_edge":   "#DCE4F6",
    "card":         "#F7F8FE",   # activity cards
    "ink":          "#0A1020",   # headline navy
    "ink_2":        "#1B2440",   # panel headings
    "muted":        "#6B7AA5",   # subtitle / descriptions
    "muted_2":      "#8591B3",   # placeholders / captions
    "blue":         "#2F6BFF",
    "blue_2":       "#4B8CFF",
    "violet":       "#7C4DFF",
    "pink":         "#E8479F",
    "green":        "#16B364",
    "green_text":   "#12A150",
    "amber":        "#F5A524",
    "red":          "#EF4444",
    "orange":       "#F58A1F",
    "send_top":     "#5AA8FF",
    "send_bottom":  "#2D5CFF",
    # circle / badge backgrounds
    "bg_blue":      "#E3ECFF",
    "bg_violet":    "#ECE6FF",
    "bg_green":     "#DDF6EA",
    "bg_orange":    "#FFEBD6",
    "bg_pink":      "#FFE3EF",
    "bg_yellow":    "#FFF3CE",
    "bg_lavender":  "#EEE6FF",
    "chip_pill":    "#F4F6FD",
}

# (family, px size, weight).  Sizes are reference pixels and are scaled live.
TYPE: dict[str, tuple[int, str]] = {
    "sub":        (21, "normal"),
    "input":      (17, "normal"),
    "chip":       (14, "normal"),
    "panel_h":    (19, "bold"),
    "panel_sub":  (15, "normal"),
    "step":       (16, "bold"),
    "step_sub":   (14, "normal"),
    "meta_lbl":   (14, "normal"),
    "meta_val":   (14, "normal"),
    "side_h":     (17, "bold"),
    "side_link":  (16, "normal"),
    "svc_name":   (14, "bold"),
    "svc_state":  (15, "normal"),
    "svc_desc":   (14, "normal"),
    "act_cmd":    (15, "normal"),
    "act_meta":   (13, "normal"),
    "act_time":   (13, "normal"),
    "res_title":  (18, "bold"),
    "res_sub":    (14, "normal"),
    "res_badge":  (14, "normal"),
    "mono":       (14, "normal"),
    "empty_h":    (15, "bold"),
    "empty_s":    (13, "normal"),
}

UI_FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"
