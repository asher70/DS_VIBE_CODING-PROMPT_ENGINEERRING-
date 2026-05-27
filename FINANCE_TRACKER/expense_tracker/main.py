import os
import sys

# Ensure parent directory is in path when executing locally
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from expense_tracker.database import DatabaseManager
from expense_tracker.ui import ExpenseTrackerApp

def main():
    """
    Main entry point for starting the Expense Tracker.
    Bootstraps folders and initiates GUI event loop.
    """
    # 1. Establish necessary data directories relative to package folder
    package_dir = os.path.dirname(os.path.abspath(__file__))
    
    dirs_to_create = [
        os.path.join(package_dir, "database"),
        os.path.join(package_dir, "assets"),
        os.path.join(package_dir, "exports")
    ]
    
    for d in dirs_to_create:
        os.makedirs(d, exist_ok=True)
        # Create a placeholder txt inside empty folders to check in git
        placeholder = os.path.join(d, "placeholder.txt")
        if not os.path.exists(placeholder):
            with open(placeholder, "w") as f:
                f.write("WealthSuite dynamic asset path placeholder.")

    # 2. Start database connection manager
    db_mgr = DatabaseManager()
    
    # 3. Boot Tkinter/ttkbootstrap GUI
    app = ExpenseTrackerApp(db_mgr)
    app.mainloop()

if __name__ == "__main__":
    main()
