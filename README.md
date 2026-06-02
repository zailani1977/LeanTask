# LeanTask: Distributed Git-Tracked Task Management CLI

LeanTask is a lightweight, decentralized task management system designed to run entirely locally while integrating seamlessly with distributed version control systems like Git. 

It uses an **append-only JSONL (JSON Lines) event sourcing model** as the primary source of truth, complemented by an **auto-hydrating SQLite read cache** for high-performance querying and a **custom Tkinter graphical dashboard** for visual interaction.

---

## Key Features & Core Philosophy

- **Git-Native & Collaborative**: Standard project issue trackers (like Jira or GitHub Issues) require central databases and internet connectivity. LeanTask stores all tasks inside your project repository under `.tasks/issues.jsonl`. 
- **Deterministic Merge Conflict Resolution**: By using Git's native `union` merge strategy and LeanTask's deterministic reconciliation engine, multiple developers can modify or create tasks offline and merge branches without manual conflicts.
- **Zero-Latency Capture**: Task creation is optimized for speed (<15ms latency) by appending directly to the JSONL log, making it perfect for instantaneous capture from scripts, hotkeys, or shell aliases.
- **Auto-Hydrating Cache**: High-performance querying, keyword searches, and dependency sorting are powered by a local SQLite read cache (`.tasks/db.sqlite`) that automatically rebuilds itself when it detects the JSONL log is newer.
- **Beautiful Graphical Dashboard**: A sleek desktop app built with `customtkinter` allows you to visualize, filter, search, comment on, and manage tasks without touching the command line.

---

## Architecture Overview

```
                        +----------------------+
                        |   User Input (CLI)   |
                        +----------+-----------+
                                   |
                                   v
+------------------+     +---------+-----------+     +------------------+
|  Custom Tkinter  |---->|   task_cli.py (App) |<----|  External AI     |
|   GUI (gui.py)   |     +---------+-----------+     |  (Bulk Import)   |
+------------------+               |                 +------------------+
                                   v
                        +----------+-----------+
                        |  .tasks/issues.jsonl |  <--- Git-tracked Source of Truth
                        +----------+-----------+
                                   |
                           (Auto-Hydration)
                                   v
                        +----------+-----------+
                        |  .tasks/db.sqlite    |  <--- SQLite Read Cache
                        +----------------------+
```

1. **Source of Truth (`.tasks/issues.jsonl`)**: An append-only log of tasks. Each line contains a complete JSON representation of a task.
2. **Rehydration Layer ([task_db.py](task_db.py))**: Instantly compares file modification timestamps. If `issues.jsonl` is newer than `db.sqlite`, the cache is wiped, validated against the JSON Schema, and rebuilt in SQLite.
3. **Union Merging & Reconciliation ([task_sync.py](task_sync.py))**: Merges duplicate records for the same task using status precedence overrides (e.g. `closed` > `open`) and chronological sorting of history/comments.

---

## Installation & Setup

### 1. Setup Virtual Environment (Recommended)
Before installing dependencies, it is recommended to run LeanTask inside a Python virtual environment:

