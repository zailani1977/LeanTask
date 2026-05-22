import json
import sys
import os

from task_db import get_connection, ISSUES_FILE
from task_sync import sync_issues
from task_schema import validate_task

def export_tasks(status=None):
    """Outputs tasks as a JSON array to stdout, optionally filtered by status."""
    conn = get_connection()
    cursor = conn.cursor()

    if status:
        # Fetch filtered
        cursor.execute("SELECT task_id, parent_id, status, priority_score, project, title, description, tags, blocked_by, due_date, created_at, updated_at, raw_input FROM tasks WHERE status = ?", (status,))
    else:
        # Fetch all
        cursor.execute("SELECT task_id, parent_id, status, priority_score, project, title, description, tags, blocked_by, due_date, created_at, updated_at, raw_input FROM tasks")

    rows = cursor.fetchall()

    tasks = []
    for r in rows:
        # Reconstruct base task dict (excluding history/comments for bulk export simplicity,
        # or we could fetch them too if the agent needs full context. We'll fetch base context)
        task = {
            "task_id": r[0],
            "parent_id": r[1],
            "status": r[2],
            "priority_score": r[3],
            "project": r[4],
            "title": r[5],
            "description": r[6],
            "tags": json.loads(r[7]) if r[7] else [],
            "blocked_by": json.loads(r[8]) if r[8] else [],
            "due_date": r[9],
            "created_at": r[10],
            "updated_at": r[11],
            "raw_input": r[12],
            # Fetch minimal history/comments just to pass validation
            "history": [],
            "comments": []
        }

        # Hydrate history/comments
        cur2 = conn.cursor()
        cur2.execute("SELECT timestamp, author, field, old_value, new_value FROM task_history WHERE task_id = ?", (r[0],))
        for h in cur2.fetchall():
            task["history"].append({
                "timestamp": h[0], "author": h[1], "field": h[2], "old_value": json.loads(h[3]) if h[3] else None, "new_value": json.loads(h[4]) if h[4] else None
            })

        cur2.execute("SELECT comment_id, timestamp, author, text FROM task_comments WHERE task_id = ?", (r[0],))
        for c in cur2.fetchall():
            task["comments"].append({
                "comment_id": c[0], "timestamp": c[1], "author": c[2], "text": c[3]
            })

        tasks.append(task)

    print(json.dumps(tasks, indent=2))
    conn.close()


def import_tasks(file_path=None):
    """Reads a JSON array of tasks from a file (or stdin), appends them to issues.jsonl, and syncs."""
    try:
        if file_path and file_path != "-":
            with open(file_path, 'r') as f:
                tasks = json.load(f)
        else:
            tasks = json.load(sys.stdin)

        if not isinstance(tasks, list):
            print("Error: Input must be a JSON array of task objects.", file=sys.stderr)
            sys.exit(1)

        valid_tasks = []
        for t in tasks:
            try:
                validate_task(t)
                valid_tasks.append(t)
            except Exception as e:
                print(f"Skipping invalid task {t.get('task_id', 'unknown')}: {e}", file=sys.stderr)

        if valid_tasks:
            with open(ISSUES_FILE, 'a') as f:
                for t in valid_tasks:
                    f.write(json.dumps(t) + "\n")

            # Resolve conflicts deterministically using existing logic
            sync_issues()
            print(f"Successfully imported and synced {len(valid_tasks)} tasks.", file=sys.stderr)
        else:
            print("No valid tasks imported.", file=sys.stderr)

    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Import Error: {e}", file=sys.stderr)
        sys.exit(1)
