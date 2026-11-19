"""Opt-in real-browser acceptance for native Agent configuration and capability gates."""
import asyncio
import os
from pathlib import Path
import re
import tempfile
import threading
from urllib.parse import urlsplit

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from agent import config, registry
from tests.platform.test_platform_assistant_browser import browser_platform
from tests.platform.test_platform_harness import call, harness, original_prepare
from tests.platform.test_platform_model_protocols import sdk_provider

pytestmark = pytest.mark.skipif(
    os.getenv('RUN_BROWSER_ACCEPTANCE') != '1',
    reason='Set RUN_BROWSER_ACCEPTANCE=1 after building the current frontend',
)


@pytest.fixture
def alignment_page(browser_platform):
    from playwright.sync_api import sync_playwright
    platform, _, _, _ = browser_platform
    screenshots = Path(tempfile.mkdtemp(prefix='showdoc-agent-alignment-browser-', dir='/tmp'))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, locale='zh-CN')
        page.set_default_timeout(10000)
        requested = []
        page.on('request', lambda request: requested.append((request.method, urlsplit(request.url).path)))
        try:
            page.goto(platform + '/login')
            page.locator('input[autocomplete="username"]').fill('test@example.com')
            page.locator('input[autocomplete="current-password"]').fill('test-password-123')
            page.get_by_role('button', name='登录', exact=True).click()
            page.wait_for_url('**/platform/**')
            yield page, screenshots, requested
        except Exception:
            page.screenshot(path=str(screenshots / 'failure.png'), full_page=True)
            print('AGENT_ALIGNMENT_BROWSER_FAILURE', screenshots, page.url, page.locator('body').inner_text()[:3500])
            raise
        finally:
            page.screenshot(path=str(screenshots / 'last-state.png'), full_page=True)
            print('AGENT_ALIGNMENT_BROWSER_LAST_STATE', screenshots, page.url)
            browser.close()


def test_failed_session_creation_restores_draft_and_local_attachment(browser_platform, alignment_page):
    from playwright.sync_api import expect
    platform, _, _, _ = browser_platform
    page, _, _ = alignment_page
    page.goto(platform + '/platform/creatChat')
    scope = page.locator('.platform-route-outlet')
    composer = scope.locator('.answers-input').get_by_role('textbox')
    question = '接口失败后必须保留这条问题和本地附件'
    composer.fill(question)
    scope.locator('.answers-input input[type="file"]').nth(1).set_input_files({
        'name': 'retry-note.txt', 'mimeType': 'text/plain', 'buffer': b'retry attachment'})
    expect(scope.get_by_text('retry-note.txt', exact=True)).to_be_visible()

    def reject_creation(route):
        if route.request.method == 'POST':
            route.fulfill(status=503, json={'success': False, 'message': 'fixture creation failure'})
        else:
            route.continue_()
    page.route('**/api/v1/sessions', reject_creation)
    composer.press('Enter')
    expect(composer).to_have_value(question)
    expect(scope.get_by_text('retry-note.txt', exact=True)).to_be_visible()
    expect(page).to_have_url(re.compile(r'/platform/creatChat$'))


def test_failed_stop_reattaches_to_native_stream(browser_platform, alignment_page):
    from playwright.sync_api import expect
    platform, model, tools, _ = browser_platform
    page, _, requested = alignment_page
    release = threading.Event()
    started = threading.Event()

    @tool
    async def wait_after_stop_failure() -> str:
        """Wait for the browser to reject stop and reattach to the native stream."""
        started.set()
        if not await asyncio.to_thread(release.wait, 45):
            raise TimeoutError('Browser did not resume after the rejected stop')
        return 'released'

    tools.append(wait_after_stop_failure)
    model.responses = [AIMessage(content='', tool_calls=[call('wait_after_stop_failure', {}, 'stop-failure-wait')]),
                       AIMessage(content='停止失败后已通过原生续流完成')]
    page.route('**/api/v1/sessions/*/stop', lambda route: route.fulfill(
        status=503, json={'success': False, 'message': 'fixture stop failure'}))
    try:
        page.goto(platform + '/platform/creatChat')
        scope = page.locator('.platform-route-outlet')
        scope.locator('.agent-mode-btn').click()
        page.locator('.agent-selector-dropdown').get_by_text('智能推理', exact=True).click()
        composer = scope.locator('.answers-input').get_by_role('textbox')
        composer.fill('验证停止失败后的原生恢复')
        with page.expect_request(lambda request: request.method == 'POST' and '/agent-chat/' in request.url):
            composer.press('Enter')
        stop = scope.get_by_role('button', name='停止生成', exact=True)
        expect(stop).to_be_visible(timeout=20000)
        expect(stop).to_be_enabled()
        assert started.wait(5), 'The native fixture tool did not start'
        with page.expect_request(lambda request: request.method == 'GET'
                                 and '/api/v1/sessions/continue-stream/' in request.url) as resumed:
            stop.click()
        assert 'message_id=' in resumed.value.url
        release.set()
        expect(scope).to_contain_text('调用 wait_after_stop_failure 失败', timeout=20000)
        expect(stop).to_have_count(0)
        expect(scope.get_by_role('button', name='发送', exact=True)).to_be_visible()
        sends = [(method, path) for method, path in requested if method == 'POST' and '/agent-chat/' in path]
        assert len(sends) == 1, sends
    finally:
        release.set()


