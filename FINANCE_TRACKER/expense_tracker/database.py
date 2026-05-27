import os
import sqlite3
from datetime import datetime, timedelta

# Default categories for transactions
DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Rent & Housing",
    "Salary & Income",
    "Utilities & Bills",
    "Entertainment & Leisure",
    "Transportation",
    "Healthcare & Medical",
    "Shopping",
    "Investments",
    "Freelance",
    "Other"
]

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Set default path relative to this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_dir = os.path.join(base_dir, "database")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "tracker.db")
        else:
            self.db_path = db_path
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
        self.init_db()

    def get_connection(self):
        """Returns a sqlite3 connection with dict-like row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables, indexes, and pre-populates seed data if new."""
        queries = [
            # Transactions table
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                transaction_type TEXT NOT NULL, -- 'Income' or 'Expense'
                date TEXT NOT NULL,             -- YYYY-MM-DD
                notes TEXT
            );
            """,
            # Budgets table
            """
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL
            );
            """,
            # Recurring reminders table
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                frequency TEXT NOT NULL,        -- 'Monthly', 'Weekly', 'Bi-weekly'
                next_due_date TEXT NOT NULL,    -- YYYY-MM-DD
                is_active INTEGER DEFAULT 1     -- 1 = Active, 0 = Completed/Paused
            );
            """,
            # Settings / metadata — tracks one-time seeding flag
            """
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        ]

        
        # Create tables
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for query in queries:
                cursor.execute(query)
            
            # Create indexes for optimized searching and filtering
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_cat ON transactions(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_type ON transactions(transaction_type);")
            
            # Only seed ONCE — check permanent flag, not row count
            # This means user can delete all their transactions without
            # the app resetting back to demo data on next launch.
            cursor.execute("SELECT value FROM settings WHERE key='seeded'")
            seeded_row = cursor.fetchone()
            if not seeded_row or seeded_row[0] != "1":
                self._seed_data(cursor)
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES ('seeded','1')"
                )

            conn.commit()

    def _seed_data(self, cursor):
        """Seeds realistic initial data for testing and demonstrations."""
        today = datetime.now()
        
        # Calculate dates relative to today
        d1 = today.strftime("%Y-%m-%d")
        d2 = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        d3 = (today - timedelta(days=5)).strftime("%Y-%m-%d")
        d4 = (today - timedelta(days=10)).strftime("%Y-%m-%d")
        d5 = (today - timedelta(days=15)).strftime("%Y-%m-%d")
        d6 = (today - timedelta(days=20)).strftime("%Y-%m-%d")
        d7 = (today - timedelta(days=25)).strftime("%Y-%m-%d")
        d8 = (today - timedelta(days=28)).strftime("%Y-%m-%d")
        
        # Sample Transactions
        transactions = [
            ("Monthly Salary", 5500.00, "Salary & Income", "Income", d8, "Main corporate salary payout"),
            ("Freelance UI Design", 1200.00, "Freelance", "Income", d5, "Completed web design project"),
            ("House Rent", 1500.00, "Rent & Housing", "Expense", d8, "May apartment rental payment"),
            ("Whole Foods Groceries", 185.50, "Food & Dining", "Expense", d1, "Weekly grocery replenishment"),
            ("Electricity & Internet Bills", 120.00, "Utilities & Bills", "Expense", d6, "Monthly utilities"),
            ("Uber Ride", 35.00, "Transportation", "Expense", d2, "Commute to corporate meeting"),
            ("Dinner with Client", 95.00, "Food & Dining", "Expense", d3, "Client networking dinner"),
            ("Weekly Supermarket", 110.20, "Food & Dining", "Expense", d4, "Essentials"),
            ("Netflix Premium", 15.99, "Entertainment & Leisure", "Expense", d7, "Monthly streaming subscription"),
            ("Tech Gadgets Shop", 350.00, "Shopping", "Expense", d4, "Mechanical keyboard and mouse"),
            ("Gym Membership", 50.00, "Healthcare & Medical", "Expense", d8, "Monthly fitness subscription"),
            ("Mutual Fund SIP", 500.00, "Investments", "Expense", d6, "Automated monthly investment")
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO transactions (title, amount, category, transaction_type, date, notes) VALUES (?, ?, ?, ?, ?, ?)",
            transactions
        )

        # Seed Budgets
        budgets = [
            ("Food & Dining", 600.00),
            ("Rent & Housing", 1800.00),
            ("Shopping", 400.00),
            ("Utilities & Bills", 200.00),
            ("Entertainment & Leisure", 150.00),
            ("Transportation", 150.00)
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO budgets (category, monthly_limit) VALUES (?, ?)",
            budgets
        )

        # Seed Reminders
        reminders = [
            ("Apartment Rent Payment", 1500.00, "Rent & Housing", "Monthly", (today + timedelta(days=5)).strftime("%Y-%m-%d")),
            ("Electricity & Gas Bill", 95.00, "Utilities & Bills", "Monthly", (today + timedelta(days=12)).strftime("%Y-%m-%d")),
            ("Internet Subscription", 55.00, "Utilities & Bills", "Monthly", (today + timedelta(days=3)).strftime("%Y-%m-%d")),
            ("Car Fuel & Wash", 65.00, "Transportation", "Weekly", (today + timedelta(days=1)).strftime("%Y-%m-%d"))
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO reminders (title, amount, category, frequency, next_due_date) VALUES (?, ?, ?, ?, ?)",
            reminders
        )

    # --- Transactions CRUD ---
    
    def add_transaction(self, title, amount, category, transaction_type, date_str, notes=""):
        """Inserts a new transaction into the database."""
        # Clean inputs
        title = title.strip()
        category = category.strip()
        notes = notes.strip() if notes else ""
        
        query = """
            INSERT INTO transactions (title, amount, category, transaction_type, date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (title, float(amount), category, transaction_type, date_str, notes))
            conn.commit()
            return cursor.lastrowid

    def get_transactions(self, search_query="", category="All", transaction_type="All", date_from=None, date_to=None):
        """Retrieves and filters transactions from the database."""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if search_query:
            query += " AND (title LIKE ? OR notes LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])
            
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
            
        if transaction_type and transaction_type != "All":
            query += " AND transaction_type = ?"
            params.append(transaction_type)
            
        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
            
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)
            
        query += " ORDER BY date DESC, id DESC"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_transaction(self, id_, title, amount, category, transaction_type, date_str, notes=""):
        """Updates an existing transaction."""
        query = """
            UPDATE transactions
            SET title = ?, amount = ?, category = ?, transaction_type = ?, date = ?, notes = ?
            WHERE id = ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (title.strip(), float(amount), category.strip(), transaction_type, date_str, notes.strip(), id_))
            conn.commit()
            return cursor.rowcount > 0

    def delete_transaction(self, id_):
        """Deletes a transaction from the database."""
        query = "DELETE FROM transactions WHERE id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (id_,))
            conn.commit()
            return cursor.rowcount > 0

    # --- Budgets API ---

    def set_budget(self, category, monthly_limit):
        """Inserts or updates a category budget limit."""
        query = """
            INSERT INTO budgets (category, monthly_limit)
            VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (category, float(monthly_limit)))
            conn.commit()

    def delete_budget(self, category):
        """Deletes a budget limit for a category."""
        query = "DELETE FROM budgets WHERE category = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (category,))
            conn.commit()

    def get_budgets(self):
        """Gets all established budgets mapped category -> limit."""
        query = "SELECT * FROM budgets"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return {row["category"]: row["monthly_limit"] for row in cursor.fetchall()}

    # --- Reminders API ---

    def add_reminder(self, title, amount, category, frequency, next_due_date):
        """Adds a recurring bill reminder."""
        query = """
            INSERT INTO reminders (title, amount, category, frequency, next_due_date, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (title.strip(), float(amount), category, frequency, next_due_date))
            conn.commit()
            return cursor.lastrowid

    def get_reminders(self, include_inactive=False):
        """Returns all reminders, sorted by upcoming due date."""
        query = "SELECT * FROM reminders"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY next_due_date ASC"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def toggle_reminder_status(self, id_, is_active):
        """Toggles status of reminder (active vs. resolved/paused)."""
        query = "UPDATE reminders SET is_active = ? WHERE id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (1 if is_active else 0, id_))
            conn.commit()

    def update_reminder_due_date(self, id_, next_due_date):
        """Updates the next due date of a recurring reminder (e.g. after checking off)."""
        query = "UPDATE reminders SET next_due_date = ? WHERE id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (next_due_date, id_))
            conn.commit()

    def delete_reminder(self, id_):
        """Deletes a reminder from the system."""
        query = "DELETE FROM reminders WHERE id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (id_,))
            conn.commit()
            return cursor.rowcount > 0
