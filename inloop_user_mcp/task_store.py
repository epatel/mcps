"""Thread-safe in-memory task store for InLoop User MCP."""

import threading
from typing import Callable, Optional


class TaskStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._tasks: list[dict] = []  # ordered list of {id, title, status}
        self._task_map: dict[str, dict] = {}  # id -> task ref
        self._done_events: dict[str, threading.Event] = {}  # id -> event
        self._title: str = ""
        self._on_change: Optional[Callable[[], None]] = None

    def set_on_change(self, callback: Callable[[], None]):
        """Register a callback invoked (outside the lock) whenever state changes."""
        self._on_change = callback

    def _notify(self):
        if self._on_change:
            self._on_change()

    def _make_task(self, raw: dict) -> dict:
        enabled = raw.get("enabled", False)
        return {
            "id": raw["id"],
            "title": raw["title"],
            "status": "enabled" if enabled else "pending",
        }

    def set_title(self, title: str):
        """Set the project/session title shown in the dashboard header."""
        with self._lock:
            self._title = title
        self._notify()

    def send_tasks(self, tasks: list[dict], title: str = None) -> list[dict]:
        """Replace all tasks with a new batch. Optionally set title. Returns the task list with statuses."""
        with self._lock:
            if title is not None:
                self._title = title
            self._tasks = []
            self._task_map = {}
            self._done_events = {}
            for raw in tasks:
                task = self._make_task(raw)
                self._tasks.append(task)
                self._task_map[task["id"]] = task
                self._done_events[task["id"]] = threading.Event()
            result = [dict(t) for t in self._tasks]
        self._notify()
        return result

    def add_task(self, raw: dict) -> dict:
        """Append a single task. Returns the task with status."""
        task = self._make_task(raw)
        with self._lock:
            self._tasks.append(task)
            self._task_map[task["id"]] = task
            self._done_events[task["id"]] = threading.Event()
            result = dict(task)
        self._notify()
        return result

    def enable_task(self, task_id: str) -> Optional[dict]:
        """Enable a pending task. Returns updated task or None if not found."""
        with self._lock:
            task = self._task_map.get(task_id)
            if task is None:
                return None
            if task["status"] == "pending":
                task["status"] = "enabled"
            result = dict(task)
        self._notify()
        return result

    def mark_done(self, task_id: str) -> Optional[dict]:
        """Mark an enabled task as done. Pending tasks cannot be marked done. Returns updated task or None."""
        with self._lock:
            task = self._task_map.get(task_id)
            if task is None:
                return None
            if task["status"] != "enabled":
                return dict(task)
            task["status"] = "done"
            event = self._done_events.get(task_id)
            if event:
                event.set()
            result = dict(task)
        self._notify()
        return result

    def check_status(self, task_id: str = None) -> Optional[list[dict] | dict]:
        """Return status of one task (by id) or all tasks (if id is None)."""
        with self._lock:
            if task_id is None:
                return [dict(t) for t in self._tasks]
            task = self._task_map.get(task_id)
            if task is None:
                return None
            return dict(task)

    def wait_for_task(self, task_id: str, timeout: float = 300.0) -> dict:
        """Block until task is done or timeout. Returns {status: 'done'} or {status: 'timeout'}."""
        with self._lock:
            task = self._task_map.get(task_id)
            if task is None:
                return {"status": "not_found"}
            if task["status"] == "done":
                return {"status": "done"}
            event = self._done_events.get(task_id)

        if event and event.wait(timeout=timeout):
            return {"status": "done"}
        return {"status": "timeout"}

    def all_done(self) -> bool:
        """Return True if all tasks are done and there is at least one task."""
        with self._lock:
            if not self._tasks:
                return False
            return all(t["status"] == "done" for t in self._tasks)

    def get_page_state(self) -> str:
        """Return the current page state: 'waiting', 'active', or 'done'."""
        with self._lock:
            if not self._tasks:
                return "waiting"
            if all(t["status"] == "done" for t in self._tasks):
                return "done"
            return "active"

    def get_full_state(self) -> dict:
        """Return the full state dict for WebSocket broadcast."""
        with self._lock:
            tasks = [dict(t) for t in self._tasks]
        page = "waiting"
        if tasks:
            page = "done" if all(t["status"] == "done" for t in tasks) else "active"
        with self._lock:
            title = self._title
        return {"type": "state", "tasks": tasks, "page": page, "title": title}
