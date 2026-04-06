"""InLoop User MCP — main entry point.

Runs the MCP stdio handler in a thread and the web/WebSocket server on asyncio.
"""

import asyncio
import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_store import TaskStore
from mcp_handler import McpHandler
from web_server import WebServer


def run_mcp_stdio(handler: McpHandler):
    """Blocking MCP stdio loop. Runs in a background thread."""
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


async def main():
    store = TaskStore()
    handler = McpHandler(store)
    web = WebServer(store)

    # Start the web server
    port = await web.start()
    url = f"http://localhost:{port}"

    # Log to stderr (stdout is reserved for MCP protocol)
    print(f"InLoop dashboard: {url}", file=sys.stderr)

    # Start MCP stdio handler in a background thread
    mcp_thread = threading.Thread(target=run_mcp_stdio, args=(handler,), daemon=True)
    mcp_thread.start()

    # Keep the asyncio loop running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down.", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
