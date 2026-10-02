"""PyInstaller entry point for the packaged Time Tracker executable.

Kept as a top-level module with absolute imports so PyInstaller freezes it
cleanly (a package ``__main__.py`` with relative imports does not freeze well as
a script). It simply delegates to the package's normal entry point.
"""

from timetracker.__main__ import main

if __name__ == "__main__":
    main()
