"""Static Skill import boundary; no installer or execution machinery."""
import io
import json
import zipfile
import os
import pytest
from agent.skill_bundle import parse_bundle, source_url
from governance.store import StoreError


def archive(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path, content in files.items():
            bundle.writestr(path, content)
    return out.getvalue()


def manifest(name='guide'):
    return f'---\nname: {name}\ndescription: An audited skill\nversion: 1.0\n---\nUse supporting files. AUDIT_TOKEN is required at runtime.'


def test_bundle_boundary_keeps_binary_and_rejects_traversal_links_duplicate_roots():
    bundle = parse_bundle(archive({'guide/SKILL.md': manifest(), 'guide/image.png': b'\x89PNG\xff\x00'}))
    assert bundle['files']['image.png'] == b'\x89PNG\xff\x00'
    for files in ({'SKILL.md': manifest(), '../escape': 'bad'}, {'one/SKILL.md': manifest(), 'two/SKILL.md': manifest('two')}):
        with pytest.raises(StoreError):
            parse_bundle(archive(files))
    linked = io.BytesIO()
    with zipfile.ZipFile(linked, 'w') as bundle:
        entry = zipfile.ZipInfo('linked')
        entry.external_attr = 0o120777 << 16
        bundle.writestr(entry, '/etc/passwd')
        bundle.writestr('SKILL.md', manifest())
    with pytest.raises(StoreError, match='链接'):
        parse_bundle(linked.getvalue())


def test_official_source_locator_rules_do_not_treat_repository_html_as_skill():
    assert source_url('https://github.com/acme/skills/tree/main/skills/guide') == ('https://codeload.github.com/acme/skills/zip/main', 'skills/guide')
    url, _ = source_url('skills-sh:acme/skills/guide')
    assert '/api/v1/skills/guide/install?' in url and 'reference=skills-sh%3Aacme%2Fskills%2Fguide' in url
    assert source_url('@acme/guide')[0].startswith('https://clawhub.ai/api/v1/download?')
    assert 'slug=guide' in source_url('https://skillhub.cn/skills/acme/guide')[0]
    with pytest.raises(StoreError, match='歧义'):
        source_url('acme/guide')
    with pytest.raises(StoreError):
        parse_bundle(b'<html>GitHub page</html>')


def test_skill_source_redirects_and_handoffs_preserve_public_network_boundary(monkeypatch):
    from agent import skill_bundle
    monkeypatch.setattr('socket.getaddrinfo', lambda *a, **k: [(2, 1, 6, '', ('127.0.0.1', 443))])
    with pytest.raises(StoreError, match='内部网络'):
        skill_bundle._public_url('https://public-looking.example/skill.zip')
    calls = []
    body = archive({'repo/skills/guide/SKILL.md': manifest(), 'repo/README.md': 'repository documentation'})
    def download(url):
        calls.append(url)
        return (json.dumps({'archiveUrl': 'https://public.example/skill.zip', 'path': 'skills/guide'}).encode(), None) if len(calls) == 1 else (body, None)
    monkeypatch.setattr(skill_bundle, '_download', download)
    bundle = skill_bundle.fetch_bundle('@acme/guide')
    assert bundle['name'] == 'guide' and list(bundle['files']) == ['SKILL.md']
    assert calls[1] == 'https://public.example/skill.zip'


def test_builtin_skill_directory_catalog_and_files_share_ready_instructions(authenticated_client):
    from agent import registry, sandbox
    http = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    uploaded = http.post('/api/v1/skills/catalog', json={'files': {
        'SKILL.md': manifest(), 'reference.txt': 'Supporting instructions'}})
    assert uploaded.status_code == 201, uploaded.json
    item = uploaded.json['data']
    catalog = http.get('/api/v1/skills/catalog').json['data']
    assert len(catalog) == 1 and catalog[0]['id'] == item['id']
    for config_id in ('state-backend', sandbox.CONFIG_ID):
        available = http.get('/api/v1/skills', query_string={'sandbox_config_id': config_id})
        assert available.status_code == 200, available.json
        assert available.json['skills_available'] is True
        assert available.json['scripts_available'] is False
        assert [row['name'] for row in available.json['data']] == ['guide']
        installation = next(row for row in catalog[0]['installations'] if row['sandbox_config_id'] == config_id)
        assert installation['status'] == 'ready' and installation['enabled'] is True
        assert installation['execution_mode'] == 'instructions_only'
        base = f'/api/v1/sandbox-configs/{config_id}/skills/{installation["skill_id"]}'
        assert http.get(base).json['data']['name'] == 'guide'
        assert http.get(base + '/files/content?path=reference.txt').json['data']['content'] == 'Supporting instructions'
        rows = http.get(f'/api/v1/sandbox-configs/{config_id}/skills').json['data']
        assert len(rows) == 1 and rows[0]['id'] == item['id']
    assert registry.records('skill_install', owner) == []


def test_skill_directory_filters_disabled_and_other_members_without_claiming_old_backends(authenticated_client):
    from agent import registry, sandbox
    owner = os.environ['TEST_PLATFORM_USER']
    registry.save_record('skill', {'id': 'disabled', 'name': 'disabled', 'enabled': False}, owner)
    registry.save_record('skill', {'id': 'private', 'name': 'private'}, 'another-owner')
    registry.save_record('sandbox', {'id': 'archived'}, owner)
    for config_id in ('state-backend', sandbox.CONFIG_ID):
        data = authenticated_client.get('/api/v1/skills', query_string={'sandbox_config_id': config_id}).json
        assert data['skills_available'] is True and data['data'] == []
    catalog = authenticated_client.get('/api/v1/skills/catalog').json['data']
    assert [row['name'] for row in catalog] == ['disabled']
    assert all(not row['enabled'] for row in catalog[0]['installations'])
    assert authenticated_client.get(f'/api/v1/sandbox-configs/{sandbox.CONFIG_ID}/skills/private').status_code == 404
    assert authenticated_client.get('/api/v1/skills?sandbox_config_id=missing').status_code == 404
    old = authenticated_client.get('/api/v1/skills?sandbox_config_id=archived').json
    assert old['skills_available'] is False and old['data'] == []

