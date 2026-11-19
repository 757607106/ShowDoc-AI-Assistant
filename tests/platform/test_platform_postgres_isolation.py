"""Isolation preparation only touches disposable test databases and roles."""
from contextlib import contextmanager
import uuid
from typing import TypedDict

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
import pytest
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph
from langgraph.store.postgres import PostgresStore
from langgraph.types import Command, interrupt

from governance import database
from scripts.ops import isolate_agent_postgres as isolation


class LegacyState(TypedDict):
    value: str


def _graph(saver):
    graph = StateGraph(LegacyState)
    graph.add_node('approval', lambda state: {'value': interrupt('Approve the preserved checkpoint')})
    graph.set_entry_point('approval')
    graph.set_finish_point('approval')
    return graph.compile(checkpointer=saver)


class Resources:
    """Keep privileged fixture credentials out of pytest's value representations."""


@pytest.fixture
def legacy(postgres_admin_database, monkeypatch):
    resource = Resources()
    resource.admin = postgres_admin_database
    suffix = uuid.uuid4().hex[:14]
    resource.platform_db, resource.agent_db = f'isolation_platform_{suffix}_test', f'isolation_agent_{suffix}_test'
    resource.platform_role, resource.agent_role = f'isolation_p_{suffix}', f'isolation_a_{suffix}'
    source = make_conninfo(resource.admin, dbname=resource.platform_db, options='-csearch_path=public')
    resource.platform = make_conninfo(source, user=resource.platform_role, password=uuid.uuid4().hex, options='')
    resource.agent = make_conninfo(source, dbname=resource.agent_db, user=resource.agent_role,
                                  password=uuid.uuid4().hex, options='')
    with psycopg.connect(resource.admin, autocommit=True) as admin:
        assert admin.execute('SELECT current_database()').fetchone()[0].endswith('_test')
        admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(resource.platform_db)))
    try:
        @contextmanager
        def source_connection():
            with psycopg.connect(source, row_factory=dict_row) as conn:
                yield conn
        with monkeypatch.context() as patch:
            patch.setattr(database, 'connection', source_connection)
            database._initialize_schema()
        with psycopg.connect(source) as conn:
            conn.execute("INSERT INTO platform_users(id,email,username,password_hash,role,contextdb_key_encrypted) VALUES ('preserved-user','migration@example.com','迁移账号','preserved-hash','admin','preserved-ciphertext')")
        with PostgresSaver.from_conn_string(source) as saver:
            saver.setup()
            graph = _graph(saver)
            result = graph.invoke({'value': 'original'}, {'configurable': {'thread_id': 'legacy-interrupted'}})
            assert result['__interrupt__']
            resource.checkpoint_id = graph.get_state({'configurable': {'thread_id': 'legacy-interrupted'}}).config['configurable']['checkpoint_id']
        with PostgresStore.from_conn_string(source) as store:
            store.setup()
            store.put(('memory', 'owner'), 'AGENTS.md', {'content': '保留的文件记忆'})
        resource.source = source
        yield resource
    finally:
        with psycopg.connect(resource.admin, autocommit=True) as admin:
            for name in (resource.agent_db, resource.platform_db):
                assert name.startswith('isolation_') and name.endswith('_test')
                admin.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
            for role in (resource.agent_role, resource.platform_role):
                admin.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(role)))


def test_default_review_does_not_create_roles_databases_or_change_source(legacy):
    report = isolation.isolate(legacy.admin, legacy.platform, legacy.agent)
    assert report['result'] == 'review' and report['target_agent_tables'] is None
    assert set(report['source_agent_tables']) == set(isolation.AGENT_KEYS)
    assert report['source_agent_tables']['checkpoints']['rows'] > 0
    with psycopg.connect(legacy.admin) as admin:
        assert admin.execute('SELECT 1 FROM pg_database WHERE datname=%s', (legacy.agent_db,)).fetchone() is None
        assert admin.execute('SELECT 1 FROM pg_roles WHERE rolname=ANY(%s)', ([legacy.platform_role, legacy.agent_role],)).fetchone() is None
    assert 'password' not in str(report).lower()


