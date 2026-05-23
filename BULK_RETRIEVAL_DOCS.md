# Bulk Retrieval & Triage Documentation for AI Agents

The Distributed Task Management CLI features dedicated bulk commands specifically designed for ingestion, modification, and update by AI Agents (like Copilot CLI, Gemini CLI, or custom autonomous agents). These capabilities allow agents to act on multiple tasks sequentially or systematically, such as evaluating untriaged tasks, applying priority scoring, tagging them, or categorizing them into projects.

## Exporting Tasks for Reading

The `export` command outputs an array of tasks to `stdout` in valid, minified JSON format.

### Command Structure
```bash
./task_cli.py export [--status <STATUS>]
```

### Examples
- **Retrieve all tasks:**
  ```bash
  ./task_cli.py export > all_tasks.json
  ```
- **Retrieve only 'open' tasks (commonly used for triage):**
  ```bash
  ./task_cli.py export --status open > to_triage.json
  ```

### Data Schema
The exported JSON structure follows the expected schema inside the system, for example:
```json
[
  {
    "task_id": "ab-1234",
    "parent_id": null,
    "status": "open",
    "priority_score": 0.0,
    "project": "untriaged",
    "title": "Fix SPI memory leak",
    "description": "Captured raw input.",
    "tags": [],
    "blocked_by": [],
    "due_date": null,
    "created_at": "2023-10-05T14:48:00Z",
    "updated_at": "2023-10-05T14:48:00Z",
    "raw_input": "Fix SPI memory leak #network #bug",
    "history": [],
    "comments": []
  }
]
```

## Modifying Tasks

Once exported, an AI Agent can process the array. Common automated actions include:
- **Triage & Priority:** Changing `priority_score` (from 0.0 up to 5.0).
- **Categorization:** Changing `project` from `"untriaged"` to an actual module name (e.g., `"backend"`, `"frontend"`).
- **Tagging:** Parsing `raw_input` to extract hashtags into the `tags` array.
- **Refinement:** Synthesizing clearer `title` and `description` texts from the raw input.
- **Dependency Map:** Updating `blocked_by` array if a task logically depends on another `task_id`.

*Note: Whenever modifying a task, it's a good practice to update the `updated_at` timestamp with the current UTC ISO-8601 formatted time string so that the conflict-resolution system honors the agent's edits during import.*

## Importing and Syncing Changes

The `import` command accepts a modified JSON array either from a file or from `stdin`. The system parses it, validates it against the internal JSON Schema, appends the modified lines to the `.tasks/issues.jsonl` tracking log, and seamlessly syncs (resolves duplicated lines deterministically).

### Command Structure
```bash
./task_cli.py import [file_path]
```

### Examples
- **Import from a modified file:**
  ```bash
  ./task_cli.py import modified_triage.json
  ```
- **Pipeline Import (via stdin):**
  ```bash
  cat modified_triage.json | ./task_cli.py import -
  ```
- **AI Agent Direct Pipeline (conceptual):**
  ```bash
  ./task_cli.py export --status open | ai_agent_script.py | ./task_cli.py import -
  ```

## Internal Merging Logic (Sync)

Agents do not need to worry about manually maintaining database records. When `import` is called, it appends the modified JSON structures to `issues.jsonl`. Because this causes the file to temporarily contain duplicate tasks (the original capture + the agent's modified version), the `import` command implicitly runs `sync`.

The `sync` step reconciles duplicates by comparing `updated_at` timestamps—the agent's newly assigned values will override the old values, establishing the AI's triage as the current state, and the SQLite cache will dynamically auto-rehydrate for subsequent queries.
