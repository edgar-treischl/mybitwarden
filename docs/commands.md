# Commands

## envmaker pull

Fetch secrets from Bitwarden and write a `.env` file.

```
envmaker pull [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--example PATH` | `.env.example` | Path to the `.env.example` file |
| `--output PATH` | `.env` | Destination path for the generated `.env` |
| `--config PATH` | auto-discovered | Path to a `.envmakerconfig` |
| `--no-prompt` | off | Fail instead of prompting for missing secrets |

**Examples**

```bash
# Basic usage — reads .env.example, writes .env
envmaker pull

# Custom paths
envmaker pull --example config/.env.example --output config/.env

# CI: fail fast if any secret is missing in Bitwarden
envmaker pull --no-prompt
```

**Item resolution order**

1. `item_id` in `.envmakerconfig` (most specific)
2. `item_name` in `.envmakerconfig`
3. Current directory name (fallback)

---

## envmaker push

Push secrets from a local `.env` file up to Bitwarden.

```
envmaker push [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--env-file PATH` | `.env` | Source `.env` file |
| `--config PATH` | auto-discovered | Path to a `.envmakerconfig` |
| `-y / --yes` | off | Skip the confirmation prompt |

Creates the Bitwarden item if it does not exist; otherwise merges the secrets into the existing item's custom fields.

**Examples**

```bash
envmaker push          # prompts for confirmation
envmaker push --yes    # non-interactive
```

---

## envmaker init

Create a `.envmakerconfig` for the current directory.

```
envmaker init [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--item-name TEXT` | prompted | Bitwarden item name |
| `--force` | off | Overwrite an existing `.envmakerconfig` |

**Example**

```bash
envmaker init --item-name "my-project"
# ✓ Created '.envmakerconfig' with item name 'my-project'.
```

---

## envmaker status

Show which variables from `.env.example` are present or missing in Bitwarden.

```
envmaker status [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--example PATH` | `.env.example` | Path to the `.env.example` file |
| `--config PATH` | auto-discovered | Path to a `.envmakerconfig` |

Exits with code `0` if all variables are present, `1` if any are missing.

**Example output**

```
Checking Bitwarden item 'my-project'…

✓ 2 variable(s) found:
  ✓ DATABASE_URL
  ✓ API_KEY

✗ 1 variable(s) missing:
  ✗ SECRET_TOKEN
```
