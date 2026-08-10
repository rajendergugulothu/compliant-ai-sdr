"""Shared LLM client with two backends.

- AnthropicBackend: real calls, used when ANTHROPIC_API_KEY is set (or SDR_LLM=anthropic).
- MockBackend: no network. Lets the WHOLE pipeline run and be tested offline.

The agent and judge check `client.is_mock` and use deterministic local logic in
mock mode, so the control flow (draft -> gate -> regenerate -> escalate) is fully
exercisable without a key. Set SDR_LLM=mock to force mock even if a key exists.
"""
from __future__ import annotations

import os


class MockBackend:
    name = "mock"

    def complete(self, system: str, user: str) -> str:  # not used in mock paths
        return ""


class AnthropicBackend:
    name = "anthropic"

    def __init__(self) -> None:
        import anthropic  # optional dependency
        self.client = anthropic.Anthropic()
        self.model = os.environ.get("SDR_MODEL", "claude-3-5-sonnet-latest")

    def complete(self, system: str, user: str) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
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

    def complete(self, system: str, user: str) -> str:
        return self.backend.complete(system, user)
