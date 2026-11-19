"""Account-based maintenance commands retain their existing owner boundaries."""
import hashlib
import json
import sys
from unittest.mock import Mock

import pytest

from scripts import migrate_runtime, verify_crawler_names, verify_knowledge_names


@pytest.mark.parametrize('module,extra', [
    (verify_crawler_names, ['--entry', 'showdoc']),
    (verify_knowledge_names, []),
])
@pytest.mark.parametrize('account,legacy,expected', [
    ('admin', 'old@example.com', 'admin'),
    (None, 'old@example.com', 'old@example.com'),
    (None, None, 'admin'),
])
def test_acceptance_scripts_send_account_without_requiring_an_email(monkeypatch, tmp_path, module, extra,
                                                                  account, legacy, expected):
    monkeypatch.setattr(module, 'load_dotenv', lambda *_: None)
    monkeypatch.setattr('common.env_sanitize.sanitize_no_proxy', lambda: None)
    for key, value in (('PLATFORM_ADMIN_ACCOUNT', account), ('PLATFORM_ADMIN_EMAIL', legacy)):
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    monkeypatch.setenv('PLATFORM_ADMIN_PASSWORD', 'test-password-123')
    monkeypatch.setattr(sys, 'argv', ['verify', *extra, '--report', str(tmp_path / 'flow.json')])
    session = Mock()
    session.request.side_effect = RuntimeError('login request captured')
    monkeypatch.setattr(module.requests, 'Session', lambda: session)
    with pytest.raises(RuntimeError, match='login request captured'):
        module.main()
    assert session.request.call_args.args[0] == 'POST'
    assert session.request.call_args.args[1].endswith('/api/v1/auth/login')
    assert session.request.call_args.kwargs['json'] == {'account': expected, 'password': 'test-password-123'}


@pytest.mark.parametrize('flags,account,legacy,expected', [
    (['--owner-account', ' ADMIN '], 'different', 'old@example.com', 'admin'),
    (['--owner-email', 'Legacy@Example.com'], 'different', None, 'legacy@example.com'),
    ([], 'admin', 'old@example.com', 'admin'),
    ([], None, 'old@example.com', 'old@example.com'),
    ([], None, None, 'admin'),
])
def test_runtime_migration_selects_the_explicit_account_and_preserves_owner_id(
        monkeypatch, tmp_path, capsys, flags, account, legacy, expected):
    monkeypatch.setattr(migrate_runtime, 'load_dotenv', lambda: None)
    monkeypatch.setattr('common.env_sanitize.sanitize_no_proxy', lambda: None)
    for key, value in (('PLATFORM_ADMIN_ACCOUNT', account), ('PLATFORM_ADMIN_EMAIL', legacy)):
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    monkeypatch.setattr(migrate_runtime, 'initialize', lambda: None)
    monkeypatch.setattr(migrate_runtime, 'initialize_checkpoints', lambda: None)
    snapshot = tmp_path / 'snapshot.json'
    snapshot.write_text(json.dumps({'records': []}))
    snapshot.with_suffix('.sha256').write_text(hashlib.sha256(snapshot.read_bytes()).hexdigest())
    connection = Mock()
    connection.execute.return_value.fetchone.return_value = {'id': 'preserved-owner', 'contextdb_member_id': 'member'}
    context = Mock()
    context.__enter__ = Mock(return_value=connection)
    context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(migrate_runtime, 'connection', lambda: context)
    apply = Mock(return_value={'imported': {}})
    monkeypatch.setattr(migrate_runtime, 'import_snapshot', apply)
    monkeypatch.setattr(sys, 'argv', ['migrate', '--snapshot', str(snapshot), '--apply', *flags])
    migrate_runtime.main()
    assert connection.execute.call_args.args[1] == (expected,)
    apply.assert_called_once_with({'records': []}, 'preserved-owner')
    assert json.loads(capsys.readouterr().out)['cloud_writes'] == 0
