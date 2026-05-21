#!/usr/bin/env python3
import sys
import argparse

from task_cli_capture import capture
from task_cli_workbench import search, comment, state
from task_cli_report import report
from task_loop import process_loop
from task_sync import sync_issues

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

    # report
    subparsers.add_parser("report", help="Print daily report")

    # loop
    loop_parser = subparsers.add_parser("loop", help="Run background triage loop")
    loop_parser.add_argument("--once", action="store_true", help="Run one pass and exit")

    # sync
    subparsers.add_parser("sync", help="Sync/resolve duplicate tasks in issues.jsonl")

    args = parser.parse_args()

    if args.command == "capture":
        capture(args.text)
    elif args.command == "search":
        search(args.keyword)
    elif args.command == "comment":
        comment(args.task_id, args.text)
    elif args.command == "state":
        state(args.task_id, args.state)
    elif args.command == "report":
        report()
    elif args.command == "loop":
        process_loop(run_once=args.once)
    elif args.command == "sync":
        sync_issues()

if __name__ == "__main__":
    main()
