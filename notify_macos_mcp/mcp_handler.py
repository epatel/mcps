"""MCP JSON-RPC protocol handler for Notify macOS MCP."""

import json
import os
import subprocess

TOOL_DEFINITIONS = [
    {
        "name": "notify",
        "description": "Post a macOS notification.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Notification title",
                },
                "message": {
                    "type": "string",
                    "description": "Notification body text",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Optional subtitle",
                },
                "sound": {
                    "type": "string",
                    "description": (
                        'Optional sound name (e.g. "default", "Basso", "Blow", '
                        '"Bottle", "Frog", "Funk", "Glass", "Hero", "Morse", '
                        '"Ping", "Pop", "Purr", "Sosumi", "Submarine", "Tink")'
                    ),
                },
            },
            "required": ["title", "message"],
        },
    },
]


def _find_terminal_notifier() -> str:
    """Find terminal-notifier, checking PATH and common locations."""
    import shutil
    path = shutil.which("terminal-notifier")
    if path:
        return path
    import glob
    candidates = glob.glob(os.path.expanduser("~/.rbenv/versions/*/bin/terminal-notifier"))
    if candidates:
        return candidates[-1]
    raise FileNotFoundError("terminal-notifier not found. Install with: brew install terminal-notifier")


def _send_notification(title: str, message: str, subtitle: str | None = None, sound: str | None = None) -> None:
    """Post a macOS notification via terminal-notifier."""
    binary = _find_terminal_notifier()
    args = [binary, "-title", title, "-message", message]
    if subtitle:
        args.extend(["-subtitle", subtitle])
    args.extend(["-sound", sound or "default"])
    subprocess.run(args, check=True, capture_output=True, text=True)


class McpHandler:
    def handle(self, msg: dict) -> dict | None:
        """Handle a JSON-RPC message. Returns response dict or None for notifications."""
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            return self._respond(req_id, {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "notify-macos-mcp", "version": "1.0.0"},
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

        if name == "notify":
            try:
                _send_notification(
                    title=args["title"],
                    message=args["message"],
                    subtitle=args.get("subtitle"),
                    sound=args.get("sound"),
                )
                return self._tool_result(req_id, json.dumps({
                    "status": "sent",
                    "title": args["title"],
                }))
            except subprocess.CalledProcessError as e:
                return self._tool_error(req_id, f"Failed to send notification: {e.stderr or e}")
            except FileNotFoundError:
                return self._tool_error(req_id, "terminal-notifier not found. Install with: brew install terminal-notifier")

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