def test_quick_creation_and_explicit_legacy_repair_do_not_write_on_read_or_cancel(browser_platform, alignment_page):
    from playwright.sync_api import expect
    platform, _, _, _ = browser_platform
    page, screenshots, _ = alignment_page
    owner = os.environ['TEST_PLATFORM_USER']
    legacy = registry.save_record('agent', {'id': 'legacy-browser-quick', 'name': '旧快速配置验收',
        'created_by': owner, 'is_builtin': False, 'tenant_id': 1,
        'config': config.validate_config({'agent_mode': 'quick-answer', 'model_id': registry.default_model_id(owner),
            'max_iterations': 1, 'allowed_tools': [], 'history_turns': 1, 'retain_retrieval_history': False,
            'enable_rewrite': True, 'context_template': '旧本地模板', 'kb_selection_mode': 'none',
            'system_prompt': '保留这段自定义提示词'}, check_runtime=False)}, owner)
    page.goto(platform + '/platform/agents')
    page.get_by_role('button', name='创建智能体', exact=True).first.click()
    editor = page.get_by_role('dialog', name='创建智能体', exact=True)
    expect(editor).to_be_visible()
    editor.get_by_text('快速问答', exact=True).click()
    expect(editor.get_by_role('radio', name='快速问答', exact=True)).to_be_checked()
    editor.get_by_placeholder('请输入智能体名称', exact=True).fill('原生快速问答浏览器验收')
    editor.get_by_role('navigation').get_by_text('提示词', exact=True).click()
    editor.get_by_placeholder(re.compile('自定义系统提示词')).fill('使用当前官方工具回答问题')
    expect(editor.get_by_text('上下文模板', exact=True)).to_have_count(0)
    with page.expect_response(lambda response: response.request.method == 'POST'
                              and urlsplit(response.url).path == '/api/v1/agents') as created:
        editor.get_by_role('button', name='创建智能体', exact=True).click()
    assert created.value.status == 201, created.value.text()
    saved = created.value.json()['data']['config']
    assert saved['agent_mode'] == 'quick-answer' and saved['max_iterations'] == 8
    assert saved['allowed_tools'] is None and saved['history_turns'] == 0
    assert saved['retain_retrieval_history'] is True and not saved.get('context_template')
    editor = page.get_by_role('dialog', name='编辑智能体', exact=True)
    expect(editor).to_be_visible()
    editor.get_by_role('button', name='取消', exact=True).click()
    expect(editor).not_to_be_visible()

    def open_legacy():
        page.get_by_role('link', name=re.compile('旧快速配置验收')).click()
        modal = page.get_by_role('dialog', name='编辑智能体', exact=True)
        expect(modal).to_be_visible()
        notice = modal.get_by_role('status').filter(has_text='retain_retrieval_history')
        expect(notice).to_contain_text('false')
        expect(notice).to_contain_text('history_turns')
        expect(notice).to_contain_text('enable_rewrite')
        expect(notice).to_contain_text('context_template')
        expect(modal.get_by_role('button', name='采用当前原生快速问答设置', exact=True)).to_be_visible()
        return modal

    editor = open_legacy()
    assert registry.record('agent', legacy['id'], owner) == legacy
    editor.get_by_role('button', name='取消', exact=True).click()
    expect(editor).not_to_be_visible()
    assert registry.record('agent', legacy['id'], owner) == legacy
    editor = open_legacy()
    editor.get_by_role('button', name='采用当前原生快速问答设置', exact=True).click()
    expect(editor.get_by_role('status').filter(has_text='retain_retrieval_history')).to_contain_text('草稿')
    assert registry.record('agent', legacy['id'], owner) == legacy
    editor.get_by_role('button', name='取消', exact=True).click()
    expect(page.get_by_text('有未保存的更改', exact=True)).to_be_visible()
    page.get_by_role('button', name='放弃更改', exact=True).click()
    expect(editor).not_to_be_visible()
    assert registry.record('agent', legacy['id'], owner) == legacy
    editor = open_legacy()
    editor.get_by_role('button', name='采用当前原生快速问答设置', exact=True).click()
    with page.expect_response(lambda response: response.request.method == 'PUT'
                              and urlsplit(response.url).path == '/api/v1/agents/' + legacy['id']) as repaired:
        editor.get_by_role('button', name='保存并关闭', exact=True).click()
    assert repaired.value.status == 200, repaired.value.text()
    expect(editor).not_to_be_visible()
    final = registry.record('agent', legacy['id'], owner)['config']
    assert final['retain_retrieval_history'] is True and final['history_turns'] == 0
    assert final['max_iterations'] == 1 and final['allowed_tools'] == []
    assert final['knowledge_bases'] == [] and final['kb_selection_mode'] == 'none'
    assert final['system_prompt'] == legacy['config']['system_prompt']
    assert not final.get('enable_rewrite') and not final.get('context_template')
    page.screenshot(path=str(screenshots / 'explicit-repair-saved.png'), full_page=True)
    print('AGENT_ALIGNMENT_BROWSER_SCREENSHOTS', screenshots)


