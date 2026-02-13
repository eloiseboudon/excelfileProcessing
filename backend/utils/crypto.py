"""Fernet encryption/decryption for sensitive values (e.g. Odoo password)."""

import os

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.environ.get("ODOO_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("ODOO_ENCRYPTION_KEY is not set")
    return Fernet(key.encode())


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string and return the Fernet token as str."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token and return the plaintext string."""
    return _get_fernet().decrypt(token.encode()).decode()
