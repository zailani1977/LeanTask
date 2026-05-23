import json
import datetime
import os
import random

from task_db import ISSUES_FILE

def capture(raw_string):
    # Fast offline append directly to issues.jsonl with a placeholder structure
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Generate task_id matching ^[a-z0-9]{2}-[a-z0-9]{4}$
    prefix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=2))
    suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=4))
    task_id = f"{prefix}-{suffix}"

    entry = {
        "task_id": task_id,
        "parent_id": None,
        "status": "open",
        "priority_score": 0.0, # Placeholder for triage agent
        "project": "untriaged",
        "title": raw_string[:50] + ("..." if len(raw_string) > 50 else ""), # Snippet as title
        "description": "Captured raw input.",
        "tags": [],
        "blocked_by": [],
        "due_date": None,
        "created_at": now,
        "updated_at": now,
        "raw_input": raw_string,
        "history": [{
            "timestamp": now,
            "author": "user",
            "field": "creation",
            "old_value": None,
            "new_value": "captured"
        }],
        "comments": []
    }

    os.makedirs(".tasks", exist_ok=True)

    with open(ISSUES_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(task_id)
