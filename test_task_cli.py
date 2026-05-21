import unittest
import time
import os
import json
import shutil
from unittest.mock import patch

import task_cli_capture
import task_loop
import task_db
import task_sync
from task_cli_workbench import _update_task_in_jsonl

class TestTaskCLI(unittest.TestCase):

    def setUp(self):
        # Fresh test workspace
        if os.path.exists(".tasks"):
            shutil.rmtree(".tasks")
        os.makedirs(".tasks")

        # Monkeypatch constants if needed, but since they read from .tasks/ we are good
        open(task_db.ISSUES_FILE, 'w').close()
        open(task_cli_capture.CAPTURE_FILE, 'w').close()

    def test_latency(self):
        """Latency Test: Assert that the capture script appends to the buffer file in under 15ms."""
        start = time.time()
        task_cli_capture.capture("Fix SPI memory leak #network #bug")
        end = time.time()
        duration = (end - start) * 1000 # ms
        self.assertLess(duration, 15.0, f"Capture took {duration}ms, which is >= 15ms")

        with open(task_cli_capture.CAPTURE_FILE, 'r') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("Fix SPI memory leak", lines[0])

    def test_rehydration(self):
        """Rehydration Test: Write structured tasks to issues.jsonl, trigger rehydration, and query them from SQLite."""
        tasks = []
        for i in range(5):
            tasks.append({
                "task_id": f"ab-123{i}",
                "parent_id": None,
                "status": "open",
                "priority_score": 1.0,
                "project": "test",
                "title": f"Test {i}",
                "description": "desc",
                "tags": [],
                "blocked_by": [],
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "raw_input": "raw",
                "history": [],
                "comments": []
            })

        with open(task_db.ISSUES_FILE, 'w') as f:
            for t in tasks:
                f.write(json.dumps(t) + "\n")

        # Trigger rehydration implicitly by getting connection
        conn = task_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 5)
        conn.close()

    def test_dependency_sort(self):
        """Dependency Sort Test: Insert Task A and Task B (blocked by A). Assert logic of report output implicitly by checking matrix sorting."""
        # Setup Tasks
        task_a = {
            "task_id": "aa-1111", "status": "open", "priority_score": 5.0,
            "project": "test", "title": "Task A", "description": "A",
            "tags": [], "blocked_by": [], "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z", "raw_input": "A", "history": [], "comments": []
        }
        task_b = {
            "task_id": "bb-2222", "status": "open", "priority_score": 4.0,
            "project": "test", "title": "Task B", "description": "B",
            "tags": [], "blocked_by": ["aa-1111"], "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z", "raw_input": "B", "history": [], "comments": []
        }
        with open(task_db.ISSUES_FILE, 'w') as f:
            f.write(json.dumps(task_a) + "\n")
            f.write(json.dumps(task_b) + "\n")

        # Rehydrate DB
        task_db.hydrate_if_needed()

        # Test agent logic from task_cli_report
        import io
        import sys
        import task_cli_report

        captured_out = io.StringIO()
        sys.stdout = captured_out
        task_cli_report.report()
        sys.stdout = sys.__stdout__

        out = captured_out.getvalue()

        # Task A should be in Daily Matrix or Triage Queue (it's open and unblocked -> Triage Queue in our code)
        # Task B should be in Blocker Alerts
        self.assertIn("Task A", out)
        self.assertIn("Task B -> Blocked by: aa-1111", out)

        # Now mark A as closed
        task_cli_workbench = __import__("task_cli_workbench")
        task_cli_workbench.state("aa-1111", "closed")

        # Re-hydrate to reflect new json state in db
        if os.path.exists(task_db.DB_FILE):
             os.remove(task_db.DB_FILE) # force rebuild since python's file mtime precision can cause issues in fast tests
        task_db.hydrate_if_needed()

        captured_out2 = io.StringIO()
        sys.stdout = captured_out2
        task_cli_report.report()
        sys.stdout = sys.__stdout__

        out2 = captured_out2.getvalue()
        # Task B is no longer blocked by an open task. Task A shouldn't show because it's closed
        self.assertNotIn("aa-1111] Task A", out2) # Closed tasks are not fetched in report
        self.assertIn("bb-2222] Task B", out2) # Should now be unblocked!

    def test_git_union_merge(self):
        """Git Union Merge Test: Mock two separate comments on same task, appended, and assert sync reconciles them."""
        # Initial task
        task = {
            "task_id": "cc-3333", "status": "open", "priority_score": 1.0,
            "project": "test", "title": "Task C", "description": "C",
            "tags": [], "blocked_by": [], "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z", "raw_input": "C", "history": [], "comments": []
        }

        # Simulating Git Union Merge: issues.jsonl has TWO lines for cc-3333, one from branch A, one from B
        task_a = dict(task)
        task_a["updated_at"] = "2023-01-02T00:00:00Z"
        task_a["comments"] = [{"comment_id": "c1", "timestamp": "2023-01-02T00:00:00Z", "author": "u1", "text": "Comment 1"}]

        task_b = dict(task)
        task_b["updated_at"] = "2023-01-03T00:00:00Z" # Newer
        task_b["comments"] = [{"comment_id": "c2", "timestamp": "2023-01-03T00:00:00Z", "author": "u2", "text": "Comment 2"}]

        with open(task_db.ISSUES_FILE, 'w') as f:
            f.write(json.dumps(task_a) + "\n")
            f.write(json.dumps(task_b) + "\n")

        task_sync.sync_issues()

        # Read back
        with open(task_db.ISSUES_FILE, 'r') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1, "Should have synced into a single row")
        synced = json.loads(lines[0])

        # Timestamps means task_b properties win
        self.assertEqual(synced["updated_at"], "2023-01-03T00:00:00Z")
        self.assertEqual(len(synced["comments"]), 2, "Comments should be unioned")
        self.assertEqual(synced["comments"][0]["comment_id"], "c1", "Should be sorted chronologically")
        self.assertEqual(synced["comments"][1]["comment_id"], "c2")

if __name__ == '__main__':
    unittest.main()
