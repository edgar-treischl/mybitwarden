"""Tests for envmaker.env_file."""

from pathlib import Path

import pytest

from envmaker.env_file import parse_env_example, read_env_file, write_env_file


class TestParseEnvExample:
    def test_basic(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("DATABASE_URL=\nAPI_KEY=\n")
        assert parse_env_example(f) == ["DATABASE_URL", "API_KEY"]

    def test_ignores_blank_lines_and_comments(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("# comment\n\nKEY=\n# another comment\nOTHER_KEY=\n")
        assert parse_env_example(f) == ["KEY", "OTHER_KEY"]

    def test_placeholder_values_are_ignored(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("DATABASE_URL=postgres://example\nAPI_KEY=your-key-here\n")
        assert parse_env_example(f) == ["DATABASE_URL", "API_KEY"]

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("# just comments\n\n")
        assert parse_env_example(f) == []

    def test_preserves_order(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("Z=\nA=\nM=\n")
        assert parse_env_example(f) == ["Z", "A", "M"]


class TestWriteAndReadEnvFile:
    def test_roundtrip(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        data = {"DATABASE_URL": "postgres://localhost", "API_KEY": "secret123"}
        write_env_file(env_path, data)
        assert read_env_file(env_path) == data

    def test_read_ignores_comments(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        env_path.write_text("# comment\nKEY=value\n")
        assert read_env_file(env_path) == {"KEY": "value"}

    def test_write_quotes_values_with_spaces(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        write_env_file(env_path, {"GREETING": "hello world"})
        assert 'GREETING="hello world"' in env_path.read_text()

    def test_read_strips_double_quotes(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        env_path.write_text('KEY="hello world"\n')
        assert read_env_file(env_path) == {"KEY": "hello world"}

    def test_read_strips_single_quotes(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        env_path.write_text("KEY='plain'\n")
        assert read_env_file(env_path) == {"KEY": "plain"}

    def test_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        env_path.write_text("")
        assert read_env_file(env_path) == {}
