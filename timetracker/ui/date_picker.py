"""Date picker widget: a read-only DD/MM/YYYY box plus a calendar popup.

The text box cannot be typed into, so an invalid or ambiguous date can never be
entered. Callers work with ``datetime.date`` objects via ``get_date`` and
``set_date`` and never touch the display string.
"""

from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date
from tkinter import ttk
from typing import Callable, Optional

from ..models import DISPLAY_DATE_FORMAT
from .style import ACCENT, BORDER, HEADER, INK, MUTED, SEL, SURFACE

_DAY_NAMES = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")


class DatePicker(ttk.Frame):
    """Read-only date box with a calendar button.

    ``on_change`` is called with no arguments whenever the user picks a date
    or ``set_date`` changes it.
    """

    def __init__(self, master: tk.Misc, initial: Optional[date] = None,
                 on_change: Optional[Callable[[], None]] = None,
                 width: int = 12) -> None:
        super().__init__(master)
        self._date = initial or date.today()
        self._on_change = on_change
        self._popup: Optional[tk.Toplevel] = None

        self._var = tk.StringVar(value=self._date.strftime(DISPLAY_DATE_FORMAT))
        self._entry = ttk.Entry(self, textvariable=self._var, width=width,
                                state="readonly")
        self._entry.pack(side="left")
        self._button = ttk.Button(self, text="📅", width=3,
                                  command=self._open_popup)
        self._button.pack(side="left", padx=(2, 0))
        self._entry.bind("<Button-1>", lambda _e: self._open_popup())

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def get_date(self) -> date:
        return self._date

    def set_date(self, value: date, notify: bool = True) -> None:
        self._date = value
        self._var.set(value.strftime(DISPLAY_DATE_FORMAT))
        if notify and self._on_change:
            self._on_change()

    # ------------------------------------------------------------------ #
    # Calendar popup
    # ------------------------------------------------------------------ #
    def _open_popup(self) -> None:
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.lift()
            return
        popup = tk.Toplevel(self)
        popup.title("Pick a date")
        popup.transient(self.winfo_toplevel())
        popup.resizable(False, False)
        popup.configure(background=SURFACE, padx=8, pady=8)
        popup.bind("<Escape>", lambda _e: popup.destroy())
        self._popup = popup

        self._shown = date(self._date.year, self._date.month, 1)
        nav = ttk.Frame(popup)
        nav.pack(fill="x")
        ttk.Button(nav, text="◀", width=3,
                   command=lambda: self._change_month(-1)).pack(side="left")
        self._header = tk.Label(nav, background=SURFACE, foreground=INK,
                                font=("Segoe UI", 10, "bold"))
        self._header.pack(side="left", expand=True)
        ttk.Button(nav, text="▶", width=3,
                   command=lambda: self._change_month(1)).pack(side="right")

        self._grid = tk.Frame(popup, background=SURFACE)
        self._grid.pack(pady=(6, 0))
        self._draw_month()

        # Place just below the entry, then take focus so Escape works.
        popup.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height() + 2
        popup.geometry(f"+{x}+{y}")
        popup.focus_set()
        popup.grab_set()

    def _change_month(self, delta: int) -> None:
        month = self._shown.month - 1 + delta
        self._shown = date(self._shown.year + month // 12, month % 12 + 1, 1)
        self._draw_month()

    def _draw_month(self) -> None:
        for child in self._grid.winfo_children():
            child.destroy()
        self._header.configure(
            text=f"{calendar.month_name[self._shown.month]} {self._shown.year}")

        for col, name in enumerate(_DAY_NAMES):
            tk.Label(self._grid, text=name, width=4, background=HEADER,
                     foreground=MUTED).grid(row=0, column=col, padx=1, pady=1)

        today = date.today()
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
            self._shown.year, self._shown.month)
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                in_month = day.month == self._shown.month
                if day == self._date:
                    bg, fg = ACCENT, "white"
                elif day == today:
                    bg, fg = SEL, INK
                else:
                    bg, fg = SURFACE, INK if in_month else BORDER
                tk.Button(self._grid, text=str(day.day), width=3, relief="flat",
                          background=bg, foreground=fg, borderwidth=0,
                          activebackground=SEL,
                          command=lambda d=day: self._pick(d)).grid(
                    row=row, column=col, padx=1, pady=1)

    def _pick(self, chosen: date) -> None:
        popup = self._popup
        self._popup = None
        if popup is not None:
            popup.destroy()
        self.set_date(chosen)
