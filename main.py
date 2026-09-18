"""多平台知识库爬取 CLI。

用法:
    python main.py --list-entries                       # 列出全部可用入口
    python main.py --entry tiantong --list-documents    # 查看分类与数量（不落盘）
    python main.py --entry tiantong                     # 全量爬取
    python main.py --entry tiantong --limit 5           # 小样本试跑
    python main.py --entry showdoc --list-projects      # 登录并列出 ShowDoc 项目
    python main.py --entry showdoc --item 412           # 爬取指定项目（公开项目免登录）
    python main.py --entry showdoc --item 412 --login   # 先登录再爬取（受保护项目）
    python main.py --entry cyb                          # 爬取云创业版（自动验证码登录）
    python main.py --entry web --url https://example.com  # 抓取通用网页并输出 Markdown
    python main.py --entry web --url https://docs.example.com/guide \
        --crawl-mode site                                # 抓取整个同域网站
"""
import argparse
import hashlib
import os
from collections import Counter

from registry import ENTRIES, create_crawler, get_entry

VALID_PIPELINES = ["auto", "builtin", "crawl4ai", "crawl4ai_firecrawl"]


def default_output_dir(args):
    if args.out:
        return args.out
    if args.entry == "showdoc" and args.item:
        return os.path.join("downloads", f"showdoc_{args.item}")
    if args.entry == "web" and args.url:
        suffix = hashlib.sha1(args.url.encode("utf-8")).hexdigest()[:10]
        return os.path.join("downloads", f"web_{suffix}")
    return os.path.join("downloads", args.entry)


def build_crawler_kwargs(args):
    kwargs = {}
    if args.page_size:
        kwargs["page_size"] = args.page_size
    if args.pipeline:
        kwargs["pipeline_mode"] = args.pipeline
    if args.item:
        kwargs["item_id"] = args.item
    if args.login:
        kwargs["auto_login"] = True
    if args.phone:
        kwargs["phone"] = args.phone
    if args.password:
        kwargs["password"] = args.password
    if args.url:
        kwargs["url"] = args.url
    if args.crawl_mode:
        kwargs["crawl_mode"] = args.crawl_mode
    if args.max_pages is not None:
        kwargs["max_pages"] = args.max_pages
    if args.max_depth is not None:
        kwargs["max_depth"] = args.max_depth
    return kwargs


def print_entries():
    print("\n可用爬取入口:\n")
    print(f"  {'键':<12} {'平台':<16} {'登录':<6} 入口地址")
    print("  " + "-" * 78)
    for entry in ENTRIES.values():
        auth = "需要" if entry.requires_auth else "免登录"
        print(f"  {entry.key:<12} {entry.display_name:<16} {auth:<6} {entry.entry_url}")
        if entry.description:
            print(f"  {'':12} {entry.description}")
    print()


def list_projects(args):
    entry = get_entry(args.entry)
    method = getattr(entry.crawler_class, "list_projects", None)
    if method is None:
        raise SystemExit(f"入口 '{entry.key}' 不支持项目列表（该平台无需选择项目）")
    projects = method()
    print(f"\n平台: {entry.display_name}，共 {len(projects)} 个项目\n")
    print(f"  {'项目ID':<12} 项目名称")
    print("  " + "-" * 50)
    for project in projects:
        print(f"  {project['item_id']:<12} {project['item_name']}")
    print("\n使用 --item <项目ID> 爬取指定项目")


def list_documents(args):
    save_dir = args.out or os.path.join("downloads", args.entry)
    crawler = create_crawler(
        args.entry, save_dir=save_dir, **build_crawler_kwargs(args)
    )
    stubs = crawler.list_documents()
    category_counts = Counter(stub.category for stub in stubs)
    print(f"\n平台: {crawler.display_name}")
    print(f"文档总数: {len(stubs)}，分类数: {len(category_counts)}\n")
    print(f"  {'数量':>5}  分类")
    print("  " + "-" * 60)
    for category, count in category_counts.most_common():
        print(f"  {count:>5}  {category}")


def run_crawl(args):
    crawler = create_crawler(
        args.entry,
        save_dir=default_output_dir(args),
        progress_callback=on_progress,
        **build_crawler_kwargs(args),
    )
    summary = crawler.crawl(limit=args.limit)

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


def on_progress(current, total, message):
    percent = int(current / total * 100) if total else 0
    print(f"[{percent:3d}%] {message}")


def main():
    parser = argparse.ArgumentParser(
        description="多平台知识库爬取：按平台分类选择入口进行爬取下载"
    )
    parser.add_argument(
        "--entry",
        choices=sorted(ENTRIES),
        help="平台分类键，见 --list-entries",
    )
    parser.add_argument(
        "--list-entries", action="store_true", help="列出全部可用入口"
    )
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="（showdoc）登录并列出账号下的项目",
    )
    parser.add_argument(
        "--list-documents",
        action="store_true",
        help="仅列出文档分类与数量，不执行爬取落盘",
    )
    parser.add_argument(
        "--item", default=None, help="（showdoc）项目 ID（item_id）"
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="（showdoc）爬取前先登录，用于访问受保护项目",
    )
    parser.add_argument(
        "--phone", default=None, help="（cyb）登录手机号（默认读 .env 的 CYB_PHONE）"
    )
    parser.add_argument(
        "--password", default=None, help="（cyb）登录密码（默认读 .env 的 CYB_PASSWORD）"
    )
    parser.add_argument(
        "--url", default=None, help="（web）要抓取的网页 URL"
    )
    parser.add_argument(
        "--crawl-mode",
        choices=("page", "site"),
        default=None,
        help="（web）page 抓当前页；site 抓站内 sitemap 或深度链接",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="（web site）最多抓取页面数，0 表示不限制（默认 0）",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="（web site 无 sitemap 时）最大遍历深度，0 表示不限制（默认 0）",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="试跑模式：只处理前 N 条（默认全量）"
    )
    parser.add_argument(
        "--page-size", type=int, default=0, help="分页大小（0 表示使用平台默认值）"
    )
    parser.add_argument("--out", default=None, help="输出目录（默认 downloads/<入口键>）")
    parser.add_argument(
        "--pipeline", choices=VALID_PIPELINES, default=None, help="内容清洗引擎"
    )
    args = parser.parse_args()

    if args.list_entries:
        print_entries()
        return

    if not args.entry:
        parser.error("必须通过 --entry 指定平台分类键，或使用 --list-entries 查看")

    if args.list_projects:
        list_projects(args)
    elif args.list_documents:
        list_documents(args)
    else:
        if args.entry == "showdoc" and not args.item:
            parser.error("showdoc 爬取需要 --item 指定项目 ID"
                         "（可用 --list-projects 查看项目列表）")
        if args.entry == "web" and not args.url:
            parser.error("web 爬取需要 --url 指定网页地址")
        run_crawl(args)


if __name__ == "__main__":
    main()
