import threading
from task_store import TaskStore


def test_send_tasks_creates_tasks():
    store = TaskStore()
    tasks = [
        {"id": "1", "title": "Do thing A", "enabled": True},
        {"id": "2", "title": "Do thing B", "enabled": False},
    ]
    result = store.send_tasks(tasks)
    assert len(result) == 2
    assert result[0]["id"] == "1"
    assert result[0]["status"] == "enabled"
    assert result[1]["id"] == "2"
    assert result[1]["status"] == "pending"


def test_send_tasks_replaces_existing():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "Old", "enabled": True}])
    store.send_tasks([{"id": "2", "title": "New", "enabled": True}])
    result = store.check_status()
    assert len(result) == 1
    assert result[0]["id"] == "2"


def test_add_task_appends():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "First", "enabled": True}])
    store.add_task({"id": "2", "title": "Second", "enabled": False})
    result = store.check_status()
    assert len(result) == 2
    assert result[1]["id"] == "2"


def test_enable_task():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "Task", "enabled": False}])
    store.enable_task("1")
    result = store.check_status("1")
    assert result["status"] == "enabled"


def test_enable_task_unknown_id():
    store = TaskStore()
    result = store.enable_task("nonexistent")
    assert result is None


def test_mark_done():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "Task", "enabled": True}])
    store.mark_done("1")
    result = store.check_status("1")
    assert result["status"] == "done"


def test_mark_done_pending_task_ignored():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "Task", "enabled": False}])
    store.mark_done("1")
    result = store.check_status("1")
    assert result["status"] == "pending"


def test_check_status_all():
    store = TaskStore()
    store.send_tasks([
        {"id": "1", "title": "A", "enabled": True},
        {"id": "2", "title": "B", "enabled": False},
    ])
    result = store.check_status()
    assert len(result) == 2


def test_check_status_single():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "A", "enabled": True}])
    result = store.check_status("1")
    assert result["id"] == "1"
    assert result["status"] == "enabled"


def test_check_status_unknown_id():
    store = TaskStore()
    result = store.check_status("nonexistent")
    assert result is None


def test_wait_for_task_already_done():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "A", "enabled": True}])
    store.mark_done("1")
    result = store.wait_for_task("1", timeout=1.0)
    assert result["status"] == "done"


def test_wait_for_task_times_out():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "A", "enabled": True}])
    result = store.wait_for_task("1", timeout=0.1)
    assert result["status"] == "timeout"


def test_wait_for_task_completes_when_marked():
    store = TaskStore()
    store.send_tasks([{"id": "1", "title": "A", "enabled": True}])

    def mark_later():
        import time
        time.sleep(0.1)
        store.mark_done("1")

    t = threading.Thread(target=mark_later)
    t.start()
    result = store.wait_for_task("1", timeout=5.0)
    t.join()
    assert result["status"] == "done"


def test_all_done():
    store = TaskStore()
    store.send_tasks([
        {"id": "1", "title": "A", "enabled": True},
        {"id": "2", "title": "B", "enabled": True},
    ])
    assert store.all_done() is False
    store.mark_done("1")
    assert store.all_done() is False
    store.mark_done("2")
    assert store.all_done() is True


def test_all_done_empty():
    store = TaskStore()
    assert store.all_done() is False


def test_get_page_state():
    store = TaskStore()
    assert store.get_page_state() == "waiting"

    store.send_tasks([{"id": "1", "title": "A", "enabled": True}])
    assert store.get_page_state() == "active"

    store.mark_done("1")
    assert store.get_page_state() == "done"


def test_thread_safety():
    store = TaskStore()
    store.send_tasks([{"id": str(i), "title": f"Task {i}", "enabled": True} for i in range(100)])

    errors = []

    def mark_done_worker(start, end):
        try:
            for i in range(start, end):
                store.mark_done(str(i))
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=mark_done_worker, args=(0, 50)),
        threading.Thread(target=mark_done_worker, args=(50, 100)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert store.all_done() is True


def test_get_full_state():
    store = TaskStore()
    state = store.get_full_state()
    assert state == {"type": "state", "tasks": [], "page": "waiting", "title": ""}

    store.send_tasks([
        {"id": "1", "title": "A", "enabled": True},
        {"id": "2", "title": "B", "enabled": False},
    ])
    state = store.get_full_state()
    assert state["type"] == "state"
    assert state["page"] == "active"
    assert state["title"] == ""
    assert len(state["tasks"]) == 2
    assert state["tasks"][0]["status"] == "enabled"
    assert state["tasks"][1]["status"] == "pending"

    store.mark_done("1")
    store.enable_task("2")
    store.mark_done("2")
    state = store.get_full_state()
    assert state["page"] == "done"


def test_title():
    store = TaskStore()
    assert store.get_full_state()["title"] == ""

    store.set_title("My Project")
    assert store.get_full_state()["title"] == "My Project"

    # send_tasks with title
    store.send_tasks([{"id": "1", "title": "A", "enabled": True}], title="Test Session")
    assert store.get_full_state()["title"] == "Test Session"

    # send_tasks without title preserves existing
    store.send_tasks([{"id": "2", "title": "B", "enabled": True}])
    assert store.get_full_state()["title"] == "Test Session"
