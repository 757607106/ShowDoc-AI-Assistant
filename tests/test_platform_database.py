"""Pool reuse must preserve transaction boundaries and isolated database targets."""
import os
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest

from governance.database import close_pool, connection, initialize


def test_pool_reuses_connections_and_nested_transactions_stay_independent():
    pids=[]
    for _ in range(5):
        with connection() as conn:
            pids.append(conn.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid'])
    assert len(set(pids)) == 1
    with connection() as outer:
        outer.execute('CREATE TABLE pool_probe (value integer)')
    with connection() as outer:
        outer.execute('INSERT INTO pool_probe VALUES (1)')
        with connection() as inner:
            assert inner.execute('SELECT count(*) AS n FROM pool_probe').fetchone()['n'] == 0
    with pytest.raises(RuntimeError):
        with connection() as conn:
            conn.execute('INSERT INTO pool_probe VALUES (2)')
            raise RuntimeError('rollback')
    with connection() as conn:
        assert conn.execute('SELECT value FROM pool_probe').fetchall() == [{'value':1}]


def test_pool_switches_database_target_without_leaking_schema(monkeypatch):
    primary=os.environ['DATABASE_URL']
    other='pool_'+uuid.uuid4().hex
    with psycopg.connect(primary,autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(other)))
    try:
        with connection() as conn:
            first=conn.execute('SELECT current_schema() AS name').fetchone()['name']
        with monkeypatch.context() as patch:
            patch.setenv('DATABASE_URL',make_conninfo(primary,options='-csearch_path='+other))
            initialize()
            with connection() as conn:
                assert conn.execute('SELECT current_schema() AS name').fetchone()['name'] == other
                assert conn.execute("SELECT to_regclass('platform_users') AS name").fetchone()['name'] == 'platform_users'
        initialize()
        with connection() as conn:
            assert conn.execute('SELECT current_schema() AS name').fetchone()['name'] == first
    finally:
        close_pool()
        with psycopg.connect(primary,autocommit=True) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(other)))


def test_concurrent_initialization_is_once_per_process_and_database_target(monkeypatch):
    primary = os.environ['DATABASE_URL']
    schema = 'initialize_' + uuid.uuid4().hex
    with psycopg.connect(primary, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    target = make_conninfo(primary, options=f'-csearch_path={schema} -clock_timeout=1000')
    try:
        with monkeypatch.context() as patch:
            patch.setenv('DATABASE_URL', target)
            barrier = threading.Barrier(8)
            def start():
                barrier.wait(timeout=5)
                initialize()
            with ThreadPoolExecutor(max_workers=8) as workers:
                futures = [workers.submit(start) for _ in range(8)]
                for future in futures:
                    future.result(timeout=15)
            with psycopg.connect(target) as reader:
                assert reader.execute('SELECT count(*) FROM platform_users').fetchone()[0] == 0
                # A normal reader blocks ALTER TABLE; warm initialization must perform no DDL.
                with ThreadPoolExecutor(max_workers=4) as workers:
                    futures = [workers.submit(initialize) for _ in range(4)]
                    for future in futures:
                        future.result(timeout=5)
    finally:
        close_pool()
        with psycopg.connect(primary, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_independent_processes_can_initialize_the_same_empty_schema_together():
    primary = os.environ['DATABASE_URL']
    schema = 'initialize_' + uuid.uuid4().hex
    with psycopg.connect(primary, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    target = make_conninfo(primary, options=f'-csearch_path={schema} -clock_timeout=10000')
    script = '''
import sys
from governance.database import connection, initialize
print('ready', flush=True)
sys.stdin.readline()
initialize()
with connection() as conn:
    assert conn.execute('SELECT count(*) AS n FROM platform_users').fetchone()['n'] == 0
print('initialized', flush=True)
'''
    children = []
    try:
        for _ in range(4):
            children.append(subprocess.Popen([sys.executable, '-c', script],
                env={**os.environ, 'DATABASE_URL': target}, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        for child in children:
            assert child.stdout.readline().strip() == 'ready'
        for child in children:
            child.stdin.write('\n')
            child.stdin.flush()
        for child in children:
            output, error = child.communicate(timeout=20)
            assert child.returncode == 0, error
            assert output.strip() == 'initialized'
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.communicate()
        with psycopg.connect(primary, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
