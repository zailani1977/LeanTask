import sqlite3
import json
import os
from task_schema import validate_task
import jsonschema

DB_FILE = ".tasks/db.sqlite"
ISSUES_FILE = ".tasks/issues.jsonl"

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            parent_id TEXT,
            status TEXT,
            priority_score REAL,
            project TEXT,
            title TEXT,
            description TEXT,
            tags TEXT, -- JSON array
            blocked_by TEXT, -- JSON array
            created_at TEXT,
            updated_at TEXT,
            raw_input TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            timestamp TEXT,
            author TEXT,
            field TEXT,
            old_value TEXT,
            new_value TEXT,
            FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_comments (
            comment_id TEXT PRIMARY KEY,
            task_id TEXT,
            timestamp TEXT,
            author TEXT,
            text TEXT,
            FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_project ON tasks(project)")

    conn.commit()

def clear_db(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS task_history")
    cursor.execute("DROP TABLE IF EXISTS task_comments")
    cursor.execute("DROP TABLE IF EXISTS tasks")
    conn.commit()

def load_db_from_jsonl(conn):
    if not os.path.exists(ISSUES_FILE):
        return

    cursor = conn.cursor()
    with open(ISSUES_FILE, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                task = json.loads(line)
                validate_task(task)

                cursor.execute("""
                    INSERT OR REPLACE INTO tasks (
                        task_id, parent_id, status, priority_score, project,
                        title, description, tags, blocked_by, created_at,
                        updated_at, raw_input
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task["task_id"],
                    task.get("parent_id"),
                    task["status"],
                    task["priority_score"],
                    task["project"],
                    task["title"],
                    task["description"],
                    json.dumps(task["tags"]),
                    json.dumps(task["blocked_by"]),
                    task["created_at"],
                    task["updated_at"],
                    task["raw_input"]
                ))

                # history
                for h in task.get("history", []):
                    cursor.execute("""
                        INSERT INTO task_history (task_id, timestamp, author, field, old_value, new_value)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        task["task_id"],
                        h["timestamp"],
                        h["author"],
                        h["field"],
                        json.dumps(h["old_value"]),
                        json.dumps(h["new_value"])
                    ))

                # comments
                for c in task.get("comments", []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO task_comments (comment_id, task_id, timestamp, author, text)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        c["comment_id"],
                        task["task_id"],
                        c["timestamp"],
                        c["author"],
                        c["text"]
                    ))
            except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                # In production we might log this; for now we skip invalid rows or let it fail
                print(f"Skipping invalid row in issues.jsonl: {e}")
    conn.commit()

def hydrate_if_needed():
    # If issues.jsonl is newer than db.sqlite, rebuild.
    issues_mtime = 0
    if os.path.exists(ISSUES_FILE):
        issues_mtime = os.path.getmtime(ISSUES_FILE)

    db_mtime = 0
    if os.path.exists(DB_FILE):
        db_mtime = os.path.getmtime(DB_FILE)

    if issues_mtime > db_mtime or db_mtime == 0:
        conn = sqlite3.connect(DB_FILE)
        # Rebuild
        clear_db(conn)
        init_db(conn)
        load_db_from_jsonl(conn)
        conn.close()

def get_connection():
    hydrate_if_needed()
    return sqlite3.connect(DB_FILE)
