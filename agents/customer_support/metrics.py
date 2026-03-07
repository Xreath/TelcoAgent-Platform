"""CustomerSupportAgent — Prometheus metrics for observability.

Tracks:
  - Agent invocation count and latency (by complaint_type, priority)
  - Tool call count (by tool name)
  - Token usage (estimated from response length)
  - Error count
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram

# ── Metrics definitions ───────────────────────────────────────

AGENT_INVOCATIONS = Counter(
    "agent_invocations_total",
    "Total number of agent invocations",
    ["agent", "complaint_type", "priority"],
)

AGENT_LATENCY = Histogram(
    "agent_latency_seconds",
    "Agent end-to-end latency in seconds",
    ["agent", "complaint_type"],
    buckets=[1, 2, 5, 10, 20, 30, 60, 120],
)

TOOL_CALLS = Counter(
    "agent_tool_calls_total",
    "Total tool calls made by the agent",
    ["agent", "tool_name"],
)

AGENT_ERRORS = Counter(
    "agent_errors_total",
    "Total errors during agent execution",
    ["agent", "error_type"],
)

TOKEN_USAGE = Counter(
    "agent_token_usage_total",
    "Estimated token usage",
    ["agent", "token_type"],  # prompt, completion
)

ACTIVE_SESSIONS = Gauge(
    "agent_active_sessions",
    "Number of currently active agent sessions",
    ["agent"],
)

AGENT_NAME = "customer_support"


class AgentMetrics:
    """Convenience wrapper around Prometheus metrics."""

    @contextmanager
    def track_invocation(self, complaint_type: str, priority: str) -> Generator[None, None, None]:
        """Context manager to track a full agent invocation."""
        AGENT_INVOCATIONS.labels(
            agent=AGENT_NAME,
            complaint_type=complaint_type,
            priority=priority,
        ).inc()
        ACTIVE_SESSIONS.labels(agent=AGENT_NAME).inc()

        start = time.perf_counter()
        try:
            yield
        except Exception as e:
            AGENT_ERRORS.labels(
                agent=AGENT_NAME,
                error_type=type(e).__name__,
            ).inc()
            raise
        finally:
            duration = time.perf_counter() - start
            AGENT_LATENCY.labels(
                agent=AGENT_NAME,
                complaint_type=complaint_type,
            ).observe(duration)
            ACTIVE_SESSIONS.labels(agent=AGENT_NAME).dec()

    def track_tool_call(self, tool_name: str) -> None:
        """Record a tool call."""
        TOOL_CALLS.labels(agent=AGENT_NAME, tool_name=tool_name).inc()

    def track_tokens(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token usage."""
        TOKEN_USAGE.labels(agent=AGENT_NAME, token_type="prompt").inc(prompt_tokens)
        TOKEN_USAGE.labels(agent=AGENT_NAME, token_type="completion").inc(completion_tokens)

    def track_error(self, error_type: str) -> None:
        """Record an error."""
        AGENT_ERRORS.labels(agent=AGENT_NAME, error_type=error_type).inc()
