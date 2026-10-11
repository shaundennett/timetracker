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


class RenameRoleDialog(tk.Toplevel):
    """Modal dialog for renaming a role."""

    def __init__(
        self,
        parent: tk.Tk,
        role_manager: RoleManager,
        role_id: str,
        on_renamed: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self.role_manager = role_manager
        self.role_id = role_id
        self.on_renamed = on_renamed

        role = next((r for r in role_manager.list_roles() if r.id == role_id), None)
        if not role:
            self.destroy()
            return

        self.title(f"Rename Role: {role.name}")
        self.geometry("400x150")
        self.transient(parent)
        self.grab_set()

        # Build the form.
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="New name:", font=("TkDefaultFont", 10)).pack(
            anchor="w", pady=(0, 5)
        )
        self.name_var = tk.StringVar(value=role.name)
        self.name_entry = tk.Entry(frame, textvariable=self.name_var, width=40)
        self.name_entry.pack(anchor="w", pady=(0, 15))
        self.name_entry.focus()
        self.name_entry.select_range(0, "end")

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
            text="Rename",
            command=self._on_rename,
            bg=ACCENT,
            fg="white",
            width=10,
        ).pack(side="left")

    def _on_rename(self) -> None:
        """Handle Rename button click."""
        new_name = self.name_var.get().strip()

        try:
            self.role_manager.rename_role(self.role_id, new_name)
        except ValueError as e:
            messagebox.showerror("Invalid name", str(e))
            return

        if self.on_renamed:
            self.on_renamed()
        self.destroy()


class DeleteRoleDialog(tk.Toplevel):
    """Modal dialog for deleting a role (with confirmation)."""

    def __init__(
        self,
        parent: tk.Tk,
        role_manager: RoleManager,
        role_id: str,
        on_deleted: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self.role_manager = role_manager
        self.role_id = role_id
        self.on_deleted = on_deleted

        role = next((r for r in role_manager.list_roles() if r.id == role_id), None)
        if not role:
            self.destroy()
            return

        self.title(f"Delete Role: {role.name}")
        self.geometry("450x200")
        self.transient(parent)
        self.grab_set()

        # Build the form.
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(
            frame,
            text=f"Are you sure you want to delete the role '{role.name}'?",
            font=("TkDefaultFont", 10),
            wraplength=400,
            justify="left",
        ).pack(anchor="w", pady=(0, 15))

        tk.Label(
            frame,
            text="This will permanently delete all data in this role (clients, visits, etc.).\nThis action cannot be undone.",
            font=("TkDefaultFont", 9),
            wraplength=400,
            justify="left",
            fg="red",
        ).pack(anchor="w", pady=(0, 15))

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
            text="Delete",
            command=self._on_delete,
            bg="red",
            fg="white",
            width=10,
        ).pack(side="left")

    def _on_delete(self) -> None:
        """Handle Delete button click."""
        try:
            self.role_manager.delete_role(self.role_id)
        except ValueError as e:
            messagebox.showerror("Cannot delete role", str(e))
            return

        if self.on_deleted:
            self.on_deleted()
        self.destroy()
