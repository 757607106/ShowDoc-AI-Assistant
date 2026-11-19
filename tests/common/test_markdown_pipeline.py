"""Real Docling regressions for document meaning and provenance."""
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from common.converter import RAGContentPipeline, prepare_review_file
from crawlers.base import BaseCrawler, CrawledDocument


@pytest.fixture
def pipeline(tmp_path):
    return RAGContentPipeline(str(tmp_path / 'assets'), 'https://docs.example.test/manual/')


def convert(pipeline, content, source='markdown'):
    return pipeline.convert([dict(id='1', title='操作手册', content=content, source_format=source)])['1']


def test_preserves_heading_relationships_and_source_nodes(pipeline):
    result = convert(pipeline, '# 采购管理\n\n模块说明。\n\n## 采购入库\n\n创建采购单并完成审核。')
    assert result.engine == 'docling'
    assert result.nodes[-1]['headings'] == ['采购管理', '采购入库']
    assert result.chunks[-1]['metadata']['section_path'] == ['采购管理', '采购入库']
    assert result.chunks[-1]['metadata']['node_refs']


def test_code_content_not_repaired_as_markdown(pipeline):
    code = '# 代码标题\nkey = "____________"\n\n\n[x](relative)\nline  '
    result = convert(pipeline, '## 示例\n\n````markdown\n' + code + '\n````')
    node = next(node for node in result.nodes if node['label'] == 'code')
    assert node['text'] == code
    assert '____________' in result.markdown
    assert not result.resources['links']


def test_html_intro_and_literal_dash_are_preserved(pipeline):
    result = convert(pipeline, '<p>业务导语</p><h2>操作</h2><p>123456</p><p>-</p><p>下一步</p>', 'html')
    assert result.nodes[0]['text'] == '业务导语'
    assert next(node for node in result.nodes if node['text'] == '123456')['label'] != 'section_header'
    assert any(node['text'] == '下一步' for node in result.nodes)


def test_spanning_table_preserves_relationships_in_structured_document(pipeline):
    result = convert(pipeline, '<table><tr><th>区域</th><th>项目</th></tr><tr><td rowspan="2">华东</td><td>A</td></tr><tr><td>B</td></tr></table>', 'html')
    document = json.loads((pipeline.output_dir / result.docling_path).read_text())
    cells = document['tables'][0]['data']['table_cells']
    assert any(cell['text'] == '华东' and cell['row_span'] == 2 for cell in cells)
    assert any(cell['text'] == 'B' for cell in cells)
    assert 'rowspan="2"' in result.preview_html


def test_relative_images_and_links_survive_without_fetching(pipeline):
    result = convert(pipeline, '## 说明\n\n[详情](next.html)\n\n![步骤](images/a.png)\n\n[编码路径](a%2Fb)')
    assert 'https://docs.example.test/manual/next.html' in result.markdown
    assert 'https://docs.example.test/manual/images/a.png' in result.markdown
    assert 'https://docs.example.test/manual/a%2Fb' in result.markdown
    assert result.resources['images'][0]['url'].endswith('images/a.png')


def test_long_table_chunks_preserve_rows_and_provenance(pipeline):
    pipeline.max_tokens = 64
    result = convert(pipeline, '| 编号 | 值 |\n| --- | --- |\n' + '\n'.join(f'| {i} | 数据{i:03d} |' for i in range(30)))
    assert len(result.chunks) > 1
    text = '\n'.join(chunk['content'] for chunk in result.chunks)
    assert all(f'数据{i:03d}' in text for i in range(30))
    assert all(chunk['metadata']['node_refs'] for chunk in result.chunks)
    assert all(chunk['metadata']['size_unit'] == 'tokens' for chunk in result.chunks)


def test_reprocessing_uses_saved_docling_json(pipeline):
    content = '# 缓存\n\n正文不变时，无需重新解析。'
    first = convert(pipeline, content)
    with patch.object(pipeline._converter, 'convert_string', side_effect=AssertionError('reparsed')):
        second = convert(pipeline, content)
    assert second.docling_path == first.docling_path
    assert second.chunks == first.chunks


def test_cache_distinguishes_declared_source_format(pipeline):
    html = convert(pipeline, '<h2>正文</h2><p>保存来源格式。</p>', 'html')
    markdown = convert(pipeline, '<h2>正文</h2><p>保存来源格式。</p>', 'markdown')
    assert html.docling_path != markdown.docling_path


