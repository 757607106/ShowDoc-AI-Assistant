"""Opt-in browser acceptance against the built frontend and isolated test database."""
import os
from pathlib import Path
import re

import pytest

from agent import config, registry, sessions
from tests.test_platform_litellm import model_record, sdk_provider
from tests.test_platform_mcp_runtime import serve


@pytest.mark.skipif(os.getenv('RUN_BROWSER_ACCEPTANCE') != '1', reason='Set RUN_BROWSER_ACCEPTANCE=1 after building the frontend')
def test_browser_model_debug_thinking_approval_and_reload(authenticated_client, sdk_provider, monkeypatch):
    from asgi import create_app
    import app as app_module
    from playwright.sync_api import sync_playwright, expect
    from tests.contextdb_fake import FakeContextDBClient

    knowledge = FakeContextDBClient()
    knowledge.api_key = 'ctxdb-fake'
    native_request = knowledge._request
    knowledge._request = lambda method, path, **kwargs: knowledge.list_knowledge_bases() if path == '/v1/knowledge/knowledge_bases' else native_request(method, path, **kwargs)
    monkeypatch.setattr('webapi.auth.ContextDBClient', lambda *args, **kwargs: knowledge)

    base, calls, state = sdk_provider
    owner = os.environ['TEST_PLATFORM_USER']
    model = registry.save_model({**model_record('aliyun', 'qwen-plus', base), 'display_name': 'SDK Qwen fixture'}, owner)
    registry.save_record('settings', {'id': 'default-settings', 'value': {'chat_model_id': model['id']}}, owner)
    agent = config.save_agent({'name': 'SDK acceptance', 'config': {'model_id': model['id'], 'kb_selection_mode': 'none',
        'mcp_selection_mode': 'none', 'memory_enabled': False, 'reasoning_effort': 'auto', 'access_level': 'confirm'}}, owner)
    session = sessions.create_session('SDK browser acceptance', owner, {'agent_id': agent['id'], 'agent_config': agent['config']})
    screenshots = Path('output/verification/litellm-sdk-20261115')
    screenshots.mkdir(parents=True, exist_ok=True)
    with serve(create_app(app_module.app)) as platform, sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, locale='zh-CN')
        network = []
        def response_received(response):
            if any(path in response.url for path in ('/agent-chat/', '/knowledge-chat/', '/messages/')):
                network.append({'url': response.url, 'status': response.status, 'request': response.request.post_data,
                                'body': response.text()})
        page.on('response', response_received)
        try:
            page.goto(platform + '/login')
            page.locator('input[autocomplete="email"]').fill('test@example.com')
            page.locator('input[autocomplete="current-password"]').fill('test-password-123')
            page.locator('button[type="submit"]').click()
            page.wait_for_url('**/platform/**')
            page.goto(platform + '/platform/settings?section=models')
            expect(page.locator('.model-settings')).to_be_visible()
            page.get_by_role('button', name='模型测试', exact=True).click()
            debug = page.locator('.model-debug')
            expect(debug).to_be_visible()
            debug.locator('.t-select').first.click()
            page.locator('.t-select-option').filter(has_text='SDK Qwen fixture').last.click()
            debug.locator('textarea').first.fill('验证 SDK 深度思考')
            debug.locator('.t-select').last.click()
            page.locator('.t-select-option').filter(has_text=re.compile('自动')).last.click()
            page.get_by_role('button', name='运行测试', exact=True).click()
            expect(page.locator('.result-banner--ok')).to_be_visible(timeout=20000)
            expect(debug).to_contain_text('fixture reasoning')
            assert calls[-1]['payload']['enable_thinking'] is True
            page.screenshot(path=str(screenshots / 'model-debug.png'), full_page=True)

            state.update(tool='write_file', args={'file_path': '/browser-sdk.txt', 'content': 'SDK browser file'})
            page.goto(platform + '/platform/chat/' + session['id'])
            page.wait_for_load_state('networkidle')
            composer = page.locator('.answers-input textarea')
            expect(composer).to_be_visible()
            composer.fill('请创建 SDK 验收文件')
            composer.press('Enter')
            approve = page.get_by_role('button', name=re.compile('通过并执行'))
            expect(approve).to_be_visible(timeout=20000)
            expect(page.locator('body')).to_contain_text('fixture reasoning')
            page.screenshot(path=str(screenshots / 'chat-approval.png'), full_page=True)
            before = len(calls)
            approve.click()
            expect(page.locator('body')).to_contain_text('fixture answer', timeout=20000)
            assert len(calls) == before + 1
            page.reload()
            expect(page.locator('body')).to_contain_text('fixture answer', timeout=20000)
            page.locator('.tree-root').last.click()
            expect(page.locator('body')).to_contain_text('fixture reasoning')
            assert len(calls) == before + 1
            page.screenshot(path=str(screenshots / 'chat-restored.png'), full_page=True)
        except Exception:
            page.screenshot(path=str(screenshots / 'browser-failure.png'), full_page=True)
            print('PROVIDER_CALLS', [{'path': c['path'], 'model': c['payload'].get('model'), 'stream': c['payload'].get('stream')} for c in calls])
            print('CHAT_NETWORK', network)
            print('BROWSER_PAGE', page.url, page.locator('body').inner_text()[:5000])
            raise
        finally:
            browser.close()
