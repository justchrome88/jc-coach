import json

from sqlalchemy import select

from app.db.models import Match
from app.services.importer import import_csv, import_json, import_rows


def test_csv_import_accepts_missing_columns(db):
    csv_data = "played_at,map_name,result,kills,deaths,adr\n2026-06-01,Mirage,win,20,10,88.5\n"

    result = import_csv(db, csv_data)
    match = db.scalar(select(Match))

    assert result == {"imported": 1, "skipped_duplicates": 0, "errors": 0}
    assert match.map_name == "Mirage"
    assert match.kd == 2.0
    assert match.kast is None


def test_json_import(db, sample_rows):
    result = import_json(db, json.dumps({"matches": sample_rows}))

    assert result["imported"] == 2
    assert len(db.scalars(select(Match)).all()) == 2


def test_import_deduplicates_same_match(db, sample_rows):
    first = import_rows(db, sample_rows, source="test")
    second = import_rows(db, sample_rows, source="test")

    assert first["imported"] == 2
    assert second["imported"] == 0
    assert second["skipped_duplicates"] == 2
    assert len(db.scalars(select(Match)).all()) == 2
