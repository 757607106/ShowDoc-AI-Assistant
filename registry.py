"""入口注册表：分类键 → 爬虫实现。新增平台只需在此登记一行。"""
import inspect
from dataclasses import dataclass

from crawlers.cyb import CYBCrawler
from crawlers.showdoc import ShowDocCrawler
from crawlers.tiantong import TiantongCrawler


@dataclass(frozen=True)
class CrawlerEntry:
    key: str
    crawler_class: type
    display_name: str
    entry_url: str
    requires_auth: bool
    description: str = ""


ENTRIES = {
    "tiantong": CrawlerEntry(
        key="tiantong",
        crawler_class=TiantongCrawler,
        display_name="天通资源管理中心",
        entry_url="http://117.172.29.67:6067/knowledge",
        requires_auth=False,
        description="免登录分页 API；含分类、关键词、作者、附件等完整元数据",
    ),
    "showdoc": CrawlerEntry(
        key="showdoc",
        crawler_class=ShowDocCrawler,
        display_name="ShowDoc",
        entry_url="https://yunhelp.gmgrasp.com.cn",
        requires_auth=False,
        description="文档站；公开项目匿名可爬（--item 指定项目 ID），"
        "--login 后可列出并访问账号下全部项目",
    ),
    "cyb": CrawlerEntry(
        key="cyb",
        crawler_class=CYBCrawler,
        display_name="管家婆云辉煌创业版",
        entry_url="https://new.yuncyb.com",
        requires_auth=True,
        description="验证码 + 手机号登录；使用教程（含视频）与常见问题 FAQ，"
        "分类为 使用教程/<模块> 与 常见问题/<业务类型>",
    ),
}


def get_entry(key):
    entry = ENTRIES.get(key)
    if entry is None:
        valid = ", ".join(sorted(ENTRIES))
        raise KeyError(f"未知入口 '{key}'，可用入口: {valid}")
    return entry


def create_crawler(key, save_dir, **kwargs):
    """按注册键创建爬虫实例，自动忽略该平台不支持的参数。"""
    entry = get_entry(key)
    accepted = set(inspect.signature(entry.crawler_class.__init__).parameters)
    unsupported = sorted(k for k in kwargs if k not in accepted)
    if unsupported:
        print(f"ℹ️ 参数 {', '.join(unsupported)} 不适用于 {entry.display_name}，已忽略")
    usable = {k: v for k, v in kwargs.items() if k in accepted}
    return entry.crawler_class(save_dir=save_dir, **usable)
