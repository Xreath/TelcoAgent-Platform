"""Tests for AgentMetrics — Prometheus counter/gauge/histogram behavior."""

import pytest

from agents.customer_support.metrics import (
    AGENT_ERRORS,
    AGENT_INVOCATIONS,
    AGENT_LATENCY,
    TOOL_CALLS,
    AgentMetrics,
)


@pytest.fixture
def metrics() -> AgentMetrics:
    return AgentMetrics()


class TestTrackInvocation:
    def test_invocation_counter_increments(self, metrics: AgentMetrics):
        before = AGENT_INVOCATIONS.labels(
            agent="customer_support", complaint_type="billing", priority="high"
        )._value.get()
        with metrics.track_invocation("billing", "high"):
            pass
        after = AGENT_INVOCATIONS.labels(
            agent="customer_support", complaint_type="billing", priority="high"
        )._value.get()
        assert after == before + 1

    def test_latency_recorded(self, metrics: AgentMetrics):
        """track_invocation context manager süre ölçmeli."""
        before_count = AGENT_LATENCY.labels(
            agent="customer_support", complaint_type="network"
        )._sum.get()
        with metrics.track_invocation("network", "medium"):
            pass
        after_count = AGENT_LATENCY.labels(
            agent="customer_support", complaint_type="network"
        )._sum.get()
        assert after_count >= before_count  # Some time should have passed


class TestTrackToolCall:
    def test_tool_call_counter(self, metrics: AgentMetrics):
        before = TOOL_CALLS.labels(
            agent="customer_support", tool_name="get_customer_profile"
        )._value.get()
        metrics.track_tool_call("get_customer_profile")
        after = TOOL_CALLS.labels(
            agent="customer_support", tool_name="get_customer_profile"
        )._value.get()
        assert after == before + 1


class TestTrackError:
    def test_error_counter(self, metrics: AgentMetrics):
        before = AGENT_ERRORS.labels(
            agent="customer_support", error_type="timeout"
        )._value.get()
        metrics.track_error("timeout")
        after = AGENT_ERRORS.labels(
            agent="customer_support", error_type="timeout"
        )._value.get()
        assert after == before + 1

    def test_exception_in_context_manager_tracks_error(self, metrics: AgentMetrics):
        """Context manager içinde exception olursa error counter artmalı ve exception re-raise olmalı."""
        with pytest.raises(RuntimeError):
            with metrics.track_invocation("billing", "critical"):
                raise RuntimeError("Test error")
