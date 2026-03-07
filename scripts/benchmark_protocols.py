"""REST vs gRPC vs MCP — Protocol Benchmark.

Compares latency and throughput of the three communication protocols
used in the TelcoAgent platform.

Usage:
    python scripts/benchmark_protocols.py

Prerequisites:
    - Customer Service running on :8001 (REST)
    - Customer MCP server importable (MCP)
    - gRPC server on :50051 (gRPC) — optional

Results are printed as a comparison table.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class BenchmarkResult:
    protocol: str
    operation: str
    iterations: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float


async def benchmark_rest(customer_id: str, iterations: int = 50) -> BenchmarkResult:
    """Benchmark REST API calls to Customer Service."""
    url = f"http://localhost:8001/v1/customers/{customer_id}"
    latencies = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Warmup
        for _ in range(3):
            try:
                await client.get(url)
            except httpx.ConnectError:
                return BenchmarkResult(
                    protocol="REST",
                    operation="get_customer",
                    iterations=0,
                    avg_ms=0,
                    p50_ms=0,
                    p95_ms=0,
                    p99_ms=0,
                    min_ms=0,
                    max_ms=0,
                )

        for _ in range(iterations):
            start = time.perf_counter()
            await client.get(url)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

    return _compute_result("REST", "get_customer", iterations, latencies)


async def benchmark_mcp(customer_id: str, iterations: int = 50) -> BenchmarkResult:
    """Benchmark MCP tool calls (direct import mode)."""
    try:
        from infrastructure.mcp.customer_mcp_server import get_customer_profile
    except ImportError:
        return BenchmarkResult(
            protocol="MCP",
            operation="get_customer",
            iterations=0,
            avg_ms=0,
            p50_ms=0,
            p95_ms=0,
            p99_ms=0,
            min_ms=0,
            max_ms=0,
        )

    latencies = []

    # Warmup
    for _ in range(3):
        await get_customer_profile(customer_id=customer_id)

    for _ in range(iterations):
        start = time.perf_counter()
        await get_customer_profile(customer_id=customer_id)
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)

    return _compute_result("MCP", "get_customer", iterations, latencies)


async def benchmark_grpc(customer_id: str, iterations: int = 50) -> BenchmarkResult:
    """Benchmark gRPC calls (placeholder — gRPC server not yet implemented)."""
    # gRPC server is defined in .proto but not implemented as a running service yet
    # This is a placeholder that estimates based on typical gRPC overhead
    latencies = []

    for _ in range(iterations):
        start = time.perf_counter()
        # Simulate gRPC call overhead (serialization + deserialization)
        await asyncio.sleep(0.001)  # ~1ms simulated
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)

    result = _compute_result("gRPC (simulated)", "get_customer", iterations, latencies)
    return result


def _compute_result(protocol: str, operation: str, iterations: int, latencies: list[float]) -> BenchmarkResult:
    if not latencies:
        return BenchmarkResult(
            protocol=protocol,
            operation=operation,
            iterations=0,
            avg_ms=0,
            p50_ms=0,
            p95_ms=0,
            p99_ms=0,
            min_ms=0,
            max_ms=0,
        )

    sorted_lat = sorted(latencies)
    return BenchmarkResult(
        protocol=protocol,
        operation=operation,
        iterations=iterations,
        avg_ms=round(statistics.mean(latencies), 2),
        p50_ms=round(sorted_lat[len(sorted_lat) // 2], 2),
        p95_ms=round(sorted_lat[int(len(sorted_lat) * 0.95)], 2),
        p99_ms=round(sorted_lat[int(len(sorted_lat) * 0.99)], 2),
        min_ms=round(min(latencies), 2),
        max_ms=round(max(latencies), 2),
    )


def print_results(results: list[BenchmarkResult]) -> None:
    """Print benchmark results as a formatted table."""
    print("\n" + "=" * 80)
    print("  REST vs gRPC vs MCP — Protocol Benchmark Results")
    print("=" * 80)
    print(f"{'Protocol':<20} {'Avg (ms)':<10} {'P50':<10} {'P95':<10} {'P99':<10} {'Min':<10} {'Max':<10}")
    print("-" * 80)
    for r in results:
        if r.iterations == 0:
            print(f"{r.protocol:<20} {'(unavailable)'}")
        else:
            print(
                f"{r.protocol:<20} {r.avg_ms:<10} {r.p50_ms:<10} "
                f"{r.p95_ms:<10} {r.p99_ms:<10} {r.min_ms:<10} {r.max_ms:<10}"
            )
    print("=" * 80)

    print("\nAnalysis:")
    available = [r for r in results if r.iterations > 0]
    if len(available) >= 2:
        fastest = min(available, key=lambda r: r.avg_ms)
        print(f"  Fastest: {fastest.protocol} (avg {fastest.avg_ms}ms)")
    print("  Note: MCP adds tool schema overhead but enables dynamic discovery.")
    print("  Note: gRPC results are simulated — real numbers require running gRPC server.")
    print()


async def main():
    # Use a sample customer ID (will use mock fallback if service is down)
    customer_id = "00000000-0000-0000-0000-000000000001"
    iterations = 50

    print(f"Running {iterations} iterations per protocol...")

    results = await asyncio.gather(
        benchmark_rest(customer_id, iterations),
        benchmark_mcp(customer_id, iterations),
        benchmark_grpc(customer_id, iterations),
    )

    print_results(list(results))


if __name__ == "__main__":
    asyncio.run(main())
