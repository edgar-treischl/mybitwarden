"""Thin wrapper around the Bitwarden CLI (``bw``)."""

from __future__ import annotations

import base64
import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BitwardenError(Exception):
    """Generic error from the bw CLI."""


class BitwardenNotFoundError(BitwardenError):
    """``bw`` binary is not installed or not on PATH."""


class BitwardenSessionError(BitwardenError):
    """Vault is locked or no session token is available."""


class BitwardenItemNotFoundError(BitwardenError):
    """The requested item does not exist in the vault."""


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


@dataclass
class BitwardenItem:
    id: str
    name: str
    fields: dict[str, str] = field(default_factory=dict)
    raw: dict = field(default_factory=dict, repr=False)

    def get_field(self, name: str) -> Optional[str]:
        """Return a value by custom-field name or dot-notation path (e.g. ``login.username``)."""
        if name in self.fields:
            return self.fields[name]
        # Resolve dot-notation paths against the raw item (e.g. "login.username")
        parts = name.split(".")
        node: object = self.raw
        for part in parts:
            if not isinstance(node, dict):
                return None
            node = node.get(part)
            if node is None:
                return None
        return str(node) if node is not None else None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class BitwardenClient:
    """Wrapper around the ``bw`` CLI binary."""

    def __init__(self, session: Optional[str] = None) -> None:
        self._session: Optional[str] = session or os.environ.get("BW_SESSION")

    @property
    def session(self) -> Optional[str]:
        return self._session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, *args: str, input_text: Optional[str] = None) -> str:
        cmd = ["bw", *args]
        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise BitwardenNotFoundError(
                "Bitwarden CLI (bw) not found. "
                "Install it from https://bitwarden.com/help/cli/"
            )
        if result.returncode != 0:
            raise BitwardenError(result.stderr.strip() or f"bw {args[0]} failed")
        return result.stdout.strip()

    def _run_authed(self, *args: str) -> str:
        if not self._session:
            raise BitwardenSessionError(
                "No active Bitwarden session. "
                "Set the BW_SESSION environment variable or run 'bw unlock' first."
            )
        return self._run(*args, "--session", self._session)

    @staticmethod
    def _parse_item(data: dict) -> BitwardenItem:
        fields: dict[str, str] = {}
        for f in data.get("fields") or []:
            if f.get("name") and f.get("value") is not None:
                fields[f["name"]] = str(f["value"])
        return BitwardenItem(id=data["id"], name=data["name"], fields=fields, raw=data)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return the parsed output of ``bw status``."""
        return json.loads(self._run("status"))

    def unlock(self, password: str) -> str:
        """Unlock the vault and store the returned session token."""
        result = subprocess.run(
            ["bw", "unlock", "--raw"],
            input=password,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise BitwardenSessionError(
                "Failed to unlock vault. Check your master password."
            )
        self._session = result.stdout.strip()
        return self._session

    def get_item(self, name_or_id: str) -> BitwardenItem:
        """Retrieve an item by name or UUID."""
        try:
            output = self._run_authed("get", "item", name_or_id)
        except BitwardenNotFoundError:
            raise
        except BitwardenError as exc:
            msg = str(exc).lower()
            if "not found" in msg or "no results" in msg:
                raise BitwardenItemNotFoundError(
                    f"Item '{name_or_id}' not found in Bitwarden."
                ) from exc
            raise
        return self._parse_item(json.loads(output))

    def create_item(self, name: str, fields: dict[str, str]) -> BitwardenItem:
        """Create a new Secure Note item with the given custom fields."""
        payload = {
            "organizationId": None,
            "collectionIds": None,
            "folderId": None,
            "type": 2,
            "name": name,
            "notes": None,
            "favorite": False,
            "fields": [{"name": k, "value": v, "type": 0} for k, v in fields.items()],
            "secureNote": {"type": 0},
            "reprompt": 0,
        }
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        output = self._run_authed("create", "item", encoded)
        return self._parse_item(json.loads(output))

    def update_item(self, item: BitwardenItem, new_fields: dict[str, str]) -> BitwardenItem:
        """Merge *new_fields* into *item*'s custom fields and save."""
        raw = dict(item.raw)
        existing: dict[str, dict] = {f["name"]: f for f in raw.get("fields") or []}
        for key, value in new_fields.items():
            if key in existing:
                existing[key]["value"] = value
            else:
                existing[key] = {"name": key, "value": value, "type": 0}
        raw["fields"] = list(existing.values())
        encoded = base64.b64encode(json.dumps(raw).encode()).decode()
        output = self._run_authed("edit", "item", item.id, encoded)
        return self._parse_item(json.loads(output))

    def create_or_update_item(self, name: str, fields: dict[str, str]) -> BitwardenItem:
        """Create the item if it does not exist; otherwise merge fields."""
        try:
            existing = self.get_item(name)
            return self.update_item(existing, fields)
        except BitwardenItemNotFoundError:
            return self.create_item(name, fields)