* **On Linux/macOS**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
* **On Windows**:
  Open Command Prompt or PowerShell and run:
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate
  ```

### 2. Install Dependencies
Make sure you have Python 3.8+ installed. Install the Python requirements:
```bash
pip install -r requirements.txt
```

> **Note for Linux Users**: The graphical dashboard requires Python's native `tkinter` bindings. If you receive a `ModuleNotFoundError: No module named 'tkinter'`, install it via your distribution's package manager:
> - **Ubuntu/Debian**: `sudo apt-get install python3-tk`
> - **Fedora/CentOS/RHEL**: `sudo dnf install python3-tkinter`
> - **Arch Linux**: `sudo pacman -S tk`

### 3. Initialize the Workspace
If initializing a new repository or starting fresh, initialize the task workspace:

* **Using Python (Cross-platform)**:
  You can initialize the workspace directly without using `make`:
  ```bash
  python task_cli.py init
  ```
* **Using Make / Nmake**:
  If you are on Windows and wish to use the `Makefile`, execute the commands inside a **Developer Command Prompt** or **Developer PowerShell** (which provides path bindings to your build tools). Both `make` and `nmake` are supported:
  ```bash
  make init
  # or
  nmake init
  ```

This sets up the `.tasks/` directory and configures Git to use the `union` merge driver for `.tasks/issues.jsonl` via `.gitattributes`.

### 4. Running Commands

* **Unix/macOS**:
  You can run commands directly (e.g. `./task_cli.py list open`).
* **Windows**:
  Run commands prefixed with `python` (e.g. `python task_cli.py list open`).

* **Deactivating the Virtual Environment**:
  Once you are done working, exit the virtual environment by running:
  ```bash
  deactivate
  ```

---

## 5-Minute Quick Start Tutorial

Let's walk through a typical workflow:

### Step 1: Submit a Task
Create a new task instantaneously:
```bash
./task_cli.py submit "Fix memory leak in SPI driver #network #bug"
```
*Output:* Prints a unique task ID (e.g., `ef-a48b`).

### Step 2: List and Find the Task
List all open tasks:
```bash
./task_cli.py list open
```
Search for tasks mentioning "memory":
```bash
./task_cli.py search "memory"
```

### Step 3: Inspect Task Details
View the full details and comments of your task:
```bash
./task_cli.py view ef-a48b
```

### Step 4: Modify Task Attributes
Update priority, project, and description:
```bash
./task_cli.py priority ef-a48b 4.5
./task_cli.py project ef-a48b "Firmware"
./task_cli.py description ef-a48b "Investigate circular buffer allocation leak under high SPI traffic."
```

### Step 5: Add a Comment
Collaborate or record progress notes:
```bash
./task_cli.py comment ef-a48b "Reviewed buffer allocations; issue seems to be in spi_dma.c line 142."
```

### Step 6: Mark as In Progress or Blocked
Update status states:
```bash
./task_cli.py state ef-a48b in_progress
```

### Step 7: Launch the GUI
Prefer a visual workflow? Fire up the customtkinter dashboard:
```bash
python gui.py
```
Double-click any task in the list to update its properties, add tags, or post comments.

On **Windows**, you can also use the included hidden launcher:
1. Double-click [`LeanTask GUI.vbs`](LeanTask%20GUI.vbs) to start the app without opening a console window.
2. The launcher activates `venv`, runs `gui.py` with `pythonw`, then deactivates the environment when the GUI closes.
3. If you need visible startup errors for troubleshooting, run [`launch_gui.cmd`](launch_gui.cmd) instead.

---

## CLI Command Reference Table

All commands are executed via [task_cli.py](task_cli.py).

| Command | Usage | Description |
| :--- | :--- | :--- |
| `submit` | `./task_cli.py submit "<text>"` | Submits raw input and creates a task with a randomized ID. |
| `search` | `./task_cli.py search "<keyword>"` | Searches titles, descriptions, and tags in the SQLite cache. |
| `comment` | `./task_cli.py comment <task_id> "<comment>"` | Appends a comment to the task's comment array. |
| `state` | `./task_cli.py state <task_id> <state>` | Updates status (`open`, `in_progress`, `blocked`, `deferred`, `closed`). |
| `priority` | `./task_cli.py priority <task_id> <score>` | Sets a priority score between `0.0` and `5.0`. |
| `project` | `./task_cli.py project <task_id> "<project>"` | Assigns the task to a specific project module. |
| `title` | `./task_cli.py title <task_id> "<title>"` | Updates the title of the task. |
| `description`| `./task_cli.py description <task_id> "<desc>"` | Updates the detailed description. |
| `tags` | `./task_cli.py tags <task_id> <tag1> [tag2 ...]` | Sets tags (e.g. `bug` `feature`). |
| `blocked_by` | `./task_cli.py blocked_by <task_id> <dep_id1> ...`| Lists parent task IDs blocking this task. |
| `due` | `./task_cli.py due <task_id> "YYYY-MM-DD"` | Sets a due date using date-only format (for example, `2026-06-05`). |
| `list` | `./task_cli.py list <status>` | Lists tasks by status, or use `all` to see everything. |
| `view` | `./task_cli.py view <task_id>` | Prints the task details, edit history, and comments. |
| `report` | `./task_cli.py report` | Generates a daily markdown progress report. |
| `sync` | `./task_cli.py sync` | Deteministically merges duplicate tasks in `issues.jsonl`. |
| `export` | `./task_cli.py export [--status <status>]` | Exports tasks as a JSON array (perfect for AI agents). |
| `import` | `./task_cli.py import <file_path>` | Imports a JSON array of tasks and automatically syncs them. |
| `clean` | `./task_cli.py clean [--hard]` | Deletes SQLite cache (soft) or the entire `.tasks/` dir (hard). |
| `help` | `./task_cli.py help` | Displays CLI syntax help. |

---

## Detailed Command Documentation

### Task Capture & Creation
- **`submit`**: Designed to be instantaneous (<15ms) to prevent interrupting development flow. It creates a task matching the JSON Schema with `status="open"`, `priority_score=0.0`, and `project="untriaged"`.
  ```bash
  ./task_cli.py submit "Fix SPI buffer overflow"
  ```

### Task Modification
- **`state`**: Transitions a task between `open`, `in_progress`, `blocked`, `deferred`, and `closed`.
- **`priority`**: Sets priority levels. Accepts floats `0.0` (lowest) to `5.0` (highest).
- **`due`**: Stores due dates in `YYYY-MM-DD` format. If you paste a full ISO timestamp, LeanTask normalizes it to the date only.
- **`blocked_by`**: Declares dependencies. If task `ab-1234` is blocked by `xy-5678`, it will show up as blocked in daily reports until `xy-5678` is closed.
  ```bash
  ./task_cli.py blocked_by ab-1234 xy-5678
  ```

### Synthesized Reports
- **`report`**: The agent-oriented report splits active issues into:
  1. **The Daily Matrix**: Active, unblocked tasks sorted by priority score (descending).
  2. **The Triage Queue**: Unprioritized tasks (open tasks with score `0.0`).
  3. **Blocker Alerts**: Active tasks that are blocked by one or more incomplete tasks.

### AI Agent Integration & Bulk Operations
LeanTask is fully compatible with AI agents for bulk triage or automated task enrichment. See [BULK_RETRIEVAL_DOCS.md](BULK_RETRIEVAL_DOCS.md) for detailed JSON schemas and pipeline examples.

---

## Graphical User Interface (GUI) Guide

LeanTask includes a desktop dashboard app built with **CustomTkinter** that provides a complete visual alternative to the command-line interface.

### Running the GUI
To start the dashboard, execute:
```bash
python gui.py
```

### GUI Architecture & Features

#### 1. Main Dashboard Window
- **Overview**: Lists all current tasks inside a database grid, providing a birds-eye view of your task space.
- **Task Grid Columns**: Shows columns for `ID`, `Status`, `Priority`, `Project`, `Due`, and `Title`.
- **Status Color-Coding**:
  - **Green** (Background: `#d4edda`): `open` tasks.
  - **Blue** (Background: `#cce5ff`): `in_progress` tasks.
  - **Red** (Background: `#f8d7da`): `blocked` tasks.
  - **Yellow** (Background: `#fff3cd`): `deferred` tasks.
  - **Grey** (Background: `#e2e3e5`): `closed` tasks.