def test_empty_or_unspecified_source_fails_without_fallback(pipeline):
    with pytest.raises(ValueError):
        convert(pipeline, '<div></div>', 'html')
    with pytest.raises(ValueError):
        convert(pipeline, '正文', 'unknown')
    errors = {}
    assert pipeline.convert([dict(id='x', title='空', content='', source_format='markdown')], errors=errors) == {}
    assert '源正文为空' in errors['x']


def test_saved_outputs_share_docling_evidence(tmp_path):
    crawler = BaseCrawler(str(tmp_path))
    document = CrawledDocument('1', '采购入库', '采购', '# 采购入库\n\n## 操作\n\n创建采购单并完成审核。', '', {}, 'markdown')
    crawler._convert_all([document])
    summary = crawler._save([document])
    record = json.loads(Path(summary.rag_documents_file).read_text().splitlines()[0])
    chunk = json.loads(Path(summary.rag_chunks_file).read_text().splitlines()[0])
    assert record['docling_path'] == document.docling_path
    assert record['nodes']
    assert chunk['metadata']['node_refs']
    assert '# 采购入库' in document.markdown


def test_html_review_export_preserves_content_without_chunker(pipeline, tmp_path):
    from tests.fakes.contextdb_fake import FakeContextDBClient
    client = FakeContextDBClient()
    kb = client.create_knowledge_base('review', review_enabled=True)
    html = ('<h1>操作步骤</h1><table><tr><th>配置</th><th>值</th></tr>'
            '<tr><td>重试次数</td><td>3</td></tr></table>'
            '<pre><code>key = "____________"\nprint(key)</code></pre>'
            '<p>请先<a href="next.html?q=1&amp;k=2">查看详情</a>，再'
            '<a href="https://example.org/download?a=1&amp;b=2">下载附件</a>。</p>'
            '<p><img src="images/step.png" alt="步骤截图"></p>'
            '<table><tr><th>链接</th></tr><tr><td><a href="table.html">表格详情</a></td></tr></table>')
    path = tmp_path / 'source.html'
    path.write_text(html)
    with patch.object(pipeline, '_initialize_chunker', side_effect=AssertionError('review must not chunk')):
        name, converted, fingerprint = prepare_review_file(client, kb['id'], '手册.html', path,
            base_url='https://docs.example.test/manual/', pipeline=pipeline)
    markdown = converted.read_text()
    assert name == '手册.md' and converted != path
    assert path.read_text() == html
    assert re.search(r'\|\s*重试次数\s*\|\s*3\s*\|', markdown)
    assert 'key = "____________"\nprint(key)' in markdown
    assert 'https://docs.example.test/manual/images/step.png' in markdown
    assert '[查看详情](https://docs.example.test/manual/next.html?q=1&k=2)' in markdown
    assert '[下载附件](https://example.org/download?a=1&b=2)' in markdown
    assert '[表格详情](https://docs.example.test/manual/table.html)' in markdown
    assert len(fingerprint) == 64
    assert pipeline._chunker is None


@pytest.mark.parametrize('extension', ['txt', 'md', 'markdown', 'pdf', 'doc', 'docx'])
def test_review_native_formats_are_not_reparsed(pipeline, tmp_path, extension):
    from tests.fakes.contextdb_fake import FakeContextDBClient
    client = FakeContextDBClient()
    kb = client.create_knowledge_base('review', review_enabled=True)
    path = tmp_path / f'original.{extension}'
    path.write_bytes(b'original source')
    with patch.object(pipeline, 'convert_record', side_effect=AssertionError('native source must pass through')):
        name = path.with_suffix('.md').name if extension == 'markdown' else path.name
        assert prepare_review_file(client, kb['id'], path.name, path, pipeline=pipeline) == (name, path, '')


def test_review_rejects_unsupported_or_empty_html_and_off_keeps_original(pipeline, tmp_path):
    from governance.store import StoreError
    from tests.fakes.contextdb_fake import FakeContextDBClient
    client = FakeContextDBClient()
    kb = client.create_knowledge_base('review', review_enabled=True)
    path = tmp_path / 'source.html'
    path.write_text('<div></div>')
    with pytest.raises(StoreError, match='可评审正文'):
        prepare_review_file(client, kb['id'], path.name, path, pipeline=pipeline)
    with pytest.raises(StoreError, match='不支持'):
        prepare_review_file(client, kb['id'], 'image.png', path, pipeline=pipeline)
    client.update_knowledge_base(kb['id'], review_enabled=False)
    with patch.object(pipeline, 'convert_record', side_effect=AssertionError('review-off uses official parsing')):
        assert prepare_review_file(client, kb['id'], 'source.html', path, pipeline=pipeline) == ('source.html', path, '')
