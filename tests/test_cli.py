"""Integration-level tests for the envmaker CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envmaker.bitwarden import BitwardenItem, BitwardenItemNotFoundError
from envmaker.cli import main

SESSION = "test-session-token"


def _make_item(
    item_id: str = "abc123",
    name: str = "myproject",
    fields: dict | None = None,
) -> BitwardenItem:
    fields = fields or {}
    raw = {
        "id": item_id,
        "name": name,
        "type": 2,
        "fields": [{"name": k, "value": v, "type": 0} for k, v in fields.items()],
        "secureNote": {"type": 0},
        "reprompt": 0,
    }
    return BitwardenItem(id=item_id, name=name, fields=fields, raw=raw)


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------


class TestPull:
    def test_pull_writes_env_file(self, runner: CliRunner, tmp_repo: Path) -> None:
        item = _make_item(
            fields={"DATABASE_URL": "postgres://localhost", "API_KEY": "k1", "SECRET_TOKEN": "s1"}
        )
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_factory.return_value.get_item.return_value = item
            result = runner.invoke(
                main,
                [
                    "pull",
                    "--example", str(tmp_repo / ".env.example"),
                    "--output", str(tmp_repo / ".env"),
                ],
            )

        assert result.exit_code == 0, result.output
        assert "Written 3 variable(s)" in result.output
        content = (tmp_repo / ".env").read_text()
        assert "DATABASE_URL=postgres://localhost" in content
        assert "API_KEY=k1" in content

    def test_pull_prompts_for_missing_vars(self, runner: CliRunner, tmp_repo: Path) -> None:
        item = _make_item(fields={"DATABASE_URL": "postgres://localhost"})
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_factory.return_value.get_item.return_value = item
            result = runner.invoke(
                main,
                [
                    "pull",
                    "--example", str(tmp_repo / ".env.example"),
                    "--output", str(tmp_repo / ".env"),
                ],
                input="my-api-key\nmy-secret\n",
            )

        assert result.exit_code == 0, result.output
        content = (tmp_repo / ".env").read_text()
        assert "API_KEY=my-api-key" in content
        assert "SECRET_TOKEN=my-secret" in content

    def test_pull_no_prompt_fails_when_missing(self, runner: CliRunner, tmp_repo: Path) -> None:
        item = _make_item(fields={"DATABASE_URL": "postgres://localhost"})
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_factory.return_value.get_item.return_value = item
            result = runner.invoke(
                main,
                [
                    "pull",
                    "--example", str(tmp_repo / ".env.example"),
                    "--output", str(tmp_repo / ".env"),
                    "--no-prompt",
                ],
            )

        assert result.exit_code != 0
        assert "Missing" in result.output

    def test_pull_missing_example_fails(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            main,
            ["pull", "--example", str(tmp_path / "nope.example"), "--output", str(tmp_path / ".env")],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_pull_uses_envmakerconfig(self, runner: CliRunner, tmp_repo: Path) -> None:
        config_file = tmp_repo / ".envmakerconfig"
        config_file.write_text('[bitwarden]\nitem_name = "custom-item"\n')
        item = _make_item(
            name="custom-item",
            fields={"DATABASE_URL": "postgres://db", "API_KEY": "k2", "SECRET_TOKEN": "s2"},
        )
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_client = mock_factory.return_value
            mock_client.get_item.return_value = item
            result = runner.invoke(
                main,
                [
                    "pull",
                    "--example", str(tmp_repo / ".env.example"),
                    "--output", str(tmp_repo / ".env"),
                    "--config", str(config_file),
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.get_item.assert_called_once_with("custom-item")

    def test_pull_applies_field_mapping(self, runner: CliRunner, tmp_repo: Path) -> None:
        config_file = tmp_repo / ".envmakerconfig"
        config_file.write_text(
            '[bitwarden]\nitem_name = "proj"\n\n[mapping]\nDATABASE_URL = "db_url"\n'
        )
        item = _make_item(
            fields={"db_url": "postgres://mapped", "API_KEY": "k", "SECRET_TOKEN": "s"}
        )
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_factory.return_value.get_item.return_value = item
            result = runner.invoke(
                main,
                [
                    "pull",
                    "--example", str(tmp_repo / ".env.example"),
                    "--output", str(tmp_repo / ".env"),
                    "--config", str(config_file),
                ],
            )

        assert result.exit_code == 0, result.output
        content = (tmp_repo / ".env").read_text()
        assert "DATABASE_URL=postgres://mapped" in content


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


class TestPush:
    def test_push_calls_create_or_update(self, runner: CliRunner, tmp_repo: Path) -> None:
        (tmp_repo / ".env").write_text("DATABASE_URL=postgres://localhost\nAPI_KEY=k\n")
        saved_item = _make_item(fields={"DATABASE_URL": "postgres://localhost", "API_KEY": "k"})
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_client = mock_factory.return_value
            mock_client.create_or_update_item.return_value = saved_item
            result = runner.invoke(
                main,
                ["push", "--env-file", str(tmp_repo / ".env"), "--yes"],
            )

        assert result.exit_code == 0, result.output
        assert "Secrets saved" in result.output
        mock_client.create_or_update_item.assert_called_once()

    def test_push_missing_env_file_fails(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            main, ["push", "--env-file", str(tmp_path / "nope"), "--yes"]
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_push_prompts_confirmation_without_yes(
        self, runner: CliRunner, tmp_repo: Path
    ) -> None:
        (tmp_repo / ".env").write_text("KEY=val\n")
        saved = _make_item(fields={"KEY": "val"})
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_factory.return_value.create_or_update_item.return_value = saved
            result = runner.invoke(
                main,
                ["push", "--env-file", str(tmp_repo / ".env")],
                input="y\n",
            )
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInit:
    def test_creates_config_file(self, runner: CliRunner) -> None:
        with runner.isolated_filesystem() as td:
            result = runner.invoke(main, ["init", "--item-name", "myproject"])
            config = Path(td) / ".envmakerconfig"
            assert result.exit_code == 0, result.output
            assert config.exists()
            assert "myproject" in config.read_text()

    def test_fails_if_config_exists(self, runner: CliRunner) -> None:
        with runner.isolated_filesystem() as td:
            Path(td, ".envmakerconfig").write_text('[bitwarden]\nitem_name = "old"\n')
            result = runner.invoke(main, ["init", "--item-name", "new"])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_force_overwrites_existing(self, runner: CliRunner) -> None:
        with runner.isolated_filesystem() as td:
            Path(td, ".envmakerconfig").write_text('[bitwarden]\nitem_name = "old"\n')
            result = runner.invoke(main, ["init", "--item-name", "new", "--force"])
            assert result.exit_code == 0
            assert "new" in Path(td, ".envmakerconfig").read_text()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_all_present_exits_zero(self, runner: CliRunner, tmp_repo: Path) -> None:
        item = _make_item(
            fields={"DATABASE_URL": "x", "API_KEY": "y", "SECRET_TOKEN": "z"}
        )
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_factory.return_value.get_item.return_value = item
            result = runner.invoke(
                main,
                ["status", "--example", str(tmp_repo / ".env.example")],
            )
        assert result.exit_code == 0, result.output
        assert "3 variable(s) found" in result.output

    def test_missing_vars_exits_nonzero(self, runner: CliRunner, tmp_repo: Path) -> None:
        item = _make_item(fields={"DATABASE_URL": "x"})
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_factory.return_value.get_item.return_value = item
            result = runner.invoke(
                main,
                ["status", "--example", str(tmp_repo / ".env.example")],
            )
        assert result.exit_code != 0
        assert "missing" in result.output.lower()

    def test_item_not_found_exits_nonzero(self, runner: CliRunner, tmp_repo: Path) -> None:
        with patch("envmaker.cli._get_client") as mock_factory:
            mock_factory.return_value.get_item.side_effect = BitwardenItemNotFoundError(
                "not found"
            )
            result = runner.invoke(
                main,
                ["status", "--example", str(tmp_repo / ".env.example")],
            )
        assert result.exit_code != 0
