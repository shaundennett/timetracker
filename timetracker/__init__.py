"""Time Tracker — record teacher client visits and produce monthly billing data.

Package layout:
    models.py    dataclasses for the two domain objects (Client, VisitRecord)
    storage.py   JSON persistence (clients in one file, visits in monthly files)
    ui/          tkinter user interface (a notebook with one tab per concern)

The application is intentionally small and dependency-free so it can be
extended in later work (e.g. invoice PDF export, a proper database backend,
reporting views). Keep new features behind the storage/model boundaries so the
UI stays thin.
"""

__version__ = "0.2.0"
