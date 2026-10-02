"""Time picker widget: two spinboxes for a 24-hour ``HH:MM`` value.

Hours run 00-23 and minutes 00-59, wrapping at the ends, and typing is limited
to digits in range, so an invalid or 12-hour time can never be entered.

The widget is bound to a ``tk.StringVar`` that always holds a valid,
zero-padded ``HH:MM`` string, so callers keep using ``var.get()`` / ``var.set()``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..models import normalize_time


class TimePicker(ttk.Frame):
    def __init__(self, master: tk.Misc, variable: tk.StringVar) -> None:
        super().__init__(master)
        self._var = variable
        self._hour = tk.StringVar()
        self._minute = tk.StringVar()
        self._syncing = False

        self._hour_box = self._make_spinbox(self._hour, 23)
        self._hour_box.pack(side="left")
        ttk.Label(self, text=":").pack(side="left", padx=2)
        self._minute_box = self._make_spinbox(self._minute, 59)
        self._minute_box.pack(side="left")

        self._hour.trace_add("write", lambda *_: self._on_box_change())
        self._minute.trace_add("write", lambda *_: self._on_box_change())
        self._var.trace_add("write", lambda *_: self._on_var_change())
        self._on_var_change()

    def _make_spinbox(self, var: tk.StringVar, maximum: int) -> ttk.Spinbox:
        # Only allow nothing, or up to two digits that stay within range.
        def allowed(proposed: str) -> bool:
            return proposed == "" or (
                proposed.isdigit() and len(proposed) <= 2
                and int(proposed) <= maximum)

        box = ttk.Spinbox(
            self, from_=0, to=maximum, wrap=True, width=3, format="%02.0f",
            textvariable=var, validate="key",
            validatecommand=(self.register(allowed), "%P"))
        # Pad a half-typed value ("9" -> "09", "" -> "00") when leaving the box.
        box.bind("<FocusOut>", lambda _e: self._pad())
        return box

    def _on_box_change(self) -> None:
        """Boxes -> variable, once both hold a complete value."""
        if self._syncing:
            return
        hour, minute = self._hour.get(), self._minute.get()
        if not hour or not minute:
            return
        self._syncing = True
        try:
            self._var.set(f"{int(hour):02d}:{int(minute):02d}")
        finally:
            self._syncing = False

    def _on_var_change(self) -> None:
        """Variable -> boxes. Unpadded or invalid values are tidied up."""
        if self._syncing:
            return
        try:
            value = normalize_time(self._var.get())
        except ValueError:
            value = "00:00" if not self._hour.get() else None
        if value is None:
            return
        self._syncing = True
        try:
            if value != self._var.get():
                self._var.set(value)
            self._hour.set(value[:2])
            self._minute.set(value[3:])
        finally:
            self._syncing = False

    def _pad(self) -> None:
        self._syncing = True
        try:
            self._hour.set(f"{int(self._hour.get() or 0):02d}")
            self._minute.set(f"{int(self._minute.get() or 0):02d}")
        finally:
            self._syncing = False
        self._on_box_change()