def test_clearing_template_prompt_blocks_save_until_actual_custom_text_is_entered(browser_platform, alignment_page):
    from playwright.sync_api import expect
    platform, _, _, _ = browser_platform
    page, screenshots, requested = alignment_page
    owner = os.environ['TEST_PLATFORM_USER']
    original_text = '保留引用的原始系统指令'
    registry.save_record('settings', {'id': 'prompt-templates', 'value': {
        'system_prompt': [], 'agent_system_prompt': [{'id': 'browser-prompt-ref', 'content': original_text}],
        'context_template': [], 'rewrite': [], 'fallback': []}}, owner)
    agent = config.save_agent({'name': '模板正文清空验收', 'config': {
        'agent_mode': 'smart-reasoning', 'system_prompt': '', 'system_prompt_id': 'browser-prompt-ref',
        'allowed_tools': [], 'kb_selection_mode': 'none'}}, owner)
    before = registry.record('agent', agent['id'], owner)
    path = '/api/v1/agents/' + agent['id']
    page.goto(platform + '/platform/agents')
    page.get_by_role('link', name=re.compile('模板正文清空验收')).click()
    editor = page.get_by_role('dialog', name='编辑智能体', exact=True)
    expect(editor).to_be_visible()
    editor.get_by_role('navigation').get_by_text('提示词', exact=True).click()
    prompt = editor.locator('.system-prompt-textarea textarea')
    expect(prompt).to_have_value(original_text)
    prompt.fill('')
    editor.get_by_role('button', name='保存并关闭', exact=True).click()
    expect(page.get_by_text('请输入系统提示词', exact=True)).to_be_visible()
    expect(editor).to_be_visible()
    assert ('PUT', path) not in requested
    assert registry.record('agent', agent['id'], owner) == before
    custom_text = '用户实际填写的新系统指令'
    prompt.fill(custom_text)
    with page.expect_response(lambda response: response.request.method == 'PUT'
                              and urlsplit(response.url).path == path) as saved:
        editor.get_by_role('button', name='保存并关闭', exact=True).click()
    assert saved.value.status == 200, saved.value.text()
    expect(editor).not_to_be_visible()
    final = registry.record('agent', agent['id'], owner)['config']
    assert final['system_prompt'] == custom_text
    assert 'system_prompt_id' not in final
    assert requested.count(('PUT', path)) == 1
    page.screenshot(path=str(screenshots / 'prompt-cleared-and-custom-saved.png'), full_page=True)


