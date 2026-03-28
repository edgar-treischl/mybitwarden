"""Shared fixtures for the envmaker test suite."""

import json
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """A temporary directory containing a minimal .env.example."""
    (tmp_path / ".env.example").write_text(
        "DATABASE_URL=\nAPI_KEY=\nSECRET_TOKEN=\n", encoding="utf-8"
    )
    return tmp_path


def make_bw_json(name: str = "myproject", fields: dict | None = None) -> str:
    """Return a JSON string that mimics a ``bw get item`` response."""
    return json.dumps(
        {
            "id": "abc123",
            "name": name,
            "type": 2,
            "fields": [
                {"name": k, "value": v, "type": 0}
                for k, v in (fields or {}).items()
            ],
            "secureNote": {"type": 0},
            "reprompt": 0,
        }
    )
