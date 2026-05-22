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
            shutil.rmtree(".tasks")
            print("Successfully deleted the .tasks/ directory (hard clean).")
        else:
            print(".tasks/ directory does not exist.")
    else:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            print("Successfully deleted the SQLite cache (db.sqlite).")
        else:
            print("SQLite cache (db.sqlite) does not exist.")
