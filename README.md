# Distributed Task Management CLI

A lightweight, local, Git-tracked task management system. It uses an append-only JSONL event sourcing model with a SQLite read-cache to provide seamless task management across distributed Git branches.

## Architecture

- **Primary Source of Truth**: `.tasks/issues.jsonl` (Append-only JSONL log tracked in Git).
- **Raw Input Buffer**: `.tasks/capture.jsonl` (Zero-latency buffer for capturing raw input, offline capable).
- **Read Cache**: `.tasks/db.sqlite` (Auto-hydrated SQLite database for querying tasks).
- **Git Integration**: `.gitattributes` uses Git's native union merge driver on the JSONL files to merge concurrent actions deterministically.

## Installation & Setup

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Initialize the workspace (if starting from scratch):
   ```bash
   make init
   ```
   This creates the `.tasks/` folder, the `.jsonl` files, and the `.gitattributes` configuration.

## Usage

You can run the CLI via `./task_cli.py <command>` or `make run ARGS="<command>"`.

### 1. Capture Client (Tier 1)

Capture raw task input instantaneously.

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

### Background Worker & Synchronization

- **AI Triage Loop**: Parses raw `.tasks/capture.jsonl` strings into structured JSON, calculates urgency, writes to `issues.jsonl`, and hydrates the SQLite cache. Run it as a daemon, or pass `--once` for a single sweep.
  ```bash
  ./task_cli.py loop --once
  ```

- **Sync (Conflict Resolution)**: When merging branches, git `union` merge might create multiple JSON lines for the same `task_id`. Run `sync` to deterministically merge them (resolving history, comments, and priority statuses chronologically).
  ```bash
  ./task_cli.py sync
  ```

## Testing

Run the test suite to verify latency, rehydration, reporting logic, and simulated Git union conflict resolution:

```bash
make test
```
