"""Create only the asynchronous runtime database and its private local env file."""
import json
import io
import os
import secrets
from pathlib import Path
from urllib.parse import quote

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / '.runtime/async-agent.env'
DATABASE = 'showdoc_async_agent'
ROLE = 'showdoc_async_agent_app'
ROLE_FLAGS = ('rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolinherit', 'rolreplication', 'rolbypassrls')
COPY_ENV = ('CREDENTIAL_ENCRYPTION_KEY', 'FLASK_SECRET_KEY', 'CONTEXTDB_BASE_URL',
            'CONTEXTDB_MCP_URL', 'AGENT_MAIN_MODEL', 'AGENT_SUB_MODEL', 'BAILIAN_API_KEY',
            'DASHSCOPE_API_KEY', 'DASHSCOPE_API_URL', 'QWEN_API_KEY', 'AGENT_BAILIAN_BASE_URL',
            'OPEN_SANDBOX_API_KEY', 'OPEN_SANDBOX_PROTOCOL', 'OPEN_SANDBOX_IMAGE')


def container_dsn(value):
    parsed = conninfo_to_dict(value)
    if parsed.get('host') not in ('localhost', '127.0.0.1', 'host.docker.internal'):
        raise ValueError('This bootstrap expects the existing local Docker PostgreSQL service')
    return make_conninfo(value, host='host.docker.internal')


def quoted(value):
    return "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"


def write_env(values):
    ENV_PATH.parent.mkdir(mode=0o700, exist_ok=True)
    temporary = ENV_PATH.with_suffix('.env.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        output.write(''.join(f'{key}={quoted(value)}\n' for key, value in values.items()))
    os.replace(temporary, ENV_PATH)


def main():
    # The DSN transformation must preserve encoded credentials and connection options.
    assert conninfo_to_dict(container_dsn('postgresql://u:p%40x@127.0.0.1:55432/db?sslmode=disable')) == {
        'user': 'u', 'password': 'p@x', 'host': 'host.docker.internal', 'port': '55432', 'dbname': 'db', 'sslmode': 'disable'}
    assert dotenv_values(stream=io.StringIO('K=' + quoted("a'$\\b")))['K'] == "a'$\\b"
    original = dotenv_values(ROOT / '.env')
    previous = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    for key in ('DATABASE_URL', 'AGENT_DATABASE_URL', 'POSTGRES_PASSWORD',
                'CREDENTIAL_ENCRYPTION_KEY', 'FLASK_SECRET_KEY'):
        if not original.get(key):
            raise ValueError(f'Missing required local configuration: {key}')
    platform = conninfo_to_dict(original['DATABASE_URL'])
    agent = conninfo_to_dict(original['AGENT_DATABASE_URL'])
    if DATABASE in (platform.get('dbname'), agent.get('dbname')) or ROLE in (
            platform.get('user'), agent.get('user')):
        raise ValueError('The asynchronous runtime must have its own database and role')
    old_runtime = conninfo_to_dict(previous['DATABASE_URL']) if previous.get('DATABASE_URL') else {}
    password = old_runtime.get('password') or secrets.token_hex(32)
    configured_data = os.getenv('GOVERNANCE_DATA_DIR', original.get('GOVERNANCE_DATA_DIR'))
    data = Path(configured_data if configured_data is not None else 'downloads')
    data = (ROOT / data).resolve()
    (data / 'skill-bundles').mkdir(parents=True, exist_ok=True)
    values = {key: original[key] for key in COPY_ENV if original.get(key)}
    values.update(DATABASE_URL=f'postgresql://{ROLE}:{quote(password, safe="")}@host.docker.internal:{platform.get("port", "5432")}/{DATABASE}',
                  PLATFORM_DATABASE_URL=container_dsn(original['DATABASE_URL']),
                  AGENT_DATABASE_URL=container_dsn(original['AGENT_DATABASE_URL']),
                  GOVERNANCE_DATA_DIR=str(data),
                  OPEN_SANDBOX_DOMAIN='host.docker.internal:8090',
                  ASYNC_AGENT_RUNTIME_URL='http://127.0.0.1:2026',
                  ASYNC_AGENT_RUNTIME_SIGNING_KEY=previous.get('ASYNC_AGENT_RUNTIME_SIGNING_KEY') or secrets.token_hex(32),
                  ASYNC_AGENT_RUNTIME_ENABLED=previous.get('ASYNC_AGENT_RUNTIME_ENABLED') or '0')
    admin = make_conninfo(original['DATABASE_URL'], dbname='postgres',
                         user=original.get('POSTGRES_USER') or 'showdoc',
                         password=original['POSTGRES_PASSWORD'], connect_timeout=5)
    with psycopg.connect(admin, autocommit=True) as conn:
        for app in (platform, agent):
            flags = conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls '
                                 'FROM pg_roles WHERE rolname=%s', (app['user'],)).fetchone()
            if flags is None or any(flags):
                raise ValueError('Existing application credentials must use restricted roles')
        existing = conn.execute('SELECT ' + ','.join(ROLE_FLAGS) + ' FROM pg_roles WHERE rolname=%s',
                                (ROLE,)).fetchone()
        if existing is not None:
            if not old_runtime or old_runtime.get('user') != ROLE or old_runtime.get('dbname') != DATABASE or any(existing):
                raise ValueError('Existing asynchronous role was not created with this private env; refusing to change it')
        database_exists = conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', (DATABASE,)).fetchone()
        if database_exists and not old_runtime:
            raise ValueError('Existing asynchronous database has no matching private env; refusing to change it')
        # Persist generated credentials before creating a role so a failed bootstrap can resume.
        write_env(values)
        if existing is None:
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE '
                                 'NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(ROLE), sql.Literal(password)))
        if not database_exists:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DATABASE)))
        conn.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(DATABASE)))
        conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(DATABASE), sql.Identifier(ROLE)))
        for app in (platform, agent):
            if conn.execute('SELECT has_database_privilege(%s,%s,\'CONNECT\')', (ROLE, app['dbname'])).fetchone()[0]:
                raise ValueError('Asynchronous role can access an existing application database; review its isolation')
    with psycopg.connect(make_conninfo(admin, dbname=DATABASE)) as conn:
        conn.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
        conn.execute(sql.SQL('GRANT USAGE,CREATE ON SCHEMA public TO {}').format(sql.Identifier(ROLE)))
    runtime_host = make_conninfo(original['DATABASE_URL'], dbname=DATABASE, user=ROLE, password=password)
    with psycopg.connect(runtime_host) as conn:
        assert conn.execute('SELECT current_database(),current_user').fetchone() == (DATABASE, ROLE)
    print(json.dumps({'database': DATABASE, 'role': ROLE, 'private_env': str(ENV_PATH.relative_to(ROOT)),
                      'credential_values': 'not printed', 'original_databases': 'unchanged'}))


if __name__ == '__main__':
    main()
