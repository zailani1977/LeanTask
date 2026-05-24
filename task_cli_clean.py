import os
import shutil
from task_db import DB_FILE

def clean(hard=False):
    """
    Cleans the workspace.
    If hard is False, it only deletes the SQLite read-cache (.tasks/db.sqlite).
    If hard is True, it wipes the entire .tasks/ directory.
    """
    if hard:
        if os.path.exists(".tasks"):
            try:
                shutil.rmtree(".tasks")
                print("Successfully deleted the .tasks/ directory (hard clean).")
            except PermissionError as e:
                print(f"Error: Could not delete the .tasks/ directory due to a file lock. Ensure no other instances of the CLI or GUI are running. Details: {e}")
        else:
            print(".tasks/ directory does not exist.")
    else:
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
                print("Successfully deleted the SQLite cache (db.sqlite).")
            except PermissionError as e:
                print(f"Error: Could not delete the SQLite cache file due to a file lock. Ensure no other instances of the CLI or GUI are running. Details: {e}")
        else:
            print("SQLite cache (db.sqlite) does not exist.")
