"""Static Skill import boundary; no installer or execution machinery."""
import io
import json
import zipfile
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

