"""Shared LLM client with two backends.

- AnthropicBackend: real calls, used when ANTHROPIC_API_KEY is set (or SDR_LLM=anthropic).
  Captures per-call latency and token usage so the evaluation suite can report
  cost/latency per message.
- MockBackend: no network. Lets the WHOLE system run and be tested offline.

Set SDR_LLM=mock to force mock even if a key exists.
"""
from __future__ import annotations

import os
import time

# Approx. USD per 1M tokens, by model (input, output). Update to your contract pricing.
PRICES = {
    "claude-3-5-sonnet-latest": (3.0, 15.0),
    "claude-3-5-haiku-latest": (0.80, 4.0),
    "default": (3.0, 15.0),
}


def cost_usd(usage, model: str) -> float | None:
    if usage is None:
        return None
    pin, pout = PRICES.get(model, PRICES["default"])
    it = getattr(usage, "input_tokens", 0) or 0
    ot = getattr(usage, "output_tokens", 0) or 0
    return (it / 1_000_000) * pin + (ot / 1_000_000) * pout


class MockBackend:
    name = "mock"

    def __init__(self) -> None:
        self.last_latency = 0.0
        self.last_usage = None
        self.model = "mock"

    def complete(self, system: str, user: str) -> str:  # not used in mock paths
        return ""


class AnthropicBackend:
    name = "anthropic"

    def __init__(self) -> None:
        import anthropic  # optional dependency
        self.client = anthropic.Anthropic()
        self.model = os.environ.get("SDR_MODEL", "claude-3-5-sonnet-latest")
        self.last_latency = 0.0
        self.last_usage = None

    def complete(self, system: str, user: str) -> str:
        t0 = time.perf_counter()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        self.last_latency = time.perf_counter() - t0
        self.last_usage = getattr(resp, "usage", None)
        return resp.content[0].text


def _auto_backend():
    mode = os.environ.get("SDR_LLM", "").lower()
    if mode == "mock":
        return MockBackend()
    if mode == "anthropic" or os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicBackend()
        except Exception:
            return MockBackend()
    return MockBackend()


class LLMClient:
    def __init__(self, backend=None) -> None:
        self.backend = backend or _auto_backend()

    @property
    def is_mock(self) -> bool:
        return isinstance(self.backend, MockBackend)

    @property
    def name(self) -> str:
        return self.backend.name

    @property
    def model(self) -> str:
        return getattr(self.backend, "model", "unknown")

    @property
    def last_latency(self) -> float:
        return getattr(self.backend, "last_latency", 0.0)

    @property
    def last_cost(self) -> float | None:
        return cost_usd(getattr(self.backend, "last_usage", None), self.model)

    def complete(self, system: str, user: str) -> str:
        return self.backend.complete(system, user)
