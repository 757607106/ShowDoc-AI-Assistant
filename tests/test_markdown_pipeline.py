"""Real Docling regressions for document meaning and provenance."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from common.converter import RAGContentPipeline
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
