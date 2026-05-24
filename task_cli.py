#!/usr/bin/env python3
import sys
import argparse

from task_cli_submit import submit
from task_cli_workbench import search, comment, state, due, list_tasks, view, priority, project, title, description, tags, blocked_by
from task_cli_report import report
from task_sync import sync_issues
from task_cli_bulk import export_tasks, import_tasks
from task_cli_clean import clean

def main():
    parser = argparse.ArgumentParser(description="Distributed Task Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # submit
    submit_parser = subparsers.add_parser("submit", help="Submit raw text task")
    submit_parser.add_argument("text", type=str, help="Raw input string")

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

    # priority
    priority_parser = subparsers.add_parser("priority", help="Update the priority score of a task (0.0 to 5.0)")
    priority_parser.add_argument("task_id", type=str)
    priority_parser.add_argument("score", type=float, help="Priority score (e.g., 3.5)")

    # project
    project_parser = subparsers.add_parser("project", help="Update the project of a task (e.g. to triage it)")
    project_parser.add_argument("task_id", type=str)
    project_parser.add_argument("project_name", type=str, help="Name of the project")

    # title
    title_parser = subparsers.add_parser("title", help="Update the title of a task")
    title_parser.add_argument("task_id", type=str)
    title_parser.add_argument("text", type=str, help="New title text")

    # description
    desc_parser = subparsers.add_parser("description", help="Update the description of a task")
    desc_parser.add_argument("task_id", type=str)
    desc_parser.add_argument("text", type=str, help="New description text")

    # tags
    tags_parser = subparsers.add_parser("tags", help="Update the tags of a task")
    tags_parser.add_argument("task_id", type=str)
    tags_parser.add_argument("tags", nargs="*", type=str, help="New tags list")

    # blocked_by
    blocked_by_parser = subparsers.add_parser("blocked_by", help="Update the blocked_by of a task")
    blocked_by_parser.add_argument("task_id", type=str)
    blocked_by_parser.add_argument("blocked_by", nargs="*", type=str, help="New blocked_by task IDs")

    # due
    due_parser = subparsers.add_parser("due", help="Update the due date of a task")
    due_parser.add_argument("task_id", type=str)
    due_parser.add_argument("date", type=str, help="Due date (e.g. YYYY-MM-DD)")

    # list
    list_parser = subparsers.add_parser("list", help="List tasks by status")
    list_parser.add_argument("status", type=str, choices=["all", "open", "in_progress", "blocked", "deferred", "closed"], help="Task status to filter by")

    # view
    view_parser = subparsers.add_parser("view", help="View a specific task and its comments")
    view_parser.add_argument("task_id", type=str)

    # help
    subparsers.add_parser("help", help="Show this help message")

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

    # clean
    clean_parser = subparsers.add_parser("clean", help="Clean the database/workspace")
    clean_parser.add_argument("--hard", action="store_true", help="Delete the entire .tasks/ directory (hard wipe)")

    args = parser.parse_args()

    if args.command == "submit":
        submit(args.text)
    elif args.command == "search":
        search(args.keyword)
    elif args.command == "comment":
        comment(args.task_id, args.text)
    elif args.command == "state":
        state(args.task_id, args.state)
    elif args.command == "priority":
        priority(args.task_id, args.score)
    elif args.command == "project":
        project(args.task_id, args.project_name)
    elif args.command == "title":
        title(args.task_id, args.text)
    elif args.command == "description":
        description(args.task_id, args.text)
    elif args.command == "tags":
        tags(args.task_id, args.tags)
    elif args.command == "blocked_by":
        blocked_by(args.task_id, args.blocked_by)
    elif args.command == "due":
        due(args.task_id, args.date)
    elif args.command == "list":
        list_tasks(args.status)
    elif args.command == "view":
        view(args.task_id)
    elif args.command == "report":
        report()
    elif args.command == "sync":
        sync_issues()
    elif args.command == "export":
        export_tasks(args.status)
    elif args.command == "import":
        import_tasks(args.file)
    elif args.command == "clean":
        clean(args.hard)
    elif args.command == "help":
        parser.print_help()

if __name__ == "__main__":
    main()
