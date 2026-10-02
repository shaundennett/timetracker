import pytest

from timetracker.models import Client, VisitRecord
from timetracker.storage import Storage


@pytest.fixture
def store(tmp_path):
    return Storage(tmp_path)


def test_client_crud(store):
    assert store.list_clients() == []

    c = Client(description="Maths", school="Oakwood", rate=30.0)
    store.save_client(c)
    assert len(store.list_clients()) == 1
    assert store.get_client(c.id).school == "Oakwood"

    # Upsert on the same id updates rather than duplicates.
    c.rate = 45.0
    store.save_client(c)
    assert len(store.list_clients()) == 1
    assert store.get_client(c.id).rate == 45.0

    store.delete_client(c.id)
    assert store.list_clients() == []
    assert store.get_client(c.id) is None


def test_clients_sorted_by_description(store):
    store.save_client(Client(description="Zebra"))
    store.save_client(Client(description="apple"))
    names = [c.description for c in store.list_clients()]
    assert names == ["apple", "Zebra"]


def test_records_stored_per_month(store):
    r1 = VisitRecord(client_id="c1", date="2026-07-01", hours=1, rate=20)
    r2 = VisitRecord(client_id="c1", date="2026-08-05", hours=2, rate=20)
    store.save_record(r1)
    store.save_record(r2)

    assert [r.id for r in store.list_records("2026-07")] == [r1.id]
    assert [r.id for r in store.list_records("2026-08")] == [r2.id]
    assert sorted(store.available_months()) == ["2026-07", "2026-08"]


def test_records_sorted_by_date_then_start(store):
    store.save_record(VisitRecord(client_id="c", date="2026-07-10",
                                  start_time="11:00"))
    store.save_record(VisitRecord(client_id="c", date="2026-07-10",
                                  start_time="09:00"))
    store.save_record(VisitRecord(client_id="c", date="2026-07-02",
                                  start_time="15:00"))
    ordered = [(r.date, r.start_time) for r in store.list_records("2026-07")]
    assert ordered == [
        ("2026-07-02", "15:00"),
        ("2026-07-10", "09:00"),
        ("2026-07-10", "11:00"),
    ]


def test_record_upsert_and_delete(store):
    r = VisitRecord(client_id="c", date="2026-07-01", hours=1, rate=20)
    store.save_record(r)
    r.rate = 50
    store.save_record(r)
    records = store.list_records("2026-07")
    assert len(records) == 1
    assert records[0].rate == 50

    store.delete_record("2026-07", r.id)
    assert store.list_records("2026-07") == []


def test_month_total(store):
    store.save_record(VisitRecord(client_id="c", date="2026-07-01",
                                  hours=2, rate=30))   # 60
    store.save_record(VisitRecord(client_id="c", date="2026-07-08",
                                  hours=1.5, rate=40))  # 60
    assert store.month_total("2026-07") == 120.0
    assert store.month_total("2026-09") == 0.0


def test_corrupt_file_falls_back(store, tmp_path):
    (tmp_path / "clients.json").write_text("{ not json", encoding="utf-8")
    # Should not raise; returns empty rather than crashing the UI.
    assert store.list_clients() == []


def test_old_unpadded_times_sort_correctly(store):
    import json
    path = store.data_dir / "time_2026-07.json"
    rows = [{"client_id": "c", "date": "2026-07-01", "start_time": t,
             "end_time": "23:00", "id": f"id{i}"}
            for i, t in enumerate(["10:00", "9:00"])]
    path.write_text(json.dumps(rows), encoding="utf-8")
    assert [r.start_time for r in store.list_records("2026-07")] == [
        "09:00", "10:00"]
