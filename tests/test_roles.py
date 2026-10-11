"""Tests for role management and multi-role support."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from timetracker.models import Client
from timetracker.roles import Role, RoleManager
from timetracker.storage import Storage


@pytest.fixture
def temp_data_dir():
    """Temporary directory for test data."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestRoleModel:
    """Tests for the Role dataclass."""

    def test_role_creation(self):
        """A role can be created with an id and name."""
        role = Role(id="abc123", name="Supply teaching")
        assert role.id == "abc123"
        assert role.name == "Supply teaching"

    def test_role_to_dict(self):
        """A role can be serialized to a dict."""
        role = Role(id="abc123", name="Supply teaching")
        assert role.to_dict() == {"id": "abc123", "name": "Supply teaching"}


class TestRoleManagerInit:
    """Tests for RoleManager initialization and bootstrap."""

    def test_bootstrap_empty_root(self, temp_data_dir):
        """A fresh empty root creates one Default role."""
        rm = RoleManager(temp_data_dir)

        roles = rm.list_roles()
        assert len(roles) == 1
        assert roles[0].name == "Default"

        active = rm.active_role()
        assert active.name == "Default"

        # Manifest file exists and is valid.
        manifest_file = temp_data_dir / "roles.json"
        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text())
        assert "active" in manifest
        assert "roles" in manifest

    def test_migrate_legacy_data(self, temp_data_dir):
        """Legacy files in the root are migrated to a Default role."""
        # Create fake legacy data.
        clients_file = temp_data_dir / "clients.json"
        clients_file.write_text(json.dumps([{"id": "c1", "description": "Fake Client"}]))

        time_file = temp_data_dir / "time_2026-09.json"
        time_file.write_text(json.dumps([{"id": "v1", "client_id": "c1"}]))

        # Initialize; should migrate.
        rm = RoleManager(temp_data_dir)

        roles = rm.list_roles()
        assert len(roles) == 1
        assert roles[0].name == "Default"

        # Legacy files still exist at root (not moved).
        assert clients_file.exists()
        assert time_file.exists()

        # Files are copied into the role directory.
        role_dir = rm.role_dir(roles[0].id)
        assert (role_dir / "clients.json").exists()
        assert (role_dir / "time_2026-09.json").exists()

        # Storage for the role sees the migrated data.
        storage = rm.storage_for(roles[0].id)
        clients = storage.list_clients()
        assert len(clients) == 1
        assert clients[0].description == "Fake Client"

    def test_migrate_idempotent(self, temp_data_dir):
        """Migrating twice does not duplicate data."""
        # Set up legacy data.
        clients_file = temp_data_dir / "clients.json"
        clients_file.write_text(json.dumps([{"id": "c1", "description": "Fake Client"}]))

        # First init: migrate.
        rm1 = RoleManager(temp_data_dir)
        roles1 = rm1.list_roles()
        role_dir = rm1.role_dir(roles1[0].id)
        client_files_1 = list(role_dir.glob("clients.json"))

        # Second init: should not re-copy.
        rm2 = RoleManager(temp_data_dir)
        roles2 = rm2.list_roles()
        client_files_2 = list(role_dir.glob("clients.json"))

        assert len(client_files_1) == len(client_files_2)
        assert len(roles1) == len(roles2)


