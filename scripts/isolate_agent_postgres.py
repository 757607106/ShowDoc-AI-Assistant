"""Review or prepare dedicated PostgreSQL databases and roles for platform and Agent state."""
import argparse
import hashlib
import json
import os

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore


PLATFORM_TABLES = ('platform_users', 'runtime_records', 'platform_tokens', 'agent_sessions',
                   'knowledge_sync', 'agent_runs', 'agent_run_events', 'agent_steers', 'platform_audit')
AGENT_KEYS = {
    'checkpoint_migrations': ('v',),
    'checkpoints': ('thread_id', 'checkpoint_ns', 'checkpoint_id'),
    'checkpoint_blobs': ('thread_id', 'checkpoint_ns', 'channel', 'version'),
    'checkpoint_writes': ('thread_id', 'checkpoint_ns', 'checkpoint_id', 'task_id', 'idx'),
    'store_migrations': ('v',), 'store': ('prefix', 'key'),
}
DATA_TABLES = ('checkpoints', 'checkpoint_blobs', 'checkpoint_writes', 'store')


class IsolationFailure(RuntimeError):
    def __init__(self, step, prepared, cause):
        self.report = {'result': 'failed', 'step': step, 'prepared': list(prepared),
                       'error_type': type(cause).__name__, 'sqlstate': getattr(cause, 'sqlstate', None)}
        super().__init__(json.dumps(self.report, ensure_ascii=False))


def _inputs(admin_url, platform_url, agent_url):
    admin, platform, agent = map(conninfo_to_dict, (admin_url, platform_url, agent_url))
    for value in (platform, agent):
        if any(not value.get(key) for key in ('dbname', 'user', 'password')) or value.get('options'):
            raise ValueError('Application DSNs require explicit dbname/user/password and the default public schema')
        if any(len(value[key].encode()) > 63 for key in ('dbname', 'user')):
            raise ValueError('Database and role names must fit PostgreSQL identifiers')
    if platform['dbname'] == agent['dbname'] or platform['user'] == agent['user']:
        raise ValueError('Platform and Agent require different databases and application roles')
    for value in (platform, agent):
        if tuple(value.get(key, '5432' if key == 'port' else '') for key in ('host', 'hostaddr', 'port')) != tuple(
                admin.get(key, '5432' if key == 'port' else '') for key in ('host', 'hostaddr', 'port')):
            raise ValueError('All DSNs must address the same PostgreSQL service')
    return platform, agent


def _admin_url(admin_url, database):
    return make_conninfo(admin_url, dbname=database, options='-csearch_path=public -clock_timeout=10000', connect_timeout=5)


def _tables(conn):
    return {row['tablename'] for row in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}


def _columns(conn, table):
    return conn.execute('''SELECT attname AS name,format_type(atttypid,atttypmod) AS type
        FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum''',
        ('public.' + table,)).fetchall()


def _export_query(conn, table):
    types = {column['name']: column['type'] for column in _columns(conn, table)}
    order = sql.SQL(',').join(sql.SQL('{} COLLATE "C"').format(sql.Identifier(key))
                             if types[key] == 'text' else sql.Identifier(key) for key in AGENT_KEYS[table])
    return sql.SQL('COPY (SELECT * FROM {} ORDER BY {}) TO STDOUT (FORMAT BINARY)').format(
        sql.Identifier('public', table), order)


def _fingerprint(conn, table):
    digest = hashlib.sha256()
    with conn.cursor().copy(_export_query(conn, table)) as output:
        for block in output:
            digest.update(block)
    count = conn.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(sql.Identifier('public', table))).fetchone()['n']
    return {'rows': count, 'sha256': digest.hexdigest()}


def _role(conn, name):
    role = conn.execute('''SELECT rolname,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls,rolcanlogin
        FROM pg_roles WHERE rolname=%s''', (name,)).fetchone()
    memberships = conn.execute('''SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
        WHERE r.rolname=%s LIMIT 1''', (name,)).fetchone()
    if role and (not role['rolcanlogin'] or memberships or any(role[key] for key in
            ('rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolinherit', 'rolreplication', 'rolbypassrls'))):
        raise ValueError(f'Application role is not a dedicated restricted login: {name}')
    return role


