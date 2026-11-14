"""Configure official ctxdb CLI/Codex integration without logging credentials."""
import json
import os
import shutil
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values


def main():
    root = Path(__file__).resolve().parents[1]
    values = dotenv_values(root / '.env')
    key = values['CONTEXTDB_API_KEY']
    home = Path.home()
    backup = root / 'downloads' / 'dev-setup-backup' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup.mkdir(parents=True, mode=0o700)
    for relative in ('.ctxdb/ctxdb.json', '.codex/config.toml', '.codex/hooks.json'):
        source = home / relative
        if source.exists():
            target = backup / relative.replace('/', '_')
            shutil.copy2(source, target)
            target.chmod(0o600)
    env = {k:v for k,v in os.environ.items() if k not in ('CTXDB_API_KEY', 'CTXDB_ACCESS_TOKEN')}
    result = subprocess.run(['ctxdb','setup','--agent=codex','--api-key='+key,
        '--base-url='+values.get('CONTEXTDB_BASE_URL','https://context-database.aliyuncs.com'),'--json'],
        env=env,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('ctxdb setup 失败：' + result.stdout.replace(key,'[REDACTED]')[-1200:])
    # The requested integration is development guidance; background capture is out of scope.
    config_path = home / '.ctxdb/ctxdb.json'
    config = json.loads(config_path.read_text())
    config['agents']['codex'].update(auto_capture=False, auto_recall=False, auto_skill_evolution=False)
    config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    config_path.chmod(0o600)
    codex_path = home / '.codex/config.toml'
    text = codex_path.read_text()
    parsed = tomllib.loads(text)
    if 'contextdb' not in parsed.get('mcp_servers',{}):
        text += '\n[mcp_servers.contextdb]\nurl = "https://context-database.aliyuncs.com/v1/mcp"\n'
        text += 'enabled_tools = '+json.dumps(['knowledge.get_base','knowledge.get_document','knowledge.get_graph','knowledge.list_bases',
            'knowledge.list_documents','knowledge.list_entity_chunks','knowledge.list_graph_entities','knowledge.search','knowledge.wiki_search'])+'\n'
        text += 'http_headers = { "X-API-Key" = '+json.dumps(key)+' }\n'
        tomllib.loads(text)
        codex_path.write_text(text)
        codex_path.chmod(0o600)
    status = subprocess.run(['ctxdb','status','--agent=codex','--json'],env=env,capture_output=True,text=True)
    data = json.loads(status.stdout)
    report = {k:data.get(k) for k in ('agent','version','connected','hooks_node_ok','auto_capture','auto_recall','auto_skill_evolution')}
    report.update(mcp_configured=True, hook_trust=data.get('hook_activation',{}).get('trust','unverified'), restart_codex_required=True, backup=str(backup))
    (root/'docs/architecture/contextdb-dev-setup.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
