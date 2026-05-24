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

### GUI Dashboard
A graphical dashboard (beautified with **CustomTkinter**) is available to view and interact with tasks without the CLI.

> **Note:** The GUI requires `customtkinter`, which is listed in `requirements.txt`. Make sure to install it via `pip install -r requirements.txt`. Additionally, the base `tkinter` package may be omitted by default on some Linux distributions. If you get a `ModuleNotFoundError: No module named 'tkinter'` error, install it via your package manager (e.g., `sudo apt-get install python3-tk` on Ubuntu/Debian).

```bash
python gui.py
```
- **Dashboard**: Displays a list of tasks with their IDs, statuses, priorities, projects, due dates, and titles.
- **Submit Task**: Click the "Submit Task" button to quickly add a raw text task.
- **Task Details & Updates**: Double-click any task in the list to open its details window. From there, you can view its full description and easily update fields such as status, priority, or tags. Click "Update Task" to apply changes.

### 1. Submit Client (Tier 1)

Submit raw task input instantaneously. This will append a placeholder JSON structure directly to the tracking log.

```bash
./task_cli.py submit "Fix SPI memory leak #network #bug"
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

- **Set Due Date**:
  Update a task's due date.
  ```bash
  ./task_cli.py due <task_id> "2024-12-31T23:59:59Z"
  ```

- **List Tasks**:
  List tasks filtered by a specific status, or view all tasks.
  ```bash
  ./task_cli.py list open
  ./task_cli.py list all
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

### Maintenance / Clean

- **Clean Cache**: Delete the local SQLite read-cache database (`.tasks/db.sqlite`). It will be automatically rebuilt the next time a command is executed.
  ```bash
  ./task_cli.py clean
  ```

- **Hard Clean**: Delete the entire `.tasks/` directory, wiping all logs and the database. Use with caution!
  ```bash
  ./task_cli.py clean --hard
  ```

## Testing

Run the test suite to verify the application:

```bash
make test
```