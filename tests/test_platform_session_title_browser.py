"""Opt-in acceptance of the official sidebar title flow, using only local models."""
import json
import os
from pathlib import Path
import tempfile

import pytest

from agent import registry, sessions
from tests.test_platform_harness import harness, original_prepare
from tests.test_platform_model_protocols import model_record, sdk_provider
from tests.test_platform_mcp_runtime import serve


@pytest.mark.skipif(os.getenv('RUN_BROWSER_ACCEPTANCE') != '1', reason='Set RUN_BROWSER_ACCEPTANCE=1 after building the frontend')
def test_first_question_updates_sidebar_and_header_and_survives_reload(harness, sdk_provider, monkeypatch):
    import app as app_module
    from asgi import create_app
    from playwright.sync_api import expect, sync_playwright
    from tests.contextdb_fake import FakeContextDBClient

    knowledge = FakeContextDBClient()
    knowledge.api_key = 'ctxdb-fake'
    native_request = knowledge._request
    knowledge._request = lambda method, path, **kwargs: knowledge.list_knowledge_bases() if path == '/v1/knowledge/knowledge_bases' else native_request(method, path, **kwargs)
    monkeypatch.setattr('webapi.auth.ContextDBClient', lambda *args, **kwargs: knowledge)

    base, calls, _ = sdk_provider
    owner = os.environ['TEST_PLATFORM_USER']
    model = registry.save_model(model_record('aliyun', 'qwen-plus', base), owner)
    registry.save_record('settings', {'id': 'default-settings', 'value': {
        'chat_model_id': model['id'], 'utility_model_id': model['id']}}, owner)
    screenshots = Path(tempfile.mkdtemp(prefix='showdoc-session-title-browser-', dir='/tmp'))

    with serve(create_app(app_module.app)) as platform, sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, locale='zh-CN')
        try:
            page.goto(platform + '/login')
            page.locator('input[autocomplete="email"]').fill('test@example.com')
            page.locator('input[autocomplete="current-password"]').fill('test-password-123')
            page.locator('button[type="submit"]').click()
            page.wait_for_url('**/platform/**')
            page.goto(platform + '/platform/creatChat')
            composer = page.locator('.platform-route-outlet .answers-input textarea')
            expect(composer).to_be_visible()
            composer.fill('请说明如何查询数据库并定位慢查询')
            with page.expect_response(lambda response: '/api/v1/agent-chat/' in response.url or '/api/v1/knowledge-chat/' in response.url) as streamed:
                composer.press('Enter')
            page.wait_for_url('**/platform/chat/*')
            session_id = page.url.split('/platform/chat/', 1)[1].split('?', 1)[0]
            title = 'fixture answer'
            sidebar = page.locator(f'.session-chat-row[data-session-id="{session_id}"] .submenu_title-text')
            header = page.locator('.chat-header__title-text')
            expect(sidebar).to_have_text(title, timeout=20000)
            expect(header).to_have_text(title)
            expect(page.locator('body')).to_contain_text('官方 Harness 回答')
            events = [json.loads(line[6:]) for line in streamed.value.text().splitlines() if line.startswith('data: ')]
            title_event = next(event for event in events if event.get('response_type') == 'session_title')
            assert title_event['data'] == {'session_id': session_id, 'title': title}
            assert sessions.get_session(session_id, owner)['title'] == title
            assert len(calls) == 1 and calls[0]['payload'].get('stream', False) is False
            page.screenshot(path=str(screenshots / 'title-updated.png'), full_page=True)

            page.reload()
            expect(sidebar).to_have_text(title, timeout=20000)
            expect(header).to_have_text(title)
            expect(page.locator('body')).to_contain_text('官方 Harness 回答')
            assert len(calls) == 1, 'Reload must read the saved title without another model request'
            page.screenshot(path=str(screenshots / 'title-restored.png'), full_page=True)
            print('SESSION_TITLE_BROWSER_SCREENSHOTS', screenshots)
        except Exception:
            page.screenshot(path=str(screenshots / 'failure.png'), full_page=True)
            print('SESSION_TITLE_BROWSER_FAILURE', screenshots, page.url, page.locator('body').inner_text()[:4000])
            raise
        finally:
            browser.close()
