"""Fernet encryption/decryption for sensitive values (e.g. Odoo password)."""

import os

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet:
    key = os.environ.get("ODOO_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("ODOO_ENCRYPTION_KEY is not set")
    return Fernet(key.encode())


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string and return the Fernet token as str."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token and return the plaintext string.

    Falls back to returning the raw value if it is not a Fernet token
    (plaintext not yet encrypted by the migration).
    """
    if not token.startswith("gAAAAA"):
        return token
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return token
