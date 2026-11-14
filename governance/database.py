"""Platform state in Docker PostgreSQL; knowledge assets remain in ContextDB."""
import os
import atexit
import threading
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


_pool = None
_pool_key = None
_pool_lock = threading.Lock()
_initialize_lock = threading.Lock()
_initialized_targets = set()


def close_pool():
    global _pool, _pool_key
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None
            _pool_key = None


atexit.register(close_pool)


@contextmanager
def connection():
    global _pool, _pool_key
    url = os.getenv('DATABASE_URL', '')
    if not url:
        raise RuntimeError('DATABASE_URL 未配置，请先启动 compose.postgres.yml')
    with _pool_lock:
        key = (os.getpid(), url)
        if _pool is None or _pool_key != key:
            if _pool is not None:
                _pool.close()
            _pool = ConnectionPool(url, kwargs={'row_factory': dict_row, 'connect_timeout': 5},
                                   min_size=0, max_size=16, timeout=5, open=True)
            _pool_key = key
        pool = _pool
    with pool.connection() as conn:
        yield conn


def initialize():
    with _initialize_lock:
        target = (os.getpid(), os.getenv('DATABASE_URL', ''))
        if target in _initialized_targets:
            return
        _initialize_schema()
        _initialized_targets.add(target)


def _initialize_schema():
    with connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(current_schema() || ':platform-initialize', 0))")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS platform_users (
                id text PRIMARY KEY,
                email text UNIQUE NOT NULL,
                username text NOT NULL,
                password_hash text NOT NULL,
                role text NOT NULL CHECK (role IN ('admin', 'editor', 'viewer')),
                contextdb_member_id text,
                contextdb_key_encrypted text,
                active boolean NOT NULL DEFAULT true,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS runtime_records (
                id text PRIMARY KEY,
                owner_id text NOT NULL DEFAULT '',
                kind text NOT NULL,
                record_key text NOT NULL,
                name text NOT NULL,
                payload jsonb NOT NULL,
                metadata jsonb NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                UNIQUE (owner_id, kind, record_key)
            );
            CREATE INDEX IF NOT EXISTS runtime_records_metadata
                ON runtime_records USING gin (metadata);
            CREATE UNIQUE INDEX IF NOT EXISTS platform_users_contextdb_member
                ON platform_users(contextdb_member_id) WHERE contextdb_member_id IS NOT NULL;
            CREATE TABLE IF NOT EXISTS platform_tokens (
                id text PRIMARY KEY,
                owner_id text NOT NULL REFERENCES platform_users(id),
                expires_at timestamptz NOT NULL DEFAULT now() + interval '30 days'
            );
            CREATE TABLE IF NOT EXISTS agent_sessions (
                id text PRIMARY KEY,
                owner_id text NOT NULL REFERENCES platform_users(id),
                title text NOT NULL,
                running_id text,
                cancel_requested boolean NOT NULL DEFAULT false,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS knowledge_sync (
                owner_id text NOT NULL,
                scope text NOT NULL,
                source_id text NOT NULL,
                target_mode text NOT NULL CHECK (target_mode IN ('wiki', 'graph')),
                knowledge_base_id text NOT NULL,
                document_id text,
                source_hash text,
                source_version text,
                status text NOT NULL,
                event_id text,
                error text,
                updated_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (owner_id, scope, source_id, target_mode)
            );
            CREATE TABLE IF NOT EXISTS agent_runs (
                id text PRIMARY KEY,
                session_id text NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
                owner_id text NOT NULL REFERENCES platform_users(id),
                status text NOT NULL,
                query text NOT NULL DEFAULT '',
                answer text NOT NULL DEFAULT '',
                references_json jsonb NOT NULL DEFAULT '[]',
                pending_json jsonb,
                error text,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            );
            ALTER TABLE platform_users ADD COLUMN IF NOT EXISTS preferences jsonb NOT NULL DEFAULT '{}';
            ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS knowledge_base_ids jsonb NOT NULL DEFAULT '[]';
            ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS pinned_at timestamptz;
            ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS agent_config jsonb NOT NULL DEFAULT '{}';
            ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS parent_session_id text REFERENCES agent_sessions(id) ON DELETE CASCADE;
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS steps_json jsonb NOT NULL DEFAULT '[]';
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS request_json jsonb NOT NULL DEFAULT '{}';
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS checkpoint_before text;
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS checkpoint_after text;
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS workspace_before jsonb;
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS workspace_after jsonb;
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS artifacts_json jsonb NOT NULL DEFAULT '[]';
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS artifact_sources jsonb NOT NULL DEFAULT '[]';
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS artifacts_truncated boolean NOT NULL DEFAULT false;
            ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS parent_run_id text REFERENCES agent_runs(id) ON DELETE CASCADE;
            CREATE TABLE IF NOT EXISTS agent_run_events (
                cursor bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                run_id text NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
                owner_id text NOT NULL,
                event_json jsonb NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS agent_run_events_run_cursor ON agent_run_events(run_id,cursor);
            CREATE TABLE IF NOT EXISTS agent_steers (
                id text PRIMARY KEY,
                session_id text NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
                owner_id text NOT NULL,
                run_id text NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
                content text NOT NULL,
                mentioned_items jsonb NOT NULL DEFAULT '[]',
                delivery text NOT NULL CHECK (delivery IN ('after','inject')),
                status text NOT NULL DEFAULT 'queued',
                created_at timestamptz NOT NULL DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS platform_audit (
                id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                owner_id text,
                action text NOT NULL,
                resource_id text,
                request_id text,
                outcome text NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            );
        ''')