@pytest.mark.parametrize('embedded', [False, True], ids=['ordinary', 'embedded'])
def test_unsupported_browser_and_steering_writes_have_no_requests_and_keep_running_draft(browser_platform, alignment_page, embedded):
    from playwright.sync_api import expect
    platform, model, tools, _ = browser_platform
    page, screenshots, requested = alignment_page
    release = threading.Event()
    started = threading.Event()

    @tool
    async def wait_for_capability_acceptance() -> str:
        """Wait for browser assertions against the current running request."""
        started.set()
        if not await asyncio.to_thread(release.wait, 45):
            raise TimeoutError('Browser did not finish observing the running composer')
        return 'released'

    tools.append(wait_for_capability_acceptance)
    model.responses = [AIMessage(content='', tool_calls=[call('wait_for_capability_acceptance', {}, 'browser-wait')]),
                       AIMessage(content='本轮能力入口验收已完成')]
    try:
        page.goto(platform + '/platform/toolbox/browserconnection')
        expect(page.get_by_text('旧入口 browserconnection 不再提供', exact=False)).to_be_visible()
        expect(page.get_by_role('tab', name='浏览器连接', exact=True)).to_have_count(0)
        page.goto(platform + '/platform/creatChat')
        if embedded:
            page.locator('[data-guide="assistant-entry"]:visible').first.click()
            scope = page.get_by_role('complementary').filter(has=page.locator('.answers-input'))
        else:
            scope = page.locator('.platform-route-outlet')
            scope.locator('.agent-mode-btn').click()
            page.locator('.agent-selector-dropdown').get_by_text('智能推理', exact=True).click()
            expect(scope.locator('.agent-mode-text')).to_have_text('智能推理')
        composer = scope.locator('.answers-input').get_by_role('textbox')
        expect(composer).to_be_visible()
        expect(scope.get_by_role('button', name='本机浏览器', exact=True)).to_have_count(0)
        composer.fill('等待实际浏览器检查完成本轮')
        with page.expect_request(lambda request: request.method == 'POST'
                                 and ('/agent-chat/' in request.url or '/knowledge-chat/' in request.url)) as sent:
            composer.press('Enter')
        assert sent.value.post_data_json['agent_id'] == (
            'builtin-weknora-assistant' if embedded else 'builtin-smart-reasoning')
        expect(scope.get_by_role('button', name='停止生成', exact=True)).to_be_visible(timeout=20000)
        assert started.wait(5), 'The real native fixture tool did not start'
        draft = '本轮结束后再由我发送的草稿'
        composer.fill(draft)
        composer.press('Enter')
        expect(composer).to_have_value(draft)
        composer.press('Meta+Enter')
        expect(composer).to_have_value(draft)
        expect(scope.get_by_role('button', name='停止生成', exact=True)).to_be_visible()
        expect(scope.get_by_role('button', name='完成后发送', exact=True)).to_have_count(0)
        expect(page.get_by_role('list', name='当前回答结束后发送', exact=True)).to_have_count(0)
        expect(page.locator('.browser-task-preview')).to_have_count(0)
        release.set()
        expect(scope).to_contain_text('本轮能力入口验收已完成', timeout=20000)
        expect(scope.get_by_role('button', name='停止生成', exact=True)).to_have_count(0)
        expect(composer).to_have_value(draft)
        expect(scope.get_by_role('button', name='发送', exact=True)).to_be_visible()
        unsupported = [(method, path) for method, path in requested
                       if path == '/api/v1/me/browser' or '/local-browser' in path
                       or ('/steer' in path and method not in ('GET', 'HEAD', 'OPTIONS'))]
        assert unsupported == [], unsupported
        sends = [(method, path) for method, path in requested
                 if method == 'POST' and ('/agent-chat/' in path or '/knowledge-chat/' in path)]
        assert len(sends) == 1, sends
        page.screenshot(path=str(screenshots / ('embedded-capabilities.png' if embedded else 'ordinary-capabilities.png')), full_page=True)
        print('CAPABILITY_ALIGNMENT_BROWSER_SCREENSHOTS', screenshots)
    finally:
        release.set()
