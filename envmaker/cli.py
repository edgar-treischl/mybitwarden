"""envmaker CLI — entry point and command definitions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .bitwarden import (
    BitwardenClient,
    BitwardenError,
    BitwardenItemNotFoundError,
)
from .config import CONFIG_FILENAME, EnvmakerConfig, find_config
from .env_file import parse_env_example, read_env_file, write_env_file

_DEFAULT_EXAMPLE = ".env.example"
_DEFAULT_OUTPUT = ".env"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _get_client() -> BitwardenClient:
    """Return an authenticated BitwardenClient.

    Looks for ``BW_SESSION`` in (in order):

    1. The ``BW_SESSION`` environment variable.
    2. The ``.env`` file in the current directory.

    Raises a :class:`click.ClickException` with actionable instructions when
    neither source provides a session token.
    """
    client = BitwardenClient()
    if client.session:
        return client

    env_path = Path(_DEFAULT_OUTPUT)
    if env_path.exists():
        session = read_env_file(env_path).get("BW_SESSION")
        if session:
            return BitwardenClient(session=session)

    raise click.ClickException(
        "No Bitwarden session found.\n"
        "Unlock your vault and export the session token:\n\n"
        "  export BW_SESSION=$(bw unlock --raw)\n\n"
        "Or add  BW_SESSION=<token>  to your .env file."
    )


def _load_config(config_path: Optional[Path]) -> Optional[EnvmakerConfig]:
    if config_path:
        return EnvmakerConfig.from_file(config_path)
    found = find_config()
    return EnvmakerConfig.from_file(found) if found else None


def _item_identifier(config: Optional[EnvmakerConfig]) -> str:
    """Determine which Bitwarden item to target."""
    if config and config.item_id:
        return config.item_id
    if config and config.item_name:
        return config.item_name
    return Path.cwd().name


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """envmaker — generate .env files from your Bitwarden vault."""


# ---------------------------------------------------------------------------
# envmaker pull
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--example",
    default=_DEFAULT_EXAMPLE,
    show_default=True,
    help="Path to the .env.example file.",
)
@click.option(
    "--output",
    default=_DEFAULT_OUTPUT,
    show_default=True,
    help="Destination path for the generated .env file.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to a .envmakerconfig file.",
)
@click.option(
    "--no-prompt",
    is_flag=True,
    help="Fail instead of interactively prompting for missing secrets.",
)
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt when updating an existing .env file.")
def pull(
    example: str,
    output: str,
    config_path: Optional[Path],
    no_prompt: bool,
    yes: bool,
) -> None:
    """Fetch secrets from Bitwarden and write a .env file."""
    example_path = Path(example)
    output_path = Path(output)

    if not example_path.exists():
        raise click.ClickException(f"'{example}' not found.")

    var_names = parse_env_example(example_path)
    if not var_names:
        raise click.ClickException(f"No variables found in '{example}'.")

    config = _load_config(config_path)
    client = _get_client()
    item_id = _item_identifier(config)

    click.echo(f"Fetching secrets from Bitwarden item '{item_id}'…")

    try:
        item = client.get_item(item_id)
    except BitwardenItemNotFoundError:
        click.echo(f"  Item '{item_id}' not found — will prompt for all variables.", err=True)
        item = None
    except BitwardenError as exc:
        raise click.ClickException(str(exc))

    resolved: dict[str, str] = {}
    missing: list[str] = []

    for var in var_names:
        bw_field = config.mapping.get(var, var) if config else var
        value = item.get_field(bw_field) if item else None
        if value is not None:
            resolved[var] = value
        else:
            missing.append(var)

    if missing:
        if no_prompt:
            raise click.ClickException(
                "Missing secrets: " + ", ".join(missing)
            )
        click.echo(
            f"  {len(missing)} variable(s) not found in Bitwarden — please enter them:"
        )
        for var in missing:
            resolved[var] = click.prompt(f"  {var}", hide_input=True)

    # Read existing .env to preserve local-only keys and detect changes.
    existing: dict[str, str] = {}
    if output_path.exists():
        existing = read_env_file(output_path)

    example_var_set = set(var_names)
    local_only = {k: v for k, v in existing.items() if k not in example_var_set}

    # Merge: Bitwarden-resolved vars first (in .env.example order), then local-only.
    merged = {**resolved, **local_only}

    if output_path.exists():
        if existing == merged:
            click.echo(f"✓ '{output}' is already up to date ({len(merged)} variable(s)).")
            return

        # Show what will change before asking for confirmation.
        new_vars = [v for v in var_names if v not in existing]
        updated_vars = [v for v in var_names if v in existing and existing.get(v) != resolved.get(v)]
        unchanged_count = len(var_names) - len(new_vars) - len(updated_vars)

        click.echo(f"\n  Changes to '{output}':")
        if new_vars:
            for v in new_vars:
                click.echo(f"    + {v}  (new)")
        if updated_vars:
            for v in updated_vars:
                click.echo(f"    ~ {v}  (updated)")
        if unchanged_count:
            click.echo(f"    · {unchanged_count} variable(s) unchanged")
        if local_only:
            click.echo(
                f"    ↳ {len(local_only)} local-only variable(s) will be preserved: "
                + ", ".join(local_only)
            )

        if not yes:
            click.confirm(f"\nUpdate '{output}'?", abort=True)

    write_env_file(output_path, merged)
    click.echo(f"✓ Written {len(merged)} variable(s) to '{output}'.")


# ---------------------------------------------------------------------------
# envmaker push
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--env-file",
    default=_DEFAULT_OUTPUT,
    show_default=True,
    help="Path to the .env file to push.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to a .envmakerconfig file.",
)
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt.")
def push(env_file: str, config_path: Optional[Path], yes: bool) -> None:
    """Push secrets from a .env file up to Bitwarden."""
    env_path = Path(env_file)
    if not env_path.exists():
        raise click.ClickException(f"'{env_file}' not found.")

    variables = read_env_file(env_path)
    if not variables:
        raise click.ClickException(f"No variables found in '{env_file}'.")

    config = _load_config(config_path)
    item_id = _item_identifier(config)

    if not yes:
        click.confirm(
            f"Push {len(variables)} secret(s) to Bitwarden item '{item_id}'?",
            abort=True,
        )

    client = _get_client()

    bw_fields = {
        (config.mapping.get(k, k) if config else k): v
        for k, v in variables.items()
    }

    click.echo(f"Pushing {len(bw_fields)} secret(s) to '{item_id}'…")
    try:
        saved = client.create_or_update_item(item_id, bw_fields)
        click.echo(f"✓ Secrets saved to Bitwarden item '{saved.name}' ({saved.id}).")
    except BitwardenError as exc:
        raise click.ClickException(str(exc))


# ---------------------------------------------------------------------------
# envmaker init
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--item-name",
    prompt="Bitwarden item name",
    help="Name of the Bitwarden item that holds this project's secrets.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing .envmakerconfig.")
def init(item_name: str, force: bool) -> None:
    """Create a .envmakerconfig for the current directory."""
    config_path = Path.cwd() / CONFIG_FILENAME
    if config_path.exists() and not force:
        raise click.ClickException(
            f"'{CONFIG_FILENAME}' already exists. Use --force to overwrite."
        )
    config = EnvmakerConfig(item_name=item_name)
    config_path.write_text(config.to_toml(include_mapping_hint=True), encoding="utf-8")
    click.echo(f"✓ Created '{CONFIG_FILENAME}' with item name '{item_name}'.")
    click.echo()
    click.echo("Next steps:")
    click.echo("  • Run 'envmaker pull' to fetch secrets from Bitwarden.")
    click.echo("  • Run 'envmaker push' to upload your local .env to Bitwarden.")
    click.echo()
    click.echo("Field mapping (optional):")
    click.echo(
        "  If a .env variable name differs from its Bitwarden custom-field name,"
    )
    click.echo(f"  add a [mapping] section to '{CONFIG_FILENAME}'.  Example:")
    click.echo()
    click.echo("    [mapping]")
    click.echo('    DATABASE_URL = "db_connection_string"')
    click.echo()
    click.echo(
        "  This maps DATABASE_URL in your .env to the field 'db_connection_string'"
        " in Bitwarden."
    )


# ---------------------------------------------------------------------------
# envmaker status
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--example",
    default=_DEFAULT_EXAMPLE,
    show_default=True,
    help="Path to the .env.example file.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to a .envmakerconfig file.",
)
def status(example: str, config_path: Optional[Path]) -> None:
    """Show which variables from .env.example are present in Bitwarden."""
    example_path = Path(example)
    if not example_path.exists():
        raise click.ClickException(f"'{example}' not found.")

    var_names = parse_env_example(example_path)
    if not var_names:
        raise click.ClickException(f"No variables found in '{example}'.")

    config = _load_config(config_path)
    client = _get_client()
    item_id = _item_identifier(config)

    click.echo(f"Checking Bitwarden item '{item_id}'…")

    try:
        item = client.get_item(item_id)
    except BitwardenItemNotFoundError:
        click.echo(f"  Item '{item_id}' not found in Bitwarden.\n")
        click.echo(f"✗ All {len(var_names)} variable(s) are missing.")
        sys.exit(1)
    except BitwardenError as exc:
        raise click.ClickException(str(exc))

    present: list[str] = []
    missing: list[str] = []
    for var in var_names:
        bw_field = config.mapping.get(var, var) if config else var
        (present if item.get_field(bw_field) is not None else missing).append(var)

    if present:
        click.echo(f"\n✓ {len(present)} variable(s) found:")
        for var in present:
            click.echo(f"  ✓ {var}")
    if missing:
        click.echo(f"\n✗ {len(missing)} variable(s) missing:")
        for var in missing:
            click.echo(f"  ✗ {var}")
        sys.exit(1)
