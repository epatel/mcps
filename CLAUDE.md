# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A collection of custom MCP (Model Context Protocol) servers for Claude Code. Each server implements the MCP JSON-RPC stdio protocol manually (no SDK) in Python.

## MCP Servers

- **inloop_user_mcp** — Human-in-the-loop task dashboard. Sends tasks to a browser UI via WebSocket; the human marks them done. Uses threading (MCP stdio in a thread, asyncio web server on main loop) with a thread-safe TaskStore.
- **notify_macos_mcp** — Sends macOS notifications via `terminal-notifier`. Stateless, single-threaded.

## Architecture

Both servers share the same hand-rolled MCP pattern:
- `server.py` — Entry point. Reads JSON-RPC lines from stdin, writes responses to stdout.
- `mcp_handler.py` — Routes `initialize`, `tools/list`, `tools/call` methods. Tool definitions are declared as dicts in `TOOL_DEFINITIONS`.
- `run.sh` — Bootstrap script (creates venv if needed, installs deps, execs python).

Key detail: `server.py` files include `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` so imports work regardless of the working directory Claude Code launches from.

Inloop additionally has:
- `task_store.py` — Thread-safe in-memory store with `threading.Event` for blocking `wait_for_task`.
- `web_server.py` — WebSocket server (using `websockets` library) that broadcasts state changes and serves a static dashboard. Opens browser on first tool call.

## Testing

Tests exist only for inloop (pytest):

```bash
cd inloop_user_mcp
source venv/bin/activate
pytest tests/
```

## Claude Code Configuration

In `~/.claude.json`, servers must use **absolute paths** for the `args` to `run.sh` — relative paths don't resolve reliably. Config changes require a **full restart** of Claude Code; `/mcp` reconnect does not re-read `~/.claude.json`.

```json
{
  "command": "bash",
  "args": ["/absolute/path/to/run.sh"],
  "cwd": "/absolute/path/to/server_dir"
}
```

## Dependencies

- **inloop_user_mcp**: `websockets>=12.0,<14.0` (managed via venv + requirements.txt)
- **notify_macos_mcp**: No Python deps. Requires `terminal-notifier` (`brew install terminal-notifier`).
