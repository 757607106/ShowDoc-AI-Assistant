"""Skill import boundary, following WeKnora's tenant_skill_source/bundle contracts.

Source: Tencent/WeKnora cbdcebabf48c5ee2d6868b370326aa8341703f62 (MIT; see frontend/UPSTREAM-LICENSE).
Execution and skill discovery stay in the official DeepAgents middleware.
"""
import hashlib
import io
import ipaddress
import json
from pathlib import PurePosixPath
import re
import socket
import stat
import tarfile
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit
import zipfile

import ssl
import urllib3
import yaml

from governance.store import StoreError

MAX_DOWNLOAD = 256 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
MAX_FILE = 32 * 1024 * 1024
MAX_FILES = 20_000
MAX_ENTRIES = 100_000
RESERVED_ENVS = {'PATH', 'HOME', 'USER', 'SHELL', 'LD_PRELOAD', 'LD_LIBRARY_PATH',
                 'PYTHONPATH', 'PYTHONHOME', 'NODE_OPTIONS', 'WEKNORA_SESSION_ID',
                 'WEKNORA_BROWSER_ROOT', 'WEKNORA_SESSION_INPUT_DIR'}


def env_name(name):
    return isinstance(name, str) and re.fullmatch(r'[A-Z_][A-Z0-9_]{0,127}', name) and name not in RESERVED_ENVS and not name.startswith('WEKNORA_SKILL_')


