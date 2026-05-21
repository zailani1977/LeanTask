import json
import datetime
import uuid
from task_db import get_connection, ISSUES_FILE

def search(keyword):
    conn = get_connection()
    cursor = conn.cursor()
    # Simple LIKE search across title, description, tags
    query = """
        SELECT task_id, status, priority_score, project, title, tags
        FROM tasks
        WHERE title LIKE ? OR description LIKE ? OR tags LIKE ?
    """
    kw = f"%{keyword}%"
    cursor.execute(query, (kw, kw, kw))
    rows = cursor.fetchall()

    print(f"Search results for '{keyword}':")
    for row in rows:
        print(f"[{row[0]}] {row[1].upper()} | P: {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    conn.close()

def _update_task_in_jsonl(task_id, updater_func):
    """Reads issues.jsonl, finds the task, applies updater_func, and rewrites the file."""
    tasks = []
    found = False
    with open(ISSUES_FILE, 'r') as f:
        for line in f:
            if not line.strip(): continue
            task = json.loads(line)
            if task["task_id"] == task_id:
                updater_func(task)
                found = True
            tasks.append(task)

    if not found:
        print(f"Task {task_id} not found.")
        return False

    with open(ISSUES_FILE, 'w') as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")
    return True

def comment(task_id, text):
    def add_comment(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        c = {
            "comment_id": str(uuid.uuid4()),
            "timestamp": now,
            "author": "user", # hardcoded for cli prototype
            "text": text
        }
        task.setdefault("comments", []).append(c)

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "comments",
            "old_value": len(task["comments"]) - 1,
            "new_value": len(task["comments"])
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, add_comment):
        print(f"Comment added to {task_id}.")

def state(task_id, new_state):
    valid_states = {"open", "in_progress", "blocked", "deferred", "closed"}
    if new_state not in valid_states:
        print(f"Invalid state: {new_state}. Must be one of {valid_states}.")
        return

    def change_state(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        old_state = task["status"]
        task["status"] = new_state

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "status",
            "old_value": old_state,
            "new_value": new_state
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, change_state):
        print(f"State of {task_id} changed to {new_state}.")
