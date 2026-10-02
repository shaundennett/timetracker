import os

import pytest

from timetracker.invoice import (
    Invoice,
    render_pdf,
    render_text,
    schools_in,
    suggest_number,
)
from timetracker.models import BusinessProfile, VisitRecord
from timetracker.storage import Storage


def _items():
    return [
        VisitRecord(client_id="c", date="2026-07-07", description="Maths",
                    school="Oakwood", hours=1.5, rate=40.0),   # 60
        VisitRecord(client_id="c", date="2026-07-14", description="Maths",
                    school="Elmfield", hours=2.0, rate=40.0),  # 80
    ]


def _invoice():
    return Invoice(number="INV-202607", date="2026-07-31",
                   business=BusinessProfile(business_name="Bright Tutoring"),
                   items=_items())


def test_business_profile_roundtrip(tmp_path):
    store = Storage(tmp_path)
    # Empty by default.
    assert store.load_business().business_name == ""
    p = BusinessProfile(full_name="Jane", business_name="Bright", utr="1234567890")
    store.save_business(p)
    loaded = store.load_business()
    assert loaded.full_name == "Jane"
    assert loaded.utr == "1234567890"


def test_business_profile_legacy_vat_reference_maps_to_utr():
    # Files written before the rename stored the UTR under "vat_reference".
    p = BusinessProfile.from_dict({"vat_reference": "9998887776",
                                   "vat_rate": 20.0})
    assert p.utr == "9998887776"
    assert not hasattr(p, "vat_rate")


def test_invoice_total_is_subtotal():
    inv = _invoice()
    assert inv.subtotal == 140.0
    assert inv.total == 140.0


def test_money_formatting():
    inv = _invoice()
    assert inv.money(1234.5) == "£1,234.50"


def test_schools_and_number_helpers():
    assert schools_in(_items()) == ["Elmfield", "Oakwood"]
    assert suggest_number("2026-07") == "INV-202607"


def test_render_text_contains_key_fields():
    text = render_text(_invoice())
    assert "INV-202607" in text
    assert "TOTAL" in text
    assert "£140.00" in text
    # VAT and bill-to were removed from the template.
    assert "VAT @" not in text
    assert "BILL TO" not in text


def test_render_pdf_writes_file(tmp_path):
    out = tmp_path / "sub" / "invoice.pdf"  # nested dir is created
    render_pdf(_invoice(), str(out))
    assert out.exists()
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 500


def test_render_pdf_empty_items(tmp_path):
    inv = Invoice(number="INV-1", date="2026-07-31",
                  business=BusinessProfile(), items=[])
    out = tmp_path / "empty.pdf"
    render_pdf(inv, str(out))
    assert out.exists() and inv.total == 0.0


def test_text_preview_shows_dd_mm_yyyy():
    text = render_text(_invoice())
    assert "31/07/2026" in text
    assert "07/07/2026" in text
    assert "2026-07-31" not in text
