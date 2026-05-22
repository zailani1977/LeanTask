#!/usr/bin/env python3
import sys
import argparse

from task_cli_capture import capture
from task_cli_workbench import search, comment, state, due, list_tasks
from task_cli_report import report
from task_sync import sync_issues
from task_cli_bulk import export_tasks, import_tasks

def main():
    parser = argparse.ArgumentParser(description="Distributed Task Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # capture
    capture_parser = subparsers.add_parser("capture", help="Capture raw text task")
    capture_parser.add_argument("text", type=str, help="Raw input string")

    # search
    search_parser = subparsers.add_parser("search", help="Search tasks")
    search_parser.add_argument("keyword", type=str, help="Search keyword")

    # comment
    comment_parser = subparsers.add_parser("comment", help="Add a comment to a task")
    comment_parser.add_argument("task_id", type=str)
    comment_parser.add_argument("text", type=str)

    # state
    state_parser = subparsers.add_parser("state", help="Change state of a task")
    state_parser.add_argument("task_id", type=str)
    state_parser.add_argument("state", type=str, choices=["open", "in_progress", "blocked", "deferred", "closed"])

    # due
    due_parser = subparsers.add_parser("due", help="Update the due date of a task")
    due_parser.add_argument("task_id", type=str)
    due_parser.add_argument("date", type=str, help="Due date (e.g. YYYY-MM-DD)")

    # list
    list_parser = subparsers.add_parser("list", help="List tasks by status")
    list_parser.add_argument("status", type=str, choices=["all", "open", "in_progress", "blocked", "deferred", "closed"], help="Task status to filter by")

    # report
    subparsers.add_parser("report", help="Print daily report")

    # sync
    subparsers.add_parser("sync", help="Sync/resolve duplicate tasks in issues.jsonl")

    # export
    export_parser = subparsers.add_parser("export", help="Export tasks as JSON array")
    export_parser.add_argument("--status", type=str, help="Filter by status (e.g. open)")

    # import
    import_parser = subparsers.add_parser("import", help="Import tasks from JSON array file or stdin")
    import_parser.add_argument("file", type=str, nargs='?', default="-", help="Path to JSON file or - for stdin")

    args = parser.parse_args()

    if args.command == "capture":
        capture(args.text)
    elif args.command == "search":
        search(args.keyword)
    elif args.command == "comment":
        comment(args.task_id, args.text)
    elif args.command == "state":
        state(args.task_id, args.state)
    elif args.command == "due":
        due(args.task_id, args.date)
    elif args.command == "list":
        list_tasks(args.status)
    elif args.command == "report":
        report()
    elif args.command == "sync":
        sync_issues()
    elif args.command == "export":
        export_tasks(args.status)
    elif args.command == "import":
        import_tasks(args.file)

if __name__ == "__main__":
    main()
