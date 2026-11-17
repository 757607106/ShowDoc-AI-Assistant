"""Shared credential cipher for the web host and its trusted agent worker."""
import os

from cryptography.fernet import Fernet

from governance.store import StoreError


def cipher():
    key = os.getenv('CREDENTIAL_ENCRYPTION_KEY', '')
    if not key:
        raise StoreError('CREDENTIAL_ENCRYPTION_KEY 未配置', 503)
    return Fernet(key.encode())
