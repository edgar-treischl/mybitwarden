"""Read and write .envmakerconfig TOML files."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_FILENAME = ".envmakerconfig"


@dataclass
class EnvmakerConfig:
    """Parsed representation of a .envmakerconfig file."""

    item_name: str = ""
    item_id: Optional[str] = None
    # Maps .env variable name → Bitwarden custom-field name
    mapping: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> "EnvmakerConfig":
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise tomllib.TOMLDecodeError(f"{path}: {exc}") from exc
        bw = data.get("bitwarden", {})
        return cls(
            item_name=bw.get("item_name", ""),
            item_id=bw.get("item_id"),
            mapping=data.get("mapping", {}),
        )

    @staticmethod
    def _toml_str(value: str) -> str:
        """Return *value* as a quoted TOML basic string with required escapes."""
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    def to_toml(self, include_mapping_hint: bool = False) -> str:
        lines = ["[bitwarden]"]
        if self.item_name:
            lines.append(f"item_name = {self._toml_str(self.item_name)}")
        if self.item_id:
            lines.append(f"item_id = {self._toml_str(self.item_id)}")
        if self.mapping:
            lines.append("")
            lines.append("[mapping]")
            for env_var, bw_field in self.mapping.items():
                lines.append(f"{env_var} = {self._toml_str(bw_field)}")
        elif include_mapping_hint:
            lines.append("")
            lines.append(
                "# [mapping]"
            )
            lines.append(
                "# Uncomment to map .env variable names to differently-named Bitwarden"
                " custom fields."
            )
            lines.append("# DATABASE_URL = \"db_connection_string\"")
        return "\n".join(lines) + "\n"


def find_config(start: Optional[Path] = None) -> Optional[Path]:
    """Walk from *start* (default: CWD) upward, returning the first
    .envmakerconfig found, or ``None`` if there is none.
    """
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None
