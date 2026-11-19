"""Opt-in page-load regression for unavailable deployment APIs."""
import os
from urllib.parse import urlsplit

import pytest

from tests.platform.test_platform_agent_alignment_browser import alignment_page
from tests.platform.test_platform_assistant_browser import browser_platform
from tests.platform.test_platform_harness import harness, original_prepare
from tests.platform.test_platform_model_protocols import sdk_provider

pytestmark = pytest.mark.skipif(
    os.getenv('RUN_BROWSER_ACCEPTANCE') != '1',
    reason='Set RUN_BROWSER_ACCEPTANCE=1 after building the current frontend',
)


def test_old_cloud_bookmark_opens_without_cloud_controls_or_requests(browser_platform, alignment_page):
    from playwright.sync_api import expect

    platform, _, _, _ = browser_platform
    page, _, requested = alignment_page
    page.goto(platform + '/platform/settings?section=weknoracloud')
    expect(page.get_by_role('heading', name='该设置已停用')).to_be_visible()
    nav = page.locator('.settings-nav')
    expect(nav.get_by_text('WeKnora Cloud', exact=True)).to_have_count(0)
    expect(page.get_by_role('button', name='保存凭证')).to_have_count(0)
    page.get_by_role('button', name='打开模型配置').click()
    expect(page.locator('.model-settings')).to_be_visible()
    nav.get_by_text('空间信息', exact=True).click()
    expect(page.locator('.tenant-info').get_by_text('10 GB', exact=True)).to_be_visible()
    assert not [path for _, path in requested if path.startswith('/api/') and 'weknoracloud' in path]


def test_page_load_skips_unsupported_assistant_and_organization_apis(browser_platform, alignment_page):
    from playwright.sync_api import expect

    platform, _, _, headers = browser_platform
    page, _, requested = alignment_page
    capabilities = page.request.get(platform + '/api/v1/system/capabilities', headers=headers)
    assert capabilities.ok, capabilities.text()
    supported = capabilities.json()['data']['capabilities']
    assert supported['organizations']['supported'] is False
    assert supported['settings.assistant']['supported'] is False

    responses = []
    page.on('response', lambda response: responses.append((response.status, urlsplit(response.url).path)))
    for path, selector in (
        ('/platform/knowledge-bases', '.kb-list-container'),
        ('/platform/agents', '.agent-list-container'),
    ):
        page.goto(platform + path)
        expect(page.locator(selector)).to_be_visible()
        page.wait_for_load_state('networkidle')
        page.reload()
        expect(page.locator(selector)).to_be_visible()
        page.wait_for_load_state('networkidle')

    unavailable = {
        '/api/v1/tenants/kv/assistant-config',
        '/api/v1/shared-agents',
        '/api/v1/organizations',
    }
    assert not [(method, path) for method, path in requested if path in unavailable]
    assert not [(status, path) for status, path in responses if status == 404 and path in unavailable]
    assert (200, '/api/v1/agents') in responses
