"""A modal dialog for managing the reusable "potential visit" definitions.

The daily entry screen stays uncluttered; you open this only when you need to
add, edit, or remove one of your regular visit templates. It reuses the same
management panel (``ClientsTab``) that used to be a notebook tab, and calls
``on_change`` whenever a definition is saved or deleted so the entry screen's
event picker refreshes live.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..storage import Storage
from .clients_tab import ClientsTab


class ClientsDialog(tk.Toplevel):
    def __init__(self, parent, storage: Storage, on_change=None):
        super().__init__(parent)
        self.title("Manage potential visits")
        self.transient(parent)  # stay on top of the main window
        self.minsize(940, 480)
        self.geometry("1040x560")

        panel = ClientsTab(self, storage, on_change=on_change)
        panel.pack(fill="both", expand=True)

        bar = ttk.Frame(self, padding=(10, 0, 10, 10))
        bar.pack(fill="x")
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")

        self.grab_set()  # modal: focus stays here until closed
