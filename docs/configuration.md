# Configuration

envmaker is configured via a `.envmakerconfig` file in your project directory (or any parent directory). The file uses [TOML](https://toml.io) syntax.

Copy `.envmakerconfig.example` from the repo to get started, or run `envmaker init`.

## `[bitwarden]` section

```toml
[bitwarden]
# Name of the Bitwarden item that holds this project's secrets.
# envmaker will search by name using `bw get item <name>`.
item_name = "my-project"

# Alternatively, pin to a specific item UUID to avoid name collisions.
# item_id takes precedence over item_name when both are set.
# item_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Item resolution order

When determining which Bitwarden item to use, envmaker checks (in order):

1. `item_id` in `.envmakerconfig`
2. `item_name` in `.envmakerconfig`
3. The current directory name (automatic fallback)

## `[mapping]` section

By default, envmaker looks for a Bitwarden custom field whose name exactly matches the `.env` variable name. The `[mapping]` section lets you override this per-variable.

```toml
[mapping]
# Env var name  =  Bitwarden custom field name
DATABASE_URL     = "db_url"
API_KEY          = "api_key"
```

This is useful when:

- You share a Bitwarden item across multiple projects with different naming conventions.
- The Bitwarden field was created with a different casing or abbreviation.

## Config file discovery

envmaker walks up from the current directory to find `.envmakerconfig`, so you can place it at the repository root and invoke envmaker from any subdirectory. You can also specify the path explicitly:

```bash
envmaker pull --config /path/to/.envmakerconfig
```

## Session management

envmaker reads `BW_SESSION` from the environment. If it is not set, envmaker calls `bw status` to check whether the vault is unlocked, and prompts for your master password if it is locked.

```bash
# Pre-unlock for a session (avoids repeated prompts):
export BW_SESSION=$(bw unlock --raw)
```

!!! warning "Do not commit `.envmakerconfig` with `item_id`"
    While `.envmakerconfig` contains no secrets, the `item_id` is a UUID that
    identifies your personal vault. Committing it is generally fine for private
    repos but consider omitting it from public repositories.