def _check_grants(conn, tables, allowed):
    unexpected = conn.execute('''SELECT DISTINCT r.rolname FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN LATERAL aclexplode(c.relacl) a JOIN pg_roles r ON r.oid=a.grantee
        WHERE n.nspname='public' AND c.relname=ANY(%s) AND a.grantee<>c.relowner
        AND NOT (r.rolname=ANY(%s))''', (list(tables), list(allowed))).fetchall()
    if unexpected:
        raise ValueError('Historical table grants require administrator review before isolation')


def inspect(admin_url, platform_url, agent_url):
    platform, agent = _inputs(admin_url, platform_url, agent_url)
    with psycopg.connect(_admin_url(admin_url, platform['dbname']), row_factory=dict_row) as source:
        source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        administrator = source.execute('SELECT current_user AS name').fetchone()['name']
        if administrator in (platform['user'], agent['user']):
            raise ValueError('The bootstrap administrator must not be either application role')
        roles = {value['user']: _role(source, value['user']) is not None for value in (platform, agent)}
        expected = set(PLATFORM_TABLES) | set(AGENT_KEYS)
        if _tables(source) != expected:
            raise ValueError('Source public tables differ from the fixed platform and official Agent table set')
        _check_grants(source, AGENT_KEYS, (administrator, platform['user'], agent['user']))
        counts = {table: source.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(
            sql.Identifier('public', table))).fetchone()['n'] for table in PLATFORM_TABLES}
        original = {table: _fingerprint(source, table) for table in AGENT_KEYS}
        target_exists = source.execute('SELECT 1 FROM pg_database WHERE datname=%s', (agent['dbname'],)).fetchone() is not None
        target_stats = None
        if target_exists:
            with psycopg.connect(_admin_url(admin_url, agent['dbname']), row_factory=dict_row) as target:
                target.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                existing = _tables(target)
                if existing - set(AGENT_KEYS):
                    raise ValueError('Agent target contains unrelated tables')
                _check_grants(target, existing, (administrator, platform['user'], agent['user']))
                target_stats = {}
                for table in existing:
                    if _columns(source, table) != _columns(target, table):
                        raise ValueError(f'Official schema differs: {table}')
                    target_stats[table] = _fingerprint(target, table)
                populated = any(target_stats.get(table, {}).get('rows', 0) for table in DATA_TABLES)
                if populated and target_stats != original:
                    raise ValueError('Agent target is nonempty and differs; nothing will be overwritten')
                for table in ('checkpoint_migrations', 'store_migrations'):
                    if table in target_stats and target_stats[table] != original[table]:
                        raise ValueError(f'Official migration versions differ: {table}')
    return {'result': 'review', 'platform_database': platform['dbname'], 'agent_database': agent['dbname'],
            'platform_role': platform['user'], 'agent_role': agent['user'], 'existing_roles': roles,
            'platform_rows': counts, 'source_agent_tables': original, 'target_agent_tables': target_stats,
            'plan': ['create restricted roles and Agent database if absent',
                     'retain bootstrap database ownership; transfer platform table ownership',
                     'revoke PUBLIC and cross-role database/schema/table privileges',
                     'initialize Agent tables with official Saver.setup and Store.setup',
                     'binary COPY and verify official tables; retain source originals',
                     'verify own-database access and reject both cross-database connections']}


