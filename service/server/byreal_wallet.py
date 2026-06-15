"""
Encrypted wallet storage for platform-managed Byreal real execution.

Security model
--------------
Opera supports multiple agents, each potentially configured for real on-chain execution
across both Solana (byreal-cli) and Hyperliquid (byreal-perps-cli).  Storing raw private
keys in the database would be an unacceptable risk in a multi-tenant environment.

This module uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256, from the
`cryptography` library) to encrypt wallet secrets at rest.  The encryption key is held
only in the environment variable BYREAL_WALLET_ENCRYPTION_KEY, not in the database —
meaning a database dump alone cannot recover any private keys.

Key properties:
  - Per-agent, per-chain wallet configs: each (agent_id, chain) pair is an independent row.
    Compromising one agent's key material does not affect others.
  - Enabled flag: wallets can be disabled without deletion, preserving the audit trail.
  - Public key masking: `mask_pubkey()` truncates addresses for display (6...4 chars),
    so wallet addresses visible in the UI and logs are never the full key.
  - Best-effort CLI configuration: `configure_cli_wallet()` injects the decrypted secret
    into the relevant CLI at run time and never writes it to disk.

The error raised when BYREAL_WALLET_ENCRYPTION_KEY is absent includes the exact command
to generate a fresh key, making production setup self-documenting.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken

from config import BYREAL_WALLET_ENCRYPTION_KEY
from database import get_db_connection

logger = logging.getLogger(__name__)

SUPPORTED_CHAINS = {"solana", "hyperliquid"}


class ByrealWalletError(RuntimeError):
    pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fernet() -> Fernet:
    key = (os.getenv("BYREAL_WALLET_ENCRYPTION_KEY") or BYREAL_WALLET_ENCRYPTION_KEY or "").strip()
    if not key:
        raise ByrealWalletError(
            "BYREAL_WALLET_ENCRYPTION_KEY is not configured. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise ByrealWalletError("Invalid BYREAL_WALLET_ENCRYPTION_KEY") from exc


def encrypt_secret(secret: str) -> str:
    payload = (secret or "").strip()
    if not payload:
        raise ByrealWalletError("wallet secret is required")
    token = _fernet().encrypt(payload.encode("utf-8"))
    return token.decode("ascii")


def decrypt_secret(encrypted: str) -> str:
    if not encrypted:
        raise ByrealWalletError("encrypted secret is missing")
    try:
        return _fernet().decrypt(encrypted.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ByrealWalletError("unable to decrypt wallet secret") from exc


def mask_pubkey(pubkey: Optional[str]) -> Optional[str]:
    if not pubkey:
        return None
    value = pubkey.strip()
    if len(value) <= 12:
        return value
    return f"{value[:6]}...{value[-4:]}"


def save_wallet_config(agent_id: int, chain: str, secret: str, pubkey: Optional[str] = None) -> dict[str, Any]:
    normalized_chain = (chain or "").strip().lower()
    if normalized_chain not in SUPPORTED_CHAINS:
        raise ByrealWalletError(f"unsupported chain: {chain}")

    encrypted = encrypt_secret(secret)
    now = _utc_now_iso()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO byreal_wallet_configs (agent_id, chain, pubkey, encrypted_secret, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(agent_id, chain) DO UPDATE SET
            pubkey = excluded.pubkey,
            encrypted_secret = excluded.encrypted_secret,
            enabled = 1,
            updated_at = excluded.updated_at
        """,
        (agent_id, normalized_chain, pubkey, encrypted, now, now),
    )
    conn.commit()
    conn.close()
    return get_wallet_status(agent_id, chain=normalized_chain)


def delete_wallet_config(agent_id: int, chain: Optional[str] = None) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    if chain:
        cursor.execute(
            "DELETE FROM byreal_wallet_configs WHERE agent_id = ? AND chain = ?",
            (agent_id, chain.strip().lower()),
        )
    else:
        cursor.execute("DELETE FROM byreal_wallet_configs WHERE agent_id = ?", (agent_id,))
    conn.commit()
    conn.close()


def get_wallet_config(agent_id: int, chain: str, *, include_secret: bool = False) -> Optional[dict[str, Any]]:
    normalized_chain = (chain or "").strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, agent_id, chain, pubkey, encrypted_secret, enabled, created_at, updated_at
        FROM byreal_wallet_configs
        WHERE agent_id = ? AND chain = ? AND COALESCE(enabled, 1) = 1
        """,
        (agent_id, normalized_chain),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    if include_secret:
        data["secret"] = decrypt_secret(data.get("encrypted_secret") or "")
    else:
        data.pop("encrypted_secret", None)
    return data


def get_wallet_status(agent_id: int, chain: Optional[str] = None) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if chain:
        cursor.execute(
            """
            SELECT chain, pubkey, enabled, updated_at
            FROM byreal_wallet_configs
            WHERE agent_id = ? AND chain = ?
            """,
            (agent_id, chain.strip().lower()),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {"connected": False, "chain": chain, "address": None}
        return {
            "connected": bool(row["enabled"]),
            "chain": row["chain"],
            "address": mask_pubkey(row["pubkey"]),
            "updated_at": row["updated_at"],
        }

    cursor.execute(
        """
        SELECT chain, pubkey, enabled, updated_at
        FROM byreal_wallet_configs
        WHERE agent_id = ?
        """,
        (agent_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    wallets = [
        {
            "chain": row["chain"],
            "connected": bool(row["enabled"]),
            "address": mask_pubkey(row["pubkey"]),
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]
    return {"wallets": wallets, "connected": any(item["connected"] for item in wallets)}


def configure_cli_wallet(agent_id: int, chain: str) -> None:
    """Apply stored wallet secret to the appropriate CLI (best-effort)."""
    from byreal_cli import run_command
    from config import BYREAL_CLI_PATH, BYREAL_PERPS_CLI_PATH

    config = get_wallet_config(agent_id, chain, include_secret=True)
    if not config:
        raise ByrealWalletError(f"no wallet configured for chain={chain}")

    secret = config["secret"]
    if chain == "solana":
        run_command(
            BYREAL_CLI_PATH,
            ["wallet", "set", "--private-key", secret],
            non_interactive=True,
            timeout=30,
        )
    elif chain == "hyperliquid":
        run_command(
            BYREAL_PERPS_CLI_PATH,
            ["wallet", "set", "--private-key", secret],
            non_interactive=True,
            timeout=30,
        )
