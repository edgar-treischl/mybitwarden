# envmaker

**envmaker** is a lightweight CLI that generates `.env` files by pulling secrets from your personal [Bitwarden](https://bitwarden.com) vault — no copying, no git-committed secrets, no custom encryption.

## How it works

```
.env.example  ──►  envmaker pull  ──►  .env
                        │
                  Bitwarden vault
```

1. Each repository contains a `.env.example` listing the variable names it needs.
2. `envmaker pull` reads that file, fetches the matching secrets from Bitwarden, and writes a `.env` locally.
3. Any variable not found in Bitwarden is prompted for interactively and can be stored back.

## Quick start

```bash
pip install envmaker      # or: pip install -e .

cd my-repo
envmaker init             # create .envmakerconfig → points to a Bitwarden item
envmaker pull             # writes .env from Bitwarden
```

## Why Bitwarden?

- Free, open-source, and self-hostable
- Official CLI (`bw`) with JSON output — no web scraping
- Already used for password management by many developers
- Secrets stay encrypted at rest; never touch your filesystem permanently

## Design principles

- **Secrets never in git** — `.env` is always gitignored
- **No background daemons** — fully on-demand
- **No custom crypto** — all storage delegated to Bitwarden
- **Minimal dependencies** — only `click` and `python-dotenv`
