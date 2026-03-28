"""Parse and write .env / .env.example files."""

from __future__ import annotations

import re
from pathlib import Path


def parse_env_example(path: Path) -> list[str]:
    """Return the ordered list of variable names declared in a .env.example file.

    Lines that are blank, start with ``#``, or cannot be parsed as a shell
    variable assignment are silently ignored.
    """
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(\s*=.*)?$", line)
        if match:
            names.append(match.group(1))
    return names


def read_env_file(path: Path) -> dict[str, str]:
    """Read a .env file and return a ``{name: value}`` mapping.

    Surrounding single or double quotes are stripped from values.
    """
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env[key] = value
    return env


def write_env_file(path: Path, variables: dict[str, str]) -> None:
    """Write *variables* to *path* in .env format.

    Values that contain spaces, quotes, or newlines are double-quoted.
    """
    lines: list[str] = []
    for key, value in variables.items():
        needs_quoting = any(c in value for c in (' ', '"', "'", '\n', '\r'))
        if needs_quoting:
            escaped = value.replace('"', '\\"')
            lines.append(f'{key}="{escaped}"')
        else:
            lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
