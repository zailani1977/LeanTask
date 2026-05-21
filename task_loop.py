import json
import time
import os
import uuid
import datetime
import math
import random
import re

from task_cli_capture import CAPTURE_FILE
from task_db import ISSUES_FILE, hydrate_if_needed
from task_schema import validate_task

def calculate_urgency(status, blockers, base_priority, created_at_iso):
    # Urgency Score = w_active * C_active + w_blocked * C_blocked + w_priority * C_priority - w_age * e^(-0.1t)
    w_active = 1.2
    c_active = 1.0 if status == "in_progress" else 0.0

    w_blocked = -2.0
    # For now, if there are ANY blockers, treat it as blocked.
    # A true system would check if blockers are open.
    c_blocked = 1.0 if len(blockers) > 0 else 0.0

    w_priority = 0.8
    c_priority = float(base_priority)

    # Age in days
    created_at = datetime.datetime.fromisoformat(created_at_iso)
    now = datetime.datetime.now(datetime.timezone.utc)
    t = (now - created_at).total_seconds() / (24 * 3600)
    if t < 0: t = 0

    w_age = 1.0 # Assuming w_age is 1 since it's not strictly defined in prompt, just - w_age * e^(-0.1t)

    urgency = (w_active * c_active) + (w_blocked * c_blocked) + (w_priority * c_priority) - (w_age * math.exp(-0.1 * t))
    return max(0.0, min(5.0, urgency)) # Clamp between 0 and 5.0 for priority_score schema

def _mock_llm_parse(raw_string):
    # Simulated structured LLM call
    # Extract tags (words starting with #)
    tags = re.findall(r'#(\w+)', raw_string)
    title = re.sub(r'#\w+', '', raw_string).strip()

    # Generate task_id matching ^[a-z0-9]{2}-[a-z0-9]{4}$
    prefix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=2))
    suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=4))
    task_id = f"{prefix}-{suffix}"

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "task_id": task_id,
        "parent_id": None,
        "status": "open",
        "priority_score": 2.5, # default
        "project": "default",
        "title": title,
        "description": "Auto-parsed from capture",
        "tags": tags,
        "blocked_by": [],
        "created_at": now,
        "updated_at": now,
        "raw_input": raw_string,
        "history": [],
        "comments": []
    }

def process_loop(run_once=False):
    """File Watcher Loop"""
    while True:
        if not os.path.exists(CAPTURE_FILE):
            if run_once: break
            time.sleep(1)
            continue

        with open(CAPTURE_FILE, "r") as f:
            lines = f.readlines()

        if not lines:
            if run_once: break
            time.sleep(1)
            continue

        remaining_lines = []
        new_tasks = []

        for line in lines:
            if not line.strip(): continue
            try:
                entry = json.loads(line)
                raw_string = entry.get("raw_string", "")

                # Mock AI Extraction
                task = _mock_llm_parse(raw_string)

                # Calculate urgency (initial)
                task["priority_score"] = calculate_urgency(
                    task["status"], task["blocked_by"], task["priority_score"], task["created_at"]
                )

                # Validate
                validate_task(task)
                new_tasks.append(task)
            except Exception as e:
                print(f"Error processing line: {line}. {e}")
                # We could append to remaining_lines to retry, but for prototype we drop bad lines
                pass

        if new_tasks:
            # Commit to issues.jsonl
            with open(ISSUES_FILE, "a") as f:
                for t in new_tasks:
                    f.write(json.dumps(t) + "\n")

            # Clear capture file
            with open(CAPTURE_FILE, "w") as f:
                for rl in remaining_lines:
                    f.write(rl)

            # Auto-hydrate DB
            hydrate_if_needed()
            print(f"Processed {len(new_tasks)} new tasks.")

        if run_once:
            break
        time.sleep(1)