class TestRoleManagerOperations:
    """Tests for role CRUD and switching."""

    def test_list_roles_sorted(self, temp_data_dir):
        """Roles are listed sorted by name."""
        rm = RoleManager(temp_data_dir)

        # Create roles out of order.
        rm.create_role("Zebra")
        rm.create_role("Apple")
        rm.create_role("Banana")

        roles = rm.list_roles()
        names = [r.name for r in roles]
        assert names == ["Apple", "Banana", "Default", "Zebra"]

    def test_create_role(self, temp_data_dir):
        """A new role is created with an empty dataset."""
        rm = RoleManager(temp_data_dir)
        new_role = rm.create_role("Private tutoring")

        assert new_role.name == "Private tutoring"
        assert new_role.id  # Has an id

        # Directory is created.
        role_dir = rm.role_dir(new_role.id)
        assert role_dir.exists()

        # Storage for the role is empty.
        storage = rm.storage_for(new_role.id)
        assert len(storage.list_clients()) == 0

    def test_create_role_validation_empty_name(self, temp_data_dir):
        """Creating a role with empty/blank name raises ValueError."""
        rm = RoleManager(temp_data_dir)

        with pytest.raises(ValueError, match="cannot be empty"):
            rm.create_role("")

        with pytest.raises(ValueError, match="cannot be empty"):
            rm.create_role("   ")

    def test_create_role_duplicate_name(self, temp_data_dir):
        """Creating a role with a duplicate name (case-insensitive) raises ValueError."""
        rm = RoleManager(temp_data_dir)
        rm.create_role("Supply teaching")

        with pytest.raises(ValueError, match="already exists"):
            rm.create_role("Supply teaching")

        with pytest.raises(ValueError, match="already exists"):
            rm.create_role("SUPPLY TEACHING")

    def test_set_active(self, temp_data_dir):
        """Switching the active role persists."""
        rm = RoleManager(temp_data_dir)
        role_a = rm.create_role("Role A")
        role_b = rm.create_role("Role B")

        # Default is active initially.
        assert rm.active_role().name == "Default"

        # Switch to Role A.
        rm.set_active(role_a.id)
        assert rm.active_role().id == role_a.id

        # Create a new manager pointing at the same root; should remember.
        rm2 = RoleManager(temp_data_dir)
        assert rm2.active_role().id == role_a.id

    def test_set_active_unknown_id(self, temp_data_dir):
        """Switching to an unknown role raises ValueError."""
        rm = RoleManager(temp_data_dir)
        with pytest.raises(ValueError, match="not found"):
            rm.set_active("unknown_id")

    def test_rename_role(self, temp_data_dir):
        """A role can be renamed."""
        rm = RoleManager(temp_data_dir)
        role = rm.create_role("Old Name")

        renamed = rm.rename_role(role.id, "New Name")
        assert renamed.name == "New Name"

        # Persists.
        rm2 = RoleManager(temp_data_dir)
        assert any(r.name == "New Name" for r in rm2.list_roles())

    def test_rename_role_validation(self, temp_data_dir):
        """Renaming with invalid names raises ValueError."""
        rm = RoleManager(temp_data_dir)
        role = rm.create_role("Role A")

        with pytest.raises(ValueError, match="cannot be empty"):
            rm.rename_role(role.id, "")

        with pytest.raises(ValueError, match="cannot be empty"):
            rm.rename_role(role.id, "   ")

    def test_rename_role_duplicate(self, temp_data_dir):
        """Renaming to a duplicate name raises ValueError."""
        rm = RoleManager(temp_data_dir)
        role_a = rm.create_role("Role A")
        rm.create_role("Role B")

        with pytest.raises(ValueError, match="already exists"):
            rm.rename_role(role_a.id, "Role B")

    def test_delete_role(self, temp_data_dir):
        """A role can be deleted (directory and manifest entry removed)."""
        rm = RoleManager(temp_data_dir)
        role_a = rm.create_role("Role A")
        role_b = rm.create_role("Role B")

        # Add some data to Role A.
        storage = rm.storage_for(role_a.id)
        client = Client(id="c1", description="Test", school="School", rate=50.0)
        storage.save_client(client)

        # Delete Role A.
        rm.delete_role(role_a.id)

        # Role A is gone from the list.
        roles = rm.list_roles()
        assert not any(r.id == role_a.id for r in roles)

        # Directory is deleted.
        role_dir = rm.role_dir(role_a.id)
        assert not role_dir.exists()

    def test_delete_role_validation(self, temp_data_dir):
        """Deleting the last or active role raises ValueError."""
        rm = RoleManager(temp_data_dir)
        role_a = rm.create_role("Role A")

        # Cannot delete the only role (besides Default).
        rm.delete_role(role_a.id)  # Delete it first; now only Default remains.
        default = rm.active_role()
        with pytest.raises(ValueError, match="Cannot delete the last role"):
            rm.delete_role(default.id)

        # Cannot delete the active role.
        role_b = rm.create_role("Role B")
        # Default is active, so try to delete it.
        with pytest.raises(ValueError, match="Cannot delete the active role"):
            rm.delete_role(default.id)


