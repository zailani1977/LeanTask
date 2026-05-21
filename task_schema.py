import json
import jsonschema

TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "pattern": "^[a-z0-9]{2}-[a-z0-9]{4}$"
        },
        "parent_id": {
            "type": ["string", "null"]
        },
        "status": {
            "type": "string",
            "enum": ["open", "in_progress", "blocked", "deferred", "closed"]
        },
        "priority_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 5.0
        },
        "project": {
            "type": "string"
        },
        "title": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "blocked_by": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "created_at": {
            "type": "string",
            "format": "date-time"
        },
        "updated_at": {
            "type": "string",
            "format": "date-time"
        },
        "raw_input": {
            "type": "string"
        },
        "history": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string", "format": "date-time"},
                    "author": {"type": "string"},
                    "field": {"type": "string"},
                    "old_value": {},
                    "new_value": {}
                },
                "required": ["timestamp", "author", "field", "old_value", "new_value"]
            }
        },
        "comments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "comment_id": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "author": {"type": "string"},
                    "text": {"type": "string"}
                },
                "required": ["comment_id", "timestamp", "author", "text"]
            }
        }
    },
    "required": [
        "task_id", "status", "priority_score", "project", "title",
        "description", "tags", "blocked_by", "created_at", "updated_at",
        "raw_input", "history", "comments"
    ]
}

def validate_task(task_obj):
    jsonschema.validate(instance=task_obj, schema=TASK_SCHEMA)
    return True
