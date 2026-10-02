"""Invoice building, rendering, and printing.

An :class:`Invoice` bundles the sender's :class:`BusinessProfile` and the visit
line items for a period. It knows how to total itself and render as:

* plain text  — for the on-screen preview, and
* PDF         — via fpdf2, for saving and printing.

Printing (Windows) hands the generated PDF to the OS print verb, which uses the
default PDF handler. If that isn't available it falls back to just opening the
file so the user can print manually.
"""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import List

from .models import BusinessProfile, VisitRecord, format_display_date

# GBP by default — VAT + "school" strongly imply a UK sole trader, and the
# symbol is latin-1 safe for fpdf2's core fonts.
CURRENCY = "£"


@dataclass
class Invoice:
    number: str
    date: str  # YYYY-MM-DD
    business: BusinessProfile
    items: List[VisitRecord] = field(default_factory=list)
    notes: str = ""
    currency: str = CURRENCY

    # ---- money -------------------------------------------------------- #
    @property
    def subtotal(self) -> float:
        return round(sum(i.amount for i in self.items), 2)

    @property
    def total(self) -> float:
        return self.subtotal

    def money(self, value: float) -> str:
        return f"{self.currency}{value:,.2f}"


# ---------------------------------------------------------------------- #
# Assembly helpers
# ---------------------------------------------------------------------- #
def schools_in(records: List[VisitRecord]) -> List[str]:
    """Distinct, non-empty school names appearing in the records, sorted."""
    return sorted({r.school for r in records if r.school})


def suggest_number(month_key: str) -> str:
    """A sensible default invoice number for a month, e.g. INV-202607."""
    return f"INV-{month_key.replace('-', '')}"


# ---------------------------------------------------------------------- #
# Text rendering (on-screen preview)
# ---------------------------------------------------------------------- #
def render_text(inv: Invoice, width: int = 74) -> str:
    b = inv.business
    lines: List[str] = []
    lines.append("=" * width)
    header = b.business_name or b.full_name or "INVOICE"
    lines.append(header.upper().center(width))
    lines.append("=" * width)
    lines.append("")

    # From / meta, side by side-ish (kept simple, stacked for the preview).
    lines.append("FROM:")
    for value in (b.full_name, b.business_name, *b.address.splitlines()):
        if value.strip():
            lines.append(f"  {value}")
    if b.telephone:
        lines.append(f"  Tel: {b.telephone}")
    if b.email:
        lines.append(f"  Email: {b.email}")
    if b.utr:
        lines.append(f"  UTR: {b.utr}")
    lines.append("")

    lines.append(f"Invoice number : {inv.number}")
    lines.append(f"Invoice date   : {format_display_date(inv.date)}")
    lines.append("-" * width)

    # Line-item table.
    lines.append(f"{'Date':<11}{'Description':<24}{'Hrs':>5}"
                 f"{'Rate':>10}{'Amount':>12}")
    lines.append("-" * width)
    for it in inv.items:
        desc = (it.description or "")[:23]
        lines.append(f"{format_display_date(it.date):<11}{desc:<24}{it.hours:>5g}"
                     f"{inv.money(it.rate):>10}{inv.money(it.amount):>12}")
    lines.append("-" * width)

    lines.append(f"{'TOTAL':>57}{inv.money(inv.total):>12}")
    lines.append("=" * width)
    if inv.notes.strip():
        lines.append("")
        lines.append("Notes:")
        for value in inv.notes.splitlines():
            lines.append(f"  {value}")
    return "\n".join(lines)


# ---------------------------------------------------------------------- #
# PDF rendering
# ---------------------------------------------------------------------- #
# Muted, professional palette (RGB).
_INK = (33, 37, 41)
_MUTED = (108, 117, 125)
_ACCENT = (37, 99, 235)
_RULE = (222, 226, 230)
_ZEBRA = (247, 249, 252)


