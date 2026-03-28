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
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        bw = data.get("bitwarden", {})
        return cls(
            item_name=bw.get("item_name", ""),
            item_id=bw.get("item_id"),
            mapping=data.get("mapping", {}),
        )

    def to_toml(self) -> str:
        lines = ["[bitwarden]"]
        if self.item_name:
            lines.append(f'item_name = "{self.item_name}"')
        if self.item_id:
            lines.append(f'item_id = "{self.item_id}"')
        if self.mapping:
            lines.append("")
            lines.append("[mapping]")
            for env_var, bw_field in self.mapping.items():
                lines.append(f'{env_var} = "{bw_field}"')
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