- **Refresh Dashboard**: The **Refresh** button synchronizes tasks with `.tasks/issues.jsonl` (running the conflict-resolution engine) and reloads the grid from the SQLite cache.
- **Create a Task**: The **Submit Task** button prompts for a raw string (e.g. `Configure UART baudrate #hardware`) and appends the new task to the log.

#### 2. Detailed Task Editing Window
- **Access**: Double-click any task in the main dashboard grid to open a dedicated task inspector window.
- **Field Editors**: Provides quick controls to edit:
  - **Title** & **Description**: Modify task summaries or details.
  - **Status Dropdown**: Switch between task states (`open`, `in_progress`, `blocked`, `deferred`, `closed`).
  - **Priority (0.0 - 5.0)**: Update priority scores.
  - **Project**: Assign tasks to modules or project namespaces.
  - **Due Date**: Manually adjust deadlines using `YYYY-MM-DD` format.
  - **Tags**: Edit tags using a comma-separated list.
  - **Update Task Button**: Clicking this writes updates to the log and auto-rehydrates the database cache.

#### 3. Integrated Collaboration Feed (Comments)
- **Overview**: Allows developers to communicate or log progress notes directly inside the task editing window.
- **Comments Log**: Displays a scrollable feed of comments sorted chronologically, showing timestamps and authors.
- **Post a Comment**: Input your comment in the text field at the bottom and click **Add** to append it to the task comment log.

---

## Testing

LeanTask has a comprehensive test suite covering database rehydration, Git union merges, conflict resolution rules, and latency benchmarks.

To execute the unit tests, simply run:
```bash
make test
```
*(or run `python -m unittest test_task_cli.py` directly)*