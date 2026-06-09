import os
import sqlite3
from datetime import datetime
from typing import Optional

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "expense.db")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_table() -> None:
    """Create the transactions table if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def insert_transaction(
    type: str,
    amount: float,
    category: str,
    description: Optional[str] = None,
    date: Optional[str] = None,
) -> int:
    """Insert a new transaction and return its id."""
    conn = get_connection()
    cursor = conn.cursor()
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        """
        INSERT INTO transactions (type, amount, category, description, date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (type, amount, category, description, date),
    )
    conn.commit()
    transaction_id = cursor.lastrowid
    conn.close()
    return transaction_id


def delete_transaction(transaction_id: int) -> bool:
    """Delete a transaction by id. Returns True if a row was deleted."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_transaction(
    transaction_id: int,
    type: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    date: Optional[str] = None,
) -> bool:
    """Update a transaction by id. Only updates provided fields."""
    conn = get_connection()
    cursor = conn.cursor()
    fields = []
    values = []
    if type is not None:
        fields.append("type = ?")
        values.append(type)
    if amount is not None:
        fields.append("amount = ?")
        values.append(amount)
    if category is not None:
        fields.append("category = ?")
        values.append(category)
    if description is not None:
        fields.append("description = ?")
        values.append(description)
    if date is not None:
        fields.append("date = ?")
        values.append(date)
    if not fields:
        conn.close()
        return False
    values.append(transaction_id)
    query = f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_transactions(
    transaction_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    month: Optional[str] = None,
    description_search: Optional[str] = None,
) -> list[dict]:
    """Retrieve transactions with optional filters."""
    conn = get_connection()
    cursor = conn.cursor()
    conditions = []
    values = []
    if transaction_type is not None:
        conditions.append("type = ?")
        values.append(transaction_type)
    if category is not None:
        conditions.append("category = ?")
        values.append(category)
    if start_date is not None:
        conditions.append("date >= ?")
        values.append(start_date)
    if end_date is not None:
        conditions.append("date <= ?")
        values.append(end_date)
    if month is not None:
        conditions.append("strftime('%Y-%m', date) = ?")
        values.append(month)
    if description_search is not None:
        conditions.append("description LIKE ?")
        values.append(f"%{description_search}%")
    query = "SELECT * FROM transactions"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY date DESC, id DESC"
    cursor.execute(query, values)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_transaction_by_id(transaction_id: int) -> dict | None:
    """Fetch a single transaction by its id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_categories() -> list[str]:
    """Return a sorted list of distinct categories."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM transactions ORDER BY category")
    rows = cursor.fetchall()
    conn.close()
    return [row["category"] for row in rows]


def get_months() -> list[str]:
    """Return a sorted list of distinct YYYY-MM months."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT strftime('%Y-%m', date) as month FROM transactions ORDER BY month DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["month"] for row in rows]
