"""Central look-and-feel for the app.

One :func:`apply_theme` call configures ttk globally (styles are per-Tk, so
every window and dialog inherits the same palette). Built on the cross-platform
``clam`` theme, which — unlike the native Windows theme — lets us recolour
buttons, headings, and tables consistently.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# Neutral grey palette with a pink default accent (roles can override it).
BG = "#eceef0"       # window background (neutral grey)
SURFACE = "#fafafa"  # cards / entries (near-white)
INK = "#2b2e33"      # primary text (charcoal)
MUTED = "#80858c"    # secondary text
ACCENT = "#d6558a"   # primary action / highlights (rose)
ACCENT_HOVER = "#bf4778"
DANGER = "#c0392b"   # distinct brick-red so it reads as "danger" on grey
BORDER = "#d3d6da"   # soft grey border
ZEBRA = "#f3f4f6"    # alternate table rows
SEL = "#d9dde3"      # selected table row
HEADER = "#e0e3e7"   # table heading / subtle fills
HOVER = "#e4e6ea"    # button hover

_current_accent = ACCENT


def is_valid_hex(color: str) -> bool:
    """True for a ``#rrggbb`` colour string."""
    return (isinstance(color, str) and len(color) == 7 and color[0] == "#"
            and all(c in "0123456789abcdefABCDEF" for c in color[1:]))


def darken(color: str, factor: float = 0.88) -> str:
    """Scale each RGB channel by ``factor`` (used for hover shades)."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(int(r * factor), int(g * factor),
                                        int(b * factor))


def readable_fg(color: str) -> str:
    """White or dark ink, whichever is more legible on ``color``."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return INK if luminance > 0.6 else "#ffffff"


def current_accent() -> str:
    """The accent applied by the last :func:`apply_theme` call.

    For plain ``tk`` widgets, which don't follow ttk styles.
    """
    return _current_accent


def apply_theme(root: tk.Misc, accent: str = ACCENT) -> ttk.Style:
    global _current_accent
    if not is_valid_hex(accent):
        accent = ACCENT
    _current_accent = accent
    accent_hover = ACCENT_HOVER if accent == ACCENT else darken(accent)
    accent_fg = readable_fg(accent)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass  # fall back to whatever is available

    base = tkfont.nametofont("TkDefaultFont")
    base.configure(family="Segoe UI", size=10)
    text_font = tkfont.nametofont("TkTextFont")
    text_font.configure(family="Segoe UI", size=10)
    root.option_add("*Font", base)

    if isinstance(root, (tk.Tk, tk.Toplevel)):
        root.configure(background=BG)

    style.configure(".", background=BG, foreground=INK,
                    fieldbackground=SURFACE, bordercolor=BORDER)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=INK)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED)
    style.configure("Heading.TLabel", background=BG, foreground=INK,
                    font=("Segoe UI Semibold", 15))
    style.configure("SubHeading.TLabel", background=BG, foreground=MUTED,
                    font=("Segoe UI", 10))
    style.configure("Total.TLabel", background=BG, foreground=accent,
                    font=("Segoe UI Semibold", 12))

    # Cards / grouped sections.
    style.configure("TLabelframe", background=BG, bordercolor=BORDER,
                    relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=BG, foreground=accent,
                    font=("Segoe UI Semibold", 10))

    # Inputs.
    style.configure("TEntry", fieldbackground=SURFACE, bordercolor=BORDER,
                    padding=4)
    style.configure("TCombobox", fieldbackground=SURFACE, bordercolor=BORDER,
                    padding=3)
    style.map("TCombobox", fieldbackground=[("readonly", SURFACE)])

    # Buttons: a neutral default and a coloured accent variant.
    style.configure("TButton", background=SURFACE, foreground=INK,
                    bordercolor=BORDER, focuscolor=BG, padding=(12, 6))
    style.map("TButton",
              background=[("active", HOVER), ("pressed", SEL)],
              bordercolor=[("active", accent)])

    style.configure("Accent.TButton", background=accent, foreground=accent_fg,
                    bordercolor=accent, padding=(14, 7),
                    font=("Segoe UI Semibold", 10))
    style.map("Accent.TButton",
              background=[("active", accent_hover), ("pressed", accent_hover)],
              foreground=[("disabled", "#e5e7eb")])

    style.configure("Danger.TButton", background=SURFACE, foreground=DANGER,
                    bordercolor=BORDER, padding=(12, 6))
    style.map("Danger.TButton",
              background=[("active", "#f7dcd8")],
              bordercolor=[("active", DANGER)])

    # Tables.
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE,
                    foreground=INK, rowheight=28, bordercolor=BORDER,
                    borderwidth=1)
    style.configure("Treeview.Heading", background=HEADER, foreground=INK,
                    font=("Segoe UI Semibold", 9), relief="flat", padding=6)
    style.map("Treeview.Heading", background=[("active", SEL)])
    style.map("Treeview",
              background=[("selected", SEL)],
              foreground=[("selected", INK)])

    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TSeparator", background=BORDER)

    return style
