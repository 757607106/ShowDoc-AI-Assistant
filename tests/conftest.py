"""Cloud-free unit tests; platform integration uses isolated schemas in Docker PostgreSQL."""
import os
import sys
import uuid
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from dotenv import dotenv_values
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tests.contextdb_fake import FakeContextDBClient


@pytest.fixture(scope='session')
def platform_test_database():
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        base = dotenv_values(PROJECT_ROOT / '.env').get('DATABASE_URL')
        if not base:
            pytest.fail('Docker PostgreSQL 未配置；设置 TEST_DATABASE_URL（库名必须以 _test 结尾）')
        with psycopg.connect(base, autocommit=True) as conn:
            if not conn.execute("SELECT 1 FROM pg_database WHERE datname='showdoc_knowledge_test'").fetchone():
                conn.execute('CREATE DATABASE showdoc_knowledge_test')
        url = make_conninfo(base, dbname='showdoc_knowledge_test')
    with psycopg.connect(url) as conn:
        name = conn.execute('SELECT current_database()').fetchone()[0]
        assert name.endswith('_test'), '测试禁止连接生产数据库'
    return url


@pytest.fixture(autouse=True)
def isolate_contextdb(monkeypatch, request, tmp_path):
    monkeypatch.setenv('CONTEXTDB_API_KEY', 'ctxdb-fake')
    monkeypatch.setenv('CONTEXTDB_MCP_URL', 'http://127.0.0.1:9/mcp')
    import requests
    native_request = requests.Session.request
    def no_cloud(session, method, url, **kwargs):
        if 'context-database.aliyuncs.com' in url or 'agentcontext.aliyuncs.com' in url:
            raise AssertionError('默认测试禁止访问 ContextDB 云端，请注入契约替身')
        return native_request(session, method, url, **kwargs)
    monkeypatch.setattr(requests.Session, 'request', no_cloud)
    monkeypatch.delenv('CONTEXTDB_KB_ID', raising=False)
    monkeypatch.delenv('CONTEXTDB_GRAPH_KB_ID', raising=False)
    monkeypatch.setenv('CONTEXTDB_GOVERNANCE_KB', '_test_governance')
    monkeypatch.setenv('GOVERNANCE_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('governance.store.ContextDBClient', FakeContextDBClient)
    uses_database = any(word in request.module.__name__ for word in ('governance_store', 'contextdb_sync', 'agent_domain', 'task_api', 'knowledge_api', 'platform', 'data_integrity_regression'))
    if not uses_database:
        monkeypatch.delenv('DATABASE_URL', raising=False)
        yield
        return
    url = request.getfixturevalue('platform_test_database')
    schema = 'test_' + uuid.uuid4().hex
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    monkeypatch.setenv('DATABASE_URL', make_conninfo(url, options=f'-csearch_path={schema}'))
    from cryptography.fernet import Fernet
    monkeypatch.setenv('CREDENTIAL_ENCRYPTION_KEY', Fernet.generate_key().decode())
    from governance.database import initialize, connection
    initialize()
    from agent.checkpointer import initialize_checkpoints
    initialize_checkpoints()
    from webapi.auth import create_user, cipher
    uid = create_user('test@example.com', '测试管理员', 'test-password-123', 'admin')
    with connection() as conn:
        conn.execute('UPDATE platform_users SET contextdb_key_encrypted=%s WHERE id=%s', (cipher().encrypt(b'ctxdb-fake').decode(), uid))
    monkeypatch.setenv('TEST_PLATFORM_USER', uid)
    yield
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


@pytest.fixture
def authenticated_client():
    import app as app_module
    app_module.app.config['TESTING'] = True
    client = app_module.app.test_client()
    response = client.post('/api/v1/auth/login', json={'email':'test@example.com','password':'test-password-123'})
    assert response.status_code == 200
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + response.get_json()['token']
    return client
