"""
Performance tests for Habit Tracker API

These tests verify NFR-07, NFR-08, NFR-09 requirements:
- NFR-07: GET /habits p95 <= 200ms @ 50 RPS
- NFR-08: POST /habits p95 <= 300ms @ 50 RPS
- NFR-09: GET /habits/{id}/stats p95 <= 500ms @ 50 RPS

Run with: pytest tests/test_performance.py -v -m performance
Skip with: pytest tests/ -m "not performance"
"""

import time
from datetime import date, timedelta
from statistics import median, quantiles

import pytest


@pytest.mark.performance
def test_get_habits_performance_baseline(authenticated_client):
    """
    NFR-07: GET /habits response time baseline

    Target: p95 <= 200ms @ 50 RPS
    This is a baseline test without actual load generation
    """
    # Setup: Create some test data
    for i in range(10):
        authenticated_client.post(
            "/habits",
            json={"name": f"Habit {i}", "description": "Test", "frequency": "daily"},
        )

    # Measure response times
    response_times = []
    iterations = 100

    for _ in range(iterations):
        start = time.perf_counter()
        response = authenticated_client.get("/habits")
        end = time.perf_counter()

        assert response.status_code == 200
        response_times.append((end - start) * 1000)  # Convert to ms

    # Calculate percentiles
    p50 = median(response_times)
    p95, p99 = (
        quantiles(response_times, n=100)[94],
        quantiles(response_times, n=100)[98],
    )

    # Report metrics
    print("\n GET /habits Performance Metrics:")
    print(f"   Iterations: {iterations}")
    print(f"   p50: {p50:.2f}ms")
    print(f"   p95: {p95:.2f}ms (target: <=200ms)")
    print(f"   p99: {p99:.2f}ms")

    # Assert NFR-07 requirement
    assert p95 <= 200, f"NFR-07 failed: p95 {p95:.2f}ms exceeds 200ms threshold"


@pytest.mark.performance
def test_post_habits_performance_baseline(authenticated_client):
    """
    NFR-08: POST /habits response time baseline

    Target: p95 <= 300ms @ 50 RPS
    """
    response_times = []
    iterations = 50

    for i in range(iterations):
        start = time.perf_counter()
        response = authenticated_client.post(
            "/habits",
            json={
                "name": f"Perf Test Habit {i}",
                "description": "Test",
                "frequency": "daily",
            },
        )
        end = time.perf_counter()

        assert response.status_code == 201
        response_times.append((end - start) * 1000)

    p50 = median(response_times)
    p95, p99 = (
        quantiles(response_times, n=100)[94],
        quantiles(response_times, n=100)[98],
    )

    print("\n POST /habits Performance Metrics:")
    print(f"   Iterations: {iterations}")
    print(f"   p50: {p50:.2f}ms")
    print(f"   p95: {p95:.2f}ms (target: <=300ms)")
    print(f"   p99: {p99:.2f}ms")

    assert p95 <= 300, f"NFR-08 failed: p95 {p95:.2f}ms exceeds 300ms threshold"


@pytest.mark.performance
def test_get_stats_performance_baseline(authenticated_client):
    """
    NFR-09: GET /habits/{id}/stats response time baseline

    Target: p95 <= 500ms @ 50 RPS
    """
    habit_resp = authenticated_client.post(
        "/habits",
        json={"name": "Stats Test Habit", "frequency": "daily"},
    )
    habit_id = habit_resp.json()["id"]

    # Create 30 tracking records
    for i in range(30):
        track_date = (date.today() - timedelta(days=i)).isoformat()
        authenticated_client.post(
            f"/habits/{habit_id}/track",
            json={"completed_date": track_date, "count": 1},
        )

    response_times = []
    iterations = 100

    for _ in range(iterations):
        start = time.perf_counter()
        response = authenticated_client.get(f"/habits/{habit_id}/stats")
        end = time.perf_counter()

        assert response.status_code == 200
        response_times.append((end - start) * 1000)

    p50 = median(response_times)
    p95, p99 = (
        quantiles(response_times, n=100)[94],
        quantiles(response_times, n=100)[98],
    )

    print("\n GET /habits/{id}/stats Performance Metrics:")
    print(f"   Iterations: {iterations}")
    print("   Data points: 30 tracking records")
    print(f"   p50: {p50:.2f}ms")
    print(f"   p95: {p95:.2f}ms (target: <=500ms)")
    print(f"   p99: {p99:.2f}ms")

    assert p95 <= 500, f"NFR-09 failed: p95 {p95:.2f}ms exceeds 500ms threshold"


@pytest.mark.performance
@pytest.mark.slow
def test_concurrent_requests_simulation(authenticated_client):
    """
    Simulate concurrent requests to verify system handles load

    This is a simplified concurrency test. For real load testing,
    use Locust or k6 with actual concurrent users.
    """
    import concurrent.futures

    # Setup
    for i in range(5):
        authenticated_client.post(
            "/habits",
            json={"name": f"Concurrent Test {i}", "frequency": "daily"},
        )

    def make_request():
        start = time.perf_counter()
        response = authenticated_client.get("/habits")
        end = time.perf_counter()
        return response.status_code, (end - start) * 1000

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    status_codes = [r[0] for r in results]
    response_times = [r[1] for r in results]

    success_rate = sum(1 for s in status_codes if s == 200) / len(status_codes) * 100
    p95 = quantiles(response_times, n=100)[94]

    print("\n Concurrent Requests Simulation:")
    print(f"   Total requests: {len(results)}")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"   p95 response time: {p95:.2f}ms")

    assert success_rate >= 99, f"Success rate {success_rate:.1f}% below 99%"
    assert p95 <= 300, f"p95 {p95:.2f}ms exceeds 300ms under concurrent load"
