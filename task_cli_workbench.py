import json
import datetime
import uuid
from task_db import get_connection, ISSUES_FILE

DUE_DATE_FORMAT = "%Y-%m-%d"

def normalize_due_date(date_str, allow_empty=False):
    value = (date_str or "").strip()
    if not value:
        if allow_empty:
            return ""
        raise ValueError("Due date must be in YYYY-MM-DD format (for example, 2026-06-05).")

    try:
        return datetime.date.fromisoformat(value).strftime(DUE_DATE_FORMAT)
    except ValueError:
        pass

    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).date().strftime(DUE_DATE_FORMAT)
    except ValueError as exc:
        raise ValueError("Due date must be in YYYY-MM-DD format (for example, 2026-06-05).") from exc

def format_due_date(due_value, empty_value="None"):
    if not due_value:
        return empty_value

    try:
        return normalize_due_date(due_value)
    except ValueError:
        return str(due_value).strip()

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
    with open(ISSUES_FILE, 'r', encoding='utf-8') as f:
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

    with open(ISSUES_FILE, 'w', encoding='utf-8') as f:
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

def due(task_id, date_str):
    normalized_date = normalize_due_date(date_str, allow_empty=True)

    def change_due_date(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        old_date = task.get("due_date")
        task["due_date"] = normalized_date or None

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "due_date",
            "old_value": old_date,
            "new_value": normalized_date or None
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, change_due_date):
        if normalized_date:
            print(f"Due date of {task_id} changed to {normalized_date}.")
        else:
            print(f"Due date of {task_id} cleared.")

def list_tasks(status):
    conn = get_connection()
    cursor = conn.cursor()
    if status == 'all':
        query = "SELECT task_id, status, priority_score, project, title, tags, due_date FROM tasks"
        cursor.execute(query)
    else:
        query = "SELECT task_id, status, priority_score, project, title, tags, due_date FROM tasks WHERE status = ?"
        cursor.execute(query, (status,))
    rows = cursor.fetchall()

    print(f"Tasks with status '{status}':")
    print(f"{'ID':^9} | {'STATUS':^11} | {'PRIORITY':^8} | {'PROJECT':^10} | {'DUE':^10} | TITLE | TAGS")
    for row in rows:
        due_val = format_due_date(row[6])
        print(f"[{row[0]}] {row[1].upper():^11} | P: {row[2]:<5} | {row[3]:^10} | Due: {due_val:<6} | {row[4]} | {row[5]}")
    conn.close()

