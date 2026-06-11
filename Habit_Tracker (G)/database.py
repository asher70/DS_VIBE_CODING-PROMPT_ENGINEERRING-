import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "habits.db"


def _get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the habits and habit_logs tables if they do not already exist."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_name TEXT NOT NULL,
                created_date DATE NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                date DATE NOT NULL,
                completed INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (habit_id) REFERENCES habits (id),
                UNIQUE (habit_id, date)
            )
            """
        )
        conn.commit()


def create_habit(habit_name: str) -> int:
    """Insert a new habit and return its id."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO habits (habit_name, created_date) VALUES (?, ?)",
            (habit_name, date.today().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid


def get_habits() -> list[dict]:
    """Return a list of all habits as dicts."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, habit_name, created_date FROM habits ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def delete_habit(habit_id: int) -> None:
    """Delete a habit by id. Raises ValueError if the id does not exist."""
    with _get_connection() as conn:
        cursor = conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"No habit found with id {habit_id}")
        conn.commit()


def log_habit(habit_id: int, log_date: date | None = None) -> None:
    """Log a habit completion for a given date. Defaults to today.
    Silently ignores duplicates thanks to the UNIQUE constraint."""
    if log_date is None:
        log_date = date.today()
    with _get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO habit_logs (habit_id, date, completed) VALUES (?, ?, 1)",
                (habit_id, log_date.isoformat()),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Duplicate entry for the same day — ignore
            pass


def is_habit_done_today(habit_id: int) -> bool:
    """Return True if the habit has already been logged for today."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM habit_logs WHERE habit_id = ? AND date = ?",
            (habit_id, date.today().isoformat()),
        )
        return cursor.fetchone() is not None


def get_habit_dates(habit_id: int) -> list[str]:
    """Return all distinct completion dates for a habit as ISO strings."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM habit_logs WHERE habit_id = ? ORDER BY date DESC",
            (habit_id,),
        ).fetchall()
        return [row["date"] for row in rows]


def get_monthly_completions(habit_id: int) -> int:
    """Return the number of distinct completed days this month for a habit."""
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(DISTINCT date)
            FROM habit_logs
            WHERE habit_id = ?
            AND strftime('%Y-%m', date) = ?
            """,
            (habit_id, date.today().strftime("%Y-%m")),
        )
        result = cursor.fetchone()
        return result[0] if result else 0


def get_streak(habit_id: int) -> int:
    """Calculate current streak: consecutive completed days ending today.
    If today is missed, the streak resets to 0.
    """
    dates = get_habit_dates(habit_id)
    if not dates:
        return 0

    date_set = set(dates)
    today = date.today()

    if today.isoformat() not in date_set:
        return 0

    streak = 0
    check_date = today
    while check_date.isoformat() in date_set:
        streak += 1
        check_date -= timedelta(days=1)

    return streak


def get_longest_streak(habit_id: int) -> int:
    """Calculate the longest consecutive streak in history."""
    dates = get_habit_dates(habit_id)
    if not dates:
        return 0

    sorted_dates = sorted(date.fromisoformat(d) for d in dates)
    longest = 0
    current = 1

    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current += 1
        else:
            longest = max(longest, current)
            current = 1

    return max(longest, current)


def get_overall_stats(habit_id: int) -> tuple[int, int, float]:
    """Return (completed_days, possible_days, percentage) since creation."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT created_date FROM habits WHERE id = ?", (habit_id,)
        ).fetchone()

    if row is None:
        raise ValueError(f"No habit found with id {habit_id}")

    created = date.fromisoformat(row["created_date"])
    today = date.today()

    dates = get_habit_dates(habit_id)
    if dates:
        earliest_log = date.fromisoformat(min(dates))
        start = min(created, earliest_log)
    else:
        start = created

    possible_days = (today - start).days + 1
    if possible_days < 1:
        possible_days = 1

    completed = len(dates)
    percentage = min((completed / possible_days) * 100, 100.0)
    return completed, possible_days, round(percentage, 1)


def get_monthly_stats(habit_id: int) -> list[dict]:
    """Return completions per month for charting."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m', date) AS month,
                   COUNT(DISTINCT date) AS completions
            FROM habit_logs
            WHERE habit_id = ?
            GROUP BY month
            ORDER BY month
            """,
            (habit_id,),
        ).fetchall()
    return [dict(row) for row in rows]
