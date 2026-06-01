import sys
import os

# Add the workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from expense_tracker.main import main

if __name__ == "__main__":
    main()