def view(task_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch base task
    cursor.execute("""
        SELECT task_id, status, priority_score, project, title, description, tags, blocked_by, due_date, created_at, updated_at
        FROM tasks WHERE task_id = ?
    """, (task_id,))
    row = cursor.fetchone()

    if not row:
        print(f"Task {task_id} not found.")
        conn.close()
        return

    print("=" * 60)
    print(f"[{row[0]}] {row[4]}")
    print("=" * 60)
    print(f"Status:     {row[1].upper()}")
    print(f"Priority:   {row[2]}")
    print(f"Project:    {row[3]}")
    print(f"Due Date:   {format_due_date(row[8])}")
    print(f"Tags:       {row[6]}")
    print(f"Blocked By: {row[7]}")
    print(f"Created:    {row[9]}")
    print(f"Updated:    {row[10]}")
    print("-" * 60)
    print(f"Description:\n{row[5]}")
    print("-" * 60)

    # Fetch comments
    cursor.execute("""
        SELECT timestamp, author, text
        FROM task_comments WHERE task_id = ?
        ORDER BY timestamp ASC
    """, (task_id,))
    comments = cursor.fetchall()

    if comments:
        print("Comments:")
        for c in comments:
            print(f"  [{c[0]}] {c[1]}: {c[2]}")
    else:
        print("No comments.")

    print("=" * 60)
    conn.close()

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

def priority(task_id, score):
    try:
        score = float(score)
    except ValueError:
        print("Priority score must be a number.")
        return

    if score < 0.0 or score > 5.0:
        print("Priority score must be between 0.0 and 5.0.")
        return

    def change_priority(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        old_score = task.get("priority_score", 0.0)
        task["priority_score"] = score

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "priority_score",
            "old_value": old_score,
            "new_value": score
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, change_priority):
        print(f"Priority of {task_id} changed to {score}.")

def project(task_id, project_name):
    def change_project(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        old_project = task.get("project", "untriaged")
        task["project"] = project_name

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "project",
            "old_value": old_project,
            "new_value": project_name
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, change_project):
        print(f"Project of {task_id} changed to {project_name}.")

def title(task_id, new_title):
    def change_title(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        old_title = task.get("title", "")
        task["title"] = new_title

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "title",
            "old_value": old_title,
            "new_value": new_title
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, change_title):
        print(f"Title of {task_id} changed.")

def description(task_id, new_description):
    def change_description(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        old_desc = task.get("description", "")
        task["description"] = new_description

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "description",
            "old_value": old_desc,
            "new_value": new_description
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, change_description):
        print(f"Description of {task_id} changed.")

def tags(task_id, tags_list):
    def change_tags(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        old_tags = task.get("tags", [])
        task["tags"] = tags_list

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "tags",
            "old_value": old_tags,
            "new_value": tags_list
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, change_tags):
        print(f"Tags of {task_id} changed.")

def blocked_by(task_id, blocked_by_list):
    def change_blocked_by(task):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        old_blocked_by = task.get("blocked_by", [])
        task["blocked_by"] = blocked_by_list

        # audit log
        h = {
            "timestamp": now,
            "author": "user",
            "field": "blocked_by",
            "old_value": old_blocked_by,
            "new_value": blocked_by_list
        }
        task.setdefault("history", []).append(h)
        task["updated_at"] = now

    if _update_task_in_jsonl(task_id, change_blocked_by):
        print(f"Blocked by of {task_id} changed.")

def archive_tasks():
    import os
    tasks_to_keep = []
    tasks_to_archive = []

    if not os.path.exists(ISSUES_FILE):
        print("No issues file found.")
        return 0

    with open(ISSUES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            task = json.loads(line)
            if task.get("status") in ["closed", "deferred"]:
                tasks_to_archive.append(task)
            else:
                tasks_to_keep.append(task)

    if not tasks_to_archive:
        print("No tasks to archive.")
        return 0

    ARCHIVE_FILE = ".tasks/archive.jsonl"
    os.makedirs(os.path.dirname(ARCHIVE_FILE), exist_ok=True)

    with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
        for t in tasks_to_archive:
            f.write(json.dumps(t) + "\n")

    with open(ISSUES_FILE, 'w', encoding='utf-8') as f:
        for t in tasks_to_keep:
            f.write(json.dumps(t) + "\n")

    print(f"Archived {len(tasks_to_archive)} tasks.")

    # We should sync_issues to make sure sqlite database is updated.
    from task_sync import sync_issues
    sync_issues()

    return len(tasks_to_archive)

def view_archive(task_id=None):
    import os
    ARCHIVE_FILE = ".tasks/archive.jsonl"

    if not os.path.exists(ARCHIVE_FILE):
        print("No archive file found.")
        return

    archived_tasks = []
    with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            archived_tasks.append(json.loads(line))

    if task_id is None:
        if not archived_tasks:
            print("Archive is empty.")
            return

        print("Archived Tasks:")
        print(f"{'ID':^9} | {'STATUS':^11} | {'PRIORITY':^8} | {'PROJECT':^10} | {'DUE':^10} | TITLE | TAGS")
        for task in archived_tasks:
            due_val = format_due_date(task.get("due_date"))
            status = task.get("status", "").upper()
            priority_val = task.get("priority_score", 0.0)
            project_val = task.get("project", "")
            title_val = task.get("title", "")
            tags_val = task.get("tags", [])
            print(f"[{task['task_id']}] {status:^11} | P: {priority_val:<5} | {project_val:^10} | Due: {due_val:<6} | {title_val} | {tags_val}")
    else:
        found_task = None
        for task in archived_tasks:
            if task.get("task_id") == task_id:
                found_task = task
                break

        if not found_task:
            print(f"Task {task_id} not found in archive.")
            return

        print("=" * 60)
        print(f"[{found_task.get('task_id')}] {found_task.get('title')}")
        print("=" * 60)
        print(f"Status:     {found_task.get('status', '').upper()}")
        print(f"Priority:   {found_task.get('priority_score')}")
        print(f"Project:    {found_task.get('project')}")
        print(f"Due Date:   {format_due_date(found_task.get('due_date'))}")
        print(f"Tags:       {found_task.get('tags')}")
        print(f"Blocked By: {found_task.get('blocked_by')}")
        print(f"Created:    {found_task.get('created_at')}")
        print(f"Updated:    {found_task.get('updated_at')}")
        print("-" * 60)
        print(f"Description:\n{found_task.get('description')}")
        print("-" * 60)

        comments = found_task.get("comments", [])
        if comments:
            print("Comments:")
            for c in comments:
                print(f"  [{c.get('timestamp')}] {c.get('author')}: {c.get('text')}")
        else:
            print("No comments.")

        print("=" * 60)
