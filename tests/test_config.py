"""Tests for envmaker.config."""

from pathlib import Path

import pytest

from envmaker.config import CONFIG_FILENAME, EnvmakerConfig, find_config


class TestEnvmakerConfig:
    def test_from_file_basic(self, tmp_path: Path) -> None:
        f = tmp_path / CONFIG_FILENAME
        f.write_text('[bitwarden]\nitem_name = "myproject"\n')
        config = EnvmakerConfig.from_file(f)
        assert config.item_name == "myproject"
        assert config.item_id is None
        assert config.mapping == {}

    def test_from_file_with_item_id(self, tmp_path: Path) -> None:
        f = tmp_path / CONFIG_FILENAME
        f.write_text('[bitwarden]\nitem_id = "abc-123"\n')
        config = EnvmakerConfig.from_file(f)
        assert config.item_id == "abc-123"

    def test_from_file_with_mapping(self, tmp_path: Path) -> None:
        f = tmp_path / CONFIG_FILENAME
        f.write_text(
            '[bitwarden]\nitem_name = "proj"\n\n'
            '[mapping]\nDATABASE_URL = "db_url"\n'
        )
        config = EnvmakerConfig.from_file(f)
        assert config.mapping == {"DATABASE_URL": "db_url"}

    def test_to_toml_roundtrip(self, tmp_path: Path) -> None:
        original = EnvmakerConfig(
            item_name="myproject", mapping={"KEY": "bw_key"}
        )
        f = tmp_path / CONFIG_FILENAME
        f.write_text(original.to_toml())
        reloaded = EnvmakerConfig.from_file(f)
        assert reloaded.item_name == original.item_name
        assert reloaded.mapping == original.mapping

    def test_to_toml_omits_empty_sections(self) -> None:
        config = EnvmakerConfig(item_name="proj")
        toml = config.to_toml()
        assert "[mapping]" not in toml


class TestFindConfig:
    def test_finds_in_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        f = tmp_path / CONFIG_FILENAME
        f.write_text('[bitwarden]\nitem_name = "test"\n')
        assert find_config() == f

    def test_finds_in_parent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        monkeypatch.chdir(subdir)
        f = tmp_path / CONFIG_FILENAME
        f.write_text('[bitwarden]\nitem_name = "test"\n')
        assert find_config() == f

    def test_returns_none_when_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert find_config() is None
