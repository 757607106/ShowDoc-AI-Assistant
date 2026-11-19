"""Safety guards for explicitly opt-in disposable cloud acceptance."""
import pytest

from scripts.smoke.contextdb_pipeline_smoke import assert_owned, run


def test_default_run_never_constructs_a_cloud_client(monkeypatch):
    monkeypatch.setattr('scripts.smoke.contextdb_pipeline_smoke.ContextDBClient',
        lambda *args, **kwargs: pytest.fail('dry run must not access any cloud resource'))
    assert run()['mutations'] is False


@pytest.mark.parametrize('id,name', [('other-id', 'ctxdb-accept-run-source-0'),
                                    ('owned-id', 'production-library'),
                                    ('owned-id', 'ctxdb-accept-other-source-0')])
def test_cleanup_refuses_resources_outside_exact_run_identity(id, name):
    fixture = {'id': 'owned-id', 'run_id': 'run', 'owned_names': ['ctxdb-accept-run-source-0']}
    with pytest.raises(RuntimeError, match='cleanup refused'):
        assert_owned(fixture, {'id': id, 'name': name})
    assert_owned(fixture, {'id': 'owned-id', 'name': fixture['owned_names'][0]})
