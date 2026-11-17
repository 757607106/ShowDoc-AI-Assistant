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


def test_native_skill_catalog_keeps_files_without_projecting_installation_success(authenticated_client):
    from agent import registry, sandbox
    http = authenticated_client
    owner = os.environ['TEST_PLATFORM_USER']
    uploaded = http.post('/api/v1/skills/catalog', json={'files': {
        'SKILL.md': manifest(), 'reference.txt': 'Supporting instructions', 'scripts/run.py': 'print("ok")'}})
    assert uploaded.status_code == 201, uploaded.json
    item = uploaded.json['data']
    catalog = http.get('/api/v1/skills/catalog').json['data']
    assert len(catalog) == 1 and catalog[0]['id'] == item['id']
    assert catalog[0]['installations'] == []
    assert catalog[0]['execution_mode'] == 'native_middleware'
    assert catalog[0]['dependency_status'] == 'not_managed'
    base = f'/api/v1/skills/catalog/{item["id"]}'
    assert http.get(base + '/files/content?path=reference.txt').json['data']['content'] == 'Supporting instructions'
    assert http.get(base + '/files/content?path=scripts/run.py').json['data']['content'] == 'print("ok")'
    for config_id in ('state-backend', sandbox.CONFIG_ID):
        available = http.get('/api/v1/skills', query_string={'sandbox_config_id': config_id})
        assert available.status_code == 200, available.json
        assert available.json['skills_available'] is True
        assert 'scripts_available' not in available.json
        assert available.json['dependency_status'] == 'not_managed'
        assert [row['name'] for row in available.json['data']] == ['guide']
        assert http.get(f'/api/v1/sandbox-configs/{config_id}/skills').json['data'] == []
        assert http.get(f'/api/v1/sandbox-configs/{config_id}/skills/{item["id"]}').status_code == 404
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
    assert catalog[0]['enabled'] is False
    assert catalog[0]['installations'] == []
    assert authenticated_client.get(f'/api/v1/sandbox-configs/{sandbox.CONFIG_ID}/skills/private').status_code == 404
    assert authenticated_client.get('/api/v1/skills?sandbox_config_id=missing').status_code == 404
    old = authenticated_client.get('/api/v1/skills?sandbox_config_id=archived').json
    assert old['skills_available'] is False and old['data'] == []


def test_old_installations_stay_read_only_and_protect_the_referenced_bundle(authenticated_client):
    from agent import registry, sandbox
    owner = os.environ['TEST_PLATFORM_USER']
    http = authenticated_client
    uploaded = http.post('/api/v1/skills/catalog', data={'file': (io.BytesIO(archive({
        'SKILL.md': manifest(), 'image.png': b'\x89PNG\xff\x00'})), 'guide.zip')})
    assert uploaded.status_code == 201
    item = uploaded.json['data']
    row = registry.save_record('skill_install', {'id': 'historic', 'catalog_id': item['id'],
        'sandbox_config_id': sandbox.CONFIG_ID, 'name': 'guide', 'status': 'ready'}, owner)
    base = f'/api/v1/sandbox-configs/{sandbox.CONFIG_ID}/skills/historic'
    historical = http.get(base).json['data']
    assert historical['id'] == row['id'] and historical['read_only'] is True
    assert historical['enabled'] is False and historical['execution_available'] is False
    binary = http.get(base + '/files/content?path=image.png').json['data']
    assert binary['encoding'] == 'base64' and binary['content'] == 'iVBOR/8A'
    assert http.delete(f'/api/v1/skills/catalog/{item["id"]}').status_code == 409
    assert http.post('/api/v1/skills/catalog', json={'files': {'SKILL.md': manifest()}}).status_code == 409
    assert http.get(f'/api/v1/skills/catalog/{item["id"]}/files/content?path=image.png').json['data'] == binary
    for suffix in ('', '/reinstall', '/stop'):
        response = http.patch(base, json={'enabled': True}) if not suffix else http.post(base + suffix, json={})
        assert response.status_code == 410
    assert http.post(f'/api/v1/skills/catalog/{item["id"]}/install', json={}).status_code == 410
    assert registry.record('skill_install', 'historic', owner)['status'] == 'ready'


def test_skill_content_mutations_require_admin_and_delete_keeps_other_catalog_data(authenticated_client):
    from agent import registry
    from webapi.auth import create_user
    owner = os.environ['TEST_PLATFORM_USER']
    http = authenticated_client
    created = http.post('/api/v1/skills/catalog', json={'files': {'SKILL.md': manifest()}}).json['data']
    registry.save_record('skill', {'id': 'untouched', 'name': 'untouched'}, owner)
    create_user('viewer@example.com', 'Viewer', 'test-password-123', 'viewer')
    viewer = http.application.test_client()
    token = viewer.post('/api/v1/auth/login', json={'email': 'viewer@example.com', 'password': 'test-password-123'}).json['token']
    viewer.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + token
    assert viewer.post('/api/v1/skills/catalog', json={'files': {'SKILL.md': manifest('viewer')}}).status_code == 403
    assert viewer.get(f'/api/v1/skills/catalog/{created["id"]}/files').status_code == 404
    assert http.delete(f'/api/v1/skills/catalog/{created["id"]}').status_code == 200
    assert [row['id'] for row in registry.records('skill', owner)] == ['untouched']

