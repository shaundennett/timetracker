"""Entry point: ``python -m timetracker`` launches the GUI.

An optional data directory can be passed to keep separate datasets (e.g. for
testing) apart from the default location.

Data location:
* Running from source (``python -m timetracker``): ``./data``.
* Running as a packaged .exe: a ``data`` folder next to the executable when
  that is writable (keeps the app portable), otherwise ``~/TimeTracker/data``.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys


def default_data_dir() -> str:
    """Pick a sensible, writable data directory for the current run mode."""
    if getattr(sys, "frozen", False):  # packaged by PyInstaller
        beside_exe = os.path.join(os.path.dirname(sys.executable), "data")
        try:
            os.makedirs(beside_exe, exist_ok=True)
            probe = os.path.join(beside_exe, ".write_test")
            with open(probe, "w"):
                pass
            os.remove(probe)
            return beside_exe
        except OSError:
            # e.g. installed under Program Files — fall back to the user's home.
            return os.path.join(os.path.expanduser("~"), "TimeTracker", "data")
    return "data"


def ensure_runtime_dependencies() -> None:
    """Install the editable project into the current environment if needed.

    This keeps ``python run_app.py`` working in a fresh clone where the local
    environment has not yet been bootstrapped. We only do anything when the
    invoice PDF dependency is missing, so packaged builds or already-set-up
    environments stay untouched.
    """
    if importlib.util.find_spec("fpdf") is not None:
        return

    print("fpdf2 is missing; installing project dependencies into this Python environment...")
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "-e",
        os.path.dirname(os.path.dirname(__file__)) or ".",
    ])


def main() -> None:
    # Imported here so a frozen build resolves them as part of the package.
    ensure_runtime_dependencies()
    from .storage import Storage
    from .ui.app import App

    parser = argparse.ArgumentParser(prog="timetracker",
                                     description="Record billable client visits.")
    parser.add_argument("--data-dir", default=None,
                        help="Directory for JSON data files.")
    args = parser.parse_args()

    App(storage=Storage(args.data_dir or default_data_dir())).mainloop()


if __name__ == "__main__":
    main()
