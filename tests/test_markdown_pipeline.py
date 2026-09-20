import json
import os
import tempfile
import unittest

from common.converter import (
    MarkdownValidationError,
    RAGContentPipeline,
    extract_markdown_resources,
    normalize_document_markdown,
    prepare_markdown_content,
    split_markdown_sections_for_rag,
    validate_canonical_markdown,
)
from crawlers.base import BaseCrawler, CrawledDocument


class MarkdownPipelineTests(unittest.TestCase):
    def test_document_headings_are_normalized_once_and_keep_hierarchy(self):
        source = "# 库存查询\n\n#### 查询条件\n\n正文\n\n##### 高级条件\n\n更多正文"

        normalized = normalize_document_markdown(source, title="库存查询")

        self.assertNotIn("# 库存查询", normalized)
        self.assertIn("## 查询条件", normalized)
        self.assertIn("### 高级条件", normalized)
        self.assertNotIn("######", normalized)

    def test_headings_inside_code_blocks_are_not_changed(self):
        source = "## 示例\n\n```markdown\n# 代码中的标题\n```"

        normalized = normalize_document_markdown(source)

        self.assertIn("## 示例", normalized)
        self.assertIn("# 代码中的标题", normalized)

    def test_section_chunks_include_full_section_path(self):
        source = (
            "## 采购管理\n\n模块说明。\n\n"
            "### 采购入库\n\n第一步创建采购单。\n\n第二步审核采购单。"
        )

        chunks = split_markdown_sections_for_rag(source, max_chars=80, overlap=10)

        self.assertEqual(chunks[0].section_path, ("采购管理",))
        self.assertEqual(chunks[-1].section_path, ("采购管理", "采购入库"))
        self.assertIn("## 采购管理", chunks[-1].content)
        self.assertIn("### 采购入库", chunks[-1].content)

    def test_builtin_pipeline_keeps_raw_and_normalized_markdown(self):
        pipeline = RAGContentPipeline(mode="builtin")

        converted = pipeline.convert([{
            "id": "1",
            "title": "库存查询",
            "content": "<h1>库存查询</h1><h3>查询条件</h3><p>输入商品名称。</p>",
            "source_format": "html",
            "resources": {"images": [], "links": []},
        }])["1"]

        self.assertIn("### 查询条件", converted.raw_markdown)
        self.assertIn("## 查询条件", converted.markdown)
        self.assertNotIn("# 库存查询", converted.markdown)

    def test_markdown_source_preserves_blocks_and_extracts_resources(self):
        source = (
            "# 操作手册\n\n"
            "## 第一步\n\n正文内容。\n\n"
            "&lt;center&gt;![](//cdn.example.test/step-1.png?x=1&amp;y=2)&lt;/center&gt;\n\n"
            "### 说明\n\n"
            "- [查看详情](guide/detail)\n\n"
            "`&lt;div&gt;代码实体必须保留&lt;/div&gt;`\n\n"
            "```html\n<a href=\"fake.html\">代码里的链接</a>\n"
            "&lt;video src=&quot;fake.mp4&quot;&gt;&lt;/video&gt;\n```\n\n"
            "[播放视频](//cdn.example.test/demo.mp4 \"播放\")\n"
            "&lt;video src=&quot;//cdn.example.test/demo.mp4&quot;&gt;&lt;/video&gt;\n"
        )
        prepared = prepare_markdown_content(source, "操作手册")
        resources = extract_markdown_resources(
            prepared,
            site_base_url="https://docs.example.test/manual/",
        )
        pipeline = RAGContentPipeline(
            mode="builtin",
            site_base_url="https://docs.example.test/",
        )

        converted = pipeline.convert([{
            "id": "markdown-1",
            "title": "操作手册",
            "content": prepared,
            "source_format": "markdown",
            "resources": resources,
        }])["markdown-1"]

        self.assertIn("## 第一步\n\n正文内容。", converted.markdown)
        self.assertIn("### 说明", converted.markdown)
        self.assertIn(
            "![操作手册 - 步骤图 1](https://cdn.example.test/step-1.png?x=1&y=2)",
            converted.markdown,
        )
        self.assertIn(
            "[查看详情](https://docs.example.test/guide/detail)",
            converted.markdown,
        )
        self.assertEqual(converted.markdown.count("demo.mp4"), 1)
        self.assertIn("`&lt;div&gt;代码实体必须保留&lt;/div&gt;`", converted.markdown)
        self.assertIn('<a href="fake.html">代码里的链接</a>', converted.markdown)
        self.assertIn(
            "&lt;video src=&quot;fake.mp4&quot;&gt;&lt;/video&gt;",
            converted.markdown,
        )
        self.assertNotIn("fake.html", [item["url"] for item in resources["links"]])
        self.assertNotIn("<center>", converted.markdown)
        self.assertNotIn("<video", converted.markdown)
        self.assertEqual(len(resources["images"]), 1)
        self.assertEqual(len(resources["links"]), 2)
        validate_canonical_markdown(
            converted.markdown,
            resources,
            title="操作手册",
        )

    def test_heading_jumps_are_repaired_for_rag_hierarchy(self):
        source = "## 一级\n\n正文\n\n#### 跳级标题\n\n更多正文"

        normalized = normalize_document_markdown(source)

        self.assertIn("## 一级", normalized)
        self.assertIn("### 跳级标题", normalized)
        self.assertNotIn("#### 跳级标题", normalized)

    def test_html_fallback_preserves_tables_code_and_code_blank_lines(self):
        pipeline = RAGContentPipeline(mode="builtin")
        converted = pipeline.convert([{
            "id": "html-structure",
            "title": "接口说明",
            "content": (
                "<h2>字段</h2>"
                "<table><tr><th>名称</th><th>值</th></tr>"
                "<tr><td>状态</td><td>启用</td></tr></table>"
                "<pre><code class='language-sql'>select 1;\n\n\nselect 2;</code></pre>"
            ),
            "source_format": "html",
            "resources": {"images": [], "links": []},
        }])["html-structure"]

        self.assertIn("| 名称 | 值 |", converted.markdown)
        self.assertIn("| --- | --- |", converted.markdown)
        self.assertIn("```sql", converted.markdown)
        self.assertIn("select 1;\n\n\nselect 2;", converted.markdown)

    def test_empty_conversion_is_rejected(self):
        pipeline = RAGContentPipeline(mode="builtin")
        with self.assertRaises(MarkdownValidationError):
            pipeline.convert([{
                "id": "empty-html",
                "title": "空文档",
                "content": "<div></div>",
                "source_format": "html",
                "resources": {"images": [], "links": []},
            }])

    def test_source_format_must_be_declared(self):
        pipeline = RAGContentPipeline(mode="builtin")
        with self.assertRaises(ValueError):
            pipeline.convert([{
                "id": "unknown-format",
                "title": "格式不明",
                "content": "<p>正文</p>",
                "resources": {"images": [], "links": []},
            }])

    def test_save_writes_raw_markdown_and_structured_chunk_metadata(self):
        with tempfile.TemporaryDirectory() as output_dir:
            crawler = BaseCrawler(output_dir, pipeline_mode="builtin")
            crawler.platform = "test"
            crawler.display_name = "测试平台"
            crawler.collection_name = "测试知识库"
            document = CrawledDocument(
                id="doc-1",
                title="采购入库",
                category="采购管理",
                content="",
                updated_at="2026-09-18",
                metadata={"url": "https://example.test/doc-1"},
                source_format="markdown",
                raw_markdown="# 采购入库\n\n原始正文",
                markdown="## 操作说明\n\n创建采购单并完成审核。",
            )

            summary = crawler._save([document])

            self.assertTrue(os.path.exists(summary.raw_documents_file))
            with open(summary.raw_documents_file, encoding="utf-8") as raw_file:
                raw_record = json.loads(raw_file.readline())
            self.assertEqual(raw_record["content"], document.raw_markdown)

            with open(summary.rag_chunks_file, encoding="utf-8") as chunk_file:
                chunk_record = json.loads(chunk_file.readline())
            self.assertEqual(chunk_record["metadata"]["section_path"], ["操作说明"])
            self.assertEqual(chunk_record["metadata"]["chunk_index"], 1)

            with open(summary.merged_file, encoding="utf-8") as merged_file:
                merged = merged_file.read()
            self.assertIn("#### 操作说明", merged)
            self.assertNotIn("###### 操作说明", merged)


if __name__ == "__main__":
    unittest.main()
