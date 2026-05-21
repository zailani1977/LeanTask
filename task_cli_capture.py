import json
import datetime
import os

CAPTURE_FILE = ".tasks/capture.jsonl"

def capture(raw_string):
    # Fast offline append to capture.jsonl
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry = {
        "timestamp": now,
        "raw_string": raw_string
    }

    # Ensure directory exists just in case
    os.makedirs(".tasks", exist_ok=True)

    with open(CAPTURE_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
