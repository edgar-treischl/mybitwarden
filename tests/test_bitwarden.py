"""Tests for envmaker.bitwarden (BitwardenClient)."""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from envmaker.bitwarden import (
    BitwardenClient,
    BitwardenError,
    BitwardenItem,
    BitwardenItemNotFoundError,
    BitwardenNotFoundError,
    BitwardenSessionError,
)

SESSION = "test-session-token"


def _mock_run(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    m.stderr = stderr
    return m


def _item_json(name: str = "myproject", fields: dict | None = None) -> str:
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


@pytest.fixture()
def client() -> BitwardenClient:
    return BitwardenClient(session=SESSION)


class TestGetItem:
    def test_success(self, client: BitwardenClient) -> None:
        payload = _item_json(fields={"DATABASE_URL": "postgres://localhost"})
        with patch("subprocess.run", return_value=_mock_run(stdout=payload)):
            item = client.get_item("myproject")

        assert item.name == "myproject"
        assert item.fields["DATABASE_URL"] == "postgres://localhost"

    def test_correct_command_invoked(self, client: BitwardenClient) -> None:
        payload = _item_json()
        with patch("subprocess.run", return_value=_mock_run(stdout=payload)) as mock_run:
            client.get_item("myproject")

        mock_run.assert_called_once_with(
            ["bw", "get", "item", "myproject", "--session", SESSION],
            input=None,
            capture_output=True,
            text=True,
        )

    def test_not_found_raises_item_not_found(self, client: BitwardenClient) -> None:
        with patch("subprocess.run", return_value=_mock_run(returncode=1, stderr="Not found.")):
            with pytest.raises(BitwardenItemNotFoundError):
                client.get_item("nonexistent")

    def test_no_session_raises_session_error(self) -> None:
        c = BitwardenClient(session=None)
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(BitwardenSessionError):
                c.get_item("myproject")

    def test_bw_missing_raises_not_found_error(self, client: BitwardenClient) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(BitwardenNotFoundError):
                client.get_item("myproject")


class TestUnlock:
    def test_success_stores_session(self) -> None:
        c = BitwardenClient()
        with patch("subprocess.run", return_value=_mock_run(stdout=SESSION)):
            token = c.unlock("master-password")
        assert token == SESSION
        assert c.session == SESSION

    def test_wrong_password_raises_session_error(self) -> None:
        c = BitwardenClient()
        with patch("subprocess.run", return_value=_mock_run(returncode=1, stderr="Invalid")):
            with pytest.raises(BitwardenSessionError):
                c.unlock("wrong")


class TestCreateItem:
    def test_base64_encodes_payload(self, client: BitwardenClient) -> None:
        created = _item_json(fields={"API_KEY": "secret"})
        with patch("subprocess.run", return_value=_mock_run(stdout=created)) as mock_run:
            item = client.create_item("myproject", {"API_KEY": "secret"})

        assert item.fields["API_KEY"] == "secret"
        cmd = mock_run.call_args[0][0]
        assert cmd[:3] == ["bw", "create", "item"]
        decoded = json.loads(base64.b64decode(cmd[3]))
        assert decoded["name"] == "myproject"
        assert decoded["fields"][0] == {"name": "API_KEY", "value": "secret", "type": 0}

    def test_returns_parsed_item(self, client: BitwardenClient) -> None:
        created = _item_json(name="proj", fields={"X": "1"})
        with patch("subprocess.run", return_value=_mock_run(stdout=created)):
            item = client.create_item("proj", {"X": "1"})
        assert isinstance(item, BitwardenItem)
        assert item.name == "proj"


class TestUpdateItem:
    def test_merges_new_fields(self, client: BitwardenClient) -> None:
        raw = json.loads(_item_json(fields={"OLD": "old_val"}))
        existing = BitwardenItem(id="abc123", name="proj", fields={"OLD": "old_val"}, raw=raw)
        updated_json = _item_json(fields={"OLD": "old_val", "NEW": "new_val"})

        with patch("subprocess.run", return_value=_mock_run(stdout=updated_json)) as mock_run:
            item = client.update_item(existing, {"NEW": "new_val"})

        assert item.fields["NEW"] == "new_val"
        cmd = mock_run.call_args[0][0]
        assert cmd[:3] == ["bw", "edit", "item"]
        payload = json.loads(base64.b64decode(cmd[4]))
        field_names = {f["name"] for f in payload["fields"]}
        assert {"OLD", "NEW"} == field_names

    def test_overwrites_existing_field(self, client: BitwardenClient) -> None:
        raw = json.loads(_item_json(fields={"KEY": "old"}))
        existing = BitwardenItem(id="abc123", name="proj", fields={"KEY": "old"}, raw=raw)
        updated_json = _item_json(fields={"KEY": "new"})

        with patch("subprocess.run", return_value=_mock_run(stdout=updated_json)):
            item = client.update_item(existing, {"KEY": "new"})

        assert item.fields["KEY"] == "new"


class TestCreateOrUpdateItem:
    def test_creates_when_not_found(self, client: BitwardenClient) -> None:
        created_json = _item_json()
        with patch("subprocess.run") as mock_run:
            # First call: get_item → not found; second call: create_item → success
            mock_run.side_effect = [
                _mock_run(returncode=1, stderr="Not found."),
                _mock_run(stdout=created_json),
            ]
            item = client.create_or_update_item("myproject", {"K": "v"})

        assert item.name == "myproject"

    def test_updates_when_found(self, client: BitwardenClient) -> None:
        existing_json = _item_json(fields={"K": "old"})
        updated_json = _item_json(fields={"K": "new"})
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mock_run(stdout=existing_json),  # get_item
                _mock_run(stdout=updated_json),   # edit item
            ]
            item = client.create_or_update_item("myproject", {"K": "new"})

        assert item.fields["K"] == "new"
