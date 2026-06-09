"""Test script for database operations."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils"))

from database import create_table, insert_transaction, get_transactions, delete_transaction, DATABASE_PATH


def main():
    # Clean start
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)

    print("Creating table...")
    create_table()
    print("Table created.\n")

    print("Inserting records...")
    id1 = insert_transaction("expense", 200.0, "Food", "Lunch", "2024-06-08")
    id2 = insert_transaction("expense", 100.0, "Travel", "Bus fare", "2024-06-08")
    id3 = insert_transaction("income", 20000.0, "Salary", "Monthly salary", "2024-06-01")
    print(f"Inserted: Food (id={id1}), Travel (id={id2}), Salary (id={id3})\n")

    print("Retrieving all records...")
    records = get_transactions()
    print(f"Total records: {len(records)}")
    for r in records:
        print(f"  id={r['id']}, type={r['type']}, amount={r['amount']}, category={r['category']}, description={r['description']}, date={r['date']}")
    print()

    print(f"Deleting record id={id2} (Travel)...")
    deleted = delete_transaction(id2)
    print(f"Deleted: {deleted}\n")

    print("Retrieving records after deletion...")
    records_after = get_transactions()
    print(f"Total records: {len(records_after)}")
    for r in records_after:
        print(f"  id={r['id']}, type={r['type']}, amount={r['amount']}, category={r['category']}, description={r['description']}, date={r['date']}")
    print()

    # Verify deletion
    ids_after = {r["id"] for r in records_after}
    if id2 not in ids_after and len(records_after) == 2:
        print("✅ Deletion verified successfully.")
    else:
        print("❌ Deletion verification failed.")


if __name__ == "__main__":
    main()
