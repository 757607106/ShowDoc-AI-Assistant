"""Opt-in acceptance of the built materials page against an isolated test database."""
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import parse_qs, urlencode, urlsplit
from zipfile import ZipFile

import pytest

from tests.platform.test_platform_mcp_runtime import serve


@pytest.mark.skipif(os.getenv('RUN_BROWSER_ACCEPTANCE') != '1',
                    reason='Set RUN_BROWSER_ACCEPTANCE=1 after building the frontend')
def test_material_workflow_keeps_tasks_receipts_and_snapshot_operations(authenticated_client, monkeypatch):
    from asgi import create_app
    import app as app_module
    from governance.spaces import save_space
    from governance.store import Store
    from playwright.sync_api import expect, sync_playwright
    from tests.fakes.contextdb_fake import FakeContextDBClient

    knowledge = FakeContextDBClient()
    knowledge.api_key = 'ctxdb-fake'
    native_request = knowledge._request

    def native_api(method, path, **kwargs):
        if path == '/v1/knowledge/knowledge_bases':
            return knowledge.list_knowledge_bases()
        if path == '/v1/workspaces/members/self/permissions':
            return {'mode': 'personal_compatibility', 'member': {
                'member_id': 'fixture-member', 'member_name': '资料验收账号', 'role': 'owner'},
                'knowledge_base_permissions': [], 'total': 0}
        return native_request(method, path, **kwargs)

    knowledge._request = native_api
    monkeypatch.setattr('webapi.auth.ContextDBClient', lambda *args, **kwargs: knowledge)
    store = Store(client=knowledge, owner_id=os.environ['TEST_PLATFORM_USER'])
    space = save_space(store, {'name': '资料流程验收', 'mode': 'wiki'})
    scope, kb_id = space['scope'], space['knowledge_base_id']
    capture = store.create_job('showdoc', {}, scope=scope, import_directory={'root_name': '已采集产品手册'})
    store.update_job(capture['task_id'], status='completed', phase='submitted', total_pages=3, completed_pages=3)
    archive = Path(capture['output_dir']).parent / 'browser-snapshot.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive, 'w') as snapshot:
        snapshot.writestr('manifest.json', json.dumps({'scope': scope, 'fixture': True}))
    historical = store.create_release('historical-capture', scope, 1, ['older-version'], archive)
    current = store.create_release(capture['task_id'], scope, 2, ['new-version'], archive)
    sync = store.create_job('contextdb', {'release_id': current, 'knowledge_base_id': kb_id,
        'target_mode': 'wiki'}, kind='ctxdb_sync', scope=scope)
    store.update_job(sync['task_id'], status='running', phase='syncing', progress=50,
                     total_pages=4, completed_pages=2, message='正在提交全库资料快照')
    failed = store.create_job('web', {}, scope=scope, import_directory={'root_name': '采集失败的帮助中心'})
    output = Path(failed['output_dir'])
    output.mkdir(parents=True)
    (output / 'failed_documents.jsonl').write_text(json.dumps({
        'id': 'missing-page', 'title': '权限配置', 'error': '来源访问权限不足'}, ensure_ascii=False) + '\n')
    store.update_job(failed['task_id'], status='partial', phase='partial', progress=50,
                     total_pages=2, completed_pages=1, failed_pages=1, message='请核对失败明细后重试')
    screenshots = Path(tempfile.mkdtemp(prefix='showdoc-material-workflow-browser-', dir='/tmp'))

    with serve(create_app(app_module.app)) as platform, sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, locale='zh-CN', accept_downloads=True)
        errors, activations = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: activations.append(request.url)
                if request.method == 'POST' and request.url.endswith('/activate') else None)
        try:
            page.goto(platform + '/login')
            page.locator('input[autocomplete="email"]').fill('test@example.com')
            page.locator('input[autocomplete="current-password"]').fill('test-password-123')
            page.locator('button[type="submit"]').click()
            page.wait_for_url('**/platform/**')
            page.goto(platform + '/platform/tasks?' + urlencode({'space': scope}))
            workspace = page.locator('.material-workspace')
            expect(workspace).to_be_visible()
            expect(page.locator('[data-guide="nav-tasks"]')).to_have_count(1)
            expect(page.locator('[data-guide="nav-collect"], [data-guide="nav-releases"]')).to_have_count(0)
            expect(workspace.locator('.source-name')).to_have_count(2)
            expect(workspace).to_contain_text('正在提交全库资料快照')
            page.screenshot(path=str(screenshots / 'tasks-desktop.png'), full_page=True)

            workspace.locator('.t-table__body tr').filter(has_text='采集失败的帮助中心').get_by_role('button', name='查看并处理').click()
            drawer = page.locator('.t-drawer').filter(has_text='任务详情').last
            expect(drawer).to_contain_text('来源访问权限不足')
            expect(drawer.get_by_role('button', name='重试采集', exact=True)).to_be_visible()
            page.screenshot(path=str(screenshots / 'failed-task-detail.png'), full_page=True)
            drawer.locator('.t-drawer__close-btn').click()

            page.goto(platform + '/platform/releases?' + urlencode({'space': scope}) + '#snapshots')
            expect(page.locator('.release-history')).to_be_visible()
            assert urlsplit(page.url).path == '/platform/tasks'
            assert parse_qs(urlsplit(page.url).query)['view'] == ['history'] and urlsplit(page.url).fragment == 'snapshots'
            expect(page.locator('.snapshot-row')).to_have_count(2)
            page.locator('.snapshot-row').filter(has_text='历史批次').get_by_role('button', name='快照详情').click()
            drawer = page.locator('.t-drawer').filter(has_text='快照详情').last
            expect(drawer).to_contain_text(historical)
            with page.expect_download() as downloaded:
                drawer.get_by_role('button', name='下载全库快照包').click()
            assert downloaded.value.suggested_filename == historical + '.zip'
            with ZipFile(downloaded.value.path()) as downloaded_archive:
                assert json.loads(downloaded_archive.read('manifest.json'))['scope'] == scope
            drawer.locator('summary').click()
            confirmations = []
            page.on('dialog', lambda dialog: (confirmations.append(dialog.message), dialog.dismiss()))
            drawer.get_by_role('button', name='重新提交这个历史快照').click()
            assert confirmations and '覆盖' in confirmations[-1] and activations == []
            assert store.get_release(current)['active'] and not store.get_release(historical)['active']
            page.screenshot(path=str(screenshots / 'snapshot-detail.png'), full_page=True)
            page.keyboard.press('Escape')

            page.goto(platform + '/platform/collect?' + urlencode({'kb_id': kb_id, 'mode': 'file'}) + '#upload')
            drawer = page.locator('.t-drawer').filter(has=page.locator('.collection-embedded')).last
            expect(drawer.locator('.collection-embedded')).to_be_visible()
            query = parse_qs(urlsplit(page.url).query)
            assert query['kb_id'] == [kb_id] and query['mode'] == ['file'] and query['add'] == ['1']
            assert urlsplit(page.url).fragment == 'upload'
            drawer.locator('.kb-upload-source-dropdown input[type="file"]').first.set_input_files({
                'name': '浏览器上传验收.md', 'mimeType': 'text/markdown', 'buffer': '# isolated browser upload'.encode()})
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and urlsplit(response.url).path == '/api/uploads') as uploaded:
                drawer.get_by_role('button', name='上传到知识库', exact=True).click()
            task_id = uploaded.value.json()['task_id']
            expect(drawer).to_contain_text('任务已创建')
            saved = store.get_job(task_id)
            assert saved['scope'] == scope and saved['params']['file_names'] == ['浏览器上传验收.md']
            assert Path(saved['params']['file_paths'][0]).read_text() == '# isolated browser upload'
            page.screenshot(path=str(screenshots / 'upload-receipt.png'), full_page=True)
            drawer.locator('.t-alert--success').get_by_role('button', name='查看任务', exact=True).click()
            drawer = page.locator('.t-drawer').filter(has_text='任务详情').last
            expect(drawer).to_contain_text('浏览器上传验收.md')
            drawer.locator('.t-drawer__close-btn').click()
            expect(drawer.locator('.t-drawer__content-wrapper')).to_be_hidden()

            page.locator('.sidebar-toggle').first.click()
            page.set_viewport_size({'width': 1024, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.set_viewport_size({'width': 320, 'height': 900})
            expect(workspace).to_be_visible()
            geometry = page.evaluate('''() => ({width:window.innerWidth, scroll:document.documentElement.scrollWidth,
                elements:[...document.querySelectorAll('.main,.platform-route-outlet,.material-workspace,.t-card__header,.t-card__body,.scope-filter,.task-toolbar,.task-pagination')]
                    .map(el=>({class:el.className,left:el.getBoundingClientRect().left,width:el.getBoundingClientRect().width,
                        minWidth:getComputedStyle(el).minWidth,scroll:el.scrollWidth,overflow:getComputedStyle(el).overflowX}))})''')
            main = next(element for element in geometry['elements'] if element['class'] == 'main')
            material = next(element for element in geometry['elements'] if 'material-workspace' in element['class'])
            # The existing platform shell has min-width:600px; this change must not widen it.
            assert geometry['scroll'] <= max(main['width'], geometry['width']), geometry
            assert material['left'] + material['width'] <= main['left'] + main['width'], geometry
            page.screenshot(path=str(screenshots / 'tasks-mobile.png'), full_page=True)
            workspace.get_by_role('button', name='添加资料', exact=True).click()
            drawer = page.locator('.t-drawer').filter(has=page.locator('.collection-embedded')).last
            expect(drawer.locator('.collection-embedded')).to_be_visible()
            expect(drawer.locator('.t-drawer__content-wrapper')).to_be_in_viewport(ratio=1)
            expect(drawer.locator('input[placeholder="选择资料所属知识库"]')).to_have_value('资料流程验收')
            drawer_box = drawer.locator('.t-drawer__content-wrapper').bounding_box()
            assert drawer_box['x'] >= 0 and drawer_box['x'] + drawer_box['width'] <= 321, drawer_box
            controls = drawer.locator('.t-form__controls, .t-form__label, .t-form input, .t-form button').evaluate_all('''items => items
                .filter(el=>el.getBoundingClientRect().width>0)
                .map(el=>({tag:el.tagName,class:el.className,text:el.textContent?.slice(0,60),
                    left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right}))''')
            page.screenshot(path=str(screenshots / 'add-mobile.png'))
            (screenshots / 'layout.json').write_text(json.dumps({'viewport_320': geometry,
                'add_viewport': {'horizontal_scroll': page.evaluate('window.scrollX'), 'drawer': drawer_box,
                    'attach_parent': drawer.evaluate('element => element.parentElement.tagName')},
                'add_controls': controls, 'limitation': 'Existing platform shell keeps min-width:600px; 320px full-page adaptation is outside this change.'}, ensure_ascii=False, indent=2))
            assert all(control['left'] >= 0 and control['right'] <= 321 for control in controls), controls
            drawer.get_by_role('button', name='查看任务', exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(screenshots / 'add-mobile-actions.png'))
            assert not errors, errors
            print('MATERIAL_WORKFLOW_BROWSER_SCREENSHOTS', screenshots)
        except Exception:
            page.screenshot(path=str(screenshots / 'failure.png'), full_page=True)
            print('MATERIAL_WORKFLOW_DRAWER_LAYOUT', page.evaluate('''() => ({scrollX:window.scrollX,innerWidth:window.innerWidth,
                viewport:{width:visualViewport.width,left:visualViewport.offsetLeft,pageLeft:visualViewport.pageLeft},
                nodes:[...document.querySelectorAll('.t-drawer--open,.t-drawer--open .t-drawer__content-wrapper,.material-workspace,.platform-route-outlet,.main')]
                    .map(el=>({class:el.className,rect:el.getBoundingClientRect().toJSON(),position:getComputedStyle(el).position,
                        transform:getComputedStyle(el).transform,contain:getComputedStyle(el).contain}))})'''))
            print('MATERIAL_WORKFLOW_BROWSER_FAILURE', screenshots, page.url, page.locator('body').inner_text()[:5000])
            print('MATERIAL_WORKFLOW_BROWSER_ERRORS', errors)
            raise
        finally:
            browser.close()