def metadata(content):
    try:
        text = content.decode('utf-8-sig') if isinstance(content, bytes) else content
    except UnicodeDecodeError as exc:
        raise StoreError('SKILL.md 必须为 UTF-8 文本', 400) from exc
    if len(text) > 10 * 1024 * 1024:
        raise StoreError('SKILL.md 超出官方 SkillsMiddleware 的10MB限制', 413)
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    try:
        value = yaml.safe_load(match[1]) if match else None
    except yaml.YAMLError as exc:
        raise StoreError('SKILL.md frontmatter 必须为有效 YAML', 400) from exc
    if not isinstance(value, dict) or not isinstance(value.get('name'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value['name']):
        raise StoreError('SKILL.md 需要有效的 name', 400)
    if not isinstance(value.get('description'), str) or not value['description'].strip():
        raise StoreError('SKILL.md 需要 description，供官方 SkillsMiddleware 发现', 400)
    return value


def _safe_path(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or path.is_absolute() or '..' in path.parts or '\x00' in name:
        raise StoreError('Skill 文件路径超出归档目录', 400)
    return str(path)


def parse_bundle(raw, *, subdir='', remote=False):
    """Read bytes without decoding binary assets or extracting to the host."""
    if len(raw) > MAX_DOWNLOAD:
        raise StoreError('Skill bundle cannot exceed 256 MB', 413)
    files, total = {}, 0
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES:
                raise StoreError('Skill archive has more than 100000 zip entries', 400)
            for entry in entries:
                if entry.is_dir():
                    continue
                name = _safe_path(entry.filename)
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise StoreError('Skill 归档不能包含符号链接', 400)
                if entry.file_size > MAX_FILE:
                    raise StoreError('Skill 单文件不得超过32MB', 413)
                if name in files:
                    raise StoreError('Skill 归档包含重复路径', 400)
                files[name] = archive.read(entry)
                total += len(files[name])
                if total > MAX_TOTAL:
                    raise StoreError('Skill 解压后不得超过512MB', 413)
    elif raw.startswith(b'---') or raw.startswith(b'\xef\xbb\xbf---'):
        files = {'SKILL.md': raw}
    else:
        try:
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:*') as archive:
                for entry in archive.getmembers():
                    if entry.isdir():
                        continue
                    if not entry.isfile():
                        raise StoreError('Skill 归档不能包含链接或设备', 400)
                    name = _safe_path(entry.name)
                    if entry.size > MAX_FILE or len(files) >= MAX_ENTRIES:
                        raise StoreError('Skill 归档超过文件数量或大小限制', 413)
                    if name in files:
                        raise StoreError('Skill 归档包含重复路径', 400)
                    files[name] = archive.extractfile(entry).read(MAX_FILE + 1)
                    total += len(files[name])
                    if total > MAX_TOTAL:
                        raise StoreError('Skill 解压后不得超过512MB', 413)
        except tarfile.TarError as exc:
            raise StoreError('来源未返回有效 ZIP/TAR 或 SKILL.md', 400) from exc
    roots = [name.removesuffix('SKILL.md').rstrip('/') for name in files if PurePosixPath(name).name == 'SKILL.md']
    wanted = _safe_path(subdir).strip('/') if subdir else ''
    if wanted:
        roots = [root for root in roots if root == wanted or root.endswith('/' + wanted)]
    if len(roots) != 1:
        raise StoreError('请选择唯一的 Skill 目录（归档需要一个 SKILL.md）', 400)
    prefix = roots[0] + '/' if roots[0] else ''
    if not remote and any(not name.startswith(prefix) for name in files):
        raise StoreError('上传归档包含 Skill 目录以外的文件', 400)
    kept = {name[len(prefix):]: data for name, data in files.items() if name.startswith(prefix)}
    if len(kept) > MAX_FILES:
        raise StoreError('Skill directory holds more than 20000 files', 400)
    kept['SKILL.md'] = kept['SKILL.md'].removeprefix(b'\xef\xbb\xbf')
    if kept['SKILL.md'].rstrip().endswith(b'---'):
        kept['SKILL.md'] += b'\n'
    meta = metadata(kept['SKILL.md'])
    normalized = io.BytesIO()
    with zipfile.ZipFile(normalized, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(kept.items()):
            archive.writestr(path, data)
    return {'name': meta['name'], 'description': meta['description'], 'version': str(meta.get('version', '')),
            'files': kept, 'archive': normalized.getvalue(), 'bundle_sha256': hashlib.sha256(normalized.getvalue()).hexdigest()}


def _registry(origin, path, query=''):
    parts = [p for p in path.strip('/').split('/') if p]
    if parts and parts[0] in ('skills', 'skill'):
        parts.pop(0)
    if not parts or len(parts) > 2:
        raise StoreError('Skill registry source 无效', 400)
    slug = parts[-1]
    version = parse_qs(query).get('version', [''])[0]
    if '@' in slug:
        slug, version = slug.rsplit('@', 1)
    values = {'slug': slug}
    if len(parts) == 2:
        values['ownerHandle'] = parts[0]
    if version and version != 'latest':
        values['version' if re.fullmatch(r'v?\d+\.\d+(?:\.\d+)?(?:[.-][\w.-]+)?', version) else 'tag'] = version
    return origin + '/api/v1/download?' + urlencode(values), ''


def source_url(source):
    """WeKnora public source locator rules; never run pasted install commands."""
    if not isinstance(source, str) or len(source) > 4000:
        raise StoreError('Skill source 无效', 400)
    source = source.strip().rstrip('/')
    if source.startswith('skills-sh:'):
        parts = source[len('skills-sh:'):].split('/')
        if len(parts) != 3:
            raise StoreError('skills-sh 来源需要 owner/repo/skill', 400)
        return 'https://clawhub.ai/api/v1/skills/' + quote(parts[2], safe='') + '/install?' + urlencode({'reference': source}), ''
    if '://' not in source:
        if '/' in source and not source.startswith('@'):
            raise StoreError('来源有歧义，请使用 GitHub URL 或 @owner/slug', 400)
        return _registry('https://clawhub.ai', source.lstrip('@'))
    url = urlsplit(source)
    if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
        raise StoreError('Skill source 必须为有效 HTTP(S) URL', 400)
    host = url.hostname.lower().removeprefix('www.')
    parts = [p for p in url.path.strip('/').split('/') if p]
    if host == 'skills.sh':
        return source_url('skills-sh:' + '/'.join(parts))
    if host == 'github.com' and len(parts) >= 2:
        owner, repo = parts[:2]
        ref, subdir = 'HEAD', ''
        if len(parts) > 2 and parts[2] in ('tree', 'blob'):
            if len(parts) < 4:
                raise StoreError('GitHub 来源缺少 ref', 400)
            ref, subdir = parts[3], '/'.join(parts[4:])
            subdir = '' if subdir == 'SKILL.md' else subdir.removesuffix('/SKILL.md')
        return f'https://codeload.github.com/{quote(owner)}/{quote(repo.removesuffix(".git"))}/zip/{quote(ref)}', subdir
    if host == 'gitlab.com' and len(parts) >= 2:
        marker = parts.index('-') if '-' in parts else len(parts)
        repo_path = '/'.join(parts[:marker]).removesuffix('.git')
        ref = parts[marker + 2] if marker + 2 < len(parts) else 'HEAD'
        subdir = '/'.join(parts[marker + 3:]) if marker + 3 < len(parts) else ''
        subdir = '' if subdir == 'SKILL.md' else subdir.removesuffix('/SKILL.md')
        return f'https://gitlab.com/{repo_path}/-/archive/{quote(ref)}/{quote(parts[marker-1].removesuffix(".git"))}-{quote(ref)}.zip', subdir
    if host in ('clawhub.ai', 'clawhub.com', 'skillhub.cn', 'api.skillhub.cn') and not url.path.startswith('/api/v1/download'):
        origin = 'https://api.skillhub.cn' if 'skillhub.cn' in host else f'{url.scheme}://{url.netloc}'
        path = parts[-1] if 'skillhub.cn' in host else url.path
        return _registry(origin, path, url.query)
    return source, ''


def _public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise StoreError('Skill 下载 URL 无效', 400)
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    except OSError as exc:
        raise StoreError('Skill 来源主机无法解析', 400) from exc
    if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise StoreError('Skill 来源不能访问内部网络地址', 400)
    return parsed, addresses[0][4][0]


def _download(url):
    parsed, address = _public_url(url)
    options = {'timeout': urllib3.Timeout(connect=10, read=120), 'retries': False}
    if parsed.scheme == 'https':
        pool = urllib3.HTTPSConnectionPool(address, parsed.port or 443, server_hostname=parsed.hostname,
            assert_hostname=parsed.hostname, ssl_context=ssl.create_default_context(), **options)
    else:
        pool = urllib3.HTTPConnectionPool(address, parsed.port or 80, **options)
    try:
        # Pin the verified public address; DNS is not resolved a second time by the client.
        response = pool.urlopen('GET', parsed.path + ('?' + parsed.query if parsed.query else ''),
            redirect=False, preload_content=False, headers={'Host': parsed.netloc,
            'User-Agent': 'WeKnora-SkillInstaller (+https://github.com/Tencent/WeKnora)'})
        try:
            if response.status in (301, 302, 303, 307, 308):
                return None, urljoin(url, response.headers.get('Location', ''))
            if not 200 <= response.status < 300:
                raise StoreError(f'Skill 来源返回 HTTP {response.status}', 400)
            data = bytearray()
            while part := response.read(1024 * 1024, decode_content=True):
                data.extend(part)
                if len(data) > MAX_DOWNLOAD:
                    raise StoreError('Skill bundle cannot exceed 256 MB', 413)
            return bytes(data), None
        finally:
            response.close()
    except urllib3.exceptions.HTTPError as exc:
        raise StoreError(f'Skill 来源下载失败（{type(exc).__name__}）', 400) from exc
    finally:
        pool.close()


def fetch_bundle(source):
    url, subdir = source_url(source)
    for _ in range(6):
        raw, redirect = _download(url)
        if redirect:
            url = redirect
            continue
        if raw.lstrip().startswith(b'{'):
            try:
                handoff = json.loads(raw)
            except ValueError as exc:
                raise StoreError('Skill 来源 JSON 无效', 400) from exc
            if handoff.get('ok') is False:
                raise StoreError('Skill 来源拒绝下载', 400)
            nested = handoff.get('github') or {}
            archive = handoff.get('archiveUrl') or handoff.get('downloadUrl') or (handoff.get('archive') or {}).get('downloadUrl')
            if archive:
                url = urljoin(url, archive)
                subdir = handoff.get('path') or subdir
            elif handoff.get('repo') or nested.get('repo'):
                repo = handoff.get('repo') or nested['repo']
                ref = handoff.get('commit') or nested.get('commit') or 'HEAD'
                url, subdir = source_url(f'https://github.com/{repo}/tree/{ref}/' + (handoff.get('path') or nested.get('path') or ''))
            else:
                raise StoreError('Skill 来源未返回归档地址', 400)
            continue
        return parse_bundle(raw, subdir=subdir, remote=True)
    raise StoreError('Skill 来源重定向或下载转交次数过多', 400)
