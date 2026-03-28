# Bitwarden CLI Setup

`envmaker` delegates all secret storage to the official Bitwarden CLI (`bw`). This page walks through the one-time setup.

## Install the Bitwarden CLI

- **macOS (Homebrew)**:

```bash
brew install bitwarden-cli
```

## Log in

Authenticates your Bitwarden account. You only need to do this once per machine.

```bash
bw login your-email@example.com
```

## Unlock your vault and export the session token

`bw unlock --raw` prints a session token. Exporting it as `BW_SESSION` lets subsequent `bw` (and `envmaker`) commands run without re-prompting for your master password.

```bash
export BW_SESSION=$(bw unlock --raw)
```

## Verify CLI access

Lists every item in your vault as JSON. A non-empty response confirms the session token is valid.

```bash
bw list items
```

## Retrieve a specific secret

Fetches the login credentials or a named custom field from a vault item. Useful for manual lookups or debugging.

```bash
# Print the username and password of an item named "MYAPI"
bw get item MYAPI | jq -r '.login.username, .login.password'

# Print the value of a custom field named "token" on the same item
bw get item MYAPI | jq -r '.fields[] | select(.name=="token") | .value'
```

## Reset CLI configuration

If you previously pointed the CLI at a self-hosted server, clear the stored config and session before switching back to Bitwarden Cloud.

```bash
rm -rf ~/.config/Bitwarden\ CLI
unset BW_SESSION
```

Then point the CLI at the correct server:

```bash
# EU cloud region
bw config server https://vault.bitwarden.com/eu
```
