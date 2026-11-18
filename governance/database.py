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


def database_url():
    return os.getenv('PLATFORM_DATABASE_URL') or os.getenv('DATABASE_URL', '')


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
    url = database_url()
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
        target = (os.getpid(), database_url())
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
                target_mode text NOT NULL CHECK (target_mode IN ('source', 'wiki', 'graph')),
                knowledge_base_id text NOT NULL,
                document_id text,
                source_hash text,
                source_version text,
                conversion_fingerprint text NOT NULL DEFAULT '',
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
            CREATE TABLE IF NOT EXISTS platform_workspaces (
                id bigint GENERATED ALWAYS AS IDENTITY (START WITH 10000) PRIMARY KEY,
                account_id text NOT NULL REFERENCES platform_users(id) ON DELETE CASCADE,
                principal_id text NOT NULL UNIQUE,
                name text NOT NULL,
                description text NOT NULL DEFAULT 'Default workspace',
                storage_quota bigint NOT NULL DEFAULT 10737418240 CHECK (storage_quota > 0),
                storage_indexed boolean NOT NULL DEFAULT true,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                deleted_at timestamptz
            );
            CREATE UNIQUE INDEX IF NOT EXISTS platform_personal_workspace
                ON platform_workspaces(account_id) WHERE deleted_at IS NULL;
            INSERT INTO platform_workspaces(account_id,principal_id,name,storage_indexed,created_at)
                SELECT u.id,u.id,concat(left(u.username,52),chr(39),'s Workspace'),false,u.created_at FROM platform_users u
                WHERE NOT EXISTS (SELECT 1 FROM platform_workspaces w WHERE w.account_id=u.id);
            ALTER TABLE platform_users ADD COLUMN IF NOT EXISTS is_system_admin boolean NOT NULL DEFAULT false;
            ALTER TABLE platform_workspaces ADD COLUMN IF NOT EXISTS default_settings jsonb;
            UPDATE platform_workspaces w SET default_settings=COALESCE(
                (SELECT jsonb_strip_nulls(jsonb_build_object(
                    'chat_model_id',coalesce(r.payload->'value'->>'chat_model_id',r.payload->'value'->>'summary_model_id'),
                    'utility_model_id',r.payload->'value'->>'utility_model_id',
                    'embedding_model_id',r.payload->'value'->>'embedding_model_id',
                    'rerank_model_id',r.payload->'value'->>'rerank_model_id',
                    'vlm_model_id',r.payload->'value'->>'vlm_model_id',
                    'asr_model_id',r.payload->'value'->>'asr_model_id'))
                 FROM runtime_records r WHERE r.owner_id=w.principal_id AND r.kind='settings'
                    AND r.record_key='default-settings'), '{}') WHERE default_settings IS NULL;
            ALTER TABLE platform_workspaces ALTER COLUMN default_settings SET DEFAULT '{}';
            ALTER TABLE platform_workspaces ALTER COLUMN default_settings SET NOT NULL;
            INSERT INTO runtime_records(id,owner_id,kind,record_key,name,payload,metadata)
                VALUES ('builtin:agent-main','','model','agent-main','agent-main',
                        '{"id":"agent-main","_kind":"model","is_builtin":true,"_from_environment":true}','{}')
                ON CONFLICT (owner_id,kind,record_key) DO NOTHING;
            CREATE OR REPLACE VIEW workspace_users AS
                SELECT w.principal_id AS id,u.id AS account_id,w.id AS workspace_id,u.role,u.active,
                       u.contextdb_key_encrypted FROM platform_workspaces w
                JOIN platform_users u ON u.id=w.account_id WHERE w.deleted_at IS NULL;
            CREATE TABLE IF NOT EXISTS workspace_storage (
                resource_key text NOT NULL,
                principal_id text NOT NULL REFERENCES platform_workspaces(principal_id) ON DELETE CASCADE,
                size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
                PRIMARY KEY (principal_id,resource_key)
            );
            DO $$ DECLARE t regclass; fk record; BEGIN
                FOREACH t IN ARRAY ARRAY['agent_sessions'::regclass,'agent_runs'::regclass] LOOP
                    FOR fk IN SELECT conname FROM pg_constraint
                              WHERE conrelid=t AND confrelid='platform_users'::regclass LOOP
                        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I',t,fk.conname);
                        EXECUTE format('ALTER TABLE %s ADD FOREIGN KEY (owner_id) REFERENCES platform_workspaces(principal_id)',t);
                    END LOOP;
                END LOOP;
            END $$;
            ALTER TABLE knowledge_sync ADD COLUMN IF NOT EXISTS conversion_fingerprint text NOT NULL DEFAULT '';
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
        conn.execute('''DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint
                WHERE conrelid='knowledge_sync'::regclass
                  AND conname='knowledge_sync_target_mode_check'
                  AND pg_get_constraintdef(oid) NOT LIKE '%source%') THEN
                ALTER TABLE knowledge_sync DROP CONSTRAINT knowledge_sync_target_mode_check;
                ALTER TABLE knowledge_sync ADD CONSTRAINT knowledge_sync_target_mode_check
                    CHECK (target_mode IN ('source', 'wiki', 'graph'));
            END IF;
        END $$''')
        from agent.model_secrets import migrate
        migrate(conn)
        bootstrap = os.getenv('PLATFORM_ADMIN_ACCOUNT') or os.getenv('PLATFORM_ADMIN_EMAIL')
        if bootstrap:
            conn.execute("UPDATE platform_users SET is_system_admin=true WHERE email=%s AND role='admin' AND NOT is_system_admin",
                         (bootstrap.strip().lower(),))
