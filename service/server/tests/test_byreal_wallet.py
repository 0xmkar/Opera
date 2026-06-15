import os
import sys

import pytest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from cryptography.fernet import Fernet

os.environ["BYREAL_WALLET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from byreal_wallet import decrypt_secret, encrypt_secret, mask_pubkey  # noqa: E402


def test_encrypt_decrypt_roundtrip():
    secret = "test-base58-secret-key"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_mask_pubkey():
    assert mask_pubkey("BRauNK1g117G19HLD5JCyD8GgB8TD7a8QnbeeXrGSfHd") == "BRauNK...SfHd"
