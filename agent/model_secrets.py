"""WeKnora AES-256-GCM model credentials and the previous Fernet record format."""
import base64
import json
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from psycopg.types.json import Jsonb

from agent.credentials import cipher
from governance.store import StoreError

FIELDS = ('api_key', 'app_secret')
PREFIX = 'enc:v1:'


def key():
    raw = os.getenv('SYSTEM_AES_KEY', '').encode()
    return raw if len(raw) == 32 else None


def _aes():
    raw = key()
    if raw is None:
        raise StoreError('模型凭证需要 32 字节的 SYSTEM_AES_KEY', 503)
    return AESGCM(raw)


def _encrypt(value):
    nonce = os.urandom(12)
    data = nonce + _aes().encrypt(nonce, value.encode(), None)
    return PREFIX + base64.urlsafe_b64encode(data).decode().rstrip('=')


def _decrypt(value):
    if not value.startswith(PREFIX):
        raise StoreError('模型凭证密文格式无效', 503)
    encoded = value[len(PREFIX):]
    try:
        data = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
        return _aes().decrypt(data[:12], data[12:], None).decode()
    except (InvalidTag, ValueError) as exc:
        raise StoreError('模型凭证无法解密，请核对 SYSTEM_AES_KEY', 503) from exc


def _map(values, transform):
    result = {field: transform(values[field]) for field in FIELDS if values.get(field)}
    if values.get('custom_headers'):
        result['custom_headers'] = {k: transform(v) for k, v in values['custom_headers'].items()}
    return result


def read(row, *, metadata=False):
    stored = row.get('_encrypted') or {}
    if isinstance(stored, str):
        try:
            stored = json.loads(cipher().decrypt(stored.encode()))
        except (InvalidToken, ValueError) as exc:
            raise StoreError('旧模型凭证无法解密，请核对 CREDENTIAL_ENCRYPTION_KEY', 503) from exc
    elif not metadata:
        stored = _map(stored, _decrypt)
    if row.get('_from_environment'):
        stored = {**stored, 'api_key': os.getenv('BAILIAN_API_KEY', '').strip() or os.getenv('DASHSCOPE_API_KEY') or os.getenv('QWEN_API_KEY', '')}
    params = row.get('parameters') or {}
    for field in (*FIELDS, 'custom_headers'):
        if params.get(field):
            stored = {field: params[field], **stored}
    legacy = (params.get('extra_config') or {}).get('secret_key')
    if legacy and not stored.get('app_secret'):
        stored = {**stored, 'app_secret': legacy}
    return stored


def store(row, private):
    params = row.setdefault('parameters', {})
    for field in (*FIELDS, 'custom_headers'):
        params.pop(field, None)
    (params.get('extra_config') or {}).pop('secret_key', None)
    encrypted = _map(private, _encrypt)
    if encrypted:
        row['_encrypted'] = encrypted
    else:
        row.pop('_encrypted', None)
    return row


def migrate(conn):
    if key() is None:
        logging.getLogger(__name__).warning('SYSTEM_AES_KEY 未配置或长度不是 32 字节，新模型凭证写入已禁用')
        return
    rows = conn.execute("""SELECT id,payload FROM runtime_records WHERE kind='model' AND
        (jsonb_typeof(payload->'_encrypted')='string' OR (payload->'parameters') ?| ARRAY['api_key','app_secret','custom_headers']
         OR (payload->'parameters'->'extra_config') ? 'secret_key') FOR UPDATE""").fetchall()
    if rows:
        existing = conn.execute("""SELECT payload FROM runtime_records WHERE kind='model'
            AND jsonb_typeof(payload->'_encrypted')='object' AND payload->'_encrypted'<>'{}'::jsonb LIMIT 1""").fetchone()
        if existing:
            read(existing['payload'])
    for row in rows:
        value = row['payload']
        conn.execute('UPDATE runtime_records SET payload=%s WHERE id=%s', (Jsonb(store(value, read(value))), row['id']))
