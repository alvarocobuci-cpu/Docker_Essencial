import pytest

from config import metrics


pytestmark = pytest.mark.unit


def test_build_request_event_normalizes_fields():
    event = metrics.build_request_event(
        method="get",
        endpoint="/api/v1/pedidos/",
        status_code=503,
        duration_ms=-12.3456,
        cache_status=" HIT ",
        timestamp=1234.5,
    )

    assert event["method"] == "GET"
    assert event["endpoint"] == "/api/v1/pedidos/"
    assert event["status_group"] == "5xx"
    assert event["duration_ms"] == 0.0
    assert event["cache_status"] == "hit"
    assert event["timestamp"] == 1234.5
    assert event["event_id"]


def test_build_request_event_truncates_endpoint():
    event = metrics.build_request_event(
        method="POST",
        endpoint="x" * 300,
        status_code=201,
        duration_ms=10,
    )

    assert len(event["endpoint"]) == 200
    assert event["status_group"] == "2xx"
    assert event["cache_status"] == "not_instrumented"


def test_record_request_metric_returns_false_when_redis_fails(
    monkeypatch,
):
    def broken_redis():
        raise RuntimeError("redis indisponivel")

    monkeypatch.setattr(metrics, "_get_redis", broken_redis)

    assert (
        metrics.record_request_metric(
            method="GET",
            endpoint="/api/v1/x",
            status_code=200,
            duration_ms=1,
        )
        is False
    )


def test_store_event_writes_pipeline_commands(monkeypatch):
    calls = {}

    class FakePipeline:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def zadd(self, key, mapping):
            calls["zadd"] = (key, mapping)

        def expire(self, key, seconds):
            calls["expire"] = (key, seconds)

        def zremrangebyscore(self, key, low, high):
            calls["zrem"] = (key, low, high)

        def execute(self):
            calls["executed"] = True

    class FakeRedis:
        def pipeline(self, transaction=False):
            return FakePipeline()

    monkeypatch.setattr(metrics, "_get_redis", lambda: FakeRedis())

    stored = metrics._store_event(
        "test:key",
        {"timestamp": 100.0, "foo": "bar"},
    )

    assert stored is True
    assert calls["executed"] is True
    assert calls["zadd"][0] == "test:key"
    assert calls["expire"] == ("test:key", metrics.RETENTION_SECONDS)
    assert calls["zrem"] == (
        "test:key",
        "-inf",
        100.0 - metrics.RETENTION_SECONDS,
    )


def test_record_cache_metric_builds_event(monkeypatch):
    captured = {}

    def fake_store(key, event):
        captured["key"] = key
        captured["event"] = event
        return True

    monkeypatch.setattr(metrics, "_store_event", fake_store)

    assert metrics.record_cache_metric(
        cache_name="inventory",
        operation="GET",
        outcome="HIT",
        timestamp=10.0,
    )

    assert captured["key"] == metrics.CACHE_METRICS_KEY
    assert captured["event"]["cache_name"] == "inventory"
    assert captured["event"]["operation"] == "get"
    assert captured["event"]["outcome"] == "hit"
    assert captured["event"]["timestamp"] == 10.0


def test_record_messaging_metric_builds_event(monkeypatch):
    captured = {}

    def fake_store(key, event):
        captured["key"] = key
        captured["event"] = event
        return True

    monkeypatch.setattr(metrics, "_store_event", fake_store)

    assert metrics.record_messaging_metric(
        topic="pedidos.criado",
        direction="PUBLISH",
        outcome="SUCCESS",
        duration_ms=12.5,
        timestamp=20.0,
    )

    assert captured["key"] == metrics.MESSAGING_METRICS_KEY
    assert captured["event"]["topic"] == "pedidos.criado"
    assert captured["event"]["direction"] == "publish"
    assert captured["event"]["outcome"] == "success"
    assert captured["event"]["duration_ms"] == 12.5
