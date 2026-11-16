"""Test end-to-end contra LocalStack (trebuie să ruleze: docker compose up -d).

Folosește un tabel separat ca să nu atingă datele din tabelul 'Tasks'.
"""

import os

os.environ["TABLE_NAME"] = "Tasks_test"

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


def test_crud_flow(table):
    t1 = db.add_task("ana", "Primul task")
    t2 = db.add_task("ana", "Al doilea task")
    db.add_task("bogdan", "Task-ul altcuiva")

    # GetItem
    got = db.get_task("ana", t1["task_id"])
    assert got["title"] == "Primul task"
    assert got["status"] == "todo"

    # Query: doar task-urile Anei
    tasks = db.list_tasks("ana")
    assert {t["task_id"] for t in tasks} == {t1["task_id"], t2["task_id"]}

    # UpdateItem
    done = db.complete_task("ana", t1["task_id"])
    assert done["status"] == "done"
    assert db.get_task("ana", t1["task_id"])["status"] == "done"

    # DeleteItem
    db.delete_task("ana", t2["task_id"])
    assert db.get_task("ana", t2["task_id"]) is None
    assert len(db.list_tasks("ana")) == 1


def test_missing_task_errors(table):
    assert db.get_task("ana", "inexistent") is None
    with pytest.raises(db.DbError, match="nu există"):
        db.complete_task("ana", "inexistent")
    with pytest.raises(db.DbError, match="nu există"):
        db.delete_task("ana", "inexistent")


def test_missing_table_error():
    original = db.TABLE_NAME
    db.TABLE_NAME = "Tabel_inexistent"
    try:
        with pytest.raises(db.DbError, match="nu există"):
            db.list_tasks("ana")
    finally:
        db.TABLE_NAME = original
