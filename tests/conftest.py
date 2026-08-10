import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sdr_eval.llm import LLMClient, MockBackend  # noqa: E402
from sdr_eval.policy import load_policy  # noqa: E402


@pytest.fixture
def policy():
    return load_policy(os.path.join(ROOT, "policies", "outbound-policy.json"))


@pytest.fixture
def product():
    with open(os.path.join(ROOT, "config", "product.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_client():
    """A forced-mock LLM client so tests never hit the network."""
    return LLMClient(backend=MockBackend())
