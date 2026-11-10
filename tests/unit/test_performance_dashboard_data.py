import json

import pytest

from performance_dashboard import metrics_data


pytestmark = pytest.mark.unit


def make_request_event(**overrides):
    event = {
        "event_id": "abc",
        "timestamp": 100.0,
        "method": "get",
        "endpoint": "/api/v1/pedidos/",
        "status_code": 200,
        "duration_ms": 12.0,
    }
    event.update(overrides)
    return event


def test_parse_request_events_normalizes_and_sorts():
    raw = [
        json.dumps(
            make_request_event(timestamp=200.0, status_code=404)
        ),
        json.dumps(
            make_request_event(timestamp=100.0, status_code=201)
        ),
        "conteudo invalido",
    ]

    records = metrics_data.parse_request_events(raw)

    assert [record["timestamp"] for record in records] == [100.0, 200.0]
    assert records[0]["status_group"] == "2xx"
    assert records[1]["status_group"] == "4xx"
    assert records[0]["method"] == "GET"
    assert records[0]["cache_status"] == "not_instrumented"


def test_parse_request_events_skips_invalid_records():
    records = metrics_data.parse_request_events(
        [
            json.dumps({"timestamp": "invalido"}),
            json.dumps({"timestamp": 1.0}),
            json.dumps(["lista", "nao", "e", "evento"]),
        ]
    )

    assert records == []


def test_filter_by_period():
    records = [{"timestamp": 100.0}, {"timestamp": 9000.0}]

    assert metrics_data.filter_by_period(
        records,
        now=10000.0,
        hours=1,
    ) == [{"timestamp": 9000.0}]

    assert (
        metrics_data.filter_by_period(
            records,
            now=10000.0,
            hours=None,
        )
        == records
    )


def test_filter_by_endpoints_and_status_groups():
    records = [
        {"endpoint": "/a", "status_group": "2xx"},
        {"endpoint": "/b", "status_group": "5xx"},
    ]

    assert metrics_data.filter_by_endpoints(records, ["/a"]) == [
        records[0]
    ]
    assert metrics_data.filter_by_status_groups(
        records,
        ["5xx"],
    ) == [records[1]]


def test_compute_kpis():
    records = [
        {"duration_ms": 10.0, "status_code": 200},
        {"duration_ms": 20.0, "status_code": 500},
        {"duration_ms": 30.0, "status_code": 200},
        {"duration_ms": 40.0, "status_code": 404},
    ]

    kpis = metrics_data.compute_kpis(records)

    assert kpis["total_requests"] == 4
    assert kpis["average_latency_ms"] == 25.0
    assert kpis["error_count"] == 2
    assert kpis["error_rate_percent"] == 50.0
    assert kpis["p95_latency_ms"] == pytest.approx(38.5)


def test_compute_kpis_empty():
    kpis = metrics_data.compute_kpis([])

    assert kpis["total_requests"] == 0
    assert kpis["average_latency_ms"] == 0.0
    assert kpis["p95_latency_ms"] == 0.0
    assert kpis["error_rate_percent"] == 0.0


def test_aggregations_by_minute_and_status():
    records = [
        {
            "timestamp": 60.0,
            "duration_ms": 10.0,
            "status_group": "2xx",
        },
        {
            "timestamp": 90.0,
            "duration_ms": 30.0,
            "status_group": "2xx",
        },
        {
            "timestamp": 120.0,
            "duration_ms": 20.0,
            "status_group": "5xx",
        },
    ]

    assert metrics_data.aggregate_latency_by_minute(records) == [
        {"minute": 60, "average_latency_ms": 20.0},
        {"minute": 120, "average_latency_ms": 20.0},
    ]

    assert metrics_data.aggregate_throughput_by_minute(records) == [
        {"minute": 60, "requests": 2},
        {"minute": 120, "requests": 1},
    ]

    assert metrics_data.aggregate_status_distribution(records) == [
        {"status_group": "2xx", "count": 2},
        {"status_group": "5xx", "count": 1},
    ]


def test_build_cache_metrics():
    rows = metrics_data.build_cache_metrics(
        hits_by_endpoint={"inventory_list": 3},
        lookups_by_endpoint={
            "inventory_list": 4,
            "inventory_detail": 0,
        },
    )

    assert rows == [
        {
            "endpoint": "inventory_detail",
            "hits": 0,
            "misses": 0,
            "lookups": 0,
            "hit_rate_percent": 0.0,
        },
        {
            "endpoint": "inventory_list",
            "hits": 3,
            "misses": 1,
            "lookups": 4,
            "hit_rate_percent": 75.0,
        },
    ]


def test_parse_and_aggregate_messaging():
    raw = [
        json.dumps(
            {
                "timestamp": 1.0,
                "topic": "pedidos.criado",
                "direction": "PUBLISH",
                "outcome": "SUCCESS",
            }
        ),
        json.dumps(
            {
                "timestamp": 2.0,
                "topic": "pedidos.criado",
                "direction": "publish",
                "outcome": "success",
            }
        ),
        json.dumps(
            {
                "timestamp": 3.0,
                "topic": "pedidos.criado",
                "direction": "consume",
                "outcome": "error",
            }
        ),
        "invalido",
    ]

    records = metrics_data.parse_messaging_events(raw)

    assert len(records) == 3
    assert metrics_data.aggregate_messaging(records) == [
        {"direction": "consume", "outcome": "error", "count": 1},
        {"direction": "publish", "outcome": "success", "count": 2},
    ]
