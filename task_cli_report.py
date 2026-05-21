import json
from task_db import get_connection

def report():
    conn = get_connection()
    cursor = conn.cursor()

    # We need to compute urgency, but for the DB report, we'll fetch all non-closed tasks
    cursor.execute("""
        SELECT task_id, status, priority_score, title, blocked_by
        FROM tasks
        WHERE status != 'closed'
    """)
    rows = cursor.fetchall()

    tasks = []
    for r in rows:
        tasks.append({
            "task_id": r[0],
            "status": r[1],
            "priority_score": r[2],
            "title": r[3],
            "blocked_by": json.loads(r[4]) if r[4] else []
        })

    # Build a lookup for status to filter resolved blockers
    status_map = {r[0]: r[1] for r in cursor.execute("SELECT task_id, status FROM tasks").fetchall()}

    # 1. Daily Matrix: Prioritized unblocked tasks
    # Active unblocked = no blockers OR all blockers are closed
    daily_matrix = []
    triage_queue = []
    blocker_alerts = []

    for t in tasks:
        # Check if actually blocked
        active_blockers = [b for b in t["blocked_by"] if status_map.get(b, "open") != "closed"]

        if t["status"] == "open" and not t["blocked_by"]: # simplified triage logic
             triage_queue.append(t)

        if active_blockers:
            t["active_blockers"] = active_blockers
            blocker_alerts.append(t)
        else:
            # If it's not blocked and not deferred
            if t["status"] not in ["deferred", "blocked"]:
                 daily_matrix.append(t)

    # Sort Daily Matrix by priority (descending)
    daily_matrix.sort(key=lambda x: x["priority_score"], reverse=True)

    print("# Daily Report\n")

    print("## The Daily Matrix (Unblocked, Prioritized)")
    if not daily_matrix:
        print("  *None*")
    for t in daily_matrix:
        print(f"  - [{t['task_id']}] {t['title']} (P: {t['priority_score']})")

    print("\n## The Triage Queue")
    if not triage_queue:
        print("  *None*")
    for t in triage_queue:
        print(f"  - [{t['task_id']}] {t['title']}")

    print("\n## Blocker Alerts")
    if not blocker_alerts:
        print("  *None*")
    for t in blocker_alerts:
        print(f"  - [{t['task_id']}] {t['title']} -> Blocked by: {', '.join(t['active_blockers'])}")

    conn.close()
