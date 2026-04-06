# Claude Code MCP Servers

Custom MCP (Model Context Protocol) servers for Claude Code.

## Servers

### inloop_user_mcp

Human-in-the-loop task manager. Sends tasks to a browser dashboard where a human can mark them as done. Claude can wait (blocking) or poll (non-blocking) for task completion.

**Tools:** `send_tasks`, `add_task`, `enable_task`, `check_status`, `wait_for_task`

### notify_macos_mcp

Sends macOS notifications via `terminal-notifier`. Automatically finds the binary in PATH or rbenv gems.

**Tools:** `notify`

**Prerequisite:** `brew install terminal-notifier` or `gem install terminal-notifier`

## Setup

1. Clone this repo
2. Add server configs to `~/.claude.json` using absolute paths:

```json
{
  "mcpServers": {
    "inloop": {
      "command": "bash",
      "args": ["/path/to/inloop_user_mcp/run.sh"],
      "cwd": "/path/to/inloop_user_mcp"
    },
    "notify-macos": {
      "command": "bash",
      "args": ["/path/to/notify_macos_mcp/run.sh"],
      "cwd": "/path/to/notify_macos_mcp"
    }
  }
}
```

3. Restart Claude Code

The `run.sh` scripts handle venv creation and dependency installation automatically on first run.
