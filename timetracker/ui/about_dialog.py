"""About dialog: application name, version and runtime details."""

from __future__ import annotations

import platform
import tkinter as tk
from tkinter import ttk

from .. import __version__


class AboutDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About Time Tracker")
        self.transient(parent)
        self.resizable(False, False)

        wrap = ttk.Frame(self, padding=18)
        wrap.pack(fill="both", expand=True)

        ttk.Label(wrap, text="Time Tracker",
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(wrap, text=f"Version {__version__}",
                  style="SubHeading.TLabel").pack(anchor="w", pady=(0, 12))
        ttk.Label(wrap, wraplength=320, justify="left", text=(
            "Log billable school visits and produce monthly invoices and "
            "UK tax-year summaries.")).pack(anchor="w")
        ttk.Label(wrap, style="Muted.TLabel",
                  text=f"Python {platform.python_version()}").pack(
            anchor="w", pady=(12, 0))

        ttk.Button(wrap, text="Close", command=self.destroy).pack(
            side="right", pady=(16, 0))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()
