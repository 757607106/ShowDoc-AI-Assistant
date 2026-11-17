"""Prepare selected Skill files for the official StateBackend, without installers."""
import base64
import hashlib
from pathlib import Path, PurePosixPath

from deepagents.backends.utils import create_file_data

from agent import registry
from agent.skill_bundle import parse_bundle
from governance.store import StoreError, data_dir


def prepare_harness_files(owner_id, agent_config, existing_files=None):
    """Return native input.files updates; never read or resume installation jobs."""
    mode = agent_config.get('skills_selection_mode', 'none')
    selected = set(agent_config.get('selected_skills') or [])
    skills = [value for value in registry.records('skill', owner_id)
              if value.get('enabled', True) and (mode == 'all' or
                  (mode == 'selected' and value['name'] in selected))] if mode != 'none' else []
    if mode == 'selected' and selected - {value['name'] for value in skills}:
        raise StoreError('所选 Skill 不存在、已停用或无权访问', 403)
    files = {}
    for skill in skills:
        name = skill['name']
        if name in ('.', '..') or '/' in name or '\\' in name:
            raise StoreError('Skill 名称无效', 400)
        if 'files' in skill:
            contents = {path: content.encode() for path, content in skill['files'].items()}
        else:
            path = Path(skill['_bundle_path']).resolve()
            directory = (data_dir() / 'skill-bundles' / hashlib.sha256(owner_id.encode()).hexdigest()).resolve()
            if not path.is_relative_to(directory):
                raise StoreError('Skill 归档不属于当前用户', 403)
            try:
                contents = parse_bundle(path.read_bytes())['files']
            except OSError as exc:
                raise StoreError('Skill 归档已缺失或无法读取', 409) from exc
        for path, raw in contents.items():
            relative = PurePosixPath(path)
            if relative.is_absolute() or '..' in relative.parts or '\\' in path or '\x00' in path:
                raise StoreError('Skill 文件路径无效', 400)
            try:
                files[f'/skills/{name}/{relative}'] = create_file_data(raw.decode('utf-8'))
            except UnicodeDecodeError:
                files[f'/skills/{name}/{relative}'] = create_file_data(base64.b64encode(raw).decode('ascii'), encoding='base64')
    for child in agent_config.get('subagents', []):
        selected_skills = child.get('selected_skills')
        if selected_skills is None:
            continue
        if set(selected_skills) - {skill['name'] for skill in skills}:
            raise StoreError('子代理只能选择主 Agent 已授权的技能', 403)
        for path, item in list(files.items()):
            if path.startswith('/skills/') and path.split('/')[2] in selected_skills:
                files[f'/subagent-skills/{child["name"]}/{path.removeprefix("/skills/")}'] = item
    files.update({path: None for path in (existing_files or {})
                  if path.startswith(('/skills/', '/subagent-skills/')) and path not in files})
    return files