def _access(admin_url, database, owner, other, archive_owner=None):
    with psycopg.connect(_admin_url(admin_url, database), row_factory=dict_row) as conn:
        conn.execute(sql.SQL('ALTER DATABASE {} OWNER TO {}').format(sql.Identifier(database), sql.Identifier(
            conn.execute('SELECT current_user AS name').fetchone()['name'])))
        conn.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC,{},{}').format(
            sql.Identifier(database), sql.Identifier(owner), sql.Identifier(other)))
        conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(database), sql.Identifier(owner)))
        conn.execute(sql.SQL('ALTER SCHEMA public OWNER TO {}').format(sql.Identifier(
            conn.execute('SELECT current_user AS name').fetchone()['name'])))
        conn.execute(sql.SQL('REVOKE ALL ON SCHEMA public FROM PUBLIC,{}').format(sql.Identifier(other)))
        conn.execute(sql.SQL('GRANT USAGE,CREATE ON SCHEMA public TO {}').format(sql.Identifier(owner)))
        conn.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC,{},{}').format(
            sql.Identifier(owner), sql.Identifier(other)))
        conn.execute(sql.SQL('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC,{},{}').format(
            sql.Identifier(owner), sql.Identifier(other)))
        owned_tables = PLATFORM_TABLES if archive_owner else tuple(table for table in AGENT_KEYS if table in _tables(conn))
        for table in owned_tables:
            conn.execute(sql.SQL('ALTER TABLE {} OWNER TO {}').format(sql.Identifier('public', table), sql.Identifier(owner)))
            conn.execute(sql.SQL('GRANT ALL ON TABLE {} TO {}').format(sql.Identifier('public', table), sql.Identifier(owner)))
        if archive_owner:
            for table in AGENT_KEYS:
                conn.execute(sql.SQL('ALTER TABLE {} OWNER TO {}').format(sql.Identifier('public', table), sql.Identifier(archive_owner)))
            for table, column in (('agent_run_events', 'cursor'), ('platform_audit', 'id')):
                sequence = conn.execute('SELECT pg_get_serial_sequence(%s,%s) AS name', ('public.' + table, column)).fetchone()['name']
                if sequence:
                    parts = conn.execute('SELECT parse_ident(%s) AS parts', (sequence,)).fetchone()['parts']
                    conn.execute(sql.SQL('GRANT ALL ON SEQUENCE {} TO {}').format(sql.Identifier(*parts), sql.Identifier(owner)))
        conn.execute(sql.SQL('ALTER ROLE {} IN DATABASE {} SET search_path=public').format(
            sql.Identifier(owner), sql.Identifier(database)))
        for kind in ('TABLES', 'SEQUENCES'):
            conn.execute(sql.SQL('ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public REVOKE ALL ON {} FROM PUBLIC,{}').format(
                sql.Identifier(owner), sql.SQL(kind), sql.Identifier(other)))


def _copy_table(source, target, table):
    with source.cursor().copy(_export_query(source, table)) as output:
        with target.cursor().copy(sql.SQL('COPY {} FROM STDIN (FORMAT BINARY)').format(sql.Identifier('public', table))) as incoming:
            for block in output:
                incoming.write(block)


def _copy_state(admin_url, platform_url, agent_url):
    platform, _ = _inputs(admin_url, platform_url, agent_url)
    with psycopg.connect(_admin_url(admin_url, platform['dbname']), row_factory=dict_row) as source:
        source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        with psycopg.connect(agent_url, row_factory=dict_row) as target:
            target.execute('SET LOCAL lock_timeout=10000')
            target.execute(sql.SQL('LOCK TABLE {} IN ACCESS EXCLUSIVE MODE').format(
                sql.SQL(',').join(sql.Identifier('public', table) for table in AGENT_KEYS)))
            original = {table: _fingerprint(source, table) for table in AGENT_KEYS}
            existing = {table: _fingerprint(target, table) for table in AGENT_KEYS}
            if any(existing[table]['rows'] for table in DATA_TABLES):
                if existing != original:
                    raise ValueError('Agent target changed and is nonempty; refusing overwrite')
            else:
                for table in AGENT_KEYS:
                    if _columns(source, table) != _columns(target, table):
                        raise ValueError(f'Official schema differs: {table}')
                for table in ('checkpoint_migrations', 'store_migrations'):
                    if existing[table] != original[table]:
                        raise ValueError(f'Official migration versions differ: {table}')
                for table in DATA_TABLES:
                    _copy_table(source, target, table)
            verified = {table: _fingerprint(target, table) for table in AGENT_KEYS}
            if verified != original:
                raise ValueError('Official Agent COPY verification failed; target data transaction rolled back')
    return verified


