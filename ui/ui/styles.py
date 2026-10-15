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
    "window_bg":    "#DDEAFF",   # Main window / app background
    "surface":      "#F7FAFF",   # Card / panel fill
    "surface_alt":  "#F3F7FF",   # Input field / subtle alternate bg
    "nav_selected": "#E4ECFF",   # Highlighted nav item background

    # Borders
    "border":       "#D5E0F5",   # Primary border / separator
    "border_input": "#CCD9F5",   # Input-field border (slightly stronger)

    # Text
    "text_primary":   "#101A31",  # Dark navy — headings and important labels
    "text_secondary": "#657DAE",  # Medium grey — body and metadata
    "text_muted":     "#8CA0C5",  # Light grey — placeholders and disabled
    "text_link":      "#365BFF",  # Blue — links and active labels

    # Actions
    "blue":       "#2867FF",   # Primary action (Send button, active nav)
    "blue_hover": "#174CE0",   # Primary button hover
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
    "heading_xl": ("Segoe UI", 24, "bold"),    # Main greeting heading
    "heading_lg": ("Segoe UI", 15, "bold"),    # Panel headings
    "heading_md": ("Segoe UI", 13, "bold"),    # Sub-headings / nav items
    "heading_sm": ("Segoe UI", 11, "bold"),    # Small headings / field labels
    "body":       ("Segoe UI", 12, "normal"),  # Standard body text
    "body_sm":    ("Segoe UI", 11, "normal"),  # Small body
    "caption":    ("Segoe UI", 10, "normal"),  # Captions / metadata values
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
    "sidebar_left_w":  0,   # Left navigation sidebar width
    "sidebar_right_w": 360,   # Right status sidebar width
    "window_w":        1536,  # Default window width
    "window_h":        1024,   # Default window height
    "window_min_w":    1100,   # Minimum resize width
    "window_min_h":    720,   # Minimum resize height
    "card_radius":     18,    # Rounded corner radius for cards
    "btn_radius":      8,     # Button corner radius
    "chip_radius":     6,     # Quick-action chip corner radius
    "border_w":        1,     # Standard border thickness
    "pad_card":        20,    # Standard card internal padding
    "pad_sm":          8,     # Small padding
    "nav_item_h":      36,    # Navigation item height
    "status_dot":      9,     # Status indicator dot diameter
    "step_circle":     58,    # Execution-step icon circle diameter
    "logo_circle":     36,    # Logo circle diameter
    "input_h":         70,    # Command input bar height
    "send_btn_w":      76,    # Send button width
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
