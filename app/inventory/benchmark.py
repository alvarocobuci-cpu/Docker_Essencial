import json
import math
import time
from urllib.request import urlopen


BASE_URL = "http://localhost:8001"
REQUESTS_PER_ENDPOINT = 100


def request_json(path):
    with urlopen(f"{BASE_URL}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def percentile_95(values):
    ordered = sorted(values)
    index = math.ceil(0.95 * len(ordered)) - 1
    return ordered[index] * 1000


def benchmark(path):
    durations = []
    start_total = time.perf_counter()

    for _ in range(REQUESTS_PER_ENDPOINT):
        start = time.perf_counter()
        request_json(path)
        durations.append(time.perf_counter() - start)

    total_time = time.perf_counter() - start_total
    average_ms = sum(durations) / len(durations) * 1000
    p95_ms = percentile_95(durations)
    rps = REQUESTS_PER_ENDPOINT / total_time

    print(f"\nEndpoint: GET {path}")
    print(f"Requisições: {REQUESTS_PER_ENDPOINT}")
    print(f"Latência média: {average_ms:.2f} ms")
    print(f"P95: {p95_ms:.2f} ms")
    print(f"RPS: {rps:.2f}")


def main():
    items = request_json("/inventory")

    if not items:
        print("Não há itens no estoque para realizar o teste.")
        return

    item_id = items[0]["id"]

    print("MEDIÇÃO COM CACHE ATIVO")
    benchmark("/inventory")
    benchmark(f"/inventory/{item_id}")


if __name__ == "__main__":
    main()