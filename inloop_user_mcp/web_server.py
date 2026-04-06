"""HTTP static file server + WebSocket handler for InLoop User MCP."""

import asyncio
import json
import os
import webbrowser
from pathlib import Path

import websockets
from websockets.asyncio.server import serve as ws_serve, ServerConnection
from websockets.datastructures import Headers
from websockets.http11 import Response

from task_store import TaskStore

STATIC_DIR = Path(__file__).parent / "static"


class WebServer:
    def __init__(self, store: TaskStore):
        self._store = store
        self._ws_clients: set[ServerConnection] = set()
        self._port: int | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._browser_opened: bool = False
        store.set_on_change(self._on_store_change)

    @property
    def port(self) -> int | None:
        return self._port

    def _on_store_change(self):
        """Called by TaskStore (from MCP thread) when state changes. Schedules a broadcast."""
        if not self._browser_opened and self._port is not None:
            self._browser_opened = True
            webbrowser.open(f"http://localhost:{self._port}")
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(asyncio.ensure_future, self._broadcast())

    async def _broadcast(self):
        """Send current state to all connected WebSocket clients."""
        if not self._ws_clients:
            return
        state = self._store.get_full_state()
        msg = json.dumps(state)
        disconnected = set()
        for ws in self._ws_clients:
            try:
                await ws.send(msg)
            except websockets.ConnectionClosed:
                disconnected.add(ws)
        self._ws_clients -= disconnected

    async def _ws_handler(self, websocket: ServerConnection):
        """Handle a WebSocket connection."""
        self._ws_clients.add(websocket)
        try:
            # Send current state immediately on connect
            state = self._store.get_full_state()
            await websocket.send(json.dumps(state))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("type") == "task_done":
                        task_id = data.get("task_id")
                        if task_id:
                            self._store.mark_done(task_id)
                except json.JSONDecodeError:
                    pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self._ws_clients.discard(websocket)

    async def _process_request(self, connection, request):
        """Intercept HTTP requests to serve static files. WebSocket upgrades pass through."""
        if request.path in ("/", "/index.html"):
            file_path = STATIC_DIR / "index.html"
            if file_path.exists():
                body = file_path.read_bytes()
                headers = Headers()
                headers["Content-Type"] = "text/html; charset=utf-8"
                headers["Content-Length"] = str(len(body))
                return Response(200, "OK", headers, body)
        return None  # Let websockets handle it as a WebSocket upgrade

    async def start(self) -> int:
        """Start the web server. Returns the port number."""
        self._loop = asyncio.get_running_loop()
        server = await ws_serve(
            self._ws_handler,
            "127.0.0.1",
            0,  # auto-pick free port
            process_request=self._process_request,
        )
        # Extract the port from the server
        self._port = server.sockets[0].getsockname()[1]
        return self._port
