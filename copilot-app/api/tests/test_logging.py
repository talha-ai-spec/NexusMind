import logging

from app.core.logging import clear_log_buffer, get_recent_logs
from tests.conftest import FakeProvider


def test_in_memory_log_buffer_records_and_filters():
    clear_log_buffer()
    logger = logging.getLogger("test.logger")

    logger.debug("A debug message")
    logger.info("An info message for testing")
    logger.warning("A warning alert message")
    logger.error("An error event")

    all_logs = get_recent_logs(limit=50, min_level="DEBUG")
    assert any("An info message for testing" in entry["message"] for entry in all_logs)

    # Filter by level
    warnings_and_up = get_recent_logs(limit=50, min_level="WARNING")
    valid_levels = ("WARNING", "WARN", "ERROR", "CRITICAL")
    assert all(entry["level"] in valid_levels for entry in warnings_and_up)
    assert any("A warning alert message" in entry["message"] for entry in warnings_and_up)
    assert not any("An info message for testing" in entry["message"] for entry in warnings_and_up)

    # Filter by search
    searched = get_recent_logs(limit=50, search="alert")
    assert len(searched) == 1
    assert "A warning alert message" in searched[0]["message"]

    # Clear buffer
    clear_log_buffer()
    assert len(get_recent_logs()) == 0


def test_request_logging_middleware_and_logs_endpoints(make_client):
    ollama = FakeProvider("ollama", local=True, models=["llama3.2"])
    client = make_client(ollama)

    # 1. Check X-Request-ID header on HTTP requests
    res = client.get("/api/health")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    req_id = res.headers["x-request-id"]
    assert req_id.startswith("req-")

    # 2. Check GET /api/logs
    logs_res = client.get("/api/logs")
    assert logs_res.status_code == 200
    data = logs_res.json()
    assert "total" in data
    assert "logs" in data
    assert isinstance(data["logs"], list)

    # 3. Check plain text format
    text_res = client.get("/api/logs?format=text")
    assert text_res.status_code == 200
    assert text_res.headers["content-type"].startswith("text/plain")

    # 4. Check HTML log viewer
    view_res = client.get("/api/logs/view")
    assert view_res.status_code == 200
    assert "<title>Copilot API · Live Log Viewer</title>" in view_res.text

    # 5. Check DELETE /api/logs
    del_res = client.delete("/api/logs")
    assert del_res.status_code == 200
    assert del_res.json() == {"cleared": True}