class TestRoleIsolation:
    """Tests that roles have isolated data."""

    def test_storage_isolation(self, temp_data_dir):
        """Two roles' Storage instances do not see each other's clients."""
        rm = RoleManager(temp_data_dir)
        role_a = rm.create_role("Role A")
        role_b = rm.create_role("Role B")

        # Add a client to Role A.
        storage_a = rm.storage_for(role_a.id)
        client_a = Client(id="c_a", description="Client A", school="School", rate=50.0)
        storage_a.save_client(client_a)

        # Add a different client to Role B.
        storage_b = rm.storage_for(role_b.id)
        client_b = Client(id="c_b", description="Client B", school="School", rate=60.0)
        storage_b.save_client(client_b)

        # Storage A should only see Client A.
        clients_a = storage_a.list_clients()
        assert len(clients_a) == 1
        assert clients_a[0].id == "c_a"

        # Storage B should only see Client B.
        clients_b = storage_b.list_clients()
        assert len(clients_b) == 1
        assert clients_b[0].id == "c_b"

    def test_active_storage(self, temp_data_dir):
        """active_storage() points to the currently active role."""
        rm = RoleManager(temp_data_dir)
        role_a = rm.create_role("Role A")

        # Add data to Role A.
        storage = rm.storage_for(role_a.id)
        client = Client(id="c1", description="Test", school="School", rate=50.0)
        storage.save_client(client)

        # Switch to Role A.
        rm.set_active(role_a.id)

        # active_storage() should reflect Role A's data.
        active_storage = rm.active_storage()
        clients = active_storage.list_clients()
        assert len(clients) == 1
        assert clients[0].id == "c1"


class TestRoleManagerRecovery:
    """Tests recovery from corrupt or missing manifest."""

    def test_corrupt_manifest_recovery(self, temp_data_dir):
        """A corrupt manifest is recovered gracefully."""
        # Write garbage manifest.
        manifest_file = temp_data_dir / "roles.json"
        manifest_file.write_text("not valid json")

        # Should not crash; bootstrap a default role.
        rm = RoleManager(temp_data_dir)
        roles = rm.list_roles()
        assert len(roles) >= 1

        # A valid manifest is now in place.
        manifest = json.loads(manifest_file.read_text())
        assert "active" in manifest
        assert "roles" in manifest


class TestRoleColor:
    """Tests for per-role accent colours."""

    def test_to_dict_omits_empty_color(self):
        assert "color" not in Role(id="a", name="A").to_dict()

    def test_to_dict_includes_color(self):
        role = Role(id="a", name="A", color="#112233")
        assert role.to_dict() == {"id": "a", "name": "A", "color": "#112233"}

    def test_from_dict_tolerates_old_and_unknown_keys(self):
        assert Role.from_dict({"id": "a", "name": "A"}).color == ""
        role = Role.from_dict({"id": "a", "name": "A", "color": "#112233", "x": 1})
        assert role.color == "#112233"

    def test_set_role_color_persists(self, temp_data_dir):
        rm = RoleManager(temp_data_dir)
        role = rm.active_role()
        rm.set_role_color(role.id, "#ABCDEF")
        assert RoleManager(temp_data_dir).active_role().color == "#abcdef"

    def test_set_role_color_resets_with_empty(self, temp_data_dir):
        rm = RoleManager(temp_data_dir)
        role = rm.active_role()
        rm.set_role_color(role.id, "#abcdef")
        rm.set_role_color(role.id, "")
        assert rm.active_role().color == ""

    @pytest.mark.parametrize("bad", ["red", "#fff", "#12345g", "abcdef"])
    def test_set_role_color_rejects_bad_values(self, temp_data_dir, bad):
        rm = RoleManager(temp_data_dir)
        with pytest.raises(ValueError):
            rm.set_role_color(rm.active_role().id, bad)

    def test_set_role_color_unknown_role(self, temp_data_dir):
        rm = RoleManager(temp_data_dir)
        with pytest.raises(ValueError):
            rm.set_role_color("missing", "#abcdef")

    def test_create_role_with_color(self, temp_data_dir):
        rm = RoleManager(temp_data_dir)
        role = rm.create_role("Other", "#123456")
        assert role.color == "#123456"
        assert rm.active_role().color == ""  # colours are per role
        with pytest.raises(ValueError):
            rm.create_role("Bad", "nope")

    def test_old_manifest_without_color_loads(self, temp_data_dir):
        (temp_data_dir / "r1").mkdir()
        (temp_data_dir / "roles.json").write_text(
            json.dumps({"active": "r1", "roles": [{"id": "r1", "name": "Old"}]}))
        assert RoleManager(temp_data_dir).active_role().color == ""
