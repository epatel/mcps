import json
from task_store import TaskStore
from mcp_handler import McpHandler


def make_request(method, params=None, req_id=1):
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def test_initialize():
    store = TaskStore()
    handler = McpHandler(store)
    req = make_request("initialize", {"protocolVersion": "2024-11-05"})
    resp = handler.handle(req)
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert "tools" in resp["result"]["capabilities"]
    assert resp["result"]["serverInfo"]["name"] == "inloop-user-mcp"


def test_tools_list():
    store = TaskStore()
    handler = McpHandler(store)
    resp = handler.handle(make_request("tools/list"))
    tools = resp["result"]["tools"]
    names = [t["name"] for t in tools]
    assert "send_tasks" in names
    assert "add_task" in names
    assert "enable_task" in names
    assert "check_status" in names
    assert "wait_for_task" in names
    assert len(names) == 5


def test_tool_call_send_tasks():
    store = TaskStore()
    handler = McpHandler(store)
    resp = handler.handle(make_request("tools/call", {
        "name": "send_tasks",
        "arguments": {
            "tasks": [
                {"id": "1", "title": "Task A", "enabled": True},
                {"id": "2", "title": "Task B", "enabled": False},
            ]
        }
    }))
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert len(data) == 2
    assert data[0]["status"] == "enabled"
    assert data[1]["status"] == "pending"


def test_tool_call_add_task():
    store = TaskStore()
    handler = McpHandler(store)
    handler.handle(make_request("tools/call", {
        "name": "send_tasks",
        "arguments": {"tasks": [{"id": "1", "title": "First", "enabled": True}]}
    }))
    resp = handler.handle(make_request("tools/call", {
        "name": "add_task",
        "arguments": {"task": {"id": "2", "title": "Second", "enabled": False}}
    }, req_id=2))
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert data["id"] == "2"
    assert data["status"] == "pending"


def test_tool_call_enable_task():
    store = TaskStore()
    handler = McpHandler(store)
    handler.handle(make_request("tools/call", {
        "name": "send_tasks",
        "arguments": {"tasks": [{"id": "1", "title": "Task", "enabled": False}]}
    }))
    resp = handler.handle(make_request("tools/call", {
        "name": "enable_task",
        "arguments": {"task_id": "1"}
    }, req_id=2))
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert data["status"] == "enabled"


def test_tool_call_enable_task_not_found():
    store = TaskStore()
    handler = McpHandler(store)
    resp = handler.handle(make_request("tools/call", {
        "name": "enable_task",
        "arguments": {"task_id": "nonexistent"}
    }))
    assert resp["result"]["isError"] is True


def test_tool_call_check_status_all():
    store = TaskStore()
    handler = McpHandler(store)
    handler.handle(make_request("tools/call", {
        "name": "send_tasks",
        "arguments": {"tasks": [{"id": "1", "title": "A", "enabled": True}]}
    }))
    resp = handler.handle(make_request("tools/call", {
        "name": "check_status",
        "arguments": {}
    }, req_id=2))
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert isinstance(data, list)
    assert len(data) == 1


def test_tool_call_check_status_single():
    store = TaskStore()
    handler = McpHandler(store)
    handler.handle(make_request("tools/call", {
        "name": "send_tasks",
        "arguments": {"tasks": [{"id": "1", "title": "A", "enabled": True}]}
    }))
    resp = handler.handle(make_request("tools/call", {
        "name": "check_status",
        "arguments": {"task_id": "1"}
    }, req_id=2))
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert data["id"] == "1"


def test_tool_call_wait_for_task_already_done():
    store = TaskStore()
    handler = McpHandler(store)
    handler.handle(make_request("tools/call", {
        "name": "send_tasks",
        "arguments": {"tasks": [{"id": "1", "title": "A", "enabled": True}]}
    }))
    store.mark_done("1")
    resp = handler.handle(make_request("tools/call", {
        "name": "wait_for_task",
        "arguments": {"task_id": "1", "timeout": 1}
    }, req_id=2))
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert data["status"] == "done"


def test_tool_call_wait_for_task_timeout():
    store = TaskStore()
    handler = McpHandler(store)
    handler.handle(make_request("tools/call", {
        "name": "send_tasks",
        "arguments": {"tasks": [{"id": "1", "title": "A", "enabled": True}]}
    }))
    resp = handler.handle(make_request("tools/call", {
        "name": "wait_for_task",
        "arguments": {"task_id": "1", "timeout": 0.1}
    }, req_id=2))
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert data["status"] == "timeout"


def test_tool_call_unknown_tool():
    store = TaskStore()
    handler = McpHandler(store)
    resp = handler.handle(make_request("tools/call", {
        "name": "nonexistent",
        "arguments": {}
    }))
    assert resp["result"]["isError"] is True


def test_unknown_method():
    store = TaskStore()
    handler = McpHandler(store)
    resp = handler.handle(make_request("bogus/method"))
    assert "error" in resp["result"] or resp["result"].get("isError")


def test_notifications_ignored():
    store = TaskStore()
    handler = McpHandler(store)
    resp = handler.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert resp is None
