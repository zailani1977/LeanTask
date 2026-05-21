import json
import os
from task_db import ISSUES_FILE

# Status precedence: closed > review (not in schema but mentioned in doc, we'll map or ignore) > in_progress > blocked > open > deferred
STATUS_PRECEDENCE = {
    "closed": 60,
    "review": 50,
    "in_progress": 40,
    "blocked": 30,
    "open": 20,
    "deferred": 10
}

def merge_tasks(t1, t2):
    # Determine timestamp winner
    ts1 = t1.get("updated_at", "")
    ts2 = t2.get("updated_at", "")
    newer, older = (t1, t2) if ts1 >= ts2 else (t2, t1)

    # Base is the newer one for most fields
    merged = dict(newer)

    # Status precedence overrides timestamp
    s1_score = STATUS_PRECEDENCE.get(t1.get("status", "open"), 0)
    s2_score = STATUS_PRECEDENCE.get(t2.get("status", "open"), 0)
    merged["status"] = t1["status"] if s1_score >= s2_score else t2["status"]

    # Merge history
    h1 = t1.get("history", [])
    h2 = t2.get("history", [])
    all_history = {json.dumps(h, sort_keys=True): h for h in h1 + h2} # deduplicate by content
    merged["history"] = sorted(all_history.values(), key=lambda x: x["timestamp"])

    # Merge comments
    c1 = t1.get("comments", [])
    c2 = t2.get("comments", [])
    all_comments = {c["comment_id"]: c for c in c1 + c2}
    merged["comments"] = sorted(all_comments.values(), key=lambda x: x["timestamp"])

    # Tags & blocked_by union
    merged["tags"] = list(set(t1.get("tags", []) + t2.get("tags", [])))
    merged["blocked_by"] = list(set(t1.get("blocked_by", []) + t2.get("blocked_by", [])))

    return merged

def sync_issues():
    if not os.path.exists(ISSUES_FILE):
        return

    tasks_by_id = {}

    with open(ISSUES_FILE, 'r') as f:
        for line in f:
            if not line.strip(): continue
            try:
                task = json.loads(line)
                tid = task["task_id"]
                if tid in tasks_by_id:
                    tasks_by_id[tid] = merge_tasks(tasks_by_id[tid], task)
                else:
                    tasks_by_id[tid] = task
            except Exception as e:
                print(f"Skipping line during sync due to error: {e}")

    # Rewrite issues.jsonl
    with open(ISSUES_FILE, 'w') as f:
        for tid, t in tasks_by_id.items():
            f.write(json.dumps(t) + "\n")

    print(f"Sync complete. {len(tasks_by_id)} unique tasks written.")
