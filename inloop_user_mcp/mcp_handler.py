"""MCP JSON-RPC protocol handler for InLoop User MCP."""

import json
from task_store import TaskStore

TOOL_DEFINITIONS = [
    {
        "name": "send_tasks",
        "description": (
            "Send a batch of tasks for the human operator to complete. "
            "Replaces any existing task list. Each task has an id, title (supports markdown), "
            "and enabled flag. Disabled tasks appear greyed out until enabled. "
            "Opens the dashboard browser on first call. Optionally set a project title."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique task identifier"},
                            "title": {"type": "string", "description": "Task description (markdown supported)"},
                            "enabled": {"type": "boolean", "description": "Whether the task is currently actionable"},
                        },
                        "required": ["id", "title", "enabled"],
                    },
                    "description": "List of tasks to display",
                },
                "title": {
                    "type": "string",
                    "description": "Project/session title shown in the dashboard header",
                },
            },
            "required": ["tasks"],
        },
    },
    {
        "name": "add_task",
        "description": "Add a single task to the existing task list.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "enabled": {"type": "boolean"},
                    },
                    "required": ["id", "title", "enabled"],
                }
            },
            "required": ["task"],
        },
    },
    {
        "name": "enable_task",
        "description": "Enable a previously disabled task, making it actionable for the human.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ID of the task to enable"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "check_status",
        "description": (
            "Non-blocking status check. Returns status of one task (by task_id) or all tasks (if task_id omitted). "
            "Statuses: pending (disabled), enabled (waiting for human), done (completed by human)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Optional: specific task ID to check"},
            },
            "required": [],
        },
    },
    {
        "name": "wait_for_task",
        "description": (
            "Blocking wait. Returns when the human marks the task done, or when timeout expires. "
            "Default timeout: 300 seconds. Returns {status: 'done'} or {status: 'timeout'}."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ID of the task to wait for"},
                "timeout": {"type": "number", "description": "Timeout in seconds (default 300)"},
            },
            "required": ["task_id"],
        },
    },
]


class McpHandler:
    def __init__(self, store: TaskStore):
        self._store = store

    def handle(self, msg: dict) -> dict | None:
        """Handle a JSON-RPC message. Returns response dict or None for notifications."""
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            return self._respond(req_id, {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "inloop-user-mcp", "version": "1.0.0"},
            })

        if method and method.startswith("notifications/"):
            return None

        if method == "tools/list":
            return self._respond(req_id, {"tools": TOOL_DEFINITIONS})

        if method == "tools/call":
            return self._handle_tool_call(req_id, params)

        if req_id is not None:
            return self._respond(req_id, {
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            })

        return None

    def _handle_tool_call(self, req_id, params: dict) -> dict:
        name = params.get("name")
        args = params.get("arguments", {})

        if name == "send_tasks":
            result = self._store.send_tasks(args["tasks"], title=args.get("title"))
            return self._tool_result(req_id, json.dumps(result))

        if name == "add_task":
            result = self._store.add_task(args["task"])
            return self._tool_result(req_id, json.dumps(result))

        if name == "enable_task":
            result = self._store.enable_task(args["task_id"])
            if result is None:
                return self._tool_error(req_id, f"Task not found: {args['task_id']}")
            return self._tool_result(req_id, json.dumps(result))

        if name == "check_status":
            task_id = args.get("task_id")
            result = self._store.check_status(task_id)
            if result is None:
                return self._tool_error(req_id, f"Task not found: {task_id}")
            return self._tool_result(req_id, json.dumps(result))

        if name == "wait_for_task":
            timeout = args.get("timeout", 300)
            result = self._store.wait_for_task(args["task_id"], timeout=timeout)
            return self._tool_result(req_id, json.dumps(result))

        return self._tool_error(req_id, f"Unknown tool: {name}")

    def _respond(self, req_id, result: dict) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _tool_result(self, req_id, text: str) -> dict:
        return self._respond(req_id, {
            "content": [{"type": "text", "text": text}],
        })

    def _tool_error(self, req_id, message: str) -> dict:
        return self._respond(req_id, {
            "content": [{"type": "text", "text": message}],
            "isError": True,
        })
