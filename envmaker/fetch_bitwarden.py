import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

import json
import subprocess
import pandas as pd

def fetch_bitwarden(item_name_or_id: str) -> pd.DataFrame:
    def coalesce(x, y):
        return y if x is None else x

    # Get session
    bw_session = os.environ.get("BW_SESSION")
    if not bw_session:
        raise RuntimeError(
            "BW_SESSION not set.\n"
            "Add it to a .env file or export it manually."
        )

    # Run Bitwarden CLI
    try:
        result = subprocess.run(
            ["bw", "get", "item", item_name_or_id, "--session", bw_session],
            capture_output=True,
            text=True,
            check=False
        )
    except Exception as e:
        raise RuntimeError(
            "Error running Bitwarden CLI. Make sure 'bw' is installed and in PATH."
        ) from e

    raw_text = result.stdout
    cli_status = result.returncode

    if cli_status != 0 or "not found" in raw_text.lower():
        raise RuntimeError(
            f"Bitwarden item '{item_name_or_id}' not found.\n"
            "Check the item name or ID."
        )

    try:
        item = json.loads(raw_text)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse Bitwarden item JSON for '{item_name_or_id}'.")

    login_info = {
        "username": coalesce(item.get("login", {}).get("username"), None),
        "password": coalesce(item.get("login", {}).get("password"), None)
    }
    login_df = pd.DataFrame([login_info])

    fields = item.get("fields", [])
    custom_field_dict = {f.get("name"): coalesce(f.get("value"), None) for f in fields}
    custom_df = pd.DataFrame([custom_field_dict])

    secret_df = pd.concat([login_df, custom_df], axis=1)
    print(f"✅ Fetched '{item_name_or_id}' from Bitwarden successfully.")

    return secret_df

# Example usage
if __name__ == "__main__":
    secret = fetch_bitwarden("MYAPI")
    print(secret)