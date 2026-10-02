"""Dialog for viewing a UK tax year summary of payments and mileage."""

from __future__ import annotations

import datetime as _dt
import tkinter as tk
from tkinter import ttk

from .. import tax_report as tax_mod
from ..storage import Storage
from .style import ACCENT, BORDER, INK, SURFACE


class TaxYearDialog(tk.Toplevel):
    def __init__(self, parent, storage: Storage):
        super().__init__(parent)
        self.storage = storage

        self.title("Tax year summary")
        self.transient(parent)
        self.minsize(720, 480)
        self.geometry("820x560")

        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Tax year summary",
                  style="Heading.TLabel").grid(row=0, column=0, columnspan=2,
                                               sticky="w")
        ttk.Label(
            outer,
            text="Payments and mileage for a UK tax year (6 April – 5 April).",
            style="SubHeading.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(1, weight=1)

        years = tax_mod.suggest_tax_years(storage)
        default_year = years[0] if years else _dt.date.today().year

        self._build_controls(outer, years, default_year)
        self._build_preview(outer)

        self._render_preview()
        self.grab_set()

    def _build_controls(self, outer, years: list[int], default_year: int) -> None:
        panel = ttk.LabelFrame(outer, text="Options", padding=14)
        panel.grid(row=2, column=0, sticky="nsw", padx=(0, 14))

        ttk.Label(panel, text="Tax year").grid(row=0, column=0, sticky="w",
                                               pady=5)
        labels = [f"{y}/{y + 1 - 2000:02d}" for y in years]
        self._year_map = dict(zip(labels, years))
        self.year_var = tk.StringVar(
            value=f"{default_year}/{default_year + 1 - 2000:02d}"
        )
        year_combo = ttk.Combobox(
            panel, textvariable=self.year_var,
            state="readonly", width=16, values=labels,
        )
        year_combo.grid(row=0, column=1, sticky="w", pady=5)
        year_combo.bind("<<ComboboxSelected>>",
                        lambda _e: self._render_preview())

        ttk.Button(panel, text="Refresh preview",
                   command=self._render_preview).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _build_preview(self, outer) -> None:
        right = ttk.Frame(outer)
        right.grid(row=2, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="Report", style="SubHeading.TLabel").grid(
            row=0, column=0, sticky="w")
        self.preview = tk.Text(
            right, wrap="none", relief="solid", borderwidth=1,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT, font=("Consolas", 10),
            background=SURFACE, foreground=INK, padx=12, pady=10,
            state="disabled",
        )
        self.preview.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(right, orient="vertical",
                           command=self.preview.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=sb.set)

        actions = ttk.Frame(outer)
        actions.grid(row=3, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(actions, text="Close", command=self.destroy).pack(
            side="right")

    def _selected_tax_year(self) -> int:
        label = self.year_var.get()
        if label in self._year_map:
            return self._year_map[label]
        # Fallback: parse "2026/27" -> 2026
        return int(label.split("/")[0])

    def _render_preview(self) -> None:
        summary = tax_mod.build_tax_year_summary(
            self.storage, self._selected_tax_year())
        text = tax_mod.render_text(summary)
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")
