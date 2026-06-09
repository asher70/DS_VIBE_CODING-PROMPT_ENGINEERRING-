"""Benchmark script: generate 10,000 transactions and measure performance."""

import os
import random
import sys
import tempfile
import time
from datetime import datetime, timedelta

# ── Use a temporary database so we never touch user data ──
import utils.database as db

TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
db.DATABASE_PATH = TMP_DB

from utils.database import (
    create_table,
    insert_transaction,
    get_transactions,
    get_categories,
    get_months,
)
from utils.analytics import (
    total_income,
    total_expenses,
    balance,
    pie_chart,
    monthly_graph,
    category_graph,
)
from utils.export import to_csv_bytes, to_excel_bytes

# ── Config ──
N = 10_000
CATEGORIES = [
    "Food",
    "Rent",
    "Salary",
    "Travel",
    "Entertainment",
    "Utilities",
    "Health",
    "Shopping",
    "Investment",
    "Freelance",
]
DESCRIPTIONS = [
    "Lunch",
    "Dinner",
    "Monthly rent",
    "Bus fare",
    "Movie ticket",
    "Electric bill",
    "Doctor visit",
    "Groceries",
    "Stock purchase",
    "Client payment",
    "",
]
TYPES = ["income", "expense"]

failures = []


def log(msg):
    print(msg, flush=True)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Setup ──
log(f"[{now()}] Creating temporary benchmark DB: {TMP_DB}")
create_table()

# ── Insert benchmark ──
log(f"[{now()}] Generating {N:,} transactions...")
insert_times = []
random.seed(42)
start_total = time.perf_counter()
for i in range(N):
    tx_type = random.choice(TYPES)
    amount = round(random.uniform(1.0, 10_000.0), 2)
    category = random.choice(CATEGORIES)
    description = random.choice(DESCRIPTIONS)
    days_back = random.randint(0, 365 * 5)
    date_str = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    t0 = time.perf_counter()
    try:
        insert_transaction(tx_type, amount, category, description, date_str)
    except Exception as exc:
        failures.append(f"Insert #{i+1}: {exc}")
    insert_times.append(time.perf_counter() - t0)

elapsed_insert = time.perf_counter() - start_total
log(f"[{now()}] Insert complete: {elapsed_insert:.2f}s total")

# ── Search benchmarks ──
log(f"[{now()}] Running search benchmarks...")
search_cases = [
    ("No filters", {}),
    ("Type = expense", {"transaction_type": "expense"}),
    ("Type = income", {"transaction_type": "income"}),
    ("Category = Food", {"category": "Food"}),
    ("Month = 2024-06", {"month": "2024-06"}),
    ("Date range (1 year)", {"start_date": "2023-01-01", "end_date": "2023-12-31"}),
    ("Description search", {"description_search": "rent"}),
    ("Combined filters", {"transaction_type": "expense", "category": "Food", "description_search": "Lunch"}),
]

search_results = []
for label, kwargs in search_cases:
    t0 = time.perf_counter()
    try:
        rows = get_transactions(**kwargs)
        elapsed = time.perf_counter() - t0
        search_results.append((label, elapsed, len(rows)))
    except Exception as exc:
        failures.append(f"Search [{label}]: {exc}")
        search_results.append((label, None, None))

# ── Chart benchmarks ──
log(f"[{now()}] Running chart benchmarks...")
chart_cases = [
    ("total_income", lambda: total_income()),
    ("total_expenses", lambda: total_expenses()),
    ("balance", lambda: balance()),
    ("pie_chart", lambda: pie_chart()),
    ("monthly_graph", lambda: monthly_graph()),
    ("category_graph", lambda: category_graph()),
]

chart_results = []
for label, fn in chart_cases:
    t0 = time.perf_counter()
    try:
        result = fn()
        elapsed = time.perf_counter() - t0
        chart_results.append((label, elapsed, result is not None))
    except Exception as exc:
        failures.append(f"Chart [{label}]: {exc}")
        chart_results.append((label, None, False))

# ── Export benchmarks ──
log(f"[{now()}] Running export benchmarks...")
export_results = []
all_records = get_transactions()
for label, fn in [("CSV", to_csv_bytes), ("Excel", to_excel_bytes)]:
    t0 = time.perf_counter()
    try:
        data = fn(all_records)
        elapsed = time.perf_counter() - t0
        export_results.append((label, elapsed, len(data)))
    except Exception as exc:
        failures.append(f"Export [{label}]: {exc}")
        export_results.append((label, None, 0))

# ── DB size ──
db_size_bytes = os.path.getsize(TMP_DB)

# ── Report ──
log("")
log("=" * 60)
log("BENCHMARK REPORT")
log("=" * 60)
log(f"Database:         {TMP_DB}")
log(f"Database size:    {db_size_bytes:,} bytes ({db_size_bytes / 1024:.1f} KB)")
log(f"Total rows:       {len(all_records):,}")
log("")

log("INSERT PERFORMANCE")
log("-" * 40)
log(f"Total time:       {elapsed_insert:.3f}s")
log(f"Transactions:     {N:,}")
log(f"Avg per insert:   {elapsed_insert / N * 1000:.3f} ms")
log(f"Inserts/sec:      {N / elapsed_insert:,.1f}")
log("")

log("SEARCH PERFORMANCE")
log("-" * 40)
for label, elapsed, count in search_results:
    if elapsed is not None:
        log(f"{label:30s} {elapsed * 1000:8.3f} ms ({count:,} rows)")
    else:
        log(f"{label:30s} FAILED")
log("")

log("CHART PERFORMANCE")
log("-" * 40)
for label, elapsed, ok in chart_results:
    if elapsed is not None:
        log(f"{label:30s} {elapsed * 1000:8.3f} ms (ok={ok})")
    else:
        log(f"{label:30s} FAILED")
log("")

log("EXPORT PERFORMANCE")
log("-" * 40)
for label, elapsed, size in export_results:
    if elapsed is not None:
        log(f"{label:30s} {elapsed * 1000:8.3f} ms ({size:,} bytes)")
    else:
        log(f"{label:30s} FAILED")
log("")

if failures:
    log(f"FAILURES: {len(failures)}")
    log("-" * 40)
    for f in failures:
        log(f"  - {f}")
else:
    log("FAILURES: 0")

log("=" * 60)

# Cleanup
os.remove(TMP_DB)
