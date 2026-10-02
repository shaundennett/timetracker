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

# Pale-pink palette.
BG = "#fbeef4"       # window background (pale pink)
SURFACE = "#fffbfd"  # cards / entries (near-white, warm)
INK = "#3d2b34"      # primary text (deep plum)
MUTED = "#9a7f8b"    # secondary text
ACCENT = "#d6558a"   # primary action / highlights (rose)
ACCENT_HOVER = "#bf4778"
DANGER = "#c0392b"   # distinct brick-red so it reads as "danger" on pink
BORDER = "#f0cede"   # soft pink border
ZEBRA = "#fdf1f6"    # alternate table rows
SEL = "#f8d3e3"      # selected table row
HEADER = "#f5d9e6"   # table heading / subtle fills
HOVER = "#f7e4ec"    # button hover


def apply_theme(root: tk.Misc) -> ttk.Style:
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
    style.configure("Total.TLabel", background=BG, foreground=ACCENT,
                    font=("Segoe UI Semibold", 12))

    # Cards / grouped sections.
    style.configure("TLabelframe", background=BG, bordercolor=BORDER,
                    relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=BG, foreground=ACCENT,
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
              bordercolor=[("active", ACCENT)])

    style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                    bordercolor=ACCENT, padding=(14, 7),
                    font=("Segoe UI Semibold", 10))
    style.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)],
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