def _verify_access(platform_url, agent_url):
    platform, agent = map(conninfo_to_dict, (platform_url, agent_url))
    for url, table, forbidden in ((platform_url, 'platform_users', agent['dbname']),
                                  (agent_url, 'checkpoints', platform['dbname'])):
        with psycopg.connect(url) as conn:
            conn.execute(sql.SQL('SELECT 1 FROM {} LIMIT 1').format(sql.Identifier('public', table)))
            if conn.execute('SELECT has_database_privilege(current_user,%s,\'CONNECT\')', (forbidden,)).fetchone()[0]:
                raise ValueError('A cross-database CONNECT privilege remains')
    for url, database in ((platform_url, agent['dbname']), (agent_url, platform['dbname'])):
        try:
            with psycopg.connect(make_conninfo(url, dbname=database, connect_timeout=5)):
                pass
        except psycopg.Error as exc:
            if exc.sqlstate == '42501' or 'permission denied for database' in str(exc):
                continue
            raise
        raise ValueError('A cross-database application connection was accepted')
    try:
        with psycopg.connect(platform_url) as conn:
            conn.execute('SELECT 1 FROM public.checkpoints LIMIT 1')
    except psycopg.errors.InsufficientPrivilege:
        return
    raise ValueError('The platform role can still read archived Agent checkpoints')


def isolate(admin_url, platform_url, agent_url, *, apply=False):
    report = inspect(admin_url, platform_url, agent_url)
    if not apply:
        return report
    platform, agent = _inputs(admin_url, platform_url, agent_url)
    prepared, step = [], 'roles'
    try:
        with psycopg.connect(admin_url, autocommit=True, row_factory=dict_row) as admin:
            administrator = admin.execute('SELECT current_user AS name').fetchone()['name']
            with admin.transaction():
                for value in (platform, agent):
                    if _role(admin, value['user']) is None:
                        admin.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS').format(
                            sql.Identifier(value['user']), sql.Literal(value['password'])))
            prepared.append('restricted_roles_ready')
            step = 'agent_database'
            if not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s', (agent['dbname'],)).fetchone():
                admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(agent['dbname'])))
            prepared.append('agent_database_ready')
        step = 'platform_privileges'
        _access(admin_url, platform['dbname'], platform['user'], agent['user'], archive_owner=administrator)
        prepared.append('platform_ownership_and_privileges_ready')
        step = 'agent_privileges'
        _access(admin_url, agent['dbname'], agent['user'], platform['user'])
        prepared.append('agent_privileges_ready')
        step = 'official_setup'
        with PostgresSaver.from_conn_string(agent_url) as saver:
            saver.setup()
        with PostgresStore.from_conn_string(agent_url) as store:
            store.setup()
        prepared.append('official_schema_ready')
        step = 'copy'
        report['verified_agent_tables'] = _copy_state(admin_url, platform_url, agent_url)
        prepared.append('agent_data_verified')
        step = 'access_verification'
        _verify_access(platform_url, agent_url)
        prepared.append('cross_database_access_rejected')
    except Exception as exc:
        raise IsolationFailure(step, prepared, exc) from exc
    report.update(result='isolated', prepared=prepared, source_agent_originals='retained_for_admin_archive_review')
    return report


def main():
    from dotenv import load_dotenv
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admin-url', required=True, help='Bootstrap administrator DSN; never used by the running application')
    parser.add_argument('--apply', action='store_true', help='Execute the reviewed role/database/ownership/COPY plan')
    args = parser.parse_args()
    if not os.getenv('DATABASE_URL') or not os.getenv('AGENT_DATABASE_URL'):
        parser.error('DATABASE_URL and AGENT_DATABASE_URL application DSNs are required')
    try:
        report = isolate(args.admin_url, os.environ['DATABASE_URL'], os.environ['AGENT_DATABASE_URL'], apply=args.apply)
    except IsolationFailure as exc:
        print(json.dumps(exc.report, ensure_ascii=False, indent=2))
        raise SystemExit(1) from None
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
