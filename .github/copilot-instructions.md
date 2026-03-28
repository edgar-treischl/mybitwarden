# Copilot Instructions

## Project Overview

`mybitwarden` is a Python CLI (`envmaker`) that generates `.env` files by pulling secrets from a personal Bitwarden vault.

```
.env.example  ──►  envmaker pull  ──►  .env
                        │
                  Bitwarden vault
```

**Core commands:** `pull` · `push` · `init` · `status`

## Build, Test & Docs

```bash
# Setup (one-time)
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Run all tests
.venv/bin/pytest

# Run a single test
.venv/bin/pytest tests/test_cli.py::TestPull::test_pull_writes_env_file

# Build docs
.venv/bin/pip install "mkdocs-material>=9.0"
.venv/bin/mkdocs build          # outputs to site/
.venv/bin/mkdocs serve          # live-reload dev server
```

## Architecture

| Module | Responsibility |
|--------|---------------|
| `envmaker/cli.py` | Click commands; calls into the other modules |
| `envmaker/bitwarden.py` | Wraps the `bw` CLI binary via `subprocess`; all Bitwarden I/O lives here |
| `envmaker/env_file.py` | Parse `.env.example`, read/write `.env` files |
| `envmaker/config.py` | Read/write `.envmakerconfig` TOML files; `find_config()` walks up the directory tree |

`BitwardenClient` encodes item payloads as base64 JSON before passing them to `bw create item` / `bw edit item` — this is what the Bitwarden CLI requires.

## Key Conventions

- **Secrets never in git** — `.env` and `.envmakerconfig` are gitignored.
- **No background processes** — fully on-demand; no daemons.
- **Bitwarden item resolution order:** `item_id` in config → `item_name` in config → `Path.cwd().name`.
- **Field mapping** — `[mapping]` in `.envmakerconfig` maps `.env` variable names to differently-named Bitwarden custom fields.
- **Session handling** — reads `BW_SESSION` env var; falls back to prompting for master password via `bw unlock --raw`.
- **Testing strategy** — all `subprocess.run` calls are mocked; `click.testing.CliRunner` is used for CLI tests; `_get_client()` is patched at the CLI layer to avoid touching Bitwarden in tests.
- **Python ≥ 3.11** required — uses `tomllib` from stdlib.