def render_pdf(inv: Invoice, path: str) -> str:
    """Write a formatted PDF invoice to ``path`` and return the path."""
    from fpdf import FPDF  # imported lazily so the app runs without it

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 16, 18)
    b = inv.business
    epw = pdf.epw  # effective page width

    # ---- Masthead --------------------------------------------------- #
    pdf.set_text_color(*_INK)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, b.business_name or b.full_name or "Invoice",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*_MUTED)
    from_bits = []
    if b.business_name and b.full_name:
        from_bits.append(b.full_name)
    from_bits += [ln for ln in b.address.splitlines() if ln.strip()]
    contact = "   ".join(
        p for p in (f"Tel: {b.telephone}" if b.telephone else "",
                    b.email) if p)
    for line in from_bits:
        pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
    if contact:
        pdf.cell(0, 5, contact, new_x="LMARGIN", new_y="NEXT")
    if b.utr:
        pdf.cell(0, 5, f"UTR: {b.utr}",
                 new_x="LMARGIN", new_y="NEXT")

    # "INVOICE" title on the right of the masthead.
    pdf.set_xy(pdf.l_margin, 16)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*_ACCENT)
    pdf.cell(epw, 12, "INVOICE", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    _rule(pdf)
    pdf.ln(4)

    # ---- Invoice meta (number + date) ------------------------------- #
    col = epw / 2
    pdf.set_font("Helvetica", "", 10)
    for label, value in (("Invoice No", inv.number),
                         ("Date", format_display_date(inv.date))):
        pdf.set_x(pdf.l_margin + col)
        pdf.set_text_color(*_MUTED)
        pdf.cell(col * 0.45, 6, label)
        pdf.set_text_color(*_INK)
        pdf.cell(col * 0.55, 6, value, align="R",
                 new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    # ---- Line-item table -------------------------------------------- #
    # Column widths (mm) across the effective page width.
    w_date, w_hrs, w_rate, w_amt = 22, 16, 26, 30
    w_desc = epw - (w_date + w_hrs + w_rate + w_amt)

    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_fill_color(*_ACCENT)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(w_date, 8, "Date", fill=True)
    pdf.cell(w_desc, 8, "Description / School", fill=True)
    pdf.cell(w_hrs, 8, "Hrs", align="R", fill=True)
    pdf.cell(w_rate, 8, "Rate", align="R", fill=True)
    pdf.cell(w_amt, 8, "Amount", align="R", fill=True,
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*_INK)
    for i, it in enumerate(inv.items):
        fill = i % 2 == 1
        if fill:
            pdf.set_fill_color(*_ZEBRA)
        desc = it.description or ""
        if it.school:
            desc = f"{desc}  ({it.school})"
        pdf.cell(w_date, 7, format_display_date(it.date), fill=fill)
        pdf.cell(w_desc, 7, _clip(pdf, desc, w_desc - 2), fill=fill)
        pdf.cell(w_hrs, 7, f"{it.hours:g}", align="R", fill=fill)
        pdf.cell(w_rate, 7, inv.money(it.rate), align="R", fill=fill)
        pdf.cell(w_amt, 7, inv.money(it.amount), align="R", fill=fill,
                 new_x="LMARGIN", new_y="NEXT")
    if not inv.items:
        pdf.set_text_color(*_MUTED)
        pdf.cell(0, 7, "  (no visits in this period)",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_INK)

    pdf.ln(2)
    _rule(pdf)

    # ---- Totals (right-aligned block) ------------------------------- #
    label_w, val_w = epw - w_amt - 30, w_amt + 30
    pdf.ln(2)

    def total_row(label, value, bold=False, accent=False):
        pdf.set_font("Helvetica", "B" if bold else "", 11 if bold else 10)
        pdf.set_text_color(*(_ACCENT if accent else _INK))
        pdf.cell(label_w, 7, "")
        pdf.set_text_color(*_MUTED if not bold else _INK)
        pdf.cell(val_w * 0.5, 7, label, align="R")
        pdf.set_text_color(*(_ACCENT if accent else _INK))
        pdf.cell(val_w * 0.5, 7, value, align="R",
                 new_x="LMARGIN", new_y="NEXT")

    total_row("TOTAL DUE", inv.money(inv.total), bold=True, accent=True)

    # ---- Notes / footer --------------------------------------------- #
    if inv.notes.strip():
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_MUTED)
        pdf.cell(0, 5, "Notes", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*_INK)
        pdf.multi_cell(0, 5, inv.notes)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pdf.output(path)
    return path


def _rule(pdf) -> None:
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.3)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)


def _clip(pdf, text: str, max_w: float) -> str:
    """Truncate text with an ellipsis so it fits within ``max_w`` mm."""
    if pdf.get_string_width(text) <= max_w:
        return text
    ell = "..."
    while text and pdf.get_string_width(text + ell) > max_w:
        text = text[:-1]
    return text + ell


# ---------------------------------------------------------------------- #
# Printing
# ---------------------------------------------------------------------- #
def print_pdf(path: str) -> None:
    """Send a PDF to the default printer (Windows), else open it.

    On Windows the shell 'print' verb hands the file to the default PDF
    handler's print action. If unavailable we open the file so the user can
    print from their viewer.
    """
    if sys.platform.startswith("win"):
        try:
            os.startfile(path, "print")  # type: ignore[attr-defined]
            return
        except OSError:
            os.startfile(path)  # type: ignore[attr-defined]
            return
    # Non-Windows fallback: just open with the default handler.
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    os.system(f'{opener} "{path}"')


def render_to_temp(inv: Invoice) -> str:
    """Render the invoice to a temp PDF (used by the Print action)."""
    safe = "".join(c for c in inv.number if c.isalnum() or c in "-_") or "invoice"
    path = os.path.join(tempfile.gettempdir(), f"{safe}.pdf")
    return render_pdf(inv, path)
