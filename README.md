# Distributed Task Management CLI

A lightweight, local, Git-tracked task management system. It uses an append-only JSONL event sourcing model with a SQLite read-cache to provide seamless task management across distributed Git branches.

## Architecture

- **Primary Source of Truth**: `.tasks/issues.jsonl` (Append-only JSONL log tracked in Git).
- **Read Cache**: `.tasks/db.sqlite` (Auto-hydrated SQLite database for querying tasks).
- **Git Integration**: `.gitattributes` uses Git's native union merge driver on the JSONL file to merge concurrent actions deterministically.

## Installation & Setup

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Initialize the workspace (if starting from scratch):
   ```bash
   make init
   ```

## Usage

You can run the CLI via `./task_cli.py <command>`.

### 1. Capture Client (Tier 1)

Capture raw task input instantaneously. This will append a placeholder JSON structure directly to the tracking log.

```bash
./task_cli.py capture "Fix SPI memory leak #network #bug"
```

### 2. Interactive Workbench (Tier 2)

Manage tasks via standard commands.

- **Search** for tasks by keywords or tags:
  ```bash
  ./task_cli.py search "memory"
  ```

- **Comment** on an existing task:
  ```bash
  ./task_cli.py comment <task_id> "Buffer allocations reviewed"
  ```

- **State Changes**:
  Change a task state (`open`, `in_progress`, `blocked`, `deferred`, `closed`).
  ```bash
  ./task_cli.py state <task_id> in_progress
  ```

### 3. Agent Reporter (Tier 3)

View a formatted Markdown progress report summarizing active priorities and blockers.

```bash
./task_cli.py report
```

### AI Agent Integration (Bulk Triage)

External AI Agents (like Copilot CLI or Gemini CLI) can interface with the system for triage through the bulk import/export commands:

- **Export Tasks**: Download a JSON array of tasks (e.g. ones that are `open` or un-triaged):
  ```bash
  ./task_cli.py export --status open > to_triage.json
  ```
- **Import Tasks**: Once the AI agent has modified the JSON array (setting tags, calculating Urgency Scores), the updated JSON is imported back in:
  ```bash
  ./task_cli.py import to_triage.json
  ```

### Synchronization

- **Sync (Conflict Resolution)**: When merging branches, git `union` merge might create multiple JSON lines for the same `task_id`. Run `sync` to deterministically merge them (resolving history, comments, and priority statuses chronologically).
  ```bash
  ./task_cli.py sync
  ```

## Testing

Run the test suite to verify the application:

```bash
make test
```