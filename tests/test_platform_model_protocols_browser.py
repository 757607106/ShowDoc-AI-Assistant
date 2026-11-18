"""Opt-in browser acceptance against the built frontend and isolated test database."""
import os
from pathlib import Path
import re
import tempfile

import pytest

from agent import config, registry, sessions
from tests.test_platform_model_protocols import model_record, sdk_provider
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
    def context_request(method, path, **kwargs):
        if path == '/v1/knowledge/knowledge_bases':
            return knowledge.list_knowledge_bases()
        if path == '/v1/workspaces/members/self/permissions':
            return {'member': {'member_id': 'test-member', 'role': 'admin'}, 'permissions': []}
        if path == '/v1/workspaces/members':
            return {'members': [{'member_id': 'test-member', 'member_name': 'Browser fixture'}], 'total': 1}
        return native_request(method, path, **kwargs)
    knowledge._request = context_request
    monkeypatch.setattr('webapi.auth.ContextDBClient', lambda *args, **kwargs: knowledge)

    base, calls, state = sdk_provider
    owner = os.environ['TEST_PLATFORM_USER']
    model = registry.save_model({**model_record('aliyun', 'qwen-plus', base), 'display_name': 'SDK Qwen fixture'}, owner)
    registry.save_record('settings', {'id': 'default-settings', 'value': {'chat_model_id': model['id']}}, owner)
    agent = config.save_agent({'name': 'SDK acceptance', 'config': {'model_id': model['id'], 'kb_selection_mode': 'none',
        'mcp_selection_mode': 'none', 'memory_enabled': False, 'reasoning_effort': 'auto', 'access_level': 'confirm'}}, owner)
    session = sessions.create_session('SDK browser acceptance', owner, {'agent_id': agent['id'], 'agent_config': agent['config']})
    screenshots = Path(tempfile.mkdtemp(prefix='showdoc-model-browser-', dir='/tmp'))
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
            page.locator('input[autocomplete="username"]').fill('test@example.com')
            page.locator('input[autocomplete="current-password"]').fill('test-password-123')
            page.locator('button[type="submit"]').click()
            page.wait_for_url('**/platform/**')
            page.goto(platform + '/platform/settings?section=models')
            expect(page.locator('.model-settings')).to_be_visible()
            page.locator('.model-header-actions').get_by_role('button', name='添加模型').click()
            editor = page.locator('.t-drawer').filter(has=page.locator('.model-type-options'))
            expect(editor.locator('.model-type-options').get_by_role('radio')).to_have_count(5)
            expect(editor.locator('.source-options').get_by_role('radio')).to_have_count(1)
            editor.locator('.t-select').first.click()
            page.locator('.provider-option').filter(has_text='阿里云').first.click()
            editor.locator('.form-item').filter(has=page.locator('.t-select')).nth(1).locator('.t-select').click()
            page.locator('.catalog-model-option').filter(has_text='Qwen3.8 Max').first.click()
            base_field = editor.locator('.form-item').filter(has=page.get_by_text('Base URL', exact=True)).locator('input')
            expect(base_field).to_have_value('https://dashscope.aliyuncs.com/compatible-mode/v1')
            display_name = editor.locator('.form-item').filter(has=page.get_by_text('显示名称（可选）', exact=True)).locator('input')
            display_name.fill('浏览器配置验收')
            base_field.fill(base + '/v1')
            editor.locator('.api-key-input input').fill('browser-fixture')
            editor.get_by_role('button', name='测试连接').click()
            expect(editor.locator('.connection-status')).to_have_text('连接成功', timeout=15000)
            assert calls[-1]['payload']['model'] == 'qwen3.8-max' and calls[-1]['headers']['authorization'] == 'Bearer browser-fixture'
            page.screenshot(path=str(screenshots / 'model-editor.png'), full_page=True)
            editor.get_by_role('button', name='保存并关闭').click()
            expect(page.locator('.model-settings')).to_contain_text('浏览器配置验收')
            card = page.locator('.model-card').filter(has_text='浏览器配置验收')
            card.locator('.model-card__title').click()
            editor = page.locator('.t-drawer').filter(has=page.locator('.credential-resource'))
            credential = editor.locator('.credential-row').first
            credential.get_by_role('button', name='更换').click()
            credential.locator('input').fill('browser-fixture-rotated')
            with page.expect_response(lambda r: r.url.endswith('/credentials') and r.request.method == 'PUT') as rotated:
                credential.get_by_role('button', name='保存', exact=True).click()
            assert rotated.value.json()['data']['fields']['api_key'] == {'configured': True}
            editor.get_by_role('button', name='测试连接').click()
            expect(editor.locator('.connection-status')).to_have_text('连接成功', timeout=15000)
            assert calls[-1]['headers']['authorization'] == 'Bearer browser-fixture-rotated'
            editor.get_by_role('button', name='保存并关闭').click()
            page.goto(platform + '/platform/settings?section=defaults')
            defaults = page.locator('.default-settings')
            expect(defaults.locator('.model-control .model-selector')).to_have_count(6)
            chat_slot = defaults.locator('.setting-row').filter(has=page.get_by_text('默认对话模型', exact=True))
            chat_slot.locator('.t-select').click()
            with page.expect_response(lambda r: r.url.endswith('/default-settings') and r.request.method == 'PUT') as selected:
                page.locator('.model-option').filter(has_text='浏览器配置验收').click()
            selected_id = selected.value.json()['data']['chat_model_id']
            assert registry.default_model_id(owner) == selected_id
            page.reload()
            expect(chat_slot).to_contain_text('浏览器配置验收')
            page.screenshot(path=str(screenshots / 'workspace-defaults.png'), full_page=True)
            page.locator('.nav-label').filter(has_text='空间信息').click()
            expect(page.locator('.tenant-info-body')).to_be_visible()
            page.locator('.nav-label').filter(has_text='成员管理').click()
            expect(page.get_by_role('button', name='添加成员')).to_be_visible()
            expect(page.locator('.t-table')).to_contain_text('test@example.com')
            # Bind a real Agent through its API before exercising the settings deletion flow.
            headers = {'Authorization': authenticated_client.environ_base['HTTP_AUTHORIZATION']}
            bound = page.request.post(platform + '/api/v1/agents', headers=headers,
                                      data={'name': '浏览器引用验收', 'config': {'model_id': selected_id}})
            assert bound.status == 201
            page.goto(platform + '/platform/settings?section=models')
            card.hover()
            card.locator('.model-card__delete').click()
            with page.expect_response(lambda r: r.request.method == 'DELETE' and r.url.endswith('/' + selected_id)) as conflict:
                page.locator('.t-popconfirm').get_by_role('button', name='删除', exact=True).click()
            assert conflict.value.status == 400 and conflict.value.json()['error']['code'] == 2300
            expect(page.locator('.model-usage-dialog')).to_contain_text('浏览器引用验收')
            page.screenshot(path=str(screenshots / 'delete-in-use.png'), full_page=True)
            page.goto(platform + '/platform/settings?section=models')
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
            composer = page.locator('.platform-route-outlet .answers-input textarea')
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
            print('MODEL_BROWSER_SCREENSHOTS', screenshots)
        except Exception:
            page.screenshot(path=str(screenshots / 'browser-failure.png'), full_page=True)
            print('PROVIDER_CALLS', [{'path': c['path'], 'model': c['payload'].get('model'), 'stream': c['payload'].get('stream')} for c in calls])
            print('CHAT_NETWORK', network)
            print('BROWSER_PAGE', page.url, page.locator('body').inner_text()[:5000])
            raise
        finally:
            browser.close()
