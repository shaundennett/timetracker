"""Dialog for creating and managing roles."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

from ..roles import RoleManager
from .style import ACCENT


class RoleDialog(tk.Toplevel):
    """Modal dialog for creating a new role.

    Allows the user to name the role and optionally copy the business profile
    from an existing role.
    """

    def __init__(
        self,
        parent: tk.Tk,
        role_manager: RoleManager,
        on_role_created: Callable[[str], None] | None = None,
    ):
        super().__init__(parent)
        self.role_manager = role_manager
        self.on_role_created = on_role_created
        self.new_role = None

        self.title("New Role")
        self.geometry("400x250")
        self.transient(parent)
        self.grab_set()

        # Build the form.
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Role name.
        tk.Label(frame, text="Role name:", font=("TkDefaultFont", 10)).pack(
            anchor="w", pady=(0, 5)
        )
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(frame, textvariable=self.name_var, width=40)
        self.name_entry.pack(anchor="w", pady=(0, 15))
        self.name_entry.focus()

        # Business profile copy option.
        tk.Label(
            frame, text="Copy business profile from:", font=("TkDefaultFont", 10)
        ).pack(anchor="w", pady=(0, 5))

        self.copy_from_var = tk.StringVar(value="")
        option_frame = tk.Frame(frame)
        option_frame.pack(anchor="w", pady=(0, 15))

        tk.Radiobutton(
            option_frame,
            text="Start with empty business profile",
            variable=self.copy_from_var,
            value="",
        ).pack(anchor="w")

        roles = self.role_manager.list_roles()
        for role in roles:
            tk.Radiobutton(
                option_frame,
                text=f"Copy from {role.name}",
                variable=self.copy_from_var,
                value=role.id,
            ).pack(anchor="w")

        # Buttons.
        button_frame = tk.Frame(frame)
        button_frame.pack(anchor="e", pady=(15, 0))

        tk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=10,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_frame,
            text="Create",
            command=self._on_create,
            bg=ACCENT,
            fg="white",
            width=10,
        ).pack(side="left")

    def _on_create(self) -> None:
        """Handle Create button click."""
        name = self.name_var.get().strip()

        # Validate and create.
        try:
            new_role = self.role_manager.create_role(name)
        except ValueError as e:
            tk.messagebox.showerror("Invalid role name", str(e))
            return

        # Copy business profile if requested.
        copy_from_id = self.copy_from_var.get()
        if copy_from_id:
            source_storage = self.role_manager.storage_for(copy_from_id)
            dest_storage = self.role_manager.storage_for(new_role.id)

            source_profile = source_storage.load_business()
            dest_storage.save_business(source_profile)

        # Notify and close.
        if self.on_role_created:
            self.on_role_created(new_role.id)
        self.destroy()
