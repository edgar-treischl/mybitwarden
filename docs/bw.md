# Bitwarden CLI Workflow


- **macOS (Homebrew)**:

```bash
brew install bitwarden-cli
```

Log in with your Bitwarden email + master password

```
bw login your-email@example.com
```


Unlock your vault and export session

```
export BW_SESSION=$(bw unlock --raw)
```

Verify basic CLI functionality

````
bw list items
````
You should now see all items in your vault in JSON format.


Get `MYAPI` secret via:

````
bw get item MYAPI | jq -r '.login.username, .login.password'
bw get item MYAPI | jq -r '.fields[] | select(.name=="token") | .value'
````


## Note: Reset CLI configuration (e.g. if you previously used self-hosted servers)

````
# macOS/Linux
rm -rf ~/.config/Bitwarden\ CLI
unset BW_SESSION
````

And set server to Bitwarden Cloud:

````
bw config server https://vault.bitwarden.com/eu
````
