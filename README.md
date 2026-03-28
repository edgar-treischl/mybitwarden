# envmaker

> Generate `.env` files from your [Bitwarden](https://bitwarden.com) vault — no copying, no git-committed secrets, no custom encryption.

```
.env.example  ──►  envmaker pull  ──►  .env
                        │
                  Bitwarden vault
```

## Installation

**Global install (recommended)** — makes `envmaker` available in every terminal session:

```bash
pipx install git+https://github.com/yourusername/mybitwarden.git
```

Or, if you have a local clone and want edits reflected immediately:

```bash
pipx install --editable /path/to/mybitwarden
```

**Project-local install:**

```bash
pip install envmaker
```

Requires Python ≥ 3.11 and the [Bitwarden CLI](https://bitwarden.com/help/cli/) (`bw`) on your `PATH`.

## Quick start

```bash
cd my-repo
envmaker init    # creates .envmakerconfig → points to a Bitwarden item
envmaker pull    # writes .env from Bitwarden secrets
```

## Commands

| Command | Description |
|---------|-------------|
| `envmaker init` | Initialise `.envmakerconfig` for the current repo |
| `envmaker pull` | Fetch secrets from Bitwarden and write `.env` |
| `envmaker push` | Create or update the Bitwarden item from the current `.env` |
| `envmaker status` | Show which variables are present, missing, or out of sync |

## How it works

1. Each repository contains a `.env.example` listing the variable names it needs.
2. `envmaker pull` reads that file, fetches the matching secrets from the configured Bitwarden item, and writes a `.env` locally.
3. Any variable not found in Bitwarden is prompted for interactively and can optionally be stored back.

## Configuration

`envmaker init` creates an `.envmakerconfig` file (gitignored) in the project root:

```toml
[bitwarden]
item_name = "my-repo secrets"   # or use item_id for a stable reference

[mapping]
DATABASE_URL = "db_url"         # map .env key → Bitwarden custom field name
```

Resolution order for the Bitwarden item: `item_id` → `item_name` → directory name.

## Session handling

`envmaker` reads `BW_SESSION` from the environment. If it is not set, it runs `bw unlock --raw` and prompts for your master password automatically.

## Design principles

- **Secrets never in git** — `.env` and `.envmakerconfig` are always gitignored
- **No background daemons** — fully on-demand
- **No custom crypto** — all storage delegated to Bitwarden
- **Minimal dependencies** — only `click` and `python-dotenv`

## Documentation

Full documentation is available at the [project docs site](https://yourusername.github.io/mybitwarden/).

## License

MIT