def test_apply_preserves_native_state_and_proves_database_role_isolation(legacy):
    report = isolation.isolate(legacy.admin, legacy.platform, legacy.agent, apply=True)
    assert report['result'] == 'isolated' and report['verified_agent_tables'] == report['source_agent_tables']
    assert isolation.isolate(legacy.admin, legacy.platform, legacy.agent, apply=True)['result'] == 'isolated'
    for url, forbidden in ((legacy.platform, legacy.agent_db), (legacy.agent, legacy.platform_db)):
        with pytest.raises(psycopg.OperationalError) as caught:
            psycopg.connect(make_conninfo(url, dbname=forbidden))
        assert 'permission denied for database' in str(caught.value)
        with psycopg.connect(url) as app:
            assert app.execute('SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls OR rolreplication FROM pg_roles WHERE rolname=current_user').fetchone()[0] is False
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(legacy.platform) as platform:
            platform.execute('SELECT * FROM public.checkpoints')
    with psycopg.connect(legacy.platform) as platform:
        assert platform.execute("SELECT contextdb_key_encrypted FROM public.platform_users WHERE id='preserved-user'").fetchone()[0] == 'preserved-ciphertext'
        assert platform.execute("INSERT INTO public.platform_audit(action,outcome) VALUES ('test','200') RETURNING id").fetchone()[0] == 1
    config = {'configurable': {'thread_id': 'legacy-interrupted'}}
    with PostgresSaver.from_conn_string(legacy.agent) as saver:
        graph = _graph(saver)
        state = graph.get_state(config)
        assert state.config['configurable']['checkpoint_id'] == legacy.checkpoint_id and state.interrupts
        assert graph.invoke(Command(resume='approved'), config)['value'] == 'approved'
    with PostgresStore.from_conn_string(legacy.agent) as store:
        assert store.get(('memory', 'owner'), 'AGENTS.md').value == {'content': '保留的文件记忆'}
    with PostgresSaver.from_conn_string(legacy.source) as saver:
        assert _graph(saver).get_state(config).interrupts


def test_nonempty_different_agent_target_is_never_overwritten(legacy):
    isolation.isolate(legacy.admin, legacy.platform, legacy.agent, apply=True)
    with PostgresStore.from_conn_string(legacy.agent) as store:
        store.put(('memory', 'owner'), 'AGENTS.md', {'content': '目标已有新内容'})
    with pytest.raises(ValueError, match='nonempty and differs'):
        isolation.isolate(legacy.admin, legacy.platform, legacy.agent, apply=True)
    with PostgresStore.from_conn_string(legacy.agent) as store:
        assert store.get(('memory', 'owner'), 'AGENTS.md').value['content'] == '目标已有新内容'


def test_copy_failure_rolls_back_data_and_reports_completed_preparation(legacy, monkeypatch):
    copy = isolation._copy_table
    def fail_after_copy(source, target, table):
        assert source.execute('SHOW transaction_read_only').fetchone()['transaction_read_only'] == 'on'
        copy(source, target, table)
        if table == 'checkpoint_blobs':
            raise RuntimeError('Injected COPY failure')
    with monkeypatch.context() as patch:
        patch.setattr(isolation, '_copy_table', fail_after_copy)
        with pytest.raises(isolation.IsolationFailure) as caught:
            isolation.isolate(legacy.admin, legacy.platform, legacy.agent, apply=True)
    assert caught.value.report['step'] == 'copy'
    assert 'official_schema_ready' in caught.value.report['prepared']
    assert 'agent_data_verified' not in caught.value.report['prepared']
    with psycopg.connect(legacy.agent) as target:
        for table in isolation.DATA_TABLES:
            assert target.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier('public', table))).fetchone()[0] == 0
    assert isolation.isolate(legacy.admin, legacy.platform, legacy.agent, apply=True)['result'] == 'isolated'


def test_existing_privileged_role_is_rejected_before_preparation(legacy):
    with psycopg.connect(legacy.admin) as admin:
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN SUPERUSER PASSWORD {}').format(
            sql.Identifier(legacy.platform_role), sql.Literal('temporary-test-password')))
    with pytest.raises(ValueError, match='restricted login'):
        isolation.isolate(legacy.admin, legacy.platform, legacy.agent, apply=True)
    with psycopg.connect(legacy.admin) as admin:
        assert admin.execute('SELECT 1 FROM pg_database WHERE datname=%s', (legacy.agent_db,)).fetchone() is None


def test_unexpected_historical_grant_requires_review_before_preparation(legacy):
    reader = 'isolation_reader_' + uuid.uuid4().hex[:12]
    with psycopg.connect(legacy.admin) as admin:
        admin.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(reader)))
    try:
        with psycopg.connect(legacy.source) as source:
            source.execute(sql.SQL('GRANT SELECT ON public.store TO {}').format(sql.Identifier(reader)))
        with pytest.raises(ValueError, match='Historical table grants'):
            isolation.isolate(legacy.admin, legacy.platform, legacy.agent, apply=True)
        with psycopg.connect(legacy.admin) as admin:
            assert admin.execute('SELECT 1 FROM pg_database WHERE datname=%s', (legacy.agent_db,)).fetchone() is None
    finally:
        with psycopg.connect(legacy.source) as source:
            source.execute(sql.SQL('REVOKE SELECT ON public.store FROM {}').format(sql.Identifier(reader)))
        with psycopg.connect(legacy.admin) as admin:
            admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(reader)))


def test_shared_database_or_application_role_is_rejected_without_connection():
    admin = 'postgresql://admin:unused@127.0.0.1:1/admin_test'
    platform = 'postgresql://platform:unused@127.0.0.1:1/platform_test'
    for agent in ('postgresql://agent:unused@127.0.0.1:1/platform_test',
                  'postgresql://platform:unused@127.0.0.1:1/agent_test'):
        with pytest.raises(ValueError, match='different databases and application roles'):
            isolation.isolate(admin, platform, agent)
