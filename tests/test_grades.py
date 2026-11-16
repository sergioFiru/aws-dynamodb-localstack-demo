"""Teste end-to-end contra LocalStack (trebuie să ruleze: docker compose up -d).

Folosesc un tabel separat ca să nu atingă datele din tabelul 'Grades'.
"""

import os

os.environ["TABLE_NAME"] = "Grades_test"

import pytest  # noqa: E402

from app import db  # noqa: E402


@pytest.fixture
def table():
    try:
        db.delete_table()
    except db.DbError:
        pass
    db.create_table()
    yield
    db.delete_table()


def test_add_and_get(table):
    db.add_grade("S1", "C1", "Rețele", 9, "2026-1")
    g = db.get_grade("S1", "C1")
    assert g["course_name"] == "Rețele"
    assert g["grade"] == 9
    assert g["semester"] == "2026-1"
    assert g["updated_at"].endswith("Z")
    assert db.get_grade("S1", "C99") is None


def test_duplicate_refused(table):
    db.add_grade("S1", "C1", "Rețele", 9, "2026-1")
    with pytest.raises(db.DbError, match="există deja"):
        db.add_grade("S1", "C1", "Rețele", 5, "2026-1")
    assert db.get_grade("S1", "C1")["grade"] == 9  # nota originală a rămas


def test_list_and_average(table):
    db.add_grade("S1", "C1", "Rețele", 9, "2026-1")
    db.add_grade("S1", "C2", "Baze de date", 8, "2026-1")
    db.add_grade("S1", "C3", "Programare", 6, "2026-1")
    db.add_grade("S2", "C1", "Rețele", 10, "2026-1")

    grades = db.list_grades("S1")
    assert [g["course_id"] for g in grades] == ["C1", "C2", "C3"]  # doar S1, sortat după SK
    assert db.average(grades) == 7.67
    assert db.list_grades("S3") == []
    assert db.average([]) is None


def test_update(table):
    db.add_grade("S1", "C1", "Rețele", 9, "2026-1")
    updated = db.update_grade("S1", "C1", 10)
    assert updated["grade"] == 10
    assert db.get_grade("S1", "C1")["grade"] == 10
    with pytest.raises(db.DbError, match="Nu există nicio notă"):
        db.update_grade("S1", "C99", 7)


def test_delete(table):
    db.add_grade("S1", "C1", "Rețele", 9, "2026-1")
    db.delete_grade("S1", "C1")
    assert db.get_grade("S1", "C1") is None
    with pytest.raises(db.DbError, match="Nu există nicio notă"):
        db.delete_grade("S1", "C1")


@pytest.mark.parametrize("bad", [0, 11, -3, 9.5, "9"])
def test_invalid_grade(table, bad):
    with pytest.raises(db.DbError, match="Notă invalidă"):
        db.add_grade("S1", "C1", "Rețele", bad, "2026-1")
    db.add_grade("S1", "C1", "Rețele", 9, "2026-1")
    with pytest.raises(db.DbError, match="Notă invalidă"):
        db.update_grade("S1", "C1", bad)
    assert db.get_grade("S1", "C1")["grade"] == 9


def test_missing_table():
    original = db.TABLE_NAME
    db.TABLE_NAME = "Tabel_inexistent"
    try:
        with pytest.raises(db.DbError, match="nu există"):
            db.list_grades("S1")
    finally:
        db.TABLE_NAME = original
