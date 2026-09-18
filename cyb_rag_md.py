"""云创业版爬取兼容入口（保留旧启动方式）。

清洗管道已迁至 common/converter.py，平台逻辑迁至 crawlers/cyb.py（第 3 阶段）。
本文件仅委托统一框架，等价于:

    python main.py --entry cyb --out downloads/cyb

输出布局随之统一为框架约定：downloads/cyb/<分类>/<标题>.md 等，
详见《多平台爬虫重构方案.md》。
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from registry import create_crawler  # noqa: E402


def crawl_and_process():
    save_dir = os.path.join(SCRIPT_DIR, "downloads", "cyb")
    crawler = create_crawler("cyb", save_dir=save_dir)
    summary = crawler.crawl()

    print("\n" + "=" * 60)
    print(f"✅ [{crawler.display_name}] 爬取完成")
    print(f"   文档: {summary.total_documents} 条"
          f"（空正文 {summary.empty_documents} 条）")
    print(f"   分类: {summary.category_count} 个")
    print(f"   输出目录: {summary.output_dir}")
    print(f"   合并文档: {summary.merged_file}")
    print(f"   RAG 文档: {summary.rag_documents_file}")
    print(f"   RAG 分块: {summary.rag_chunks_file}")
    if summary.finetuning_file:
        print(f"   微调数据: {summary.finetuning_file}")
    print("=" * 60 + "\n")
    return summary


if __name__ == "__main__":
    crawl_and_process()
