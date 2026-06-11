import os
import sqlite3
import tempfile

import database as db


def setup_function() -> None:
    """Use a temporary database for every test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.DB_PATH = path
    db.init_db()


def teardown_function() -> None:
    """Remove the temporary database after every test."""
    if os.path.exists(db.DB_PATH):
        os.unlink(db.DB_PATH)


def test_init_db_creates_table() -> None:
    """The database file and habits table must exist after init_db."""
    assert os.path.exists(db.DB_PATH)
    with sqlite3.connect(str(db.DB_PATH)) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='habits'"
        )
        assert cursor.fetchone() is not None


def test_create_habit_returns_id() -> None:
    """create_habit must return a positive integer id."""
    habit_id = db.create_habit("read")
    assert isinstance(habit_id, int)
    assert habit_id > 0


def test_get_habits_returns_list() -> None:
    """get_habits must return a list of dicts with correct keys."""
    db.create_habit("read")
    habits = db.get_habits()
    assert isinstance(habits, list)
    assert len(habits) == 1
    assert set(habits[0].keys()) == {"id", "habit_name", "created_date"}


def test_delete_habit_removes_habit() -> None:
    """delete_habit must remove the habit from the database."""
    habit_id = db.create_habit("read")
    db.delete_habit(habit_id)
    habits = db.get_habits()
    assert len(habits) == 0


def test_delete_habit_invalid_id_raises() -> None:
    """delete_habit must raise ValueError for a non-existent id."""
    try:
        db.delete_habit(9999)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_create_and_get_multiple_habits() -> None:
    """Multiple created habits must all be returned by get_habits."""
    db.create_habit("morning run")
    db.create_habit("meditation")
    db.create_habit("coding")
    habits = db.get_habits()
    assert len(habits) == 3
    names = {h["habit_name"] for h in habits}
    assert names == {"morning run", "meditation", "coding"}


def test_delete_one_of_many() -> None:
    """Deleting one habit must leave the others intact."""
    id1 = db.create_habit("a")
    db.create_habit("b")
    db.delete_habit(id1)
    habits = db.get_habits()
    assert len(habits) == 1
    assert habits[0]["habit_name"] == "b"
