# Technical Documentation

This document explains the internal mechanics of the Distributed Task Management CLI, detailing the responsibilities and logic of each core component.

---

## 1. Environment Setup & Data Layer

### Event-Sourced Storage
The system relies on `.tasks/issues.jsonl` as the primary source of truth. JSONL (JSON Lines) is chosen over a traditional relational database because it is append-only and natively Git-trackable. By appending serialized JSON objects per line, the system avoids complex merge conflicts inherent to tracking binary database files in Git.

### SQLite Auto-Hydration (`task_db.py`)
To enable fast, complex querying (like searching by keyword or computing blocker graphs), the system builds a local SQLite cache (`db.sqlite`).
- **Lazy Initialization:** Every time the application requests a database connection (`get_connection()`), the system compares the modification timestamp (`mtime`) of `issues.jsonl` against `db.sqlite`.
- **Rebuilding:** If `issues.jsonl` is newer, it means external changes (like a Git pull or a raw capture) occurred. The system instantly clears the SQLite tables, re-reads the JSON lines, strictly validates them against the JSON Schema using the `jsonschema` library, and rebuilds the tables.

### Git Union Merging
`.gitattributes` configures Git to use the native `union` merge strategy for `issues.jsonl`. If two branches simultaneously add tasks, Git will automatically append both lines chronologically without prompting the user for a manual merge conflict resolution. Duplicate `task_id` rows are then merged gracefully via the conflict resolution logic.

---

## 2. Capture Client (Tier 1) (`task_cli_capture.py`)

**Goal:** Zero-latency task input.
When a user runs `./task_cli.py capture <text>`, it instantly generates a valid JSON Schema skeleton (with a random UUID, default placeholder status, and preserves the raw string). It appends this JSON line directly to `.tasks/issues.jsonl`. This ensures execution finishes in <15ms, completely offline.

---

## 3. Interactive Workbench (Tier 2) (`task_cli_workbench.py`)

This tier provides the standard CRUD tools to interact with tasks.

- **Search:** Uses SQL `LIKE` queries against the SQLite read-cache.
- **State Changes & Commenting:** Modifying an issue requires rewriting the `.tasks/issues.jsonl` file to maintain it as the source of truth. The updater reads the file line-by-line, applies the state change or comment (along with an audit history log), and writes back the updated JSON line. It does *not* write directly to SQLite; instead, the change to `issues.jsonl` triggers the DB to auto-hydrate on the next read.

---

## 4. Synthesized Agent Reporter (Tier 3) (`task_cli_report.py`)

**Goal:** Provide an automated, priority-sorted daily summary.
The report queries all non-closed tasks from SQLite and splits them into three categories:

1. **The Triage Queue:** New, unprioritized tasks waiting for review.
2. **Blocker Alerts:** Tasks that have an active (non-closed) blocker in their `blocked_by` array.
3. **The Daily Matrix:** Unblocked, active tasks sorted descendingly by their topological Urgency Score.

The logic dynamically cross-references blocker IDs against current task statuses, ensuring a task natively moves from "Blocker Alerts" to the "Daily Matrix" the moment its blocking parent is marked as closed.

---

## 5. Agent Bulk Operations (Triage API) (`task_cli_bulk.py`)

To facilitate on-demand AI triage (e.g. via Copilot CLI or Gemini CLI), the system allows bulk interactions instead of a background daemon loop:
- **`export`:** Outputs an array of tasks (optionally filtered by `status`) straight to `stdout` in valid JSON format. This allows an AI agent to ingest the current state of tasks needing prioritization.
- **`import`:** Accepts a JSON array (from a file or `stdin`) containing the modified tasks. The AI agent recalculates urgency scores or tags and hands them back. The script validates the payloads against the schema, appends them to `issues.jsonl`, and instantly invokes the conflict resolution sync to merge updates.

---

## 6. Conflict Resolution & Merge Automation (`task_sync.py`)

Because of Git's `union` merge strategy, two users working offline might modify the same task, resulting in two JSON lines with the identical `task_id` in `issues.jsonl`.

The `sync` command executes a deterministic reconciliation:
1. **Timestamp Dominance:** Fields generally adopt the value of the object with the newer `updated_at` timestamp.
2. **Status Precedence Overrides:** Task state transitions are strictly ranked (e.g., `closed` > `in_progress` > `open`). A `closed` status from an older timestamp will always override an `open` status from a newer timestamp to prevent regression.
3. **Log Merging:** Sub-arrays like `comments` and `history` are combined, deduplicated via unique UUIDs, and sorted purely chronologically.

The sync output rewrites `issues.jsonl` leaving only one normalized record per `task_id`.
