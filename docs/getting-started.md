# Getting Started

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | `python3 --version` |
| [Bitwarden CLI](https://bitwarden.com/help/cli/) (`bw`) | `brew install bitwarden-cli` or download from the Bitwarden site |
| A Bitwarden account | Free tier is sufficient |

## Installation

```bash
pip install envmaker
```

Or from source:

```bash
git clone https://github.com/yourusername/mybitwarden
cd mybitwarden
pip install -e ".[dev]"
```

## First-time Bitwarden setup

Log in once with the Bitwarden CLI:

```bash
bw login
```

On subsequent runs, unlock the vault. envmaker will prompt for your master password automatically if `BW_SESSION` is not set. You can also unlock manually and export the token:

```bash
export BW_SESSION=$(bw unlock --raw)
```

## Setting up a repository

### 1. Add a `.env.example`

List every environment variable your project needs — no values, just names:

```bash
# .env.example
DATABASE_URL=
API_KEY=
SECRET_TOKEN=
```

### 2. Create a `.envmakerconfig`

Run `init` to create a config file pointing at a Bitwarden item:

```bash
envmaker init
# Bitwarden item name: my-project
```

This writes `.envmakerconfig`:

```toml
[bitwarden]
item_name = "my-project"
```

### 3. Push your secrets (first time)

If your Bitwarden item doesn't exist yet, create a `.env` manually and push it:

```bash
# Write .env manually for the first time, then:
envmaker push --yes
```

This creates a Secure Note in Bitwarden with your secrets as custom fields.

### 4. Pull on any machine

```bash
envmaker pull
# ✓ Written 3 variable(s) to '.env'.
```

## Typical workflow

```
New machine
│
├─ bw login
├─ cd my-repo
├─ envmaker pull        ← generates .env in seconds
└─ start developing
```

## Running tests

```bash
pytest                          # all tests
pytest tests/test_cli.py        # single file
pytest tests/test_cli.py::TestPull::test_pull_writes_env_file  # single test
```
