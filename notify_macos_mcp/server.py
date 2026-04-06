"""Notify macOS MCP — main entry point.

Runs the MCP stdio handler, forwarding JSON-RPC messages to the handler.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_handler import McpHandler


def run_mcp_stdio(handler: McpHandler):
    """Blocking MCP stdio loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handler.handle(msg)
        if response is not None:
            out = json.dumps(response)
            sys.stdout.write(out + "\n")
            sys.stdout.flush()


def main():
    handler = McpHandler()
    print("notify-macos-mcp started", file=sys.stderr)
    run_mcp_stdio(handler)


if __name__ == "__main__":
    main()
