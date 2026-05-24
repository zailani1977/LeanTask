import unittest
import time
import os
import json
import shutil
from unittest.mock import patch

import task_cli_submit
import task_db
import task_sync
from task_cli_workbench import _update_task_in_jsonl
import task_cli_bulk

class TestTaskCLI(unittest.TestCase):

    def setUp(self):
        # Fresh test workspace
        import gc
        gc.collect()
        if os.path.exists(".tasks"):
            shutil.rmtree(".tasks")
        os.makedirs(".tasks")

        open(task_db.ISSUES_FILE, 'w', encoding='utf-8').close()

    def test_latency_and_submit(self):
        """Latency Test: Assert that the submit script appends a valid json to issues.jsonl in under 15ms."""
        start = time.time()
        task_cli_submit.submit("Fix SPI memory leak #network #bug")
        end = time.time()
        duration = (end - start) * 1000 # ms
        self.assertLess(duration, 15.0, f"Submit took {duration}ms, which is >= 15ms")

        with open(task_db.ISSUES_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

        # Verify it's a valid JSON with placeholder struct
        task = json.loads(lines[0])
        self.assertEqual(task["status"], "open")
        self.assertEqual(task["priority_score"], 0.0)
        self.assertIn("Fix SPI memory leak", task["raw_input"])

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
                "due_date": None,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "raw_input": "raw",
                "history": [],
                "comments": []
            })

        with open(task_db.ISSUES_FILE, 'w', encoding='utf-8') as f:
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
            "tags": [], "blocked_by": [], "due_date": None, "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z", "raw_input": "A", "history": [], "comments": []
        }
        task_b = {
            "task_id": "bb-2222", "status": "open", "priority_score": 4.0,
            "project": "test", "title": "Task B", "description": "B",
            "tags": [], "blocked_by": ["aa-1111"], "due_date": None, "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z", "raw_input": "B", "history": [], "comments": []
        }
        with open(task_db.ISSUES_FILE, 'w', encoding='utf-8') as f:
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
        import gc
        gc.collect()
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
            "tags": [], "blocked_by": [], "due_date": None, "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z", "raw_input": "C", "history": [], "comments": []
        }

        # Simulating Git Union Merge: issues.jsonl has TWO lines for cc-3333, one from branch A, one from B
        task_a = dict(task)
        task_a["updated_at"] = "2023-01-02T00:00:00Z"
        task_a["comments"] = [{"comment_id": "c1", "timestamp": "2023-01-02T00:00:00Z", "author": "u1", "text": "Comment 1"}]

        task_b = dict(task)
        task_b["updated_at"] = "2023-01-03T00:00:00Z" # Newer
        task_b["comments"] = [{"comment_id": "c2", "timestamp": "2023-01-03T00:00:00Z", "author": "u2", "text": "Comment 2"}]

        with open(task_db.ISSUES_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps(task_a) + "\n")
            f.write(json.dumps(task_b) + "\n")

        task_sync.sync_issues()

        # Read back
        with open(task_db.ISSUES_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1, "Should have synced into a single row")
        synced = json.loads(lines[0])

        # Timestamps means task_b properties win
        self.assertEqual(synced["updated_at"], "2023-01-03T00:00:00Z")
        self.assertEqual(len(synced["comments"]), 2, "Comments should be unioned")
        self.assertEqual(synced["comments"][0]["comment_id"], "c1", "Should be sorted chronologically")
        self.assertEqual(synced["comments"][1]["comment_id"], "c2")

    def test_bulk_export_import(self):
        """Test the bulk API by exporting, modifying the json, and importing it back."""
        # Setup initial task
        task = {
            "task_id": "dd-4444", "status": "open", "priority_score": 0.0,
            "project": "untriaged", "title": "Bulk Test", "description": "Need tags",
            "tags": [], "blocked_by": [], "due_date": None, "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z", "raw_input": "Bulk Test", "history": [], "comments": []
        }
        with open(task_db.ISSUES_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps(task) + "\n")

        # Rehydrate DB
        task_db.hydrate_if_needed()

        import io
        import sys

        # Test Export
        captured_out = io.StringIO()
        sys.stdout = captured_out
        task_cli_bulk.export_tasks()
        sys.stdout = sys.__stdout__

        exported_json_str = captured_out.getvalue()
        exported_tasks = json.loads(exported_json_str)

        self.assertEqual(len(exported_tasks), 1)
        self.assertEqual(exported_tasks[0]["task_id"], "dd-4444")

        # AI modifies task
        exported_tasks[0]["priority_score"] = 4.5
        exported_tasks[0]["tags"] = ["#ai", "#triaged"]
        exported_tasks[0]["updated_at"] = "2023-01-02T00:00:00Z" # Newer

        # Test Import
        with open(".tasks/ai_triage.json", "w", encoding='utf-8') as f:
            json.dump(exported_tasks, f)

        task_cli_bulk.import_tasks(".tasks/ai_triage.json")

        # Re-hydrate to ensure DB caught the new json line
        import gc
        gc.collect()
        if os.path.exists(task_db.DB_FILE):
             os.remove(task_db.DB_FILE)
        task_db.hydrate_if_needed()

        # Check if issues.jsonl merged it properly
        with open(task_db.ISSUES_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1, "Sync should have resolved duplicates")
        synced = json.loads(lines[0])

        self.assertEqual(synced["priority_score"], 4.5)
        self.assertCountEqual(synced["tags"], ["#ai", "#triaged"])
        self.assertEqual(synced["updated_at"], "2023-01-02T00:00:00Z")

if __name__ == '__main__':
    unittest.main()
