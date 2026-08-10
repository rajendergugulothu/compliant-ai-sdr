"""Load a compliance policy from JSON."""
from __future__ import annotations

import json


def load_policy(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
