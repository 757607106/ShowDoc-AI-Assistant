"""Opt-in browser checks of the upstream assistant and sidebar against local fixtures."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlsplit

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
import pytest

from agent import registry
from tests.platform.test_platform_harness import call, harness, original_prepare
from tests.platform.test_platform_model_protocols import model_record, sdk_provider
from tests.platform.test_platform_mcp_runtime import serve

pytestmark = pytest.mark.skipif(
    os.getenv('RUN_BROWSER_ACCEPTANCE') != '1',
    reason='Set RUN_BROWSER_ACCEPTANCE=1 after building the frontend',
)


@pytest.fixture
def browser_platform(harness, sdk_provider, original_prepare, monkeypatch):
    import app as app_module
    from asgi import create_app
    from tests.fakes.contextdb_fake import FakeContextDBClient
    from webapi import harness as api

    knowledge = FakeContextDBClient()
    knowledge.api_key = 'ctxdb-fake'
    native_request = knowledge._request
    def native_api(method, path, **kwargs):
        if path == '/v1/knowledge/knowledge_bases':
            return knowledge.list_knowledge_bases()
        if path == '/v1/workspaces/members/self/permissions':
            return {'mode': 'personal_compatibility', 'member': {
                'member_id': 'fixture-member', 'member_name': '验收知识库账号', 'role': 'owner'},
                'knowledge_base_permissions': [], 'total': 0}
        return native_request(method, path, **kwargs)
    knowledge._request = native_api
    monkeypatch.setattr('webapi.auth.ContextDBClient', lambda *args, **kwargs: knowledge)
    monkeypatch.setattr(api, '_prepare', original_prepare)
    base, _, _ = sdk_provider
    model = registry.save_model(model_record('aliyun', 'qwen-plus', base), os.environ['TEST_PLATFORM_USER'])
    registry.save_record('settings', {'id': 'default-settings', 'value': {
        'chat_model_id': model['id'], 'utility_model_id': model['id']}}, os.environ['TEST_PLATFORM_USER'])
    _, _, runtime_model, tools, _, _, headers = harness
    with serve(create_app(app_module.app)) as platform:
        yield platform, runtime_model, tools, headers


def _login(page, platform, account='test@example.com', password='test-password-123', target='**/platform/**'):
    page.goto(platform + '/login')
    page.locator('input[autocomplete="username"]').fill(account)
    page.locator('input[autocomplete="current-password"]').fill(password)
    page.locator('button[type="submit"]').click()
    page.wait_for_url(target)


def _get(page, platform, path, headers):
    response = page.request.get(platform + path, headers=headers)
    assert response.ok, (path, response.status, response.text())
    return response.json()


def test_assistant_keeps_its_panel_history_and_session_kind_and_settings_domains(browser_platform):
    from playwright.sync_api import expect, sync_playwright

    platform, model, _, headers = browser_platform
    model.responses = [AIMessage(content='页面助手浏览器验收回答')]
    screenshots = Path(tempfile.mkdtemp(prefix='showdoc-assistant-browser-', dir='/tmp'))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, locale='zh-CN')
        requests = []
        responses, errors = [], []
        page.on('request', lambda request: requests.append(request) if '/agent-chat/' in request.url else None)
        page.on('response', lambda response: responses.append(response)
                if '/agent-chat/' in response.url or '/knowledge-chat/' in response.url else None)
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            _login(page, platform)
            page.goto(platform + '/platform/creatChat')
            page.locator('[data-guide="assistant-entry"]:visible').first.click()
            panel = page.locator('.assistant-panel.is-open')
            expect(panel).to_be_visible()
            composer = panel.locator('.answers-input textarea')
            expect(composer).to_be_visible()
            composer.fill('在页面助手中回答并保留此会话')
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and urlsplit(response.url).path == '/api/v1/sessions') as created:
                composer.press('Enter')
            session_id = created.value.json()['data']['id']
            expect(panel).to_contain_text('页面助手浏览器验收回答', timeout=20000)
            expect(panel.locator('.stop-btn')).to_have_count(0, timeout=20000)
            assert urlsplit(page.url).path == '/platform/creatChat'
            sent = next(request for request in requests if request.url.endswith('/agent-chat/' + session_id))
            assert sent.post_data_json['agent_id'] == 'builtin-weknora-assistant'
            assistant_sessions = _get(page, platform, '/api/v1/sessions?kind=assistant', headers)['data']
            ordinary_sessions = _get(page, platform, '/api/v1/sessions', headers)['data']
            assert session_id in {item['id'] for item in assistant_sessions}
            assert session_id not in {item['id'] for item in ordinary_sessions}
            messages = _get(page, platform, f'/api/v1/messages/{session_id}/load?limit=20', headers)['data']
            assert any(message['role'] == 'assistant' and message['is_completed']
                       and '页面助手浏览器验收回答' in message['content'] for message in messages)
            expect(page.locator(f'.session-chat-row[data-session-id="{session_id}"]')).to_have_count(0)
            page.screenshot(path=str(screenshots / 'assistant-answer.png'), full_page=True)

            page.reload()
            expect(panel).to_contain_text('页面助手浏览器验收回答', timeout=20000)
            assert len(requests) == 1, 'Reload reads checkpoint history without replaying the question'
            panel.locator('button[aria-label="历史对话"]').click()
            expect(panel.locator('.assistant-history__row')).not_to_have_count(0)
            panel.locator('.assistant-history__select').first.click()
            expect(panel).to_contain_text('页面助手浏览器验收回答')

            page.goto(platform + '/platform/settings?section=models')
            expect(page.locator('.model-settings')).to_be_visible()
            expect(page.locator('.native-settings')).to_have_count(0)
            page.screenshot(path=str(screenshots / 'official-model-settings.png'), full_page=True)
            page.goto(platform + '/platform/settings?section=permissions')
            expect(page.locator('.native-settings')).to_be_visible()
            expect(page.locator('.native-settings')).to_contain_text('验收知识库账号')
            expect(page.locator('.native-settings .t-alert--error')).to_have_count(0)
            page.screenshot(path=str(screenshots / 'knowledge-settings-preserved.png'), full_page=True)
            print('ASSISTANT_BROWSER_SCREENSHOTS', screenshots)
        except Exception:
            page.screenshot(path=str(screenshots / 'failure.png'), full_page=True)
            print('ASSISTANT_BROWSER_FAILURE', screenshots, page.url, page.locator('body').inner_text()[:4000])
            print('ASSISTANT_BROWSER_ERRORS', errors)
            print('ASSISTANT_BROWSER_REQUESTS', [request.post_data_json for request in requests])
            print('ASSISTANT_BROWSER_RESPONSES', [(response.status, response.url) for response in responses])
            raise
        finally:
            browser.close()


def test_sidebar_running_completion_and_reload_unread_use_real_message_history(browser_platform):
    from playwright.sync_api import expect, sync_playwright

    platform, model, tools, headers = browser_platform
    release = threading.Event()

    @tool
    async def wait_for_sidebar_check() -> str:
        """Wait until the browser has observed the running indicator."""
        if not await asyncio.to_thread(release.wait, 30):
            raise TimeoutError('Browser did not release the fixture tool')
        return 'released'

    tools.append(wait_for_sidebar_check)
    model.responses = [AIMessage(content='', tool_calls=[call('wait_for_sidebar_check', {})]),
                       AIMessage(content='侧栏状态浏览器验收完成')]
    screenshots = Path(tempfile.mkdtemp(prefix='showdoc-sidebar-browser-', dir='/tmp'))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, locale='zh-CN')
        try:
            _login(page, platform)
            page.goto(platform + '/platform/creatChat')
            composer = page.locator('.platform-route-outlet .answers-input textarea')
            expect(composer).to_be_visible()
            composer.fill('等待侧栏观察后完成本轮')
            composer.press('Enter')
            page.wait_for_url('**/platform/chat/*')
            session_id = urlsplit(page.url).path.rsplit('/', 1)[1]
            row = page.locator(f'.session-chat-row[data-session-id="{session_id}"]')
            expect(row.locator('.session-running-indicator')).to_be_visible(timeout=20000)
            page.wait_for_function('''id => Object.entries(localStorage).some(([key, value]) =>
                key.startsWith('weknora:session-activity:') && Boolean(JSON.parse(value).running[id]))''',
                arg=session_id)
            snapshot = page.evaluate('''() => Object.entries(localStorage)
                .find(([key]) => key.startsWith('weknora:session-activity:'))''')
            assert snapshot and session_id in json.loads(snapshot[1])['running']
            release.set()
            expect(page.locator('body')).to_contain_text('侧栏状态浏览器验收完成', timeout=20000)
            expect(row.locator('.session-running-indicator')).to_have_count(0)
            messages = _get(page, platform, f'/api/v1/messages/{session_id}/load?limit=20', headers)['data']
            assert any(message['role'] == 'assistant' and message['is_completed'] for message in messages)

            # Reopen an earlier persisted running snapshot after server-side completion.
            page.goto(platform + '/platform/creatChat')
            page.evaluate('([key, value]) => localStorage.setItem(key, value)', snapshot)
            page.reload()
            expect(row.locator('.session-unread-indicator')).to_be_visible(timeout=20000)
            row.locator('.submenu_title-text').click()
            expect(row.locator('.session-unread-indicator')).to_have_count(0)
            expect(page.locator('body')).to_contain_text('侧栏状态浏览器验收完成')
            page.screenshot(path=str(screenshots / 'sidebar-completed.png'), full_page=True)
            print('SIDEBAR_BROWSER_SCREENSHOTS', screenshots)
        except Exception:
            page.screenshot(path=str(screenshots / 'failure.png'), full_page=True)
            print('SIDEBAR_BROWSER_FAILURE', screenshots, page.url, page.locator('body').inner_text()[:4000])
            raise
        finally:
            release.set()
            browser.close()


def test_two_personal_workspaces_in_separate_browsers(browser_platform):
    from playwright.sync_api import expect, sync_playwright
    from webapi.auth import create_user

    platform, _, _, headers = browser_platform
    create_user('workspace-reader', 'Reader', 'reader-password', 'viewer')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        a = browser.new_page(locale='zh-CN')
        b = browser.new_page(locale='zh-CN')
        try:
            _login(a, platform)
            _login(b, platform, 'workspace-reader', 'reader-password')
            result = a.request.post(platform + '/api/uploads', headers=headers,
                multipart={'files': {'name':'note.md', 'mimeType':'text/markdown', 'buffer':b'workspace'}})
            assert result.ok, result.text()
            url = platform + '/platform/settings?section=tenant'
            a.goto(url)
            b.goto(url)
            for page, used in [(a, '9 B'), (b, '0 B')]:
                section = page.locator('.tenant-info')
                expect(section.get_by_text('10 GB', exact=True)).to_be_visible()
                expect(section.get_by_text(used, exact=True)).to_be_visible()
                expect(section.get_by_role('button', name='删除空间', exact=True)).to_be_visible()
            a.get_by_role('button', name='修改名称').click()
            a.get_by_placeholder('请输入新的空间名称').fill('Alpha')
            a.get_by_role('button', name='保存', exact=True).click()
            a.get_by_role('button', name='修改描述').click()
            a.get_by_placeholder('请输入新的空间描述').fill('Private files')
            a.get_by_role('button', name='保存', exact=True).click()
            a.reload()
            section = a.locator('.tenant-info')
            expect(section.get_by_text('Private files', exact=True)).to_be_visible()
            expect(section.get_by_text('Alpha', exact=True)).to_be_visible()
            expect(b.locator('.tenant-info').get_by_text("Reader's Workspace", exact=True)).to_be_visible()
            section.get_by_role('button', name='删除空间', exact=True).click()
            dialog = a.locator('.t-dialog').filter(has_text='删除当前空间？')
            confirm = dialog.get_by_role('button', name='删除', exact=True)
            expect(confirm).to_be_disabled()
            dialog.get_by_placeholder('Alpha').fill('Alpha')
            confirm.click()
            a.wait_for_url('**/login**')
            b.reload()
            expect(b.locator('.tenant-info').get_by_text("Reader's Workspace", exact=True)).to_be_visible()
            expect(b.locator('.tenant-info').get_by_text('0 B', exact=True)).to_be_visible()
            _login(a, platform, target='**/onboarding/workspace')
            a.get_by_role('button', name='创建空间', exact=True).click()
            dialog = a.locator('.t-dialog').filter(has_text='创建新空间')
            dialog.locator('input').fill('Fresh')
            dialog.get_by_role('button', name='创建', exact=True).click()
            a.wait_for_url('**/platform/**')
            a.goto(url)
            expect(a.locator('.tenant-info').get_by_text('Fresh', exact=True)).to_be_visible()
            expect(a.locator('.tenant-info').get_by_text('0 B', exact=True)).to_be_visible()
        finally:
            browser.close()
