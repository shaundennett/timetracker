"""Dialog for editing the sole-trader's business/invoice details.

These are stored once (``business.json``) and used as the "From" block on every
invoice. All fields are optional — a partial profile still produces a usable
invoice — but a complete one makes for a professional document.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..models import BusinessProfile
from ..storage import Storage
from .style import ACCENT, BORDER, INK, SURFACE


class BusinessDialog(tk.Toplevel):
    def __init__(self, parent, storage: Storage, on_change=None):
        super().__init__(parent)
        self.storage = storage
        self.on_change = on_change or (lambda: None)

        self.title("Business & invoice details")
        self.transient(parent)
        self.minsize(460, 520)
        self.resizable(False, True)

        wrap = ttk.Frame(self, padding=18)
        wrap.pack(fill="both", expand=True)

        ttk.Label(wrap, text="Business details",
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(wrap, text="Used as the sender on every invoice.",
                  style="SubHeading.TLabel").pack(anchor="w", pady=(0, 12))

        card = ttk.LabelFrame(wrap, text="Your details", padding=14)
        card.pack(fill="both", expand=True)
        card.columnconfigure(1, weight=1)

        profile = storage.load_business()
        self.vars = {
            "full_name": tk.StringVar(value=profile.full_name),
            "business_name": tk.StringVar(value=profile.business_name),
            "utr": tk.StringVar(value=profile.utr),
            "telephone": tk.StringVar(value=profile.telephone),
            "email": tk.StringVar(value=profile.email),
        }

        row = 0
        row = self._field(card, "Full name", "full_name", row)
        row = self._field(card, "Business name", "business_name", row)
        row = self._field(card, "UTR", "utr", row)
        row = self._field(card, "Telephone", "telephone", row)
        row = self._field(card, "Email", "email", row)

        ttk.Label(card, text="Address").grid(row=row, column=0, sticky="nw",
                                             pady=6, padx=(0, 10))
        self.address = tk.Text(card, height=4, width=32, wrap="word",
                               relief="solid", borderwidth=1,
                               highlightthickness=1, highlightbackground=BORDER,
                               highlightcolor=ACCENT, background=SURFACE,
                               foreground=INK, insertbackground=INK,
                               padx=6, pady=4, font=("Segoe UI", 10))
        self.address.grid(row=row, column=1, sticky="ew", pady=6)
        self.address.insert("1.0", profile.address)
        row += 1

        btns = ttk.Frame(wrap)
        btns.pack(fill="x", pady=(14, 0))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Save", style="Accent.TButton",
                   command=self._save).pack(side="right", padx=(0, 8))

        self.grab_set()

    def _field(self, parent, label, key, row, width=30) -> int:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w",
                                           pady=6, padx=(0, 10))
        ttk.Entry(parent, textvariable=self.vars[key], width=width).grid(
            row=row, column=1, sticky="ew", pady=6)
        return row + 1

    def _save(self) -> None:
        profile = BusinessProfile(
            full_name=self.vars["full_name"].get().strip(),
            business_name=self.vars["business_name"].get().strip(),
            utr=self.vars["utr"].get().strip(),
            telephone=self.vars["telephone"].get().strip(),
            email=self.vars["email"].get().strip(),
            address=self.address.get("1.0", "end").strip(),
        )
        self.storage.save_business(profile)
        self.on_change()
        self.destroy()